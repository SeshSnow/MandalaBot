"""
Module-level AgentLoop reference — set at server startup.

Services that need to call the agent (e.g. article_generator) import from here
instead of receiving the loop as a parameter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nanobot.agent.loop import AgentLoop

_agent_loop: "AgentLoop | None" = None


def set_agent_loop(loop: "AgentLoop") -> None:
    """Store the agent loop. Called once during server startup."""
    global _agent_loop
    _agent_loop = loop


def get_agent_loop() -> "AgentLoop":
    """Return the agent loop. Raises if not yet initialized."""
    if _agent_loop is None:
        raise RuntimeError("AgentLoop not initialized. Ensure Mandala server started correctly.")
    return _agent_loop
