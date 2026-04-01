"""
SSE utilities for streaming endpoints.

Event contract (backend → frontend):
- progress: {"type": "progress", "step": "<id>", "progress": N?, **metadata}
- data:     {"type": "<event_type>", **kwargs}
- complete: {"type": "complete", "message": "...?", **kwargs}
- error:    {"type": "error", "error": "..."}
"""

import json
from collections.abc import AsyncIterator, Iterator
from datetime import date, datetime
from typing import Any, Union

from fastapi.responses import StreamingResponse

SSE_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def streaming_sse_response(
    stream: Union[AsyncIterator[str], Iterator[str]],
) -> StreamingResponse:
    """Return a StreamingResponse for SSE with standard headers."""
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers=SSE_STREAM_HEADERS,
    )


def _to_serializable(obj: Any) -> Any:
    """Recursively convert date/datetime to ISO strings for JSON serialization."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_to_serializable(v) for v in obj)
    if isinstance(obj, set):
        return [_to_serializable(v) for v in obj]
    return obj


def send_progress_event(
    step: str | None = None,
    progress: int | None = None,
    **metadata: Any,
) -> str:
    """Create a progress SSE event string."""
    data: dict[str, Any] = {"type": "progress", **metadata}
    if step is not None:
        data["step"] = step
    if progress is not None:
        data["progress"] = progress
    return f"data: {json.dumps(_to_serializable(data), default=str)}\n\n"


def send_data_event(event_type: str, **kwargs: Any) -> str:
    """Create a data SSE event string."""
    data: dict[str, Any] = {"type": event_type, **kwargs}
    return f"data: {json.dumps(_to_serializable(data), default=str)}\n\n"


def send_results_event(results: Any, **kwargs: Any) -> str:
    """Create a standardized results SSE event string."""
    data: dict[str, Any] = {"type": "data", "results": results, **kwargs}
    return f"data: {json.dumps(_to_serializable(data), default=str)}\n\n"


def send_error_event(error: str) -> str:
    """Create an error SSE event string."""
    data = {"type": "error", "error": error}
    return f"data: {json.dumps(data)}\n\n"


def send_complete_event(message: str | None = None, **kwargs: Any) -> str:
    """Create a completion SSE event string."""
    data: dict[str, Any] = {"type": "complete", **kwargs}
    if message is not None:
        data["message"] = message
    return f"data: {json.dumps(_to_serializable(data), default=str)}\n\n"
