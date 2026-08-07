import asyncio
from app.core.db import engine
from app.models.scan import Base
# Import all models to ensure they are registered with Base.metadata
from app.models import scan, user, token_denylist, device_token, threat_log, triage_models

async def run_migration():
    print("Connecting to local SQLite database to create tables...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("All database tables created successfully in vulnara.db!")

if __name__ == "__main__":
    asyncio.run(run_migration())
