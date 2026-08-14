"""
seed_test_accounts.py

Creates the four known QA accounts (admin / analyst / client1 / client2)
directly in the ephemeral test database, the same way seed_db.py seeds demo
data for local dev. Run once per test session, before the server starts,
against DATABASE_URL from the environment.

admin can't be created through the public API (POST /auth/register only
allows self-registration as 'client' or 'analyst' by design -- see
api/routes/auth.py), so the very first admin account always has to come
from a trusted, out-of-band path like this one, exactly as it would in a
real deployment.
"""
import asyncio
import sys

from app.core.db import engine
from app.core.security import get_password_hash
from app.models.scan import Base
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Keep these in sync with conftest.py
ACCOUNTS = [
    ("admin.qa@vulnara-qa-suite.com", "AdminQA123!", "QA Admin", "admin"),
    ("analyst.qa@vulnara-qa-suite.com", "AnalystQA123!", "QA Analyst", "analyst"),
    ("client1.qa@vulnara-qa-suite.com", "Client1QA123!", "QA Client One", "client"),
    ("client2.qa@vulnara-qa-suite.com", "Client2QA123!", "QA Client Two", "client"),
]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        for email, password, full_name, role in ACCOUNTS:
            existing = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing:
                print(f"· {email} already exists, skipping.")
                continue
            session.add(
                User(
                    email=email,
                    password_hash=get_password_hash(password),
                    full_name=full_name,
                    role=role,
                    is_active=True,
                )
            )
            print(f"✓ seeded {role}: {email}")
        await session.commit()
    print("QA account seeding complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: seeding failed: {exc}", file=sys.stderr)
        sys.exit(1)
