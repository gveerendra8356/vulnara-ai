"""
schemas/device.py

Request/response models for POST /devices/register (new endpoint, see
migration 003 and core/push_notifications.py docstrings for why this
exists outside the original API contract).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, description="FCM registration token from the device")
    platform: str = Field(..., description="'android' or 'ios'")

    @field_validator("platform")
    @classmethod
    def platform_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("android", "ios"):
            raise ValueError("platform must be 'android' or 'ios'")
        return v

    @field_validator("fcm_token")
    @classmethod
    def token_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("fcm_token cannot be blank")
        return v.strip()


class DeviceRegisterResponse(BaseModel):
    device_token_id: uuid.UUID
    platform: str
    created_at: datetime
