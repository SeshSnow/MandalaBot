"""
Mandala tool registry with auto-discovery.

Discovers BaseTool instances from nanobot/tools/builtin/ and nanobot/tools/custom/.
Separate from nanobot's built-in ToolRegistry so Mandala tools are cleanly namespaced.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.tools.base import BaseTool


class MandalaToolRegistry:
    """Registry for Mandala custom tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_definitions(self) -> list[dict[str, Any]]:
        return [t.to_schema() for t in self._tools.values()]

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def auto_discover(self) -> None:
        """Scan builtin/ and custom/ under nanobot/tools/ and register all BaseTool instances."""
        tools_dir = Path(__file__).resolve().parent
        for subdir in ("builtin", "custom"):
            subpath = tools_dir / subdir
            if subpath.is_dir():
                self._discover_in_path(subpath, f"nanobot.tools.{subdir}")

    def _discover_in_path(self, path: Path, module_prefix: str) -> None:
        for item in sorted(path.iterdir()):
            if item.name.startswith("_"):
                continue
            if item.is_file() and item.suffix == ".py":
                self._load_module(f"{module_prefix}.{item.stem}")
            elif item.is_dir() and (item / "__init__.py").exists():
                self._discover_in_path(item, f"{module_prefix}.{item.name}")

    def _load_module(self, mod_name: str) -> None:
        try:
            spec = importlib.util.find_spec(mod_name)
            if spec is None or spec.loader is None:
                return
            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
            else:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, BaseTool) and attr.name and attr.name not in self._tools:
                    self.register(attr)
        except Exception as e:
            logger.warning("Could not load tool module {}: {}", mod_name, e)


# Singleton registry — populated by auto_discover() at server startup
mandala_registry = MandalaToolRegistry()
