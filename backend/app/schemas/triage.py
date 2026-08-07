from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class CVEDefinitionResponse(BaseModel):
    cve_id: str
    description: str
    cvss_v3_score: Optional[float] = None
    severity: Optional[str] = None
    published_date: Optional[datetime] = None
    last_modified_date: Optional[datetime] = None
    source: str
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VulnerabilityResponse(BaseModel):
    vuln_id: UUID
    scan_id: UUID
    cve_id: Optional[str] = None
    host: str
    port: Optional[int] = None
    service_name: Optional[str] = None
    service_version: Optional[str] = None
    severity: str
    cvss_score: Optional[float] = None
    confidence_score: float
    ai_reasoning: Optional[str] = None
    status: str
    discovered_at: datetime
    
    # We optionally include the nested CVE Definition for convenience on the frontend
    cve: Optional[CVEDefinitionResponse] = None

    model_config = ConfigDict(from_attributes=True)

class VulnerabilityUpdateRequest(BaseModel):
    status: str

class ThreatLogResponse(BaseModel):
    log_id: UUID
    scan_id: UUID
    vuln_id: Optional[UUID] = None
    attack_type: str
    target_url: str
    target_param: Optional[str] = None
    payload_used: str
    ai_verified: bool
    verification_notes: Optional[str] = None
    risk_rating: str
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RemediationResponse(BaseModel):
    remediation_id: UUID
    vuln_id: UUID
    target_os: Optional[str] = None
    executive_summary: str
    technical_script: str
    ai_confidence: float
    status: str
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RemediationRejectRequest(BaseModel):
    reason: str
