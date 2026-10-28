"""Definitions and typed access for administrator settings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig

DEFAULT_CONFIG = {
    "max_concurrent_scans": ("5", "Maximum concurrent scans"),
    "ai_remediation_enabled": ("true", "Allow AI remediation generation"),
    "email_alerts_enabled": ("true", "Send HIGH/CRITICAL email alerts"),
}


async def get_config_value(session: AsyncSession, key: str) -> str:
    result = await session.execute(
        select(SystemConfig.config_value).where(SystemConfig.config_key == key)
    )
    value = result.scalar_one_or_none()
    return value if value is not None else DEFAULT_CONFIG[key][0]
