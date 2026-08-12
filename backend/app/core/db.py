"""
db.py

Async SQLAlchemy engine/session setup against Neon Postgres.
Neon's serverless connection auto-wakes on query but has a brief cold-start
latency after idle periods -- worth noting in your report as a known
trade-off of the free tier (first query after idle can take ~1-2s longer).
"""

from __future__ import annotations

import os
import re
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

# Example: postgresql+asyncpg://user:password@ep-xxxx.neon.tech/vulnara?sslmode=require
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./vulnara.db")

_connect_args: dict = {}

if DATABASE_URL.startswith("postgresql+asyncpg"):
    # asyncpg's connect() rejects the "sslmode" query param that Neon's
    # dashboard gives you by default (that's a psycopg2/libpq-style name).
    # Strip it from the URL and pass the equivalent as connect_args instead,
    # regardless of which style (sslmode=require or ssl=require) was pasted in.
    if "sslmode=" in DATABASE_URL or "ssl=" in DATABASE_URL:
        DATABASE_URL = re.sub(r"[?&](sslmode|ssl)=[^&]*", "", DATABASE_URL)
        DATABASE_URL = re.sub(r"\?&", "?", DATABASE_URL).rstrip("?&")
    _connect_args = {"ssl": "require"}

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)

# pool_pre_ping=True matters specifically for Neon: it detects and
# transparently reconnects stale connections after the DB has been
# auto-suspended from inactivity, instead of surfacing a connection error.

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    """FastAPI dependency for request-scoped DB sessions."""
    async with AsyncSessionLocal() as session:
        yield session