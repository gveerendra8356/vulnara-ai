"""
core/auth.py

Minimal stand-in for the JWT auth dependency described in the Task 2 API
contract (POST /auth/login etc.). That module isn't the subject of this
task, so this is a lightweight but functional stub so scans.py below is
actually runnable end-to-end, not pseudocode. Swap this out for real JWT
decode/verify logic (e.g. python-jose) when the auth module is built.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass
class CurrentUser:
    user_id: uuid.UUID
    email: str
    role: str


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    """
    STUB: replace with real JWT verification. Currently just checks a
    token is present at all, and fabricates a user identity from it so
    downstream code (which needs a real user_id for the audit log and
    the Scans.user_id FK) has something concrete to work with.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    # TODO: decode JWT, look up user in DB, verify not revoked/expired.
    return CurrentUser(user_id=uuid.uuid4(), email="stub@example.com", role="analyst")
