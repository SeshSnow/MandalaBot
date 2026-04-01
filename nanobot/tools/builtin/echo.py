"""Echo tool for testing."""

from nanobot.tools.decorator import tool


@tool(description="Echo back the input message. Use for testing.")
async def echo(message: str) -> str:
    """Return the same message that was sent."""
    return message
