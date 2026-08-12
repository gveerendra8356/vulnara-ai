import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.core.db import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models.scan import Scan
from app.models.triage_models import CVEDefinition, Vulnerability, Remediation
from app.models.threat_log import ThreatLog
from app.models.user import User
from app.core.security import get_password_hash

async def seed_db():
    SessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with SessionLocal() as session:
        print("Seeding database...")
        
        # ── 1. Users ──────────────────────────────────────────────────────────
        admin_email = "admin@vulnara.com"
        analyst_email = "analyst@vulnara.com"
        
        admin_row = (await session.execute(
            text("SELECT user_id FROM users WHERE email=:e"), {"e": admin_email}
        )).scalar()

        if not admin_row:
            admin_id = uuid.uuid4()
            analyst_id = uuid.uuid4()
            session.add(User(
                user_id=admin_id,
                email=admin_email,
                password_hash=get_password_hash("Admin123!"),
                full_name="System Admin",
                role="admin"
            ))
            session.add(User(
                user_id=analyst_id,
                email=analyst_email,
                password_hash=get_password_hash("Analyst123!"),
                full_name="Security Analyst",
                role="analyst"
            ))
            await session.commit()
            print("✓ Created Admin and Analyst users.")
        else:
            admin_id = uuid.UUID(str(admin_row))
            print("· Admin/Analyst users already exist, skipping.")

        client_row = (await session.execute(
            text("SELECT user_id FROM users WHERE role='client' LIMIT 1")
        )).scalar()
        if not client_row:
            client_id = uuid.uuid4()
            session.add(User(
                user_id=client_id,
                email="client@vulnara.com",
                password_hash=get_password_hash("Client123!"),
                full_name="Demo Client",
                role="client"
            ))
            await session.commit()
            print("✓ Created Demo Client.")
        else:
            client_id = uuid.UUID(str(client_row))
            print("· Demo Client already exists, skipping.")

        # ── 2. CVE Definitions (required before vulns that reference them) ────
        cve_rows = [
            ("CVE-2021-44228", "Apache Log4j2 JNDI features used in configuration, log messages, and parameters do not protect against attacker-controlled LDAP and other JNDI related endpoints — Log4Shell RCE.", 10.0, "CRITICAL"),
            ("CVE-2019-11043",  "In PHP versions 7.1.x below 7.1.33, 7.2.x below 7.2.24 and 7.3.x below 7.3.11 in certain configurations of FPM setup it is possible to cause FPM module to write past allocated buffers into the space reserved for FCGI protocol data, thus opening the possibility of remote code execution.", 9.8, "CRITICAL"),
        ]
        for cve_id, desc, score, sev in cve_rows:
            exists = (await session.execute(
                text("SELECT 1 FROM cve_definitions WHERE cve_id=:c"), {"c": cve_id}
            )).scalar()
            if not exists:
                session.add(CVEDefinition(
                    cve_id=cve_id,
                    description=desc,
                    cvss_v3_score=score,
                    severity=sev,
                    source="NVD"
                ))
        await session.commit()
        print("✓ CVE definitions ready.")

        # ── 3. Scans ──────────────────────────────────────────────────────────
        DEMO_TARGET = "https://demo.vulnerable-app.com"
        existing_scan = (await session.execute(
            text("SELECT scan_id FROM scans WHERE target=:t AND user_id=:u LIMIT 1"),
            {"t": DEMO_TARGET, "u": str(client_id)}
        )).scalar()

        now = datetime.now(timezone.utc)

        if not existing_scan:
            scan_id = uuid.uuid4()
            scan2_id = uuid.uuid4()
            session.add(Scan(
                scan_id=scan_id,
                user_id=client_id,
                target=DEMO_TARGET,
                status="COMPLETED",
                active_testing_enabled=True,
                authorization_confirmed=True,
                authorization_justification="Authorized for demo purposes",
                started_at=now - timedelta(hours=1),
                completed_at=now
            ))
            session.add(Scan(
                scan_id=scan2_id,
                user_id=client_id,
                target="10.0.0.55",
                status="PENDING",
                active_testing_enabled=False,
                authorization_confirmed=True,
                authorization_justification="Authorized for internal subnets"
            ))
            await session.commit()
            print("✓ Created Scans.")
        else:
            scan_id = uuid.UUID(str(existing_scan))
            print("· Scans already exist, skipping.")

        # ── 4. Vulnerabilities ────────────────────────────────────────────────
        existing_vuln_count = (await session.execute(
            text("SELECT COUNT(*) FROM vulnerabilities WHERE scan_id=:sid"),
            {"sid": str(scan_id)}
        )).scalar()

        vulns = []
        if not existing_vuln_count:
            vuln_data = [
                # (cve_id, title, cvss_score Numeric(3,1) max=9.9, severity)
                ("CVE-2021-44228", "Log4Shell RCE",           9.8, "CRITICAL"),
                (None,             "SQL Injection in /login",  8.5, "HIGH"),
                ("CVE-2019-11043", "PHP-FPM RCE",             9.8, "CRITICAL"),
                (None,             "Reflected XSS on /search", 6.1, "MEDIUM"),
                (None,             "Missing Security Headers",  2.0, "LOW"),
            ]
            for cve_id, title, cvss, severity in vuln_data:
                v = Vulnerability(
                    vuln_id=uuid.uuid4(),
                    scan_id=scan_id,
                    cve_id=cve_id,            # FK to cve_definitions; None is fine (nullable)
                    host="10.0.0.55",
                    port=443,
                    service_name="HTTPS",
                    severity=severity,
                    cvss_score=cvss,           # Numeric(3,1): 0.0–9.9
                    confidence_score=0.95,     # Numeric(3,2): 0.00–9.99 fraction
                    ai_reasoning=(
                        f"AI confirmed {title} based on signature match "
                        "and active testing payload response."
                    ),
                    status="OPEN"
                )
                session.add(v)
                vulns.append(v)
            await session.commit()
            print(f"✓ Created {len(vulns)} Vulnerabilities.")
        else:
            rows = (await session.execute(
                text("SELECT vuln_id FROM vulnerabilities WHERE scan_id=:sid ORDER BY discovered_at"),
                {"sid": str(scan_id)}
            )).fetchall()
            for row in rows:
                obj = object.__new__(Vulnerability)
                obj.vuln_id = uuid.UUID(str(row[0]))
                vulns.append(obj)
            print(f"· Vulnerabilities already exist ({len(vulns)} found), skipping insert.")

        # ── 5. Threat Logs ────────────────────────────────────────────────────
        existing_logs = (await session.execute(
            text("SELECT COUNT(*) FROM threat_logs WHERE scan_id=:sid"),
            {"sid": str(scan_id)}
        )).scalar()

        if not existing_logs and len(vulns) >= 4:
            session.add_all([
                ThreatLog(
                    scan_id=scan_id,
                    vuln_id=vulns[1].vuln_id,
                    attack_type="SQLI",
                    target_url=f"{DEMO_TARGET}/login",
                    target_param="username",
                    payload_used="' OR 1=1--",
                    ai_verified=True,
                    verification_notes="Login bypassed successfully.",
                    risk_rating="HIGH"
                ),
                ThreatLog(
                    scan_id=scan_id,
                    vuln_id=vulns[3].vuln_id,
                    attack_type="XSS",
                    target_url=f"{DEMO_TARGET}/search",
                    target_param="q",
                    payload_used="<script>alert(1)</script>",
                    ai_verified=True,
                    verification_notes="Alert executed in sandboxed headless browser.",
                    risk_rating="MEDIUM"
                ),
                ThreatLog(
                    scan_id=scan_id,
                    attack_type="CMDI",
                    target_url=f"{DEMO_TARGET}/ping",
                    target_param="ip",
                    payload_used="127.0.0.1; id",
                    ai_verified=True,
                    verification_notes="Command executed, return output contained 'uid='",
                    risk_rating="HIGH"
                ),
            ])
            await session.commit()
            print("✓ Created Threat Logs.")
        else:
            print("· Threat Logs already exist or insufficient vulns, skipping.")

        # ── 6. Remediations ───────────────────────────────────────────────────
        existing_remediations = (await session.execute(
            text("SELECT COUNT(*) FROM remediations WHERE vuln_id=:vid"),
            {"vid": str(vulns[0].vuln_id)}
        )).scalar() if vulns else 1  # skip if no vulns

        if not existing_remediations and len(vulns) >= 4:
            session.add_all([
                Remediation(
                    vuln_id=vulns[0].vuln_id,
                    target_os="Linux",
                    executive_summary="Update log4j to version 2.17.1 immediately to patch Log4Shell.",
                    technical_script="apt-get update && apt-get install --only-upgrade log4j2",
                    ai_confidence=0.99,
                    status="EXECUTED",
                    reviewed_by=admin_id,
                    reviewed_at=now,
                    executed_at=now
                ),
                Remediation(
                    vuln_id=vulns[1].vuln_id,
                    target_os="Any",
                    executive_summary="Use parameterized queries in the login form to prevent SQL injection.",
                    technical_script=(
                        "# Python example update\n"
                        "- cursor.execute(f\"SELECT * FROM users WHERE username='{username}'\")\n"
                        "+ cursor.execute(\"SELECT * FROM users WHERE username=%s\", (username,))"
                    ),
                    ai_confidence=0.95,
                    status="PENDING"
                ),
                Remediation(
                    vuln_id=vulns[3].vuln_id,
                    target_os="Any",
                    executive_summary="Escape user input before rendering in the search template.",
                    technical_script="import html\nescaped_query = html.escape(request.GET['q'])",
                    ai_confidence=0.90,
                    status="APPROVED",
                    reviewed_by=admin_id,
                    reviewed_at=now
                ),
            ])
            await session.commit()
            print("✓ Created Remediations.")
        else:
            print("· Remediations already exist, skipping.")
        
        print("\n✅ Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed_db())
