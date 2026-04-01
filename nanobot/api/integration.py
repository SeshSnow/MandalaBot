"""
Mandala agent integration layer.

Provides:
- NanobotToolAdapter  — bridges Mandala BaseTool → nanobot's Tool interface
- EventEmittingToolWrapper — wraps built-in nanobot tools for SSE event emission
- ContextVar-based event callback (per-request isolation, safe for concurrency)
- process_message() / process_message_stream() — called by FastAPI route handlers
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from loguru import logger
from nanobot.agent.loop import AgentLoop
from nanobot.agent.tools.base import Tool as NanobotTool
from nanobot.bus.events import InboundMessage
from nanobot.api.utils.stream_utils import iter_with_heartbeat

# ---------------------------------------------------------------------------
# Event callback — ContextVar for per-request isolation
# ---------------------------------------------------------------------------

_event_callback_var: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "event_callback", default=None
)


def set_event_callback(callback: Callable[[dict[str, Any]], None] | None) -> None:
    _event_callback_var.set(callback)


def emit_event(event: dict[str, Any]) -> None:
    cb = _event_callback_var.get()
    if cb:
        cb(event)


# ---------------------------------------------------------------------------
# Tool wrappers
# ---------------------------------------------------------------------------

class NanobotToolAdapter(NanobotTool):
    """
    Adapts a Mandala BaseTool to nanobot's Tool interface.
    Emits SSE events on tool_call and tool_result.
    """

    def __init__(self, our_tool) -> None:
        self._tool = our_tool

    @property
    def name(self) -> str:
        return self._tool.name

    @property
    def description(self) -> str:
        return self._tool.description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._tool.parameters

    async def execute(self, **kwargs: Any) -> str:
        emit_event({"type": "tool_call", "tool": self._tool.name, "arguments": kwargs})

        # Set per-tool config context (for model override in LLM-calling tools)
        cfg = getattr(self._tool, "tool_config", None)
        try:
            from nanobot.tools.base import set_tool_config_context
            set_tool_config_context(cfg)
        except ImportError:
            pass

        try:
            result = await self._tool.execute(**kwargs)
            if isinstance(result, dict):
                event_success = result.get("success", True)
                try:
                    result_str = json.dumps(result, default=str)
                except (TypeError, ValueError):
                    result_str = str(result)
            else:
                event_success = True
                result_str = result if isinstance(result, str) else str(result)

            result_truncated = result_str[:500] if len(result_str) > 500 else result_str
            event_payload: dict[str, Any] = {
                "type": "tool_result",
                "tool": self._tool.name,
                "success": event_success,
                "result": result_truncated,
            }
            # Pass through structured save_topic_cluster result for the stream consumer
            if (
                self._tool.name == "save_topic_cluster"
                and isinstance(result, dict)
                and result.get("success") is True
                and "cluster_id" in result
            ):
                event_payload["saved_cluster"] = {
                    "cluster_id": result["cluster_id"],
                    "cluster_structure": result.get("cluster_structure"),
                }
            emit_event(event_payload)

            return json.dumps(result, default=str) if isinstance(result, dict) else result
        except Exception as e:
            emit_event({"type": "tool_result", "tool": self._tool.name, "success": False, "error": str(e)})
            raise

    def to_schema(self) -> dict[str, Any]:
        return self._tool.to_schema()


class EventEmittingToolWrapper(NanobotTool):
    """Wraps any nanobot built-in tool to emit SSE events."""

    def __init__(self, original_tool: NanobotTool) -> None:
        self._original = original_tool

    @property
    def name(self) -> str:
        return self._original.name

    @property
    def description(self) -> str:
        return self._original.description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._original.parameters

    async def execute(self, **kwargs: Any) -> str:
        emit_event({"type": "tool_call", "tool": self._original.name, "arguments": kwargs})
        try:
            result = await self._original.execute(**kwargs)
            result_str = str(result) if result else ""
            emit_event({
                "type": "tool_result",
                "tool": self._original.name,
                "success": True,
                "result": result_str[:500] if len(result_str) > 500 else result_str,
            })
            return result
        except Exception as e:
            emit_event({"type": "tool_result", "tool": self._original.name, "success": False, "error": str(e)})
            raise

    def to_schema(self) -> dict[str, Any]:
        return self._original.to_schema()


# ---------------------------------------------------------------------------
# Message processing
# ---------------------------------------------------------------------------

async def process_message(
    agent_loop: AgentLoop,
    message: str,
    session_key: str,
    tenant_context: dict[str, Any] | None = None,
    model: str | None = None,
    timeout: float | None = None,
    skill_hint: str | None = None,
) -> str:
    """
    Process a message and return the final response text (blocking).

    Args:
        agent_loop: The AgentLoop instance to use.
        message: User message text.
        session_key: Session key in format "channel:chat_id".
        tenant_context: Optional tenant state dict (shop_domain, store_config, etc.).
        model: Optional model override.
        timeout: Optional timeout in seconds.
        skill_hint: Optional skill name to prepend as instruction.
    """
    _apply_tenant_context(tenant_context)
    try:
        channel, chat_id = _parse_session_key(session_key)
        if skill_hint:
            message = f"Execute the {skill_hint} skill. {message}"

        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=message)

        async def _run() -> str:
            response = await agent_loop._process_message(msg)
            return response.content if response else ""

        if timeout:
            return await asyncio.wait_for(_run(), timeout=timeout)
        return await _run()
    finally:
        _clear_tenant_context(tenant_context)


async def process_message_stream(
    agent_loop: AgentLoop,
    message: str,
    session_key: str,
    tenant_context: dict[str, Any] | None = None,
    model: str | None = None,
    skill_hint: str | None = None,
) -> AsyncIterator[tuple[dict[str, Any] | None, bool]]:
    """
    Process a message with streaming events.

    Yields (event, is_heartbeat) tuples:
    - is_heartbeat=True  → event is None (keep-alive)
    - is_heartbeat=False → event is dict with type: thinking/tool_call/tool_result/response/done/error
    """
    channel, chat_id = _parse_session_key(session_key)
    if skill_hint:
        message = f"Execute the {skill_hint} skill. {message}"

    event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    def queue_event(event: dict[str, Any]) -> None:
        try:
            event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    async def _raw_event_stream() -> AsyncIterator[dict[str, Any]]:
        yield {"type": "thinking", "content": "Processing your message..."}
        set_event_callback(queue_event)

        async def run_agent() -> str:
            _apply_tenant_context(tenant_context)
            try:
                msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=message)
                response = await agent_loop._process_message(msg)
                return response.content if response else ""
            finally:
                _clear_tenant_context(tenant_context)

        agent_task = asyncio.create_task(run_agent())
        try:
            while not agent_task.done():
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield event
                except TimeoutError:
                    continue

            while not event_queue.empty():
                yield event_queue.get_nowait()

            response_text = await agent_task
            yield {"type": "response", "content": response_text}
            yield {"type": "done"}
        except Exception as e:
            yield {"type": "error", "content": str(e)}
            yield {"type": "done"}
        finally:
            set_event_callback(None)

    async for event, is_heartbeat in iter_with_heartbeat(_raw_event_stream(), 15.0):
        yield event, is_heartbeat


# ---------------------------------------------------------------------------
# Tenant context helpers
# ---------------------------------------------------------------------------

def _parse_session_key(session_key: str) -> tuple[str, str]:
    if ":" in session_key:
        channel, chat_id = session_key.split(":", 1)
    else:
        channel, chat_id = "http", session_key
    return channel, chat_id


def _apply_tenant_context(tenant_context: dict[str, Any] | None) -> None:
    if not tenant_context:
        return
    store_config = tenant_context.get("store_config")
    if store_config is not None:
        try:
            from nanobot.tenant.context import set_store_config
            set_store_config(store_config)
        except ImportError:
            pass


def _clear_tenant_context(tenant_context: dict[str, Any] | None) -> None:
    if not tenant_context:
        return
    try:
        from nanobot.tenant.context import set_store_config
        set_store_config(None)
    except ImportError:
        pass
