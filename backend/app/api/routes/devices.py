"""
api/routes/devices.py

POST /devices/register -- NOT part of the original Task 2 API contract.
Added in Task 6 because the mobile app's push-notification requirement
(FCM alerts on `alert.critical`) has nowhere to store a device's FCM
token without it. Same auth pattern as every other Authenticated route
(app/core/auth.py's get_current_user stub -- see the note at the bottom
of this file about what that means today).

Upsert semantics: if the same fcm_token is registered again (app
relaunch, token refresh callback firing twice), we update last_seen_at
and re-point it at the current user rather than erroring on the UNIQUE
constraint -- a token can only ever belong to one user at a time (e.g.
after a logout/login-as-different-user on the same device).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.models.device_token import DeviceToken
from app.schemas.device import DeviceRegisterRequest, DeviceRegisterResponse

router = APIRouter()


@router.post("/devices/register", response_model=DeviceRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceRegisterRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeviceRegisterResponse:
    existing = await session.scalar(
        select(DeviceToken).where(DeviceToken.fcm_token == payload.fcm_token)
    )

    if existing is not None:
        existing.user_id = current_user.user_id
        existing.platform = payload.platform
        from datetime import datetime, timezone
        existing.last_seen_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(existing)
        return DeviceRegisterResponse(
            device_token_id=existing.device_token_id,
            platform=existing.platform,
            created_at=existing.created_at,
        )

    device = DeviceToken(
        user_id=current_user.user_id,
        fcm_token=payload.fcm_token,
        platform=payload.platform,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    return DeviceRegisterResponse(
        device_token_id=device.device_token_id,
        platform=device.platform,
        created_at=device.created_at,
    )

# NOTE: like every other Authenticated route in this codebase right now,
# current_user comes from the auth.py STUB (fabricated random user per
# request) until real JWT auth is built -- see the auth gap flagged at
# the end of Task 5. Once real auth exists, this route needs no changes;
# current_user.user_id will just be real instead of random.
