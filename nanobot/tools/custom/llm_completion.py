"""Direct LLM completion tool (no agent loop)."""

from nanobot.tools.decorator import tool


@tool(description="Get a direct completion from the LLM for a short prompt. Use for quick facts or rewrites.")
async def llm_completion(prompt: str) -> str:
    """
    Call the LLM once with the given prompt and return the response.
    Does not use the agent loop or other tools.
    """
    # Actual implementation will be wired to the provider in the agent layer.
    # For now return a placeholder; the agent loop will inject the real provider.
    return f"[LLM would complete: {prompt[:50]}...]"
