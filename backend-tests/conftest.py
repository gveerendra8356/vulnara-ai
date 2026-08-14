"""
conftest.py — Vulnara backend test suite

Spins up a REAL, ephemeral FastAPI + SQLite instance (a subprocess running
`uvicorn app.main:app`) and talks to it over real HTTP for every single
test in this suite, per the "no handler-in-isolation" requirement: this
exercises CORS middleware, JSON parsing, the real JWT auth dependency, and
real async DB round trips end to end -- not just the route function called
directly in-process.

Nothing here ever touches a production database. DATABASE_URL always
points at a throwaway file-based SQLite DB created fresh for the run and
deleted afterwards (BACKEND_DATABASE_URL / BACKEND_TARGET_URL env vars
let you point this at a different ephemeral target -- e.g. a docker
service in CI -- without touching this file).
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest

_FIXTURE_DATA: dict = {}

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------

THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = Path(os.environ.get("BACKEND_DIR", THIS_DIR.parent / "backend")).resolve()

TEST_DB_FILENAME = "ci_test.db"
TEST_DB_PATH = BACKEND_DIR / TEST_DB_FILENAME

HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
PORT = int(os.environ.get("BACKEND_PORT", "0")) or None  # 0/None -> pick a free port
SECRET_KEY = os.environ.get("VULNARA_SECRET_KEY", "ci-ephemeral-secret-key-do-not-use-in-prod")

# Set to an already-running instance (e.g. `http://127.0.0.1:8000`) to skip
# spawning a subprocess entirely and test against a server you started
# yourself. Used by `--live-server-url` style workflows / local debugging.
EXTERNAL_BASE_URL = os.environ.get("BACKEND_TARGET_URL")

STARTUP_TIMEOUT_S = 25
HEALTH_POLL_INTERVAL_S = 0.3

# ---------------------------------------------------------------------------
# Seeded test accounts
#
# Two same-role client accounts are essential for cross-tenant / IDOR
# authorization tests, not just "logged in vs not logged in" checks
# (client1 owns fixture data; client2 exists purely to attempt to read it).
# Credentials are test-only, generated fresh for this ephemeral DB, and are
# never valid against any deployed environment.
# ---------------------------------------------------------------------------

ADMIN_EMAIL = "admin.qa@vulnara-qa-suite.com"
ADMIN_PASSWORD = "AdminQA123!"

ANALYST_EMAIL = "analyst.qa@vulnara-qa-suite.com"
ANALYST_PASSWORD = "AnalystQA123!"

CLIENT1_EMAIL = "client1.qa@vulnara-qa-suite.com"
CLIENT1_PASSWORD = "Client1QA123!"

CLIENT2_EMAIL = "client2.qa@vulnara-qa-suite.com"
CLIENT2_PASSWORD = "Client2QA123!"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Session-scoped: ephemeral server lifecycle
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url():
    if EXTERNAL_BASE_URL:
        yield EXTERNAL_BASE_URL.rstrip("/")
        return

    port = PORT or _free_port()
    url = f"http://{HOST}:{port}"

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///./{TEST_DB_FILENAME}"
    env["VULNARA_SECRET_KEY"] = SECRET_KEY
    env["CORS_ORIGINS"] = env.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    env["ENVIRONMENT"] = "development"
    env.setdefault("PYTHONUNBUFFERED", "1")

    # 1. Create schema against the ephemeral DB (mirrors apply_migration.py).
    migrate = subprocess.run(
        [sys.executable, "apply_migration.py"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert migrate.returncode == 0, (
        f"Failed to create ephemeral schema.\nstdout={migrate.stdout}\nstderr={migrate.stderr}"
    )

    # 2. Seed the four QA accounts directly (admin can't be self-registered
    #    via the API -- POST /auth/register only allows client/analyst roles
    #    by design, so the first admin has to be created out-of-band, same
    #    as a real deployment would via a one-off script).
    seed_env = dict(env)
    seed_env["PYTHONPATH"] = str(BACKEND_DIR) + os.pathsep + seed_env.get("PYTHONPATH", "")
    seed = subprocess.run(
        [sys.executable, str(THIS_DIR / "seed_test_accounts.py")],
        cwd=str(BACKEND_DIR),
        env=seed_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert seed.returncode == 0, (
        f"Failed to seed QA accounts.\nstdout={seed.stdout}\nstderr={seed.stderr}"
    )

    # 2b. Seed one scan + vulnerability + two remediations directly (there is
    #     no POST /vulnerabilities endpoint -- they only come from the scan
    #     pipeline -- so authorization/functional tests need a known,
    #     pre-existing record to point at).
    fixture_seed = subprocess.run(
        [sys.executable, str(THIS_DIR / "seed_fixture_data.py")],
        cwd=str(BACKEND_DIR),
        env=seed_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert fixture_seed.returncode == 0, (
        f"Failed to seed fixture data.\nstdout={fixture_seed.stdout}\nstderr={fixture_seed.stderr}"
    )
    global _FIXTURE_DATA
    _FIXTURE_DATA = json.loads(fixture_seed.stdout.strip().splitlines()[-1])

    # 3. Launch the real server as a subprocess.
    log_path = THIS_DIR / "reports" / "logs" / "backend-server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "w")

    popen_kwargs = {}
    if os.name != "nt":
        popen_kwargs["preexec_fn"] = os.setsid  # own process group -> clean shutdown

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", HOST, "--port", str(port), "--log-level", "info",
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        **popen_kwargs,
    )

    # 4. Wait for /health to answer.
    deadline = time.time() + STARTUP_TIMEOUT_S
    up = False
    last_err = None
    while time.time() < deadline:
        if proc.poll() is not None:
            log_file.flush()
            raise RuntimeError(
                f"Backend process exited early (code={proc.returncode}). "
                f"See {log_path} for details."
            )
        try:
            r = httpx.get(f"{url}/health", timeout=2)
            if r.status_code == 200:
                up = True
                break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        time.sleep(HEALTH_POLL_INTERVAL_S)

    if not up:
        proc.terminate()
        raise RuntimeError(f"Backend never became healthy at {url}/health ({last_err})")

    yield url

    # 5. Teardown.
    try:
        if os.name != "nt":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except Exception:  # noqa: BLE001
        proc.kill()
    log_file.close()


@pytest.fixture
async def client(base_url):
    async with httpx.AsyncClient(base_url=base_url, timeout=15) as c:
        yield c


# ---------------------------------------------------------------------------
# Authenticated-session fixtures (real login calls against the real server)
# ---------------------------------------------------------------------------

async def _login(base_url: str, email: str, password: str) -> dict:
    async with httpx.AsyncClient(base_url=base_url, timeout=15) as c:
        r = await c.post("/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()


@pytest.fixture(scope="session")
def admin_session(base_url):
    return asyncio.run(_login(base_url, ADMIN_EMAIL, ADMIN_PASSWORD))


@pytest.fixture(scope="session")
def analyst_session(base_url):
    return asyncio.run(_login(base_url, ANALYST_EMAIL, ANALYST_PASSWORD))


@pytest.fixture(scope="session")
def client1_session(base_url):
    return asyncio.run(_login(base_url, CLIENT1_EMAIL, CLIENT1_PASSWORD))


@pytest.fixture(scope="session")
def client2_session(base_url):
    return asyncio.run(_login(base_url, CLIENT2_EMAIL, CLIENT2_PASSWORD))


def auth_headers(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['access_token']}"}


@pytest.fixture
def admin_headers(admin_session):
    return auth_headers(admin_session)


@pytest.fixture
def analyst_headers(analyst_session):
    return auth_headers(analyst_session)


@pytest.fixture
def client1_headers(client1_session):
    return auth_headers(client1_session)


@pytest.fixture
def client2_headers(client2_session):
    return auth_headers(client2_session)


@pytest.fixture
def unique_email():
    """A fresh, never-before-seen email for register-flow tests."""
    return f"qa.{uuid.uuid4().hex[:12]}@vulnara-qa-suite.com"


# ---------------------------------------------------------------------------
# Fixture data: a scan + vulnerability owned by client1, used across
# functional / authorization / DAST tests so we're not re-creating scan
# rows from scratch in every test.
# ---------------------------------------------------------------------------

async def _create_owned_scan(base_url: str, headers: dict) -> dict:
    async with httpx.AsyncClient(base_url=base_url, timeout=15) as c:
        r = await c.post(
            "/scans",
            headers=headers,
            json={
                "target": "scanme.qa.vulnara.test",
                "authorization_confirmed": True,
                "authorization_justification": "QA regression suite - synthetic in-house target.",
                "active_testing_enabled": False,
            },
        )
        r.raise_for_status()
        return r.json()


@pytest.fixture(scope="session")
def client1_scan(base_url, client1_session):
    return asyncio.run(_create_owned_scan(base_url, auth_headers(client1_session)))


# ---------------------------------------------------------------------------
# Directly-seeded fixture data (scan/vulnerability/remediation) -- see
# seed_fixture_data.py. base_url must already have run (it populates
# _FIXTURE_DATA as a side effect of starting the server), so every fixture
# below depends on it even though it doesn't use the URL itself.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seeded_scan(base_url):
    return {"scan_id": _FIXTURE_DATA["scan_id"]}


@pytest.fixture(scope="session")
def seeded_vulnerability(base_url):
    return {"vuln_id": _FIXTURE_DATA["vuln_id"], "scan_id": _FIXTURE_DATA["scan_id"]}


@pytest.fixture(scope="session")
def seeded_remediation(base_url):
    return {"remediation_id": _FIXTURE_DATA["remediation_id"], "vuln_id": _FIXTURE_DATA["vuln_id"]}


@pytest.fixture(scope="session")
def seeded_remediation_2(base_url):
    return {"remediation_id": _FIXTURE_DATA["remediation_id_2"], "vuln_id": _FIXTURE_DATA["vuln_id"]}
