"""Shared finding lookup enforcing the scan ownership boundary."""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.models.scan import Scan
from app.models.triage_models import Vulnerability


async def get_visible_vulnerability(
    session: AsyncSession, vuln_id: uuid.UUID, current_user: CurrentUser
) -> Vulnerability:
    if current_user.role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await session.execute(
        select(Vulnerability).where(Vulnerability.vuln_id == vuln_id)
    )
    vuln = result.scalar_one_or_none()
    if vuln is None:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    # Enforce the scan ownership / department boundary. Admins see every
    # finding; an analyst with a department only their department's scans; a
    # department-less analyst only their own. Out-of-scope is reported as 404
    # so the endpoint does not reveal that the finding exists (closes the
    # cross-tenant IDOR these previously leaked, since every user is an
    # analyst/admin and the old role check never blocked).
    if current_user.role != "admin":
        scan = (
            await session.execute(select(Scan).where(Scan.scan_id == vuln.scan_id))
        ).scalar_one_or_none()
        if current_user.department_id is not None:
            allowed = scan is not None and scan.department_id == current_user.department_id
        else:
            allowed = scan is not None and scan.user_id == current_user.user_id
        if not allowed:
            raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vuln
