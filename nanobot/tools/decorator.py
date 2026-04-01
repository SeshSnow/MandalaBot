"""
@tool decorator for defining tools from functions.

Auto-generates JSON Schema from type hints and Pydantic models.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, get_origin, get_type_hints

from pydantic import BaseModel

from tools.base import BaseTool, ToolResult


def _pydantic_model_to_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic model to JSON Schema for tool parameters."""
    schema = model.model_json_schema()
    # Remove title/extra for OpenAI format; keep properties and required
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }


def _annotation_to_json_schema(name: str, annotation: Any, default: Any = inspect.Parameter.empty) -> tuple[dict, bool]:
    """Convert a simple type hint to a JSON Schema property. Returns (property_schema, required)."""
    required = default is inspect.Parameter.empty
    if hasattr(annotation, "model_json_schema") and isinstance(annotation, type) and issubclass(annotation, BaseModel):
        schema = annotation.model_json_schema()
        return schema, required
    if annotation is str:
        return {"type": "string", "description": name}, required
    if annotation is int:
        return {"type": "integer", "description": name}, required
    if annotation is float:
        return {"type": "number", "description": name}, required
    if annotation is bool:
        return {"type": "boolean", "description": name}, required
    if annotation is list:
        return {"type": "array", "description": name}, required
    if annotation is dict:
        return {"type": "object", "description": name}, required
    origin = get_origin(annotation)
    if origin is dict:
        return {"type": "object", "description": name}, required
    if origin is type(None) or (hasattr(annotation, "__origin__") and get_origin(annotation) is type(None)):
        return {"type": "string", "description": name}, required
    if origin is list:
        return {"type": "array", "items": {"type": "string"}, "description": name}, required
    return {"type": "string", "description": name}, required


class FunctionTool(BaseTool):
    """Wraps a callable as a BaseTool with auto-generated schema."""

    def __init__(
        self,
        fn: Callable[..., Any],
        name: str,
        description: str,
        parameters: dict[str, Any],
        pydantic_model: type[BaseModel] | None = None,
        pydantic_param_name: str | None = None,
    ):
        self._fn = fn
        self._name = name
        self._description = description
        self._parameters = parameters
        self._pydantic_model = pydantic_model
        self._pydantic_param_name = pydantic_param_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs: Any) -> str:
        sig = inspect.signature(self._fn)
        hints = get_type_hints(self._fn) if hasattr(self._fn, "__annotations__") else {}
        resolved: dict[str, Any] = {}

        # If we have a Pydantic model param and kwargs are flat (not nested), wrap them
        if self._pydantic_model and self._pydantic_param_name:
            if self._pydantic_param_name not in kwargs:
                # Flat kwargs - wrap them into the Pydantic model
                resolved[self._pydantic_param_name] = self._pydantic_model.model_validate(kwargs)
            else:
                # Nested kwargs - handle normally
                val = kwargs[self._pydantic_param_name]
                if isinstance(val, dict):
                    resolved[self._pydantic_param_name] = self._pydantic_model.model_validate(val)
                else:
                    resolved[self._pydantic_param_name] = val
        else:
            # No Pydantic model - resolve params normally
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                val = kwargs.get(param_name)
                annotation = hints.get(param_name, Any)
                if isinstance(annotation, type) and issubclass(annotation, BaseModel) and isinstance(val, dict):
                    resolved[param_name] = annotation.model_validate(val)
                else:
                    resolved[param_name] = val

        if inspect.iscoroutinefunction(self._fn):
            result = await self._fn(**resolved)
        else:
            result = self._fn(**resolved)
        if isinstance(result, ToolResult):
            return result.to_string()
        if isinstance(result, dict):
            import json

            return json.dumps(result)
        return str(result)


def tool(
    description: str,
    name: str | None = None,
    streaming: bool = False,
) -> Callable[[Callable[..., Any]], FunctionTool]:
    """
    Decorator to register an async (or sync) function as a tool.
    Schema is derived from type hints and Pydantic model parameters.
    """

    def decorator(fn: Callable[..., Any]) -> FunctionTool:
        tool_name = name or fn.__name__
        sig = inspect.signature(fn)
        hints = get_type_hints(fn) if hasattr(fn, "__annotations__") else {}
        properties: dict[str, Any] = {}
        required: list[str] = []
        pydantic_model: type[BaseModel] | None = None
        pydantic_param_name: str | None = None

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            annotation = hints.get(
                param_name,
                param.annotation if param.annotation is not inspect.Parameter.empty else Any,
            )
            default = param.default
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                schema = _pydantic_model_to_json_schema(annotation)
                properties = schema.get("properties", {})
                required = schema.get("required", [])
                pydantic_model = annotation
                pydantic_param_name = param_name
                break
            prop_schema, is_req = _annotation_to_json_schema(param_name, annotation, default)
            properties[param_name] = prop_schema
            if is_req:
                required.append(param_name)

        parameters: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "required": required,
        }
        return FunctionTool(
            fn=fn,
            name=tool_name,
            description=description,
            parameters=parameters,
            pydantic_model=pydantic_model,
            pydantic_param_name=pydantic_param_name,
        )

    return decorator
