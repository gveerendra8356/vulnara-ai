"""
scan.py

SQLAlchemy 2.0-style async model for the `Scans` table, matching the
Task 1 schema exactly (field names/types/constraints). Only the fields
this module needs to read/write are included here; other tables
(Vulnerabilities, Threat_Logs, etc.) live in their own model files,
built out alongside the modules that own them (AI triage, active
testing) — not duplicated here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Scan(Base):
    __tablename__ = "scans"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    target: Mapped[str] = mapped_column(String(255), nullable=False)

    authorization_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    authorization_justification: Mapped[str] = mapped_column(String, nullable=False)

    active_testing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    # Valid values (enforced at the DB level via CHECK constraint, see Task 1 SQL):
    # PENDING | IN_PROGRESS | COMPLETED | FAILED | CANCELLED

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
