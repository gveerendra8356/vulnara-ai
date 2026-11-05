"""
api/routes/departments.py

Admin-managed organizational departments plus analyst assignment.
Admins create departments and assign each analyst to one; analysts are then
scoped to their department's scans and activity everywhere else in the app.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.models.department import Department
from app.models.user import User
from app.models.scan import Scan

router = APIRouter()


def _require_admin(current_user: CurrentUser) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class AssignDepartmentRequest(BaseModel):
    department_id: uuid.UUID | None = None  # null un-assigns the analyst


@router.get("/departments")
async def list_departments(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Lists departments with their analyst count. Any authenticated user can
    read the list (needed for assignment dropdowns and labels); only admins
    can mutate it via the endpoints below.
    """
    members = (
        select(User.department_id, func.count().label("member_count"))
        .where(User.department_id.isnot(None))
        .group_by(User.department_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(Department, members.c.member_count)
            .outerjoin(members, Department.department_id == members.c.department_id)
            .order_by(Department.name)
        )
    ).all()
    return [
        {
            "department_id": str(dept.department_id),
            "name": dept.name,
            "description": dept.description,
            "member_count": int(count or 0),
            "created_at": dept.created_at,
        }
        for dept, count in rows
    ]


@router.post("/admin/departments", status_code=201)
async def create_department(
    payload: DepartmentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(current_user)
    existing = await session.execute(select(Department).where(Department.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="A department with that name already exists")
    dept = Department(name=payload.name.strip(), description=payload.description)
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    return {
        "department_id": str(dept.department_id),
        "name": dept.name,
        "description": dept.description,
        "member_count": 0,
        "created_at": dept.created_at,
    }


@router.delete("/admin/departments/{department_id}", status_code=204)
async def delete_department(
    department_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(current_user)
    # Un-assign any analysts and un-tag any scans, then remove the department.
    await session.execute(
        update(User).where(User.department_id == department_id).values(department_id=None)
    )
    await session.execute(
        update(Scan).where(Scan.department_id == department_id).values(department_id=None)
    )
    await session.execute(delete(Department).where(Department.department_id == department_id))
    await session.commit()
    return None


@router.patch("/admin/users/{user_id}/department")
async def assign_user_department(
    user_id: uuid.UUID,
    payload: AssignDepartmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(current_user)
    user = (await session.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.department_id is not None:
        dept = (
            await session.execute(
                select(Department).where(Department.department_id == payload.department_id)
            )
        ).scalar_one_or_none()
        if dept is None:
            raise HTTPException(status_code=404, detail="Department not found")

    user.department_id = payload.department_id
    await session.commit()
    return {"user_id": str(user.user_id), "department_id": str(payload.department_id) if payload.department_id else None}
