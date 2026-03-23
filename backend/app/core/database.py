"""
TBAPS Database Connection
SQLAlchemy async engine and session management.
Supports both local PostgreSQL and Neon PostgreSQL (production SSL).
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

from app.core.config import settings


def _build_database_url() -> str:
    """
    Convert the DATABASE_URL to asyncpg format and add SSL for production.

    Rules:
    - Replace postgresql:// → postgresql+asyncpg://
    - Replace postgres:// → postgresql+asyncpg:// (Render/Heroku shorthand)
    - In production, append ?sslmode=require if not already present
      (required for Neon PostgreSQL and most managed cloud databases)
    """
    url = settings.DATABASE_URL

    # Normalize scheme
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+asyncpg://"):
        pass  # Already correct
    else:
        # Fallback — attempt as-is
        return url

    # Add SSL for production (Neon requires it; harmless on other managed DBs)
    if settings.APP_ENV == "production":
        if "sslmode" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"

    return url


_DATABASE_URL = _build_database_url()

# asyncpg connect_args
_CONNECT_ARGS: dict = {
    "statement_cache_size": 0,  # Required for PgBouncer compatibility
    "command_timeout": 60,
}

# Add SSL context for production (Neon requires SSL; asyncpg needs it explicitly)
if settings.APP_ENV == "production":
    import ssl as _ssl
    _ssl_ctx = _ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = _ssl.CERT_NONE  # Neon uses managed certs
    _CONNECT_ARGS["ssl"] = _ssl_ctx

# Create async engine with production-grade connection pool
engine = create_async_engine(
    _DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,           # Verify connection health before use
    pool_recycle=3600,            # Recycle connections after 1 hour
    pool_timeout=30,              # Wait up to 30s for a connection from pool
    pool_reset_on_return="rollback",  # Clean state on connection return
    connect_args=_CONNECT_ARGS,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (used in lifespan)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections (used in lifespan shutdown)."""
    await engine.dispose()
