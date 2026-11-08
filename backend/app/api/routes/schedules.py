"""
api/routes/schedules.py

Manage recurring (scheduled) scans. Same authorization gate as manual scans,
same department scoping for visibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.models.scan_schedule import ScanSchedule

router = APIRouter()

MIN_INTERVAL_MINUTES = 5


class ScheduleCreateRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    authorization_confirmed: bool
    authorization_justification: str = Field(min_length=10)
    active_testing_enabled: bool = False
    interval_minutes: int = Field(ge=MIN_INTERVAL_MINUTES, le=10080)  # 5 min .. 1 week


class ScheduleUpdateRequest(BaseModel):
    enabled: bool


def _scope(current_user: CurrentUser):
    if current_user.role == "admin":
        return None
    if current_user.department_id is not None:
        return ScanSchedule.department_id == current_user.department_id
    return ScanSchedule.user_id == current_user.user_id


def _serialize(s: ScanSchedule) -> dict:
    return {
        "schedule_id": str(s.schedule_id),
        "target": s.target,
        "active_testing_enabled": s.active_testing_enabled,
        "interval_minutes": s.interval_minutes,
        "enabled": s.enabled,
        "next_run_at": s.next_run_at,
        "last_run_at": s.last_run_at,
        "created_at": s.created_at,
        "user_id": str(s.user_id),
    }


@router.post("/schedules", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not payload.authorization_confirmed:
        raise HTTPException(status_code=403, detail="You must confirm authorization to scan this target.")

    now = datetime.now(timezone.utc)
    sched = ScanSchedule(
        user_id=current_user.user_id,
        department_id=current_user.department_id,
        target=payload.target,
        authorization_justification=payload.authorization_justification,
        active_testing_enabled=payload.active_testing_enabled,
        interval_minutes=payload.interval_minutes,
        enabled=True,
        next_run_at=now,  # first run on the next scheduler tick
    )
    session.add(sched)
    await session.commit()
    await session.refresh(sched)
    return _serialize(sched)


@router.get("/schedules")
async def list_schedules(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ScanSchedule).order_by(ScanSchedule.created_at.desc())
    cond = _scope(current_user)
    if cond is not None:
        stmt = stmt.where(cond)
    rows = (await session.execute(stmt)).scalars().all()
    return [_serialize(s) for s in rows]


async def _get_owned(session, schedule_id, current_user) -> ScanSchedule:
    sched = (await session.execute(
        select(ScanSchedule).where(ScanSchedule.schedule_id == schedule_id)
    )).scalar_one_or_none()
    if sched is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if current_user.role != "admin" and sched.user_id != current_user.user_id:
        # analysts may manage schedules in their own department
        if not (current_user.department_id and sched.department_id == current_user.department_id):
            raise HTTPException(status_code=403, detail="Not authorized for this schedule")
    return sched


@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: uuid.UUID,
    payload: ScheduleUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    sched = await _get_owned(session, schedule_id, current_user)
    sched.enabled = payload.enabled
    await session.commit()
    await session.refresh(sched)
    return _serialize(sched)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_owned(session, schedule_id, current_user)
    await session.execute(delete(ScanSchedule).where(ScanSchedule.schedule_id == schedule_id))
    await session.commit()
    return None
