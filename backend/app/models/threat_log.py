"""
models/threat_log.py

Matches the Task 1 Threat_Logs schema, with attack_type's allowed values
extended from ('SQLI','XSS') to also include 'CMDI' -- see
migrations/002_add_cmdi_attack_type.sql for the corresponding DB-side
CHECK constraint update. This is a genuine schema change from Task 1,
not an oversight left unhandled.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, ForeignKey, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.scan import Base


class ThreatLog(Base):
    __tablename__ = "threat_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False
    )
    vuln_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vulnerabilities.vuln_id", ondelete="SET NULL"), nullable=True
    )
    attack_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Valid values (enforced via CHECK constraint, see migration 002):
    # SQLI | XSS | CMDI
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    target_param: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_used: Mapped[str] = mapped_column(Text, nullable=False)
    ai_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_rating: Mapped[str] = mapped_column(String(10), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
