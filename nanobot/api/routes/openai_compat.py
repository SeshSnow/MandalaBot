"""
OpenAI-compatible API routes.

Provides /v1/chat/completions, /v1/models, and /health endpoints
that are always present regardless of Mandala config.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from nanobot.api.utils.sse_utils import SSE_STREAM_HEADERS

router = APIRouter()

_API_SESSION_KEY = "api:default"
_API_CHAT_ID = "default"


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _error_json(status: int, message: str, err_type: str = "invalid_request_error") -> JSONResponse:
    return JSONResponse(
        {"error": {"message": message, "type": err_type, "code": status}},
        status_code=status,
    )


def _chat_completion_chunk(content: str, model: str, finish_reason: str | None = None) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason,
            }
        ],
    }


def _chat_completion_response(content: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
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
    if value is None:
        return ""
    if hasattr(value, "content"):
        return str(getattr(value, "content") or "")
    return str(value)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(request: Request) -> JSONResponse | StreamingResponse:
    """OpenAI-compatible chat completions endpoint."""
    try:
        body = await request.json()
    except Exception:
        return _error_json(400, "Invalid JSON body")

    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 1:
        return _error_json(400, "Only a single user message is supported")

    message = messages[0]
    if not isinstance(message, dict) or message.get("role") != "user":
        return _error_json(400, "Only a single user message is supported")

    user_content = message.get("content", "")
    if isinstance(user_content, list):
        user_content = " ".join(
            part.get("text", "") for part in user_content if part.get("type") == "text"
        )

    agent_loop = request.app.state.agent_loop
    timeout_s: float = request.app.state.request_timeout
    model_name: str = request.app.state.model_name

    if (requested_model := body.get("model")) and requested_model != model_name:
        return _error_json(400, f"Only configured model '{model_name}' is available")

    stream = body.get("stream", False)

    logger.info("API request session_key={} stream={} content={}", _API_SESSION_KEY, stream, user_content[:80])

    if stream:
        return await _streaming_response(agent_loop, user_content, model_name, timeout_s)

    return await _sync_response(agent_loop, user_content, model_name, timeout_s)


async def _sync_response(agent_loop, user_content: str, model_name: str, timeout_s: float) -> JSONResponse:
    _FALLBACK = "I've completed processing but have no response to give."
    try:
        response = await asyncio.wait_for(
            agent_loop.process_direct(
                content=user_content,
                session_key=_API_SESSION_KEY,
                channel="api",
                chat_id=_API_CHAT_ID,
            ),
            timeout=timeout_s,
        )
        response_text = _response_text(response)

        if not response_text or not response_text.strip():
            logger.warning("Empty response for session {}, retrying", _API_SESSION_KEY)
            retry_response = await asyncio.wait_for(
                agent_loop.process_direct(
                    content=user_content,
                    session_key=_API_SESSION_KEY,
                    channel="api",
                    chat_id=_API_CHAT_ID,
                ),
                timeout=timeout_s,
            )
            response_text = _response_text(retry_response)
            if not response_text or not response_text.strip():
                response_text = _FALLBACK

    except asyncio.TimeoutError:
        return _error_json(504, f"Request timed out after {timeout_s}s")
    except Exception:
        logger.exception("Error processing request for session {}", _API_SESSION_KEY)
        return _error_json(500, "Internal server error", err_type="server_error")

    return JSONResponse(_chat_completion_response(response_text, model_name))


async def _streaming_response(agent_loop, user_content: str, model_name: str, timeout_s: float) -> StreamingResponse:
    import json

    async def generate():
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        collected: list[str] = []
        stream_done = asyncio.Event()

        async def on_stream(delta: str) -> None:
            collected.append(delta)
            await queue.put(delta)

        try:
            async def _run_agent():
                try:
                    return await asyncio.wait_for(
                        agent_loop.process_direct(
                            content=user_content,
                            session_key=_API_SESSION_KEY,
                            channel="api",
                            chat_id=_API_CHAT_ID,
                            on_stream=on_stream,
                        ),
                        timeout=timeout_s,
                    )
                finally:
                    stream_done.set()
                    await queue.put(None)

            run_task = asyncio.create_task(_run_agent())

            # Emit stream chunks as soon as they arrive from agent_loop.on_stream.
            while True:
                delta = await queue.get()
                if delta is None:
                    break
                chunk = _chat_completion_chunk(delta, model_name)
                yield f"data: {json.dumps(chunk)}\n\n"

            response = await run_task

            # If streaming didn't fire (non-streaming provider), send full content now.
            if not collected:
                full_text = _response_text(response)
                if full_text:
                    chunk = _chat_completion_chunk(full_text, model_name)
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Final chunk with finish_reason.
            final_chunk = _chat_completion_chunk("", model_name, finish_reason="stop")
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        except asyncio.TimeoutError:
            err = {"error": {"message": f"Request timed out after {timeout_s}s", "type": "timeout"}}
            yield f"data: {json.dumps(err)}\n\n"
        except Exception:
            logger.exception("Streaming error for session {}", _API_SESSION_KEY)
            err = {"error": {"message": "Internal server error", "type": "server_error"}}
            yield f"data: {json.dumps(err)}\n\n"
        finally:
            if not stream_done.is_set():
                stream_done.set()
                await queue.put(None)

    # generate() is an async generator — wrap it properly
    async def _gen():
        async for chunk in generate():
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers=SSE_STREAM_HEADERS,
    )


@router.get("/v1/models", response_model=None)
async def list_models(request: Request) -> JSONResponse:
    """List available models."""
    model_name = request.app.state.model_name
    return JSONResponse({
        "object": "list",
        "data": [
            {
                "id": model_name,
                "object": "model",
                "created": 0,
                "owned_by": "nanobot",
            }
        ],
    })


@router.get("/health", response_model=None)
async def health() -> JSONResponse:
    """Health check."""
    return JSONResponse({"status": "ok"})
