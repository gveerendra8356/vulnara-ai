"""
api/routes/overview.py

Organization security overview -- the admin's "network activity" view, built
from scan data. Admins see the whole organization; analysts see only their
department. Returns headline metrics, a discovered-asset inventory, a recent
activity feed, and (for admins) a per-department breakdown.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.models.scan import Scan
from app.models.user import User
from app.models.department import Department
from app.models.triage_models import Vulnerability

router = APIRouter()

_OPEN_STATES = ("OPEN", "CONFIRMED", None)


def _visible_scan_ids_subquery(current_user: CurrentUser):
    """Scan-ids this user may see: all for admin, else their department's
    scans (or their own scans when they have no department yet)."""
    stmt = select(Scan.scan_id)
    if current_user.role != "admin":
        if current_user.department_id is not None:
            stmt = stmt.where(Scan.department_id == current_user.department_id)
        else:
            stmt = stmt.where(Scan.user_id == current_user.user_id)
    return stmt.subquery()


@router.get("/overview")
async def organization_overview(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    visible = _visible_scan_ids_subquery(current_user)
    scan_scope = select(Scan).where(Scan.scan_id.in_(select(visible.c.scan_id)))
    vuln_scope = Vulnerability.scan_id.in_(select(visible.c.scan_id))

    # ---- headline metrics -------------------------------------------------
    total_scans = await session.scalar(
        select(func.count()).select_from(scan_scope.subquery())
    )
    completed_scans = await session.scalar(
        select(func.count()).select_from(
            scan_scope.where(Scan.status == "COMPLETED").subquery()
        )
    )
    total_assets = await session.scalar(
        select(func.count()).select_from(
            select(Vulnerability.host, Vulnerability.port)
            .where(vuln_scope)
            .group_by(Vulnerability.host, Vulnerability.port)
            .subquery()
        )
    )
    sev_rows = (
        await session.execute(
            select(Vulnerability.severity, func.count())
            .where(vuln_scope)
            .group_by(Vulnerability.severity)
        )
    ).all()
    findings_by_severity = {sev: int(n) for sev, n in sev_rows if sev}
    open_findings = await session.scalar(
        select(func.count()).select_from(
            Vulnerability.__table__
        ).where(vuln_scope, Vulnerability.status.in_(_OPEN_STATES))
    ) or 0

    # ---- discovered assets (host:port:service) ---------------------------
    asset_rows = (
        await session.execute(
            select(
                Vulnerability.host,
                Vulnerability.port,
                func.max(Vulnerability.service_name).label("service_name"),
                func.count().label("finding_count"),
                func.max(Vulnerability.cvss_score).label("max_cvss"),
                func.max(Vulnerability.discovered_at).label("last_seen"),
            )
            .where(vuln_scope)
            .group_by(Vulnerability.host, Vulnerability.port)
            .order_by(func.max(Vulnerability.cvss_score).desc().nullslast())
            .limit(100)
        )
    ).all()
    assets = [
        {
            "host": r.host,
            "port": r.port,
            "service_name": r.service_name,
            "finding_count": int(r.finding_count),
            "max_cvss": float(r.max_cvss) if r.max_cvss is not None else None,
            "last_seen": r.last_seen,
        }
        for r in asset_rows
    ]

    # ---- recent activity feed (scans + their finding counts) -------------
    vuln_counts = (
        select(Vulnerability.scan_id, func.count().label("finding_count"))
        .group_by(Vulnerability.scan_id)
        .subquery()
    )
    activity_rows = (
        await session.execute(
            select(
                Scan.scan_id, Scan.target, Scan.status, Scan.created_at,
                User.email, User.full_name,
                func.coalesce(vuln_counts.c.finding_count, 0).label("finding_count"),
            )
            .join(User, Scan.user_id == User.user_id)
            .outerjoin(vuln_counts, vuln_counts.c.scan_id == Scan.scan_id)
            .where(Scan.scan_id.in_(select(visible.c.scan_id)))
            .order_by(Scan.created_at.desc())
            .limit(25)
        )
    ).all()
    activity = [
        {
            "scan_id": str(r.scan_id),
            "target": r.target,
            "status": r.status,
            "created_at": r.created_at,
            "user_email": r.email,
            "user_full_name": r.full_name,
            "finding_count": int(r.finding_count),
        }
        for r in activity_rows
    ]

    # ---- time series for charts -----------------------------------------
    scans_by_day = (await session.execute(
        select(func.date(Scan.created_at).label("d"), func.count())
        .where(Scan.scan_id.in_(select(visible.c.scan_id)))
        .group_by(func.date(Scan.created_at))
        .order_by(func.date(Scan.created_at))
    )).all()
    findings_by_day = (await session.execute(
        select(func.date(Vulnerability.discovered_at).label("d"), func.count())
        .where(vuln_scope)
        .group_by(func.date(Vulnerability.discovered_at))
        .order_by(func.date(Vulnerability.discovered_at))
    )).all()
    status_dist = (await session.execute(
        select(Scan.status, func.count())
        .where(Scan.scan_id.in_(select(visible.c.scan_id)))
        .group_by(Scan.status)
    )).all()

    payload = {
        "scope": "organization" if current_user.role == "admin" else "department",
        "metrics": {
            "total_scans": int(total_scans or 0),
            "completed_scans": int(completed_scans or 0),
            "total_assets": int(total_assets or 0),
            "open_findings": int(open_findings or 0),
            "findings_by_severity": findings_by_severity,
        },
        "assets": assets,
        "activity": activity,
        "time_series": {
            "scans_by_day": [{"date": str(d), "count": int(n)} for d, n in scans_by_day],
            "findings_by_day": [{"date": str(d), "count": int(n)} for d, n in findings_by_day],
        },
        "scan_status_distribution": {str(s): int(n) for s, n in status_dist if s},
    }

    # ---- per-department breakdown (admin only) ---------------------------
    if current_user.role == "admin":
        dept_scan_counts = (
            await session.execute(
                select(Department.name, func.count(Scan.scan_id))
                .outerjoin(Scan, Scan.department_id == Department.department_id)
                .group_by(Department.name)
                .order_by(Department.name)
            )
        ).all()
        payload["departments"] = [
            {"name": name, "scan_count": int(n or 0)} for name, n in dept_scan_counts
        ]

    return payload
