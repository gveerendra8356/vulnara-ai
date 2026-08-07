"""
triage/nvd_client.py

Async client for the NVD (National Vulnerability Database) REST API v2.0.
https://services.nvd.nist.gov/rest/json/cves/2.0

WHY KEYWORD SEARCH, NOT CPE MATCHING:
The "correct" way to look up CVEs for a specific product/version is via
CPE (Common Platform Enumeration) matching, e.g. cpe:2.3:a:apache:http_server:2.4.41.
Building a reliable CPE resolver from a raw nmap banner string
("Apache httpd 2.4.41 ((Ubuntu))") is its own significant project (fuzzy
vendor/product name mapping, version normalization, etc.) and is exactly
the kind of ambiguous judgment call we're offloading to the AI layer
instead. So this client does a broader `keywordSearch` (e.g. "Apache
2.4.41") and returns a set of *candidate* CVEs -- it is deliberately
over-inclusive. It is Gemini's job (see gemini_client.py) to decide which
candidates are actually relevant to the exact banner it was given, and
which are false positives (e.g. keyword collisions with unrelated
products). This mirrors your spec: "AI cross-references service/version
... scores severity/confidence, filters false positives."

RATE LIMITING:
Without an API key, NVD allows 5 requests per rolling 30s window.
With a free API key (https://nvd.nist.gov/developers/request-an-api-key),
that jumps to 50 requests per 30s. Get a key -- it's free and instant,
and 5/30s will bottleneck triage on any scan with more than a couple of
open ports. This client rate-limits itself either way, using whichever
window applies based on whether NVD_API_KEY is set.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_API_KEY = os.environ.get("NVD_API_KEY")  # optional but strongly recommended


class NVDRateLimiter:
    """
    Simple async sliding-window rate limiter matching NVD's published
    limits. Shared across the process (module-level instance below) since
    the limit is per API key / per source IP, not per request.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < self.window_seconds]

            if len(self._timestamps) >= self.max_requests:
                sleep_for = self.window_seconds - (now - self._timestamps[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)

            self._timestamps.append(time.monotonic())


_rate_limiter = NVDRateLimiter(
    max_requests=50 if NVD_API_KEY else 5,
    window_seconds=30.0,
)


class NVDClient:
    def __init__(self, timeout_seconds: float = 15.0):
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        await self._client.aclose()

    async def search_cves(
        self,
        service_name: str,
        service_version: Optional[str],
        max_results: int = 8,
    ) -> list[dict[str, Any]]:
        """
        Returns a list of candidate CVE dicts:
        { cve_id, description, cvss_v3_score, severity, published_date,
          last_modified_date, raw_data }

        Returns an empty list (not an exception) if NVD has nothing --
        a plain-text banner like "SSH-2.0-OpenSSH" with no version isn't
        always going to have a keyword match, and that's a legitimate
        "no known CVEs found" result, not a failure.
        """
        if not service_name:
            return []

        keyword = service_name if not service_version else f"{service_name} {service_version}"

        params = {
            "keywordSearch": keyword,
            "resultsPerPage": max_results,
        }
        headers = {"apiKey": NVD_API_KEY} if NVD_API_KEY else {}

        await _rate_limiter.acquire()

        resp = await self._client.get(NVD_BASE_URL, params=params, headers=headers)

        if resp.status_code == 429:
            # Defensive fallback: even with our own limiter, NVD occasionally
            # 429s under load. Back off once and retry rather than losing
            # this finding's CVE context entirely.
            await asyncio.sleep(6.0)
            resp = await self._client.get(NVD_BASE_URL, params=params, headers=headers)

        resp.raise_for_status()
        payload = resp.json()

        return [self._parse_cve(v["cve"]) for v in payload.get("vulnerabilities", [])]

    @staticmethod
    def _parse_cve(cve_raw: dict[str, Any]) -> dict[str, Any]:
        cve_id = cve_raw.get("id")

        # English description, falling back to the first available.
        descriptions = cve_raw.get("descriptions", [])
        description = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            descriptions[0]["value"] if descriptions else "",
        )

        # CVSS v3.1 preferred, fall back to v3.0, then v2 if that's all NVD has.
        metrics = cve_raw.get("metrics", {})
        cvss_score = None
        severity = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            entries = metrics.get(key)
            if entries:
                cvss_data = entries[0].get("cvssData", {})
                cvss_score = cvss_data.get("baseScore")
                severity = entries[0].get("baseSeverity") or cvss_data.get("baseSeverity")
                break

        def _parse_dt(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                return None

        return {
            "cve_id": cve_id,
            "description": description,
            "cvss_v3_score": cvss_score,
            "severity": severity,
            "published_date": _parse_dt(cve_raw.get("published")),
            "last_modified_date": _parse_dt(cve_raw.get("lastModified")),
            "raw_data": cve_raw,
        }
