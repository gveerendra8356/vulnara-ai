"""
load-tests/locustfile.py — Locust load profile for the Vulnara backend API.

This exercises ONLY the web application's own backend (started locally in CI),
never a third-party system. Request names are grouped (e.g. "GET /scans/:id")
so per-endpoint statistics map cleanly onto thresholds.py and the generated
report, regardless of how many distinct ids are hit.

Run headless (what CI does):
    locust -f locustfile.py --headless -u 20 -r 4 -t 60s \
           --csv reports/load --csv-full-history --only-summary
"""

from __future__ import annotations

import random

from locust import HttpUser, TaskSet, between, task

import config


def _login(client, email: str, password: str) -> str | None:
    with client.post(
        "/auth/login",
        json={"email": email, "password": password},
        name="POST /auth/login",
        catch_response=True,
    ) as resp:
        if resp.status_code == 200:
            try:
                token = resp.json().get("access_token")
            except Exception:
                token = None
            if token:
                resp.success()
                return token
            resp.failure("login returned 200 but no access_token")
            return None
        # 401 against a fresh DB (accounts not seeded) should not be counted as
        # a load failure of the endpoint itself — the endpoint responded fine.
        if resp.status_code in (400, 401):
            resp.success()
            return None
        resp.failure(f"login HTTP {resp.status_code}")
        return None


class AnalystBehaviour(TaskSet):
    """Read-heavy workload mirroring how an analyst uses the dashboard."""

    def on_start(self):
        self.token = _login(self.client, config.LOAD_USER_EMAIL, config.LOAD_USER_PASSWORD)
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.scan_ids: list[str] = []

    @task(5)
    def list_scans(self):
        with self.client.get("/scans", headers=self.headers, name="GET /scans",
                             catch_response=True) as r:
            if r.status_code == 200:
                r.success()
                try:
                    data = r.json()
                    items = data if isinstance(data, list) else data.get("items", [])
                    self.scan_ids = [s.get("scan_id") for s in items if s.get("scan_id")][:10]
                except Exception:
                    pass
            elif r.status_code in (401, 403):
                r.success()  # auth gate working, not a load fault
            else:
                r.failure(f"HTTP {r.status_code}")

    @task(3)
    def overview(self):
        self._get("/overview", "GET /overview")

    @task(3)
    def remediations(self):
        self._get("/remediations", "GET /remediations")

    @task(2)
    def departments(self):
        self._get("/departments", "GET /departments")

    @task(2)
    def schedules(self):
        self._get("/schedules", "GET /schedules")

    @task(2)
    def me(self):
        self._get("/auth/me", "GET /auth/me")

    @task(2)
    def scan_detail(self):
        if not self.scan_ids:
            return
        sid = random.choice(self.scan_ids)
        self._get(f"/scans/{sid}", "GET /scans/:id")

    @task(1)
    def scan_risk(self):
        if not self.scan_ids:
            return
        sid = random.choice(self.scan_ids)
        self._get(f"/scans/{sid}/risk", "GET /scans/:id/risk")

    @task(2)
    def ml_analyze(self):
        payload = {
            "cvss_score": round(random.uniform(1, 10), 1),
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "cve_id": random.choice([None, "CVE-2021-44228", "CVE-2022-0543"]),
            "service_name": random.choice(["http", "ssh", "redis", "mysql", "telnet"]),
            "service_version": random.choice([None, "1.0", "5.0.1"]),
            "port": random.choice([22, 80, 443, 6379, 3306]),
            "confidence_score": round(random.uniform(0.2, 0.99), 2),
        }
        with self.client.post("/ml/analyze", json=payload, headers=self.headers,
                              name="POST /ml/analyze", catch_response=True) as r:
            if r.status_code in (200, 401, 403):
                r.success()
            else:
                r.failure(f"HTTP {r.status_code}")

    def _get(self, path: str, name: str):
        with self.client.get(path, headers=self.headers, name=name, catch_response=True) as r:
            if r.status_code in (200, 401, 403, 404):
                r.success()  # endpoint responded; auth/empty are not load faults
            else:
                r.failure(f"HTTP {r.status_code}")


class HealthBehaviour(TaskSet):
    """Unauthenticated liveness traffic — the cheapest, highest-frequency path."""

    @task
    def health(self):
        with self.client.get("/health", name="GET /health", catch_response=True) as r:
            r.success() if r.status_code == 200 else r.failure(f"HTTP {r.status_code}")


class VulnaraUser(HttpUser):
    host = config.BASE_URL
    wait_time = between(0.2, 1.2)
    tasks = {AnalystBehaviour: 8, HealthBehaviour: 2}
