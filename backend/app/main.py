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
from app.api.routes.departments import router as departments_router
from app.api.routes.overview import router as overview_router
from app.api.routes.ml import router as ml_router
from app.api.routes.schedules import router as schedules_router
from app.core.db import AsyncSessionLocal
from app.models.system_config import SystemConfig
from app.core.db import engine

logging.basicConfig(level=logging.INFO)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vulnara API")


@app.on_event("startup")
async def ensure_config_table():
    from sqlalchemy import inspect as sa_inspect
    from app.models.scan import Base
    # Import every model so Base.metadata is complete before create_all,
    # otherwise ForeignKeys to not-yet-imported tables (e.g. departments)
    # break table creation on a fresh database.
    from app.models import (  # noqa: F401
        user, scan, department, scan_schedule, triage_models, threat_log,
        token_denylist, device_token, system_config,
    )

    async with engine.begin() as conn:
        # Create any tables that don't exist yet (fresh DB); existing tables
        # are left untouched. Column additions are handled by the ALTERs below.
        await conn.run_sync(Base.metadata.create_all)

        # Idempotent schema catch-up: make sure columns added by later
        # migrations exist even if the deployed database (e.g. Render/Neon)
        # was never migrated. ADD COLUMN on an existing column would error,
        # so we check the live columns first. Safe to run on every startup.
        def _columns(sync_conn, table):
            try:
                return {c["name"] for c in sa_inspect(sync_conn).get_columns(table)}
            except Exception:
                return set()

        scan_cols = await conn.run_sync(_columns, "scans")
        if scan_cols and "failure_reason" not in scan_cols:
            await conn.execute(text("ALTER TABLE scans ADD COLUMN failure_reason VARCHAR(255)"))
            logging.info("startup migration: added scans.failure_reason")

        vuln_cols = await conn.run_sync(_columns, "vulnerabilities")
        if vuln_cols and "banner" not in vuln_cols:
            await conn.execute(text("ALTER TABLE vulnerabilities ADD COLUMN banner TEXT"))
            logging.info("startup migration: added vulnerabilities.banner")

        # Departments feature: departments table is created by create_all
        # above; attach department_id to the pre-existing users/scans tables.
        # UUID column type differs by dialect.
        uuid_sql_type = "UUID" if conn.dialect.name == "postgresql" else "CHAR(32)"
        for _table in ("users", "scans"):
            _cols = await conn.run_sync(_columns, _table)
            if _cols and "department_id" not in _cols:
                await conn.execute(
                    text(f"ALTER TABLE {_table} ADD COLUMN department_id {uuid_sql_type}")
                )
                logging.info("startup migration: added %s.department_id", _table)


@app.on_event("startup")
async def start_scheduler():
    """Launch the recurring-scan scheduler as a background task."""
    from app.scanner.scheduler import scheduler_loop
    asyncio.create_task(scheduler_loop())


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
app.include_router(departments_router, tags=["departments"])
app.include_router(overview_router, tags=["overview"])
app.include_router(ml_router, tags=["ml"])
app.include_router(schedules_router, tags=["schedules"])


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
