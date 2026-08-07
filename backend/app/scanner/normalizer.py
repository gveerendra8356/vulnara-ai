"""
normalizer.py

Converts the raw HostResult/OpenPort dataclasses produced by nmap_wrapper
into the structured JSON contract expected downstream.

IMPORTANT SCOPE NOTE:
This normalized payload is the *input to the AI triage layer* (Data Flow 2
in the project spec) — it is NOT written directly into the `Vulnerabilities`
table. The AI triage module (a separate module, not built in this task)
consumes this JSON, cross-references it against CVE_Definitions via Gemini,
assigns severity/cvss/confidence, and is what actually writes rows to
`Vulnerabilities`. Keeping that boundary explicit here so this module
doesn't accidentally take on triage responsibility.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.scanner.nmap_wrapper import HostResult


def normalize_scan_results(
    scan_id: str,
    target: str,
    hosts: list[HostResult],
) -> dict[str, Any]:
    """
    Produces the normalized telemetry JSON for a completed recon pass.

    Shape:
    {
      "scan_id": "uuid",
      "target": "example.com",
      "normalized_at": "2026-08-07T12:00:00Z",
      "hosts": [
        {
          "host": "203.0.113.10",
          "status": "up",
          "open_port_count": 3,
          "ports": [
            {
              "port": 443,
              "protocol": "tcp",
              "service_name": "https",
              "service_version": "nginx 1.24.0",
              "banner": "raw banner text or null"
            }
          ]
        }
      ]
    }
    """
    return {
        "scan_id": scan_id,
        "target": target,
        "normalized_at": datetime.now(timezone.utc).isoformat(),
        "hosts": [_normalize_host(h) for h in hosts],
    }


def _normalize_host(host: HostResult) -> dict[str, Any]:
    return {
        "host": host.ip,
        "status": host.status,
        "open_port_count": len(host.ports),
        "ports": [
            {
                "port": p.port,
                "protocol": p.protocol,
                "service_name": p.service_name,
                "service_version": p.service_version,
                "banner": p.banner,
            }
            for p in host.ports
        ],
    }
