"""
test_vulnara_features.py

Fast, self-contained tests for Vulnara's current feature set, run in-process
against the ASGI app with a throwaway SQLite database (no external server).

Covers:
  - auth: login, analyst-only self-registration, forgot/reset password
  - departments: admin-only management + analyst assignment
  - RBAC: department-scoped scan visibility (analyst sees only their dept)
  - ML: the vulnerability-priority predictor endpoint
  - overview: organization-wide vs department-scoped
"""

from __future__ import annotations

import os
import uuid

# Point the app at a throwaway DB BEFORE importing it (the engine binds at import).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_vulnara_features.db")
os.environ.setdefault("VULNARA_SECRET_KEY", "test-secret-key")
os.environ.setdefault("GROQ_API_KEY", "test-not-used-here")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.scan import Base
from app.models import (  # noqa: F401 -- register all tables before create_all
    user, scan, department, triage_models, threat_log,
    token_denylist, device_token, system_config,
)
from app.core.db import engine, AsyncSessionLocal
from app.core.security import get_password_hash, create_password_reset_token
from app.models.user import User
from app.models.department import Department

ADMIN = ("admin@t.com", "Admin123!")
ALPHA = ("a.alpha@t.com", "Pass123!")   # analyst in department "Alpha"
NODEPT = ("a.none@t.com", "Pass123!")   # analyst with no department


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def api():
    """Fresh schema + seed + in-process client for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as s:
        dept = Department(department_id=uuid.uuid4(), name="Alpha", description="test dept")
        s.add(dept)
        s.add(User(user_id=uuid.uuid4(), email=ADMIN[0], password_hash=get_password_hash(ADMIN[1]),
                   full_name="Admin", role="admin"))
        s.add(User(user_id=uuid.uuid4(), email=ALPHA[0], password_hash=get_password_hash(ALPHA[1]),
                   full_name="Alpha Analyst", role="analyst", department_id=dept.department_id))
        s.add(User(user_id=uuid.uuid4(), email=NODEPT[0], password_hash=get_password_hash(NODEPT[1]),
                   full_name="No Dept Analyst", role="analyst"))
        await s.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def token(api, creds) -> str:
    r = await api.post("/auth/login", json={"email": creds[0], "password": creds[1]})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ---------------------------------------------------------------- auth -------
async def test_health_ok(api):
    assert (await api.get("/health")).status_code == 200


async def test_login_returns_role_and_department(api):
    r = await api.post("/auth/login", json={"email": ALPHA[0], "password": ALPHA[1]})
    body = r.json()
    assert body["user"]["role"] == "analyst"
    assert body["user"]["department_id"] is not None


async def test_self_registration_is_analyst_only(api):
    ok = await api.post("/auth/register", json={
        "email": "new@t.com", "password": "Passw0rd!", "full_name": "New", "role": "analyst"})
    assert ok.status_code == 201
    rejected_client = await api.post("/auth/register", json={
        "email": "c@t.com", "password": "Passw0rd!", "full_name": "C", "role": "client"})
    assert rejected_client.status_code == 400
    rejected_admin = await api.post("/auth/register", json={
        "email": "ad@t.com", "password": "Passw0rd!", "full_name": "A", "role": "admin"})
    assert rejected_admin.status_code == 400


async def test_forgot_password_is_generic(api):
    known = await api.post("/auth/forgot-password", json={"email": ALPHA[0]})
    unknown = await api.post("/auth/forgot-password", json={"email": "nobody@nowhere.com"})
    assert known.status_code == 200
    assert known.json() == unknown.json()  # no account enumeration


async def test_reset_password_is_single_use(api):
    async with AsyncSessionLocal() as s:
        u = (await s.execute(select(User).where(User.email == NODEPT[0]))).scalar_one()
        tok = create_password_reset_token(u.user_id, u.password_hash)
    first = await api.post("/auth/reset-password", json={"token": tok, "new_password": "BrandNew1!"})
    assert first.status_code == 200
    # new password works, old one doesn't
    assert (await api.post("/auth/login", json={"email": NODEPT[0], "password": "BrandNew1!"})).status_code == 200
    assert (await api.post("/auth/login", json={"email": NODEPT[0], "password": NODEPT[1]})).status_code == 401
    # reusing the same token fails (fingerprint changed)
    reuse = await api.post("/auth/reset-password", json={"token": tok, "new_password": "Another1!"})
    assert reuse.status_code == 400


# -------------------------------------------------------- departments -------
async def test_department_management_is_admin_only(api):
    admin_t = await token(api, ADMIN)
    alpha_t = await token(api, ALPHA)
    assert (await api.post("/admin/departments", headers=auth(alpha_t),
                           json={"name": "Finance"})).status_code == 403
    assert (await api.post("/admin/departments", headers=auth(admin_t),
                           json={"name": "Finance"})).status_code == 201


# --------------------------------------------------------- scan RBAC --------
async def test_scans_are_department_scoped(api, monkeypatch):
    # don't actually run the background scanner during the test
    monkeypatch.setattr("app.api.routes.scans.start_scan_task", lambda *a, **k: None)
    admin_t = await token(api, ADMIN)
    alpha_t = await token(api, ALPHA)
    payload = {"authorization_confirmed": True,
               "authorization_justification": "automated test justification",
               "active_testing_enabled": False}
    assert (await api.post("/scans", headers=auth(alpha_t),
                           json={**payload, "target": "127.0.0.1"})).status_code == 201
    assert (await api.post("/scans", headers=auth(admin_t),
                           json={**payload, "target": "10.0.0.9"})).status_code == 201

    alpha_targets = {s["target"] for s in (await api.get("/scans", headers=auth(alpha_t))).json()}
    admin_targets = {s["target"] for s in (await api.get("/scans", headers=auth(admin_t))).json()}
    assert "127.0.0.1" in alpha_targets           # analyst sees their department's scan
    assert "10.0.0.9" not in alpha_targets        # not the admin's (no department)
    assert {"127.0.0.1", "10.0.0.9"} <= admin_targets  # admin sees everything


# ---------------------------------------------------------------- ML --------
async def test_ml_priority_predictor(api):
    t = await token(api, ALPHA)
    high = (await api.post("/ml/risk-score", headers=auth(t), json={
        "cvss_score": 9.8, "severity": "CRITICAL", "cve_id": "CVE-X",
        "service_name": "redis", "port": 6379, "confidence_score": 0.9,
        "active_verified": True})).json()
    low = (await api.post("/ml/risk-score", headers=auth(t), json={
        "cvss_score": 2.0, "severity": "LOW", "service_name": "http",
        "port": 80, "confidence_score": 0.3})).json()
    assert high["priority_label"] == "HIGH"
    assert low["priority_label"] == "LOW"
    assert high["priority_score"] > low["priority_score"]


# ------------------------------------------------------------ overview ------
async def test_overview_scope_by_role(api):
    admin_t = await token(api, ADMIN)
    alpha_t = await token(api, ALPHA)
    assert (await api.get("/overview", headers=auth(admin_t))).json()["scope"] == "organization"
    assert (await api.get("/overview", headers=auth(alpha_t))).json()["scope"] == "department"
