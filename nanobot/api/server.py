"""OpenAI-compatible HTTP API server for nanobot (FastAPI).

Provides /v1/chat/completions and /v1/models endpoints.
Supports multi-turn conversations via conversation_id and tenant
isolation via X-Shopify-Shop-Domain header.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

from nanobot.api.middleware import TenantMiddleware

API_CHAT_ID = "default"


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[dict[str, Any]]
    stream: bool = False
    conversation_id: str | None = Field(
        None,
        description="Pass back to continue a conversation. Omit or null for a new conversation.",
    )


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _error_response(status: int, message: str, err_type: str = "invalid_request_error") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"message": message, "type": err_type, "code": status}},
    )


def _chat_completion_response(
    content: str,
    model: str,
    conversation_id: str,
) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "conversation_id": conversation_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _response_text(value: Any) -> str:
    """Normalize process_direct output to plain assistant text."""
    if value is None:
        return ""
    if hasattr(value, "content"):
        return str(getattr(value, "content") or "")
    return str(value)


# ---------------------------------------------------------------------------
# Lifespan (replaces aiohttp on_startup / on_cleanup)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect MCP servers on startup, disconnect on shutdown."""
    agent_loop = app.state.agent_loop
    await agent_loop._connect_mcp()
    yield
    await agent_loop.close_mcp()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(
    agent_loop,
    model_name: str = "nanobot",
    request_timeout: float = 120.0,
) -> FastAPI:
    """Create the FastAPI application.

    Args:
        agent_loop: An initialized AgentLoop instance.
        model_name: Model name reported in responses.
        request_timeout: Per-request timeout in seconds.
    """
    app = FastAPI(
        title="nanobot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # -- shared state --
    app.state.agent_loop = agent_loop
    app.state.model_name = model_name
    app.state.request_timeout = request_timeout
    app.state.session_lock = asyncio.Lock()

    # -- middleware (order matters: last added runs first) --
    cors_origins = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware)

    # -- routes --
    app.add_api_route("/health", _handle_health, methods=["GET"])
    app.add_api_route("/v1/models", _handle_models, methods=["GET"])
    app.add_api_route("/v1/chat/completions", _handle_chat_completions, methods=["POST"])

    return app


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

async def _handle_health(request: Request) -> dict[str, str]:
    """GET /health"""
    return {"status": "ok"}


async def _handle_models(request: Request) -> dict[str, Any]:
    """GET /v1/models"""
    model_name = request.app.state.model_name
    return {
        "object": "list",
        "data": [
            {
                "id": model_name,
                "object": "model",
                "created": 0,
                "owned_by": "nanobot",
            }
        ],
    }


async def _handle_chat_completions(request: Request) -> JSONResponse:
    """POST /v1/chat/completions — OpenAI-compatible chat endpoint.

    Supports multi-turn conversations: include ``conversation_id`` in the
    request body to continue an existing conversation.  The same ID is
    returned in the response so the front-end can pass it back.
    """
    # --- Parse body ---
    try:
        body_raw = await request.json()
        body = ChatCompletionRequest.model_validate(body_raw)
    except Exception:
        return _error_response(400, "Invalid JSON body or missing required fields")

    if not body.messages or len(body.messages) < 1:
        return _error_response(400, "At least one message is required")

    if body.stream:
        return _error_response(400, "stream=true is not supported yet. Set stream=false or omit it.")

    # Extract last user message
    last_msg = body.messages[-1]
    if not isinstance(last_msg, dict) or last_msg.get("role") != "user":
        return _error_response(400, "Last message must have role 'user'")

    user_content = last_msg.get("content", "")
    if isinstance(user_content, list):
        user_content = " ".join(
            part.get("text", "") for part in user_content if part.get("type") == "text"
        )

    # --- Conversation / session mapping ---
    conversation_id = body.conversation_id or uuid.uuid4().hex
    session_key = f"api:{conversation_id}"

    agent_loop = request.app.state.agent_loop
    timeout_s: float = request.app.state.request_timeout
    model_name: str = request.app.state.model_name

    if body.model and body.model != model_name:
        return _error_response(400, f"Only configured model '{model_name}' is available")

    session_lock: asyncio.Lock = request.app.state.session_lock

    logger.info(
        "API request session_key={} conversation_id={} content={}",
        session_key,
        conversation_id,
        user_content[:80],
    )

    _FALLBACK = "I've completed processing but have no response to give."

    try:
        async with session_lock:
            try:
                response = await asyncio.wait_for(
                    agent_loop.process_direct(
                        content=user_content,
                        session_key=session_key,
                        channel="api",
                        chat_id=API_CHAT_ID,
                    ),
                    timeout=timeout_s,
                )
                response_text = _response_text(response)

                if not response_text or not response_text.strip():
                    logger.warning("Empty response for session {}, retrying", session_key)
                    retry_response = await asyncio.wait_for(
                        agent_loop.process_direct(
                            content=user_content,
                            session_key=session_key,
                            channel="api",
                            chat_id=API_CHAT_ID,
                        ),
                        timeout=timeout_s,
                    )
                    response_text = _response_text(retry_response)
                    if not response_text or not response_text.strip():
                        logger.warning("Empty response after retry for session {}, using fallback", session_key)
                        response_text = _FALLBACK

            except asyncio.TimeoutError:
                return _error_response(504, f"Request timed out after {timeout_s}s")
            except Exception:
                logger.exception("Error processing request for session {}", session_key)
                return _error_response(500, "Internal server error", err_type="server_error")
    except Exception:
        logger.exception("Unexpected API lock error for session {}", session_key)
        return _error_response(500, "Internal server error", err_type="server_error")

    return JSONResponse(
        content=_chat_completion_response(response_text, model_name, conversation_id),
    )
