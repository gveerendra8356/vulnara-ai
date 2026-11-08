"""
scanner/scheduler.py

A lightweight in-process scheduler for recurring scans. A single asyncio task,
started at app startup, wakes every minute, finds schedules whose next_run_at
is due, launches a scan for each, and advances next_run_at.

Deployment note: on a single always-on backend this is enough. (On a free host
that sleeps when idle, a keep-alive ping -- e.g. cron-job.org hitting /health --
keeps the process awake so this loop keeps ticking.) A multi-worker deployment
would move this to a real scheduler/queue (APScheduler, Celery beat).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models.scan import Scan
from app.models.scan_schedule import ScanSchedule
from app.scanner.task_runner import start_scan_task

logger = logging.getLogger("vulnara.scheduler")
_CHECK_INTERVAL_SECONDS = 60


async def _run_due_schedules() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        due = (await session.execute(
            select(ScanSchedule).where(
                ScanSchedule.enabled.is_(True),
                ScanSchedule.next_run_at <= now,
            )
        )).scalars().all()

        for sch in due:
            try:
                scan = Scan(
                    user_id=sch.user_id,
                    department_id=sch.department_id,
                    target=sch.target,
                    authorization_confirmed=True,
                    authorization_justification=sch.authorization_justification,
                    active_testing_enabled=sch.active_testing_enabled,
                    status="PENDING",
                )
                session.add(scan)
                sch.last_run_at = now
                sch.next_run_at = now + timedelta(minutes=sch.interval_minutes)
                await session.commit()
                await session.refresh(scan)
                start_scan_task(scan.scan_id, scan.target, scan.active_testing_enabled)
                logger.info(
                    "scheduler: launched scan %s for schedule %s (%s)",
                    scan.scan_id, sch.schedule_id, sch.target,
                )
            except Exception:
                logger.exception("scheduler: failed to run schedule %s", sch.schedule_id)
                await session.rollback()


async def scheduler_loop() -> None:
    logger.info("Recurring-scan scheduler started")
    while True:
        try:
            await _run_due_schedules()
        except Exception:
            logger.exception("scheduler loop iteration failed")
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
