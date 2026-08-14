"""
scripts/run_perf_standalone.py

One-shot driver: boots the same ephemeral server conftest.py uses, logs in
as client1, runs perf_sample.run(), writes reports/perf_stats.json, tears
the server down. Kept separate from the pytest run itself so a perf sample
never affects (or is affected by) the 400-case functional suite's timing.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
BACKEND_DIR = Path(os.environ.get("BACKEND_DIR", ROOT.parent / "backend")).resolve()
DB_PATH = BACKEND_DIR / "perf_sample.db"

sys.path.insert(0, str(THIS_DIR))
import perf_sample  # noqa: E402


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite:///./perf_sample.db"
    env["VULNARA_SECRET_KEY"] = "perf-sample-ephemeral-secret"
    env["CORS_ORIGINS"] = "http://localhost:5173"
    env["PYTHONPATH"] = str(BACKEND_DIR)

    subprocess.run([sys.executable, "apply_migration.py"], cwd=str(BACKEND_DIR), env=env, check=True, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / "seed_test_accounts.py")], cwd=str(BACKEND_DIR), env=env, check=True, capture_output=True)

    port = 8321
    base_url = f"http://127.0.0.1:{port}"
    log_file = open(ROOT / "reports" / "logs" / "perf-server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BACKEND_DIR), env=env, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True,
    )

    try:
        deadline = time.time() + 25
        up = False
        while time.time() < deadline:
            try:
                if httpx.get(f"{base_url}/health", timeout=2).status_code == 200:
                    up = True
                    break
            except Exception:
                pass
            time.sleep(0.3)
        if not up:
            raise RuntimeError("perf-sample server never became healthy")

        login = httpx.post(f"{base_url}/auth/login", json={
            "email": "client1.qa@vulnara-qa-suite.com", "password": "Client1QA123!",
        }, timeout=10)
        login.raise_for_status()
        token = login.json()["access_token"]

        stats = asyncio.run(perf_sample.run(base_url, token))
        out_path = ROOT / "reports" / "perf_stats.json"
        out_path.write_text(json.dumps(stats, indent=2))
        print(json.dumps(stats, indent=2))
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        log_file.close()
        if DB_PATH.exists():
            DB_PATH.unlink()


if __name__ == "__main__":
    main()
