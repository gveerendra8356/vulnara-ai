"""
schemas/scan.py

Pydantic models for the POST /scans request/response. The authorization
gate is enforced at TWO layers, deliberately redundant:

  1. Pydantic field validation (fast-fails malformed/empty justification
     before any DB or business logic runs).
  2. An explicit check in the route handler itself (scans.py), which is
     the one that actually blocks scan creation and writes the audit log
     entry with a timestamp. Pydantic alone isn't enough because
     `authorization_confirmed=False` is still a perfectly valid boolean —
     validation can't express "and also this must be true", that's a
     business rule that belongs in the endpoint.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ScanCreateRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=255, description="Domain or IP to scan")
    authorization_confirmed: bool = Field(
        ..., description="Must be true — user attests they have permission to scan `target`"
    )
    authorization_justification: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Required explanation/proof of authorization, logged verbatim for audit.",
    )
    active_testing_enabled: bool = Field(
        default=False, description="Opt-in only — active SQLi/XSS testing, never default-on."
    )

    @field_validator("authorization_justification")
    @classmethod
    def justification_not_blank(cls, v: str) -> str:
        # min_length=10 already blocks empty strings, but explicitly guard
        # against whitespace-only input (e.g. "          ") slipping through.
        if not v.strip():
            raise ValueError("authorization_justification cannot be blank or whitespace-only")
        return v.strip()

    @field_validator("target")
    @classmethod
    def target_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target cannot be blank")
        return v.strip()


class ScanCreateResponse(BaseModel):
    scan_id: uuid.UUID
    target: str
    status: str
    active_testing_enabled: bool
    created_at: datetime
