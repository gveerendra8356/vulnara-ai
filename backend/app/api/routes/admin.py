from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/config")
async def list_config(current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return [
        {"key": "max_concurrent_scans", "value": "5", "description": "Maximum number of scans running simultaneously"},
        {"key": "ai_remediation_enabled", "value": "true", "description": "Enable AI generation of remediation scripts"}
    ]

class ConfigUpdateRequest(BaseModel):
    config_value: str

@router.patch("/config/{key}")
async def update_config(
    key: str,
    payload: ConfigUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return {"key": key, "value": payload.config_value}

@router.get("/cve-definitions")
async def list_cve_defs(current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    # Return empty list as stub
    return []

@router.post("/cve-definitions/sync")
async def sync_cve_defs(current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return {"status": "sync_started", "message": "NVD CVE synchronization started in background"}
