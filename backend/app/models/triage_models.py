"""
models/cve_definition.py, models/vulnerability.py, models/remediation.py
(kept in one file for this task's deliverable; split into separate files
in your real repo if you prefer one-model-per-file convention)

All three match the Task 1 schema field-for-field.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, ForeignKey, DateTime, Integer, Boolean, Text, func
from sqlalchemy import Uuid as UUID, JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.scan import Base  # shared declarative base from Task 3


class CVEDefinition(Base):
    __tablename__ = "cve_definitions"

    cve_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cvss_v3_score: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_modified_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="NVD")
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    vuln_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False
    )
    cve_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cve_definitions.cve_id", ondelete="SET NULL"), nullable=True
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    cvss_score: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Remediation(Base):
    __tablename__ = "remediations"

    remediation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vuln_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vulnerabilities.vuln_id", ondelete="CASCADE"), nullable=False
    )
    target_os: Mapped[str | None] = mapped_column(String(100), nullable=True)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    technical_script: Mapped[str] = mapped_column(Text, nullable=False)
    ai_confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
