"""
main.py

Minimal FastAPI app entrypoint, just enough to show the routers built
across Task 3 (scans) and Task 4 (remediations) actually mount together.
Auth routes (Task 2's /auth/*) aren't implemented yet -- app/core/auth.py
is still the stub described in Task 3 -- so this app is runnable for
import/schema-validation purposes but not a full working server until
that module exists for real.
"""

from __future__ import annotations

import logging
import sys
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes.scans import router as scans_router
from app.api.routes.remediations import router as remediations_router
from app.api.routes.devices import router as devices_router
from app.api.routes.auth import router as auth_router
from app.api.routes.vulnerabilities import router as vulnerabilities_router
from app.api.routes.admin import router as admin_router
from app.core.db import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vulnara API")

# Comma-separated list, e.g. "https://vulnara.vercel.app,http://localhost:5173"
_origins_env = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, tags=["auth"])
app.include_router(scans_router, tags=["scans"])
app.include_router(vulnerabilities_router, tags=["vulnerabilities"])
app.include_router(remediations_router, tags=["remediations"])
app.include_router(devices_router, tags=["devices"])
app.include_router(admin_router)


@app.get("/health")
async def health():
    """
    Pings the DB with a real query so this endpoint doubles as a
    keep-alive target (cron-job.org every ~4 min) that prevents both
    the host (Render/Koyeb free tier) and Neon's serverless Postgres
    from going idle/suspended.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logging.getLogger(__name__).warning("Health check DB ping failed: %s", exc)
        db_status = "unreachable"

    return {"status": "ok", "db": db_status}