"""
models/device_token.py

SQLAlchemy model for DeviceTokens (migration 003). Stores one row per
FCM registration token per user/device, so the backend knows where to
push `alert.critical` notifications for a given user_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.scan import Base


class DeviceToken(Base):
    __tablename__ = "devicetokens"

    device_token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    fcm_token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    # 'android' | 'ios' -- enforced at DB level via CHECK constraint (migration 003)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )