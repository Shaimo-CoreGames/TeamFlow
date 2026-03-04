from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# ==============================
# DATABASE URL
# ==============================
DATABASE_URL = settings.DATABASE_URL  # e.g., sqlite+aiosqlite:///./teamflow.db

# ==============================
# ASYNC ENGINE
# ==============================
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # True if you want SQL logs
    future=True,
    pool_pre_ping=True,
)

# ==============================
# BASE CLASS for models
# ==============================
Base = declarative_base()

# ==============================
# ASYNC SESSION FACTORY
# ==============================
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ==============================
# DEPENDENCY
# ==============================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async DB session.
    Ensures proper session closing.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()