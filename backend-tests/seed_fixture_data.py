"""
seed_fixture_data.py

Seeds one scan (owned by client1.qa) plus one vulnerability on that scan
plus two remediations on that vulnerability, directly via SQLAlchemy --
there is no POST /vulnerabilities endpoint (vulnerabilities are only ever
produced by the scan pipeline itself), so this mirrors how they'd really
land in the table.

Two remediations are created (not one) so approve-flow and reject-flow
tests don't collide over the same row's status transition.

Prints a single JSON line to stdout on success; conftest.py parses it.
"""
import asyncio
import json
import sys
import uuid

from app.core.db import engine
from app.models.scan import Base, Scan
from app.models.triage_models import Vulnerability, Remediation
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        owner = (
            await session.execute(select(User).where(User.email == "client1.qa@vulnara-qa-suite.com"))
        ).scalar_one()

        scan = Scan(
            scan_id=uuid.uuid4(),
            user_id=owner.user_id,
            target="fixture-scan-target.qa.internal",
            authorization_confirmed=True,
            authorization_justification="Fixture data seeded directly for the QA regression suite.",
            active_testing_enabled=False,
            status="COMPLETED",
        )
        session.add(scan)
        await session.flush()

        vuln = Vulnerability(
            vuln_id=uuid.uuid4(),
            scan_id=scan.scan_id,
            host="fixture-scan-target.qa.internal",
            port=443,
            service_name="https",
            service_version="nginx/1.18.0",
            severity="HIGH",
            cvss_score=7.5,
            confidence_score=0.92,
            ai_reasoning="Fixture vulnerability seeded for the QA regression suite.",
            status="OPEN",
        )
        session.add(vuln)
        await session.flush()

        rem1 = Remediation(
            remediation_id=uuid.uuid4(),
            vuln_id=vuln.vuln_id,
            target_os="Ubuntu 22.04",
            executive_summary="Fixture remediation #1 (approve-flow) for the QA regression suite.",
            technical_script="# fixture script\necho 'apply fix'",
            ai_confidence=0.88,
            status="PENDING",
        )
        rem2 = Remediation(
            remediation_id=uuid.uuid4(),
            vuln_id=vuln.vuln_id,
            target_os="Ubuntu 22.04",
            executive_summary="Fixture remediation #2 (reject-flow) for the QA regression suite.",
            technical_script="# fixture script\necho 'apply fix'",
            ai_confidence=0.81,
            status="PENDING",
        )
        session.add_all([rem1, rem2])
        await session.commit()

        print(json.dumps({
            "scan_id": str(scan.scan_id),
            "vuln_id": str(vuln.vuln_id),
            "remediation_id": str(rem1.remediation_id),
            "remediation_id_2": str(rem2.remediation_id),
        }))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: fixture seeding failed: {exc}", file=sys.stderr)
        sys.exit(1)
