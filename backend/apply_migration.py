import asyncio
from sqlalchemy import inspect, text
from app.core.db import engine
from app.models.scan import Base
# Import all models to ensure they are registered with Base.metadata
from app.models import scan, user, token_denylist, device_token, threat_log, triage_models, system_config

async def run_migration():
    print("Connecting to the configured database to create/update tables...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        scan_columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"] for column in inspect(sync_conn).get_columns("scans")
            }
        )
        if "failure_reason" not in scan_columns:
            await conn.execute(
                text("ALTER TABLE scans ADD COLUMN failure_reason VARCHAR(255)")
            )
        vulnerability_columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"]
                for column in inspect(sync_conn).get_columns("vulnerabilities")
            }
        )
        if "banner" not in vulnerability_columns:
            await conn.execute(
                text("ALTER TABLE vulnerabilities ADD COLUMN banner TEXT")
            )
        
    print("Database schema is ready.")

if __name__ == "__main__":
    asyncio.run(run_migration())
