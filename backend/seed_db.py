import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.core.db import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models.scan import Scan
from app.models.triage_models import Vulnerability, Remediation
from app.models.threat_log import ThreatLog
from app.models.user import User
from app.core.security import get_password_hash

async def seed_db():
    SessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with SessionLocal() as session:
        print("Seeding database...")
        
        # 1. Create Users
        admin_email = "admin@vulnara.com"
        analyst_email = "analyst@vulnara.com"
        
        # Check if users already exist
        admin = (await session.execute(text(f"SELECT user_id FROM users WHERE email='{admin_email}'"))).scalar()
        if not admin:
            admin_id = uuid.uuid4()
            session.add(User(
                user_id=admin_id,
                email=admin_email,
                password_hash=get_password_hash("Admin123!"),
                full_name="System Admin",
                role="admin"
            ))
            
            analyst_id = uuid.uuid4()
            session.add(User(
                user_id=analyst_id,
                email=analyst_email,
                password_hash=get_password_hash("Analyst123!"),
                full_name="Security Analyst",
                role="analyst"
            ))
            await session.commit()
            print("Created Admin and Analyst users.")
        else:
            admin_id = uuid.UUID(admin)
            print("Users already exist.")

        # Let's get any client user to own the scan. We'll pick the first client.
        client = (await session.execute(text("SELECT user_id FROM users WHERE role='client' LIMIT 1"))).scalar()
        if not client:
            client_id = uuid.uuid4()
            session.add(User(
                user_id=client_id,
                email="client@vulnara.com",
                password_hash=get_password_hash("Client123!"),
                full_name="Demo Client",
                role="client"
            ))
            await session.commit()
            print("Created Demo Client.")
        else:
            # client might be a string in sqlite
            if isinstance(client, str):
                client_id = uuid.UUID(client)
            else:
                client_id = client

        # 2. Create Scans
        scan_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        
        scan = Scan(
            scan_id=scan_id,
            user_id=client_id,
            target="https://demo.vulnerable-app.com",
            status="COMPLETED",
            active_testing_enabled=True,
            authorization_confirmed=True,
            authorization_justification="Authorized for demo purposes",
            started_at=now - timedelta(hours=1),
            completed_at=now
        )
        session.add(scan)
        
        scan2_id = uuid.uuid4()
        scan2 = Scan(
            scan_id=scan2_id,
            user_id=client_id,
            target="10.0.0.55",
            status="PENDING",
            active_testing_enabled=False,
            authorization_confirmed=True,
            authorization_justification="Authorized for internal subnets"
        )
        session.add(scan2)
        await session.commit()
        print("Created Scans.")

        # 3. Create Vulnerabilities
        vulns = []
        vuln_data = [
            ("CVE-2021-44228", "Log4Shell RCE", 9.8, "CRITICAL"),
            (None, "SQL Injection in /login", 8.5, "HIGH"),
            ("CVE-2019-11043", "PHP-FPM RCE", 9.8, "CRITICAL"),
            (None, "Reflected XSS on /search", 6.1, "MEDIUM"),
            (None, "Missing Security Headers", 2.0, "LOW"),
        ]
        
        for cve_id, title, cvss, severity in vuln_data:
            vid = uuid.uuid4()
            v = Vulnerability(
                vuln_id=vid,
                scan_id=scan_id,
                cve_id=cve_id,
                host="10.0.0.55",
                port=443,
                service_name="HTTPS",
                severity=severity,
                cvss_score=cvss,
                confidence_score=95.0,
                ai_reasoning=f"AI confirmed {title} based on signature match and active testing payload response.",
                status="OPEN"
            )
            session.add(v)
            vulns.append(v)
            
        await session.commit()
        print("Created Vulnerabilities.")

        # 4. Create Threat Logs
        t1 = ThreatLog(
            scan_id=scan_id,
            vuln_id=vulns[1].vuln_id,
            attack_type="SQLI",
            target_url="https://demo.vulnerable-app.com/login",
            target_param="username",
            payload_used="' OR 1=1--",
            ai_verified=True,
            verification_notes="Login bypassed successfully.",
            risk_rating="HIGH"
        )
        t2 = ThreatLog(
            scan_id=scan_id,
            vuln_id=vulns[3].vuln_id,
            attack_type="XSS",
            target_url="https://demo.vulnerable-app.com/search",
            target_param="q",
            payload_used="<script>alert(1)</script>",
            ai_verified=True,
            verification_notes="Alert executed in sandboxed headless browser.",
            risk_rating="MEDIUM"
        )
        t3 = ThreatLog(
            scan_id=scan_id,
            attack_type="CMDI",
            target_url="https://demo.vulnerable-app.com/ping",
            target_param="ip",
            payload_used="127.0.0.1; id",
            ai_verified=True,
            verification_notes="Command executed, return output contained 'uid='",
            risk_rating="HIGH"
        )
        session.add_all([t1, t2, t3])
        await session.commit()
        print("Created Threat Logs.")

        # 5. Create Remediations
        r1 = Remediation(
            vuln_id=vulns[0].vuln_id,
            target_os="Linux",
            executive_summary="Update log4j to version 2.17.1 immediately to patch Log4Shell.",
            technical_script="apt-get update && apt-get install --only-upgrade log4j2",
            ai_confidence=0.99,
            status="EXECUTED",
            reviewed_by=admin_id,
            reviewed_at=now,
            executed_at=now
        )
        r2 = Remediation(
            vuln_id=vulns[1].vuln_id,
            target_os="Any",
            executive_summary="Use parameterized queries in the login form to prevent SQL injection.",
            technical_script="""
# Python example update
- cursor.execute(f"SELECT * FROM users WHERE username='{username}'")
+ cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            """,
            ai_confidence=0.95,
            status="PENDING"
        )
        r3 = Remediation(
            vuln_id=vulns[3].vuln_id,
            target_os="Any",
            executive_summary="Escape user input before rendering in the search template.",
            technical_script="import html\nescaped_query = html.escape(request.GET['q'])",
            ai_confidence=0.90,
            status="APPROVED",
            reviewed_by=admin_id,
            reviewed_at=now
        )
        session.add_all([r1, r2, r3])
        await session.commit()
        print("Created Remediations.")
        
        print("Done!")

if __name__ == "__main__":
    asyncio.run(seed_db())
