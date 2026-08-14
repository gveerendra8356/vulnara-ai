"""
Central configuration for the Vulnara web Selenium suite.

Every value here is derived from the actual vulnara-web source (not assumed):
  - BrowserRouter with basename "/vulnara-ai/"        -> vulnara-web/src/App.jsx, vite.config.js
  - VITE_USE_MOCK flips the whole app to an in-memory  -> vulnara-web/src/lib/api.js
    mock backend, explicitly built for exactly this kind of
    "fully clickable without a real backend" testing (see
    vulnara-web/.env.example comment on VITE_USE_MOCK).
  - Seeded mock users/scans/vulns/remediations         -> vulnara-web/src/lib/mockData.js
  - Real (non-mock) seeded DB accounts                 -> backend/seed_db.py, docs/testing_guide.md

Why we test against a CI-local `vite preview` build (Mock Mode ON) instead of
the deployed GitHub Pages site (Mock Mode OFF, real Render backend):
  1. docs/testing_guide.md and .env.example both say Mock Mode is what makes
     the web app "fully clickable" -- Auth, Scans, Vulnerabilities, Remediation
     Queue and Admin are not yet backed by the real API contract everywhere.
  2. The deployed site talks to a free-tier Render backend that cold-starts
     and can 502/timeout for 30-50s -- that would make CI flaky for reasons
     that have nothing to do with the web app under test.
  3. vite preview's dev server serves the exact production build (vite build)
     with SPA history-fallback built in, entirely inside the GitHub Actions
     runner -- no external network calls, deterministic, fast.
  4. This mirrors the base-URL pattern already used for this author's other
     projects (http://localhost:4173/<repo>/) -- see the sample
     Automation_Test_Report.xlsx "Execution Metrics" sheet.
"""

import os

# ---------------------------------------------------------------------------
# Base URL
# ---------------------------------------------------------------------------
# vite.config.js sets base: "/vulnara-ai/". `vite preview` serves the built
# app under that same base path on the port below.
PREVIEW_PORT = os.environ.get("PREVIEW_PORT", "4173")
BASE_URL = os.environ.get("BASE_URL", f"http://127.0.0.1:{PREVIEW_PORT}/vulnara-ai/").rstrip("/") + "/"

# ---------------------------------------------------------------------------
# Routes (relative to BASE_URL, no leading slash -- BrowserRouter, not
# HashRouter, so these are plain paths: BASE_URL + route)
# ---------------------------------------------------------------------------
ROUTES = {
    "login": "login",
    "register": "register",
    "dashboard": "",
    "scans": "scans",
    "new_scan": "scans/new",
    "scan_detail": "scans/scan-1001",
    "vuln_detail": "vulnerabilities/vuln-2001",
    "remediations": "remediations",
    "remediation_review": "remediations/rem-4001",
    "admin_config": "admin/config",
    "admin_cve": "admin/cve",
    "unknown": "this-route-does-not-exist-1234",
}

# Every route a signed-in, non-admin user should be able to reach.
CORE_PROTECTED_ROUTES = ["dashboard", "scans", "new_scan", "scan_detail", "vuln_detail",
                          "remediations", "remediation_review"]

# Admin-only routes (ProtectedRoute requireAdmin -> src/components/ProtectedRoute.jsx)
ADMIN_ROUTES = ["admin_config", "admin_cve"]

ALL_PROTECTED_ROUTES = CORE_PROTECTED_ROUTES + ADMIN_ROUTES

# Pages with no nav chrome (outside AppLayout)
PUBLIC_ROUTES = ["login", "register"]

# ---------------------------------------------------------------------------
# Seeded Mock Mode accounts (src/lib/mockData.js -> mockUsers)
# Mock login() matches by email only; ANY password is accepted
# (src/lib/mockApi.js login(): `state.users.find(u => u.email === email) || mockUser`).
# An email that doesn't match a seeded user silently logs in as the default
# analyst (mockUser) -- so "client" role coverage registers a fresh account
# via RegisterPage first, in the same browser session, then logs in with it.
# ---------------------------------------------------------------------------
MOCK_PASSWORD = "TestPass123!"  # accepted verbatim by Mock Mode; value is irrelevant

CREDENTIALS = {
    "analyst": {"email": "analyst@vulnara.dev", "password": MOCK_PASSWORD, "full_name": "Priya Analyst"},
    "admin": {"email": "admin@vulnara.dev", "password": MOCK_PASSWORD, "full_name": "Arjun Admin"},
}

# An email guaranteed not to match a seeded mock user -> exercises the
# "falls back to default analyst" behavior deliberately.
UNSEEDED_EMAIL = "nobody-seeded@vulnara.dev"

# ---------------------------------------------------------------------------
# Seeded mock data IDs (src/lib/mockData.js) used by detail-page tests
# ---------------------------------------------------------------------------
SEED = {
    "scan_completed": "scan-1001",       # COMPLETED, active_testing_enabled: true
    "scan_in_progress": "scan-1003",     # IN_PROGRESS
    "scan_failed": "scan-1004",          # FAILED
    "vuln_critical_open": "vuln-2001",   # CRITICAL / OPEN
    "vuln_false_positive": "vuln-2005",  # INFO / FALSE_POSITIVE
    "remediation_pending": "rem-4001",   # PENDING
    "remediation_approved": "rem-4002",  # APPROVED
    "config_key": "ai_confidence_threshold",
}

# ---------------------------------------------------------------------------
# localStorage keys the app reads/writes (src/lib/httpClient.js)
# ---------------------------------------------------------------------------
TOKEN_KEY = "vulnara_access_token"

# ---------------------------------------------------------------------------
# Timeouts / retries
# ---------------------------------------------------------------------------
DEFAULT_WAIT = int(os.environ.get("SELENIUM_DEFAULT_WAIT", "12"))
SHORT_WAIT = 4
HEALTHCHECK_RETRIES = 30
HEALTHCHECK_DELAY_SECONDS = 2

HEADLESS = os.environ.get("HEADLESS", "true").lower() != "false"
