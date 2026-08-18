"""
core/email_alert.py

Sends HTML email alerts when HIGH or CRITICAL vulnerabilities are found
during a scan. Uses Python's stdlib smtplib — no extra dependencies.

Configuration (set in backend/.env):
  SMTP_HOST       e.g. smtp.gmail.com
  SMTP_PORT       e.g. 587
  SMTP_USER       your Gmail address
  SMTP_PASSWORD   Gmail App Password (not your normal password!)
  SMTP_FROM_EMAIL sender address shown in emails (defaults to SMTP_USER)

Gmail setup:
  1. Enable 2-Factor Authentication on your Google account.
  2. Go to https://myaccount.google.com/apppasswords
  3. Create an App Password for "Mail" → copy the 16-char password.
  4. Set SMTP_USER and SMTP_PASSWORD to that address & app password.

Design:
  - Best-effort, never fails a scan. All exceptions are caught and logged.
  - Disabled silently when SMTP_HOST is not configured.
  - Sends rich HTML email with severity badge, CVSS score, and AI reasoning.
"""

from __future__ import annotations

import logging
import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("vulnara.email")

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", SMTP_USER)

# The public URL of the web app (for the "View Scan" button link)
APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://gveerendra8356.github.io/vulnara-ai")

SEVERITY_COLORS = {
    "CRITICAL": "#dc2626",
    "HIGH": "#ea580c",
    "MEDIUM": "#eab308",
    "LOW": "#3b82f6",
    "INFO": "#94a3b8",
}


def _build_html(
    recipient_name: str,
    scan_target: str,
    scan_id: str,
    severity: str,
    service_name: str,
    host: str,
    port: int,
    cvss_score: float | None,
    explanation: str,
) -> str:
    color = SEVERITY_COLORS.get(severity, "#94a3b8")
    scan_url = f"{APP_BASE_URL}/scans/{scan_id}"
    cvss_text = f"{cvss_score:.1f}" if cvss_score else "N/A"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0d1117; color: #e6edf3; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 32px auto; background: #161b22; border-radius: 12px; overflow: hidden; border: 1px solid #30363d; }}
    .header {{ background: linear-gradient(135deg, #0d1117 0%, #1a2332 100%); padding: 32px 32px 24px; border-bottom: 1px solid #30363d; }}
    .header h1 {{ margin: 0 0 4px; font-size: 22px; color: #e6edf3; }}
    .header p {{ margin: 0; color: #8b949e; font-size: 13px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700;
              color: white; background: {color}; letter-spacing: 0.05em; margin-top: 12px; }}
    .body {{ padding: 28px 32px; }}
    .field {{ margin-bottom: 18px; }}
    .field label {{ display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
                    color: #8b949e; margin-bottom: 4px; }}
    .field value {{ display: block; font-size: 14px; color: #e6edf3; font-family: monospace; }}
    .reasoning {{ background: #0d1117; border-left: 3px solid {color}; padding: 14px 16px;
                  border-radius: 0 8px 8px 0; font-size: 13px; color: #c9d1d9; line-height: 1.6; margin-top: 8px; }}
    .cta {{ text-align: center; padding: 24px 32px 32px; }}
    .cta a {{ display: inline-block; background: {color}; color: white; text-decoration: none;
               padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; }}
    .footer {{ text-align: center; padding: 16px; border-top: 1px solid #21262d; color: #8b949e; font-size: 11px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>⚠ Vulnerability Detected</h1>
      <p>Scan of <strong>{scan_target}</strong> found a new finding</p>
      <span class="badge">{severity}</span>
    </div>
    <div class="body">
      <p style="color:#c9d1d9;margin-top:0">Hi {recipient_name},</p>
      <p style="color:#8b949e;font-size:13px">
        A <strong style="color:{color}">{severity}</strong> vulnerability was discovered during your Vulnara scan.
        Review and remediate as soon as possible.
      </p>

      <div class="field">
        <label>Target</label>
        <value>{scan_target}</value>
      </div>
      <div class="field">
        <label>Host / Port</label>
        <value>{host}:{port}</value>
      </div>
      <div class="field">
        <label>Service</label>
        <value>{service_name}</value>
      </div>
      <div class="field">
        <label>CVSS Score</label>
        <value>{cvss_text}</value>
      </div>
      <div class="field">
        <label>AI Analysis</label>
        <div class="reasoning">{explanation[:500]}{'...' if len(explanation) > 500 else ''}</div>
      </div>
    </div>
    <div class="cta">
      <a href="{scan_url}">View Full Scan Report →</a>
    </div>
    <div class="footer">
      Vulnara Vulnerability Intelligence Platform &bull; This is an automated alert
    </div>
  </div>
</body>
</html>"""


def send_vulnerability_alert(
    *,
    recipient_email: str,
    recipient_name: str,
    scan_target: str,
    scan_id: uuid.UUID | str,
    severity: str,
    service_name: str,
    host: str,
    port: int,
    cvss_score: float | None,
    explanation: str,
) -> None:
    """
    Sends an HTML email alert for a HIGH or CRITICAL vulnerability finding.
    Best-effort: all errors are logged and swallowed — never raises.
    """
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.debug(
            "SMTP not configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD missing) — "
            "skipping email alert for %s finding on %s", severity, scan_target
        )
        return

    subject = f"[Vulnara] {severity} Vulnerability Found — {scan_target}"
    html_body = _build_html(
        recipient_name=recipient_name,
        scan_target=scan_target,
        scan_id=str(scan_id),
        severity=severity,
        service_name=service_name,
        host=host,
        port=port,
        cvss_score=cvss_score,
        explanation=explanation,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, [recipient_email], msg.as_string())
        logger.info(
            "Email alert sent to %s for %s finding on %s:%s",
            recipient_email, severity, host, port
        )
    except Exception:
        logger.exception(
            "Failed to send email alert to %s for %s finding — scan continues",
            recipient_email, severity
        )
