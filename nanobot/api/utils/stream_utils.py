"""
Stream utilities for SSE and long-running async iterators.

Provides iter_with_heartbeat() so consumers can yield heartbeats while waiting
for the next event, keeping the connection alive and ensuring final events are delivered.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import TypeVar

T = TypeVar("T")

_DONE = object()  # sentinel


async def iter_with_heartbeat(
    stream: AsyncIterator[T],
    heartbeat_interval_sec: float,
) -> AsyncIterator[tuple[T | None, bool]]:
    """
    Consume an async stream and yield (event, is_heartbeat).

    - When an event is available: yield (event, False).
    - When heartbeat_interval_sec passes with no event: yield (None, True).

    Keeps the SSE connection alive through proxies and load balancers.
    """
    queue: asyncio.Queue[T | object] = asyncio.Queue()

    async def feed() -> None:
        try:
            async for event in stream:
                await queue.put(event)
        finally:
            await queue.put(_DONE)

    task = asyncio.create_task(feed())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval_sec)
            except asyncio.TimeoutError:
                yield None, True
                continue
            if event is _DONE:
                break
            yield event, False
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
