"""Get current date and time."""

from datetime import UTC, datetime

from nanobot.tools.decorator import tool


@tool(description="Get the current date and time in ISO format (UTC).")
async def get_datetime() -> str:
    """Return current UTC datetime."""
    return datetime.now(UTC).isoformat()
