"""
api/routes/admin.py

Admin-only endpoints:
  - GET  /admin/config               — list runtime config values
  - PATCH /admin/config/{key}        — update a config value
  - GET  /admin/cve-definitions      — list cached CVE definitions
  - POST /admin/cve-definitions/sync — trigger NVD sync
  - GET  /admin/users                — list all users with scan counts (admin)
  - GET  /admin/users/{user_id}/scans — list all scans for a specific user
  - PATCH /admin/users/{user_id}     — toggle user active status
  - GET  /admin/scans                — all scans with user attribution
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session, AsyncSessionLocal
from app.models.user import User
from app.models.scan import Scan
from app.models.system_config import SystemConfig
from app.core.config import DEFAULT_CONFIG

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: CurrentUser):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")


# ── Config ────────────────────────────────────────────────────────────────────

@router.get("/config")
async def list_config(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(current_user)
    result = await session.execute(select(SystemConfig))
    rows = {row.config_key: row for row in result.scalars()}
    return [{
        "config_key": key,
        "config_value": rows[key].config_value if key in rows else default,
        "description": description,
        "updated_at": rows[key].updated_at if key in rows else None,
    } for key, (default, description) in DEFAULT_CONFIG.items()]


class ConfigUpdateRequest(BaseModel):
    config_value: str


@router.patch("/config/{key}")
async def update_config(
    key: str,
    payload: ConfigUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(current_user)
    if key not in DEFAULT_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown configuration key")
    value = payload.config_value.strip().lower()
    if key == "max_concurrent_scans":
        if not value.isdigit() or not 1 <= int(value) <= 100:
            raise HTTPException(status_code=422, detail="max_concurrent_scans must be 1-100")
    elif value not in ("true", "false"):
        raise HTTPException(status_code=422, detail="Value must be true or false")
    result = await session.execute(select(SystemConfig).where(SystemConfig.config_key == key))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemConfig(config_key=key, config_value=value)
        session.add(row)
    else:
        row.config_value = value
        row.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return {"config_key": key, "config_value": row.config_value,
            "description": DEFAULT_CONFIG[key][1], "updated_at": row.updated_at}


# ── CVE Definitions ───────────────────────────────────────────────────────────

@router.get("/cve-definitions")
async def list_cve_defs(current_user: CurrentUser = Depends(get_current_user)):
    _require_admin(current_user)
    from app.models.triage_models import CVEDefinition
    async with AsyncSessionLocal() as session:
        stmt = select(CVEDefinition).order_by(CVEDefinition.published_date.desc()).limit(100)
        result = await session.execute(stmt)
        return result.scalars().all()


@router.post("/cve-definitions/sync")
async def sync_cve_defs(current_user: CurrentUser = Depends(get_current_user)):
    _require_admin(current_user)
    raise HTTPException(status_code=501, detail="Manual NVD sync is not implemented; CVEs are cached during scans")


# ── User Management ───────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all users with their scan counts."""
    _require_admin(current_user)

    # Subquery: count scans per user
    scan_counts_stmt = (
        select(Scan.user_id, func.count(Scan.scan_id).label("scan_count"))
        .group_by(Scan.user_id)
        .subquery()
    )

    stmt = (
        select(
            User.user_id,
            User.email,
            User.full_name,
            User.role,
            User.is_active,
            User.created_at,
            User.last_login_at,
            func.coalesce(scan_counts_stmt.c.scan_count, 0).label("scan_count"),
        )
        .outerjoin(scan_counts_stmt, User.user_id == scan_counts_stmt.c.user_id)
        .order_by(User.created_at.desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "user_id": str(row.user_id),
            "email": row.email,
            "full_name": row.full_name,
            "role": row.role,
            "is_active": row.is_active,
            "created_at": row.created_at,
            "last_login_at": row.last_login_at,
            "scan_count": row.scan_count,
        }
        for row in rows
    ]


@router.get("/users/{user_id}/scans")
async def get_user_scans(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get all scans for a specific user (admin only)."""
    _require_admin(current_user)

    # Verify user exists
    user_result = await session.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Scan).where(Scan.user_id == user_id).order_by(Scan.created_at.desc())
    result = await session.execute(stmt)
    scans = result.scalars().all()

    return {
        "user": {
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        "scans": [
            {
                "scan_id": str(s.scan_id),
                "target": s.target,
                "status": s.status,
                "active_testing_enabled": s.active_testing_enabled,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
                "created_at": s.created_at,
            }
            for s in scans
        ],
    }


class ToggleActiveRequest(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    payload: ToggleActiveRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Toggle a user's active status (admin only)."""
    _require_admin(current_user)

    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot modify your own account status")

    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = payload.is_active
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


# ── All Scans with Attribution ────────────────────────────────────────────────

@router.get("/scans")
async def list_all_scans(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List every scan in the system with the scanning user's details (admin only)."""
    _require_admin(current_user)

    stmt = (
        select(Scan, User.email, User.full_name, User.role)
        .join(User, Scan.user_id == User.user_id)
        .order_by(Scan.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "scan_id": str(row.Scan.scan_id),
            "target": row.Scan.target,
            "status": row.Scan.status,
            "active_testing_enabled": row.Scan.active_testing_enabled,
            "started_at": row.Scan.started_at,
            "completed_at": row.Scan.completed_at,
            "created_at": row.Scan.created_at,
            "user_id": str(row.Scan.user_id),
            "user_email": row.email,
            "user_full_name": row.full_name,
            "user_role": row.role,
        }
        for row in rows
    ]
