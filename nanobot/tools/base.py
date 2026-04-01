"""
Base class and types for agent tools.

Provides BaseTool ABC and ToolResult for class-based tools.
Supports optional per-tool config: model override
(Option 2 from workflow_model_switching.md).
"""

from abc import ABC, abstractmethod
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolConfig:
    """
    Per-tool configuration for model override

    Used by tools that make LLM calls internally (e.g. llm_completion,
    describe_image) to use a different model or inject step-specific guidance.
    """

    model: str | None = None


# Context var for current tool's config during execution (set by NanobotToolAdapter)
_current_tool_config: ContextVar[ToolConfig | None] = ContextVar("current_tool_config", default=None)


def get_current_tool_config() -> ToolConfig | None:
    """
    Get the current tool's config during execution.

    Tools that make LLM calls can use this to respect model override
    from the @tool decorator.
    """
    return _current_tool_config.get()


def set_tool_config_context(cfg: ToolConfig | None) -> Any:
    """
    Set the current tool config for the duration of tool execution.
    Returns a token to pass to reset_tool_config_context when done.
    """
    return _current_tool_config.set(cfg)


def reset_tool_config_context(token: Any) -> None:
    """Reset tool config context after tool execution."""
    _current_tool_config.reset(token)


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    data: str | dict[str, Any]
    error: str | None = None

    def to_string(self) -> str:
        """Return a string representation for the LLM."""
        if not self.success and self.error:
            return f"Error: {self.error}"
        if isinstance(self.data, str):
            return self.data
        import json

        return json.dumps(self.data)


class BaseTool(ABC):
    """
    Abstract base class for stateful or complex tools.
    For simple tools, use the @tool decorator instead.

    Subclasses may override tool_config to provide model
    for tools that make LLM calls internally.
    """

    @property
    def tool_config(self) -> ToolConfig | None:
        """Optional per-tool config (model override)."""
        return None

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used in function calls."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """
        Execute the tool with given parameters.

        Returns:
            String result for the LLM (or ToolResult.to_string()).
        """
        ...

    def to_schema(self) -> dict[str, Any]:
        """OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters.get("properties", {}),
                    "required": self.parameters.get("required", []),
                },
            },
        }
