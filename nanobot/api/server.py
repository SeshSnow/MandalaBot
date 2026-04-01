"""
FastAPI application factory for nanobot.

Replaces the previous aiohttp server. Provides:
  - OpenAI-compatible /v1/chat/completions, /v1/models, /health (always)
  - Mandala business routes under /api/v1/ (when mandala.enabled)

Usage (programmatic):
    app = create_app(agent_loop, model_name="my-model", request_timeout=120.0)
    uvicorn.run(app, host="0.0.0.0", port=8900)

Usage (CLI):
    nanobot serve [--port 8900] [--host 0.0.0.0]
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from nanobot.agent.loop import AgentLoop
    from nanobot.config.mandala import MandalaConfig


def create_app(
    agent_loop: "AgentLoop",
    model_name: str = "nanobot",
    request_timeout: float = 120.0,
    mandala_config: "MandalaConfig | None" = None,
):
    """
    Create the FastAPI application.

    Args:
        agent_loop: Initialized AgentLoop instance.
        model_name: Model name reported in /v1/models responses.
        request_timeout: Per-request timeout in seconds.
        mandala_config: Optional Mandala config. When enabled, activates DB and
            Mandala-specific routes (/api/v1/agent/chat, /api/v1/shop, etc.).
    """
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        raise ImportError(
            "fastapi is required. Install with: pip install 'nanobot-ai[server]'"
        )

    mandala_enabled = mandala_config is not None and mandala_config.enabled

    # ------------------------------------------------------------------
    # Lifespan: startup/shutdown hooks
    # ------------------------------------------------------------------
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Connect MCP servers
        await agent_loop._connect_mcp()

        if mandala_enabled:
            # Expose agent loop at module level for services (e.g. article_generator)
            from nanobot.api import agent_context as _agent_ctx
            _agent_ctx.set_agent_loop(agent_loop)
            await _startup_mandala(app, mandala_config)

        yield

        await agent_loop.close_mcp()

        if mandala_enabled:
            await _shutdown_mandala(app)

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    app = FastAPI(
        title="nanobot",
        description="nanobot AI agent API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Store shared state on app.state (accessible in route handlers via request.app.state)
    app.state.agent_loop = agent_loop
    app.state.model_name = model_name
    app.state.request_timeout = request_timeout
    app.state.mandala_config = mandala_config

    # CORS — open when Mandala enabled (uses configured origins), permissive for API-only mode
    cors_origins = mandala_config.cors_origins_list if mandala_enabled else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routes: OpenAI-compatible (always present)
    # ------------------------------------------------------------------
    from nanobot.api.routes.openai_compat import router as openai_router
    app.include_router(openai_router)

    # ------------------------------------------------------------------
    # Tenant middleware (only when DB configured)
    # ------------------------------------------------------------------
    if mandala_enabled:
        try:
            from nanobot.tenant.middleware import TenantMiddleware
            app.add_middleware(TenantMiddleware)
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Routes: Mandala business layer (only when DB configured)
    # ------------------------------------------------------------------
    if mandala_enabled:
        _register_mandala_routes(app, mandala_config)

    return app


# ---------------------------------------------------------------------------
# Mandala startup / shutdown
# ---------------------------------------------------------------------------

async def _startup_mandala(app, mandala_config: "MandalaConfig") -> None:
    """Initialize DB and auto-discover tools when Mandala is enabled."""
    try:
        from sqlalchemy import text
        from nanobot.db.engine import create_engine, create_session_factory
        from nanobot.db.base import Base

        engine = create_engine(mandala_config.async_database_url)
        session_factory = create_session_factory(engine)
        app.state.db_engine = engine
        app.state.db_session_factory = session_factory

        # Expose session factory at module level so tools can import it directly
        from nanobot.db import session as _db_session
        _db_session.init(session_factory)

        # Wait for DB connectivity (Docker: db container may not be ready)
        for attempt in range(1, 11):
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                break
            except Exception as exc:
                if attempt == 10:
                    raise
                logger.warning("DB not ready (attempt {}/10): {}", attempt, exc)
                await asyncio.sleep(2)

        # Enable required PostgreSQL extensions
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Mandala DB ready")

    except ImportError as exc:
        logger.warning("Mandala DB dependencies not installed ({}), DB features disabled", exc)
        app.state.db_engine = None
        app.state.db_session_factory = None

    # Auto-discover Mandala custom tools
    try:
        from nanobot.tools.registry import mandala_registry
        mandala_registry.auto_discover()
        logger.info("Mandala tools registered: {}", mandala_registry.tool_names)
        # Register into the agent loop's tool registry
        _register_mandala_tools(app.state.agent_loop, mandala_registry)
    except ImportError:
        logger.debug("Mandala tools package not yet available, skipping tool discovery")


async def _shutdown_mandala(app) -> None:
    """Dispose DB engine on shutdown."""
    engine = getattr(app.state, "db_engine", None)
    if engine is not None:
        await engine.dispose()
        logger.info("Mandala DB engine disposed")


def _register_mandala_tools(agent_loop, mandala_registry) -> None:
    """Wrap and register Mandala custom tools into the agent loop."""
    from nanobot.api.integration import NanobotToolAdapter, EventEmittingToolWrapper

    # Disable default filesystem/shell tools (no direct FS access in server mode)
    _DISABLED = frozenset({"read_file", "write_file", "edit_file", "list_dir", "exec", "spawn"})
    for name in _DISABLED:
        agent_loop.tools.unregister(name)
        agent_loop.tools._tools.pop(name, None)

    # Wrap built-in remaining tools for event emission
    for name in list(agent_loop.tools._tools.keys()):
        original = agent_loop.tools._tools[name]
        if not isinstance(original, EventEmittingToolWrapper):
            agent_loop.tools._tools[name] = EventEmittingToolWrapper(original)

    # Register Mandala custom tools
    for tool in mandala_registry._tools.values():
        if agent_loop.tools.get(tool.name) is None:
            agent_loop.tools.register(NanobotToolAdapter(tool))


def _register_mandala_routes(app, mandala_config: "MandalaConfig") -> None:
    """Include Mandala business routes."""
    try:
        from nanobot.api.routes.mandala import create_mandala_router
        mandala_router = create_mandala_router()
        app.include_router(mandala_router, prefix="/api/v1")
        logger.info("Mandala routes registered under /api/v1")
    except ImportError as exc:
        logger.warning("Could not register Mandala routes: {}", exc)
