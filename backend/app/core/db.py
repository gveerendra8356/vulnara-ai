"""
db.py

Async SQLAlchemy engine/session setup against Neon Postgres.
Neon's serverless connection auto-wakes on query but has a brief cold-start
latency after idle periods -- worth noting in your report as a known
trade-off of the free tier (first query after idle can take ~1-2s longer).
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

# Example: postgresql+asyncpg://user:password@ep-xxxx.neon.tech/vulnara?ssl=require
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./vulnara.db")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

# pool_pre_ping=True matters specifically for Neon: it detects and
# transparently reconnects stale connections after the DB has been
# auto-suspended from inactivity, instead of surfacing a connection error.

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    """FastAPI dependency for request-scoped DB sessions."""
    async with AsyncSessionLocal() as session:
        yield session
