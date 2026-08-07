"""
triage/schemas.py

Pydantic models defining the EXACT JSON shape we require back from Gemini
for both the triage step and the remediation step. These serve two jobs:
  1. Passed to Gemini as a response_schema so the model is constrained to
     emit exactly this structure (see gemini_client.py).
  2. Used again on our side to validate/parse whatever comes back, so a
     malformed or partial response fails loudly (and triggers a retry)
     instead of silently corrupting a DB write.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, confloat

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


class TriageFinding(BaseModel):
    """One assessed finding for a single host:port:service combination."""

    host: str
    port: Optional[int] = None
    service_name: Optional[str] = None
    service_version: Optional[str] = None

    cve_id: Optional[str] = Field(
        default=None, description="Matched CVE ID, or null if this isn't tied to a specific CVE."
    )
    is_false_positive: bool = Field(
        ..., description="True if the AI judges this candidate match is not a real risk."
    )
    severity: Severity
    cvss_score: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    confidence_score: confloat(ge=0.0, le=1.0) = Field(
        ..., description="AI's confidence in this assessment, 0.0-1.0. Never omit."
    )
    explanation: str = Field(
        ..., min_length=1, description="Plain-English reasoning, suitable for a report reader."
    )


class TriageResponse(BaseModel):
    """Top-level shape Gemini must return for a triage batch call."""

    findings: list[TriageFinding]


class RemediationResponse(BaseModel):
    """Top-level shape Gemini must return for a remediation-generation call."""

    executive_summary: str = Field(..., min_length=1)
    technical_script: str = Field(..., min_length=1)
    ai_confidence: confloat(ge=0.0, le=1.0)
    script_language: Literal["bash", "powershell"] = Field(
        default="bash", description="Lets the frontend syntax-highlight correctly."
    )


class ActiveTestVerdict(BaseModel):
    """
    Top-level shape Gemini must return for active-test result verification
    (Data Flow 3). This is the layer that turns a heuristic SIGNAL
    (verifiers.py) into an actual judgment about reflection vs. real
    exploitation, using the surrounding response context the heuristics
    can't reason about (e.g. "is this inside an HTML comment," "does this
    look like our literal input being echoed vs. real command output").
    """

    ai_verified: bool = Field(
        ..., description="True only if the AI judges this represents a real, exploitable finding."
    )
    verification_notes: str = Field(
        ..., min_length=1, description="Plain-English reasoning for the verdict, for human review."
    )
    risk_rating: Severity = Field(..., description="Final risk rating, may differ from the heuristic's preliminary rating.")
