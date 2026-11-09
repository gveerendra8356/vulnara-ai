"""
load-tests/config.py — environment configuration for the Vulnara load suite.

All values are overridable via environment variables so the same suite runs
unchanged locally and on GitHub-hosted runners.
"""

import os

# The backend API under test. In CI we start a local uvicorn instance with a
# SQLite DB (see .github/workflows/deploy.yml, the load-tests job), so the
# default points at localhost. Never point this at a third-party system.
BASE_URL = os.environ.get("LOAD_BASE_URL", "http://127.0.0.1:8000")

# Seeded credentials (backend/seed_db.py creates these). An analyst account is
# enough for the read-heavy endpoints the load profile exercises.
LOAD_USER_EMAIL = os.environ.get("LOAD_USER_EMAIL", "analyst@vulnara.com")
LOAD_USER_PASSWORD = os.environ.get("LOAD_USER_PASSWORD", "Analyst123!")

# A fallback admin account, used by the admin-weighted scenarios.
LOAD_ADMIN_EMAIL = os.environ.get("LOAD_ADMIN_EMAIL", "admin@vulnara.com")
LOAD_ADMIN_PASSWORD = os.environ.get("LOAD_ADMIN_PASSWORD", "Admin123!")

# CI-friendly defaults (overridden by the workflow for the real run).
USERS = int(os.environ.get("LOAD_USERS", "20"))
SPAWN_RATE = float(os.environ.get("LOAD_SPAWN_RATE", "4"))
RUN_TIME = os.environ.get("LOAD_RUN_TIME", "60s")
