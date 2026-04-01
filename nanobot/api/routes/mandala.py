"""
Mandala business routes — mounted under /api/v1/ when Mandala is enabled.

Aggregates all sub-routers: agent chat, tools, shop, brand, billing, research, SEO.
Sub-routers are imported lazily so missing optional dependencies don't crash startup.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from nanobot.api.integration import process_message, process_message_stream
from nanobot.api.utils.sse_utils import (
    send_complete_event,
    send_data_event,
    send_error_event,
    send_progress_event,
    streaming_sse_response,
)


# ---------------------------------------------------------------------------
# Dependency: tenant resolver
# ---------------------------------------------------------------------------

async def get_shop_domain(
    x_shopify_shop_domain: Annotated[str | None, Header(alias="X-Shopify-Shop-Domain")] = None,
) -> str:
    """Resolve current tenant from X-Shopify-Shop-Domain header."""
    if not x_shopify_shop_domain or not str(x_shopify_shop_domain).strip():
        raise HTTPException(status_code=400, detail="X-Shopify-Shop-Domain header is required")
    return str(x_shopify_shop_domain).strip()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32_000)
    conversation_id: str | None = Field(None)


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    role: str = "assistant"


# ---------------------------------------------------------------------------
# Agent routes
# ---------------------------------------------------------------------------

agent_router = APIRouter(prefix="/agent", tags=["agent"])


def _agent_event_to_sse(ev: dict) -> str | None:
    t = ev.get("type", "")
    if t == "thinking":
        return send_progress_event(step="thinking", progress=10)
    if t == "tool_call":
        return send_progress_event(step="tool_call", tool=ev.get("tool") or "")
    if t == "tool_result":
        return send_progress_event(
            step="tool_result",
            tool=ev.get("tool") or "",
            success=ev.get("success", False),
            error=ev.get("error"),
        )
    if t == "response":
        return send_data_event("response", content=ev.get("content", ""))
    if t == "done":
        return send_complete_event(message="Complete", conversation_id=ev.get("conversation_id"))
    if t == "error":
        return send_error_event(ev.get("content", "Unknown error"))
    if t == "heartbeat":
        return send_progress_event(step="heartbeat")
    return None


@agent_router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    shop_domain: str = Depends(get_shop_domain),
):
    """Stream agent response as Server-Sent Events."""
    agent_loop = request.app.state.agent_loop
    cid = body.conversation_id or uuid.uuid4().hex
    session_key = f"http:{cid}"
    tenant_context = {"shop_domain": shop_domain}

    async def generate():
        try:
            async for event, is_heartbeat in process_message_stream(
                agent_loop,
                body.message,
                session_key,
                tenant_context=tenant_context,
            ):
                ev = {"type": "heartbeat"} if is_heartbeat else event
                if ev is not None:
                    if ev.get("type") == "done":
                        ev = {**ev, "conversation_id": cid}
                    chunk = _agent_event_to_sse(ev)
                    if chunk:
                        yield chunk
        except RuntimeError as e:
            yield send_error_event(str(e))
            yield send_complete_event()

    return streaming_sse_response(generate())


@agent_router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(
    body: ChatRequest,
    request: Request,
    shop_domain: str = Depends(get_shop_domain),
) -> ChatResponse:
    """Synchronous chat — use for webhooks/background jobs."""
    agent_loop = request.app.state.agent_loop
    cid = body.conversation_id or uuid.uuid4().hex
    session_key = f"http:{cid}"
    tenant_context = {"shop_domain": shop_domain}

    try:
        response_text = await process_message(
            agent_loop,
            body.message,
            session_key,
            tenant_context=tenant_context,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return ChatResponse(conversation_id=cid, message=response_text, role="assistant")


# ---------------------------------------------------------------------------
# Tools list route
# ---------------------------------------------------------------------------

tools_router = APIRouter(prefix="/tools", tags=["tools"])


@tools_router.get("")
async def list_tools(request: Request):
    """List all registered tools."""
    agent_loop = request.app.state.agent_loop
    return {"tools": agent_loop.tools.get_definitions()}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Factory: aggregate all sub-routers
# ---------------------------------------------------------------------------

def create_mandala_router() -> APIRouter:
    """Build and return the combined Mandala API router."""
    router = APIRouter()

    # Core routes (always included)
    router.include_router(health_router)
    router.include_router(agent_router)
    router.include_router(tools_router)

    # Optional feature routes — imported lazily; skip if deps missing
    _try_include(router, "nanobot.api.routes.mandala_shop", "shop_router", prefix="/shop", tags=["shop"])
    _try_include(router, "nanobot.api.routes.mandala_brand", "brand_router", prefix="/brand", tags=["brand"])
    _try_include(router, "nanobot.api.routes.mandala_billing", "billing_router", prefix="/billing", tags=["billing"])
    _try_include(router, "nanobot.api.routes.mandala_research", "research_router", prefix="/research", tags=["research"])
    _try_include(router, "nanobot.api.routes.mandala_seo", "seo_router", prefix="/seo", tags=["seo"])
    _try_include(router, "nanobot.api.routes.mandala_attachments", "attachments_router", prefix="/attachments", tags=["attachments"])

    return router


def _try_include(router: APIRouter, module: str, attr: str, **kwargs) -> None:
    try:
        import importlib
        mod = importlib.import_module(module)
        sub_router = getattr(mod, attr)
        router.include_router(sub_router, **kwargs)
    except (ImportError, AttributeError) as e:
        logger.debug("Skipping optional route module {}: {}", module, e)
