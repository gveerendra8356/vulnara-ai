"""
task_runner.py

Orchestrates a single scan end-to-end as an asyncio background task:
  1. Marks the Scan row IN_PROGRESS, broadcasts scan.status_changed
  2. Runs NmapScanner.run_full_scan(), forwarding phase progress as
     recon.progress WebSocket events
  3. Normalizes results via normalizer.normalize_scan_results()
  4. Hands the normalized payload off to the AI triage layer (stubbed —
     out of scope for this module; see TRIAGE HANDOFF note below)
  5. On any unhandled error, marks the scan FAILED and broadcasts
     scan.failed with the error message

DEPLOYMENT NOTE:
This uses asyncio.create_task() fire-and-forget style, which is
appropriate for a single-VM, thesis-scale deployment. If Vulnara needed
to survive a backend process restart mid-scan, or run scans across
multiple workers, this would need to move to a real task queue (Celery,
RQ, or arq) backed by Redis. Flagging this as a known scaling limit
rather than solving it now, since the locked stack is a single
always-on Oracle VM.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.models.scan import Scan
from app.scanner.nmap_wrapper import NmapScanner, NmapExecutionError, NmapNotFoundError
from app.scanner.normalizer import normalize_scan_results
from app.websocket.manager import scan_connection_manager

logger = logging.getLogger("vulnara.scanner")


def _extract_web_base_urls(normalized: dict) -> list[str]:
    """
    Filters normalized recon output down to ports that look like HTTP(S)
    services, and builds base URLs for the active-testing discovery step.
    Heuristic only (service_name/port-number based) -- nmap's -sV service
    detection is generally reliable for this, but a service running HTTP
    on a nonstandard port with a generic/unrecognized banner could be
    missed. Flagged here rather than in FALSE_POSITIVES.md since this is
    a discovery gap, not a verification false-positive.
    """
    HTTP_HINTS = ("http", "www", "ssl/http")
    COMMON_HTTPS_PORTS = {443, 8443}

    urls = []
    for host_entry in normalized["hosts"]:
        for port_info in host_entry["ports"]:
            service_name = (port_info["service_name"] or "").lower()
            port = port_info["port"]
            if any(hint in service_name for hint in HTTP_HINTS):
                scheme = "https" if (port in COMMON_HTTPS_PORTS or "ssl" in service_name) else "http"
                urls.append(f"{scheme}://{host_entry['host']}:{port}")
    return urls


async def run_scan_task(scan_id: uuid.UUID, target: str, active_testing_enabled: bool) -> None:
    """
    Entry point launched via asyncio.create_task() from the POST /scans
    route. Owns its own DB session since it runs outside the request
    lifecycle (the request-scoped session from FastAPI's dependency
    injection is already closed by the time this executes).
    """
    scan_id_str = str(scan_id)

    async with AsyncSessionLocal() as session:
        try:
            await _mark_in_progress(session, scan_id)
            await scan_connection_manager.broadcast(
                scan_id_str, "scan.status_changed", {"status": "IN_PROGRESS"}
            )

            scanner = NmapScanner()

            async def on_progress(stage: str, extra: dict) -> None:
                await scan_connection_manager.broadcast(
                    scan_id_str, "recon.progress", {"stage": stage, **extra}
                )

            host_results = await scanner.run_full_scan(target, on_progress=on_progress)

            normalized = normalize_scan_results(scan_id_str, target, host_results)

            logger.info(
                "Scan %s recon complete, handing off %d hosts to AI triage",
                scan_id_str, len(normalized["hosts"]),
            )

            # Recon's own DB session (`session`, opened above) is done with
            # its job at this point -- the triage pipeline opens and manages
            # its own session for the remainder of the work (writing
            # Vulnerabilities rows, marking the scan COMPLETED, and
            # broadcasting scan.completed once triage itself finishes).
            # We deliberately don't call _mark_completed/broadcast
            # scan.completed here anymore -- that's now the triage
            # pipeline's responsibility, since the scan isn't actually
            # "done" from the user's perspective until triage has run.
            from app.triage.pipeline import run_triage
            await run_triage(scan_id, normalized)

            # ------------------------------------------------------------
            # Active testing (Data Flow 3) -- runs AFTER triage, only if
            # this scan opted in. Deliberately sequential, not parallel
            # with triage: both stages hit the same target, and running
            # them concurrently would make the rate-limiting/throttling
            # story harder to reason about (two independent request
            # streams hitting the target at once, even if each is
            # individually throttled). run_active_testing() re-checks the
            # opt-in flag itself against the DB -- this call happening
            # unconditionally here is not the actual gate.
            # ------------------------------------------------------------
            if active_testing_enabled:
                web_targets = _extract_web_base_urls(normalized)
                if web_targets:
                    from app.active_testing.pipeline import run_active_testing
                    await run_active_testing(scan_id, web_targets)
                else:
                    logger.info(
                        "Scan %s: active_testing_enabled but no HTTP(S)-looking "
                        "ports found in recon results -- nothing to test.",
                        scan_id_str,
                    )

        except (NmapNotFoundError, NmapExecutionError) as e:
            logger.exception("Scan %s failed during recon", scan_id_str)
            await _mark_failed(session, scan_id, str(e))
            await scan_connection_manager.broadcast(
                scan_id_str, "scan.failed", {"status": "FAILED", "error_message": str(e)}
            )

        except Exception as e:  # noqa: BLE001 - top-level task guard, must not raise
            # asyncio.create_task() swallows exceptions silently unless the
            # task is awaited/inspected, so we must catch everything here
            # or a bug would leave the scan stuck IN_PROGRESS forever with
            # no error surfaced to the user.
            logger.exception("Scan %s failed with unexpected error", scan_id_str)
            await _mark_failed(session, scan_id, "Internal error during scan")
            await scan_connection_manager.broadcast(
                scan_id_str,
                "scan.failed",
                {"status": "FAILED", "error_message": "Internal error during scan"},
            )


# ----------------------------------------------------------------------
# DB helper functions
# ----------------------------------------------------------------------
async def _get_scan(session: AsyncSession, scan_id: uuid.UUID) -> Scan:
    result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
    scan = result.scalar_one()
    return scan


async def _mark_in_progress(session: AsyncSession, scan_id: uuid.UUID) -> None:
    scan = await _get_scan(session, scan_id)
    scan.status = "IN_PROGRESS"
    scan.started_at = datetime.now(timezone.utc)
    await session.commit()


async def _mark_completed(session: AsyncSession, scan_id: uuid.UUID) -> None:
    scan = await _get_scan(session, scan_id)
    scan.status = "COMPLETED"
    scan.completed_at = datetime.now(timezone.utc)
    await session.commit()


async def _mark_failed(session: AsyncSession, scan_id: uuid.UUID, error_message: str) -> None:
    scan = await _get_scan(session, scan_id)
    scan.status = "FAILED"
    scan.completed_at = datetime.now(timezone.utc)
    await session.commit()
    logger.error("Scan %s marked FAILED: %s", scan_id, error_message)
