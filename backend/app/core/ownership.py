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
    stmt = select(Vulnerability).where(Vulnerability.vuln_id == vuln_id)
    # Admin and analyst both triage every finding globally; any other role is
    # not authorized.
    if current_user.role not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await session.execute(stmt)
    vuln = result.scalar_one_or_none()
    if vuln is None:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vuln
