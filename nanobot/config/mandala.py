"""
Mandala-specific configuration sections.

These settings activate when NANOBOT_DATABASE_URL is set.
When database_url is empty, Mandala features are disabled and nanobot
falls back to filesystem-based sessions and memory (default behavior).

Environment variables (prefix: NANOBOT_):
  NANOBOT_DATABASE_URL          PostgreSQL connection string
  NANOBOT_DATABASE_HOST         Override DB host (e.g. "db" in Docker)
  NANOBOT_OPENROUTER_API_KEY    OpenRouter API key
  NANOBOT_DEFAULT_MODEL         Default LLM model
  NANOBOT_BRAVE_API_KEY         Brave Search API key
  NANOBOT_AZURE_STORAGE_CONNECTION_STRING
  NANOBOT_AZURE_STORAGE_CONTAINER
  NANOBOT_SE_RANKING_API_KEY
  NANOBOT_SHOPIFY_TOKEN_ENCRYPTION_KEY
  NANOBOT_CORS_ORIGINS          Comma-separated or "*"
  NANOBOT_LOG_LEVEL             DEBUG/INFO/WARNING/ERROR
"""

from urllib.parse import urlparse

from pydantic import ConfigDict

from nanobot.config.schema import Base


class MandalaConfig(Base):
    model_config = ConfigDict(env_prefix="")
    """
    Optional Mandala application config. Activates when database_url is set.

    Reads env vars with NANOBOT_ prefix (no nested delimiter).
    E.g. NANOBOT_DATABASE_URL, NANOBOT_OPENROUTER_API_KEY, etc.
    """

    # --- Database ---
    database_url: str = ""
    database_host: str | None = None

    # --- LLM (OpenRouter) ---
    openrouter_api_key: str = ""
    default_model: str = "minimax/minimax-m2.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    brave_api_key: str = ""

    # --- Azure Blob Storage ---
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "nanobot-attachments"

    # --- SEO ---
    se_ranking_api_key: str = ""

    # --- Third-party integrations ---
    firecrawl_api_key: str = ""

    # --- Shopify ---
    shopify_token_encryption_key: str = ""

    # --- Security / CORS ---
    token_limit_free: int = 5
    token_limit_premium: int = 25
    token_limit_elite: int = 50
    cors_origins: str = "*"

    # --- Vector Store ---
    vector_store_embedding_model: str = "qwen/qwen3-embedding-8b"
    vector_store_embedding_dims: int = 2000

    # --- Server ---
    log_level: str = "INFO"
    backend_url: str = ""

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """True when Mandala features should activate (DB URL configured)."""
        return bool(self.database_url)

    @property
    def async_database_url(self) -> str:
        """Return asyncpg-compatible URL, with optional host override."""
        url = self.database_url
        if not url:
            return ""
        if "asyncpg" not in url and url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_host:
            parsed = urlparse(url)
            if parsed.hostname:
                url = url.replace(parsed.hostname, self.database_host, 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Return psycopg2-compatible URL (for alembic)."""
        url = self.database_url
        if not url:
            return ""
        if "asyncpg" in url:
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if self.database_host:
            parsed = urlparse(url)
            if parsed.hostname:
                url = url.replace(parsed.hostname, self.database_host, 1)
        return url

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
