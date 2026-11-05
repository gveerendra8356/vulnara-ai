"""
api/routes/auth.py

Implements Task 2 API Contract Section 1: Auth
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.auth import CurrentUser, get_current_user, oauth2_scheme
from app.core.db import get_session
from app.core.security import (
    get_password_hash, verify_password, create_access_token, create_refresh_token,
    SECRET_KEY, ALGORITHM,
    create_password_reset_token, verify_password_reset_token, password_fingerprint,
)
from app.core.email_alert import send_password_reset_email
from app.models.user import User
from app.models.token_denylist import TokenDenylist
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    AdminCreateUserRequest,
    UpdateProfileRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse
)

router = APIRouter()

# Base URL of the web app, used to build the password-reset link in the email.
FRONTEND_BASE_URL = os.environ.get("APP_BASE_URL", "https://gveerendra8356.github.io/vulnara-ai")


@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)):
    """
    Starts the password-reset flow. Always returns the same generic message so
    the endpoint can't be used to discover which emails have accounts. If the
    email belongs to an active user, a one-time reset link is emailed (or, when
    SMTP isn't configured, logged server-side so the flow is still testable).
    """
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is not None and user.is_active:
        token = create_password_reset_token(user.user_id, user.password_hash)
        reset_link = f"{FRONTEND_BASE_URL}/reset-password?token={token}"
        send_password_reset_email(
            recipient_email=user.email,
            recipient_name=user.full_name or "User",
            reset_link=reset_link,
        )
    return {"message": "If an account exists for that email, a password reset link has been sent."}


@router.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest, session: AsyncSession = Depends(get_session)):
    """
    Completes the reset: validates the one-time token (purpose, expiry, and a
    fingerprint of the current password hash so a used link can't be replayed),
    then sets the new password.
    """
    data = verify_password_reset_token(payload.token)
    if not data:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    try:
        user_id = uuid.UUID(data["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    # A mismatched fingerprint means the password already changed since the
    # link was issued -> the link was used (or is stale). Reject it.
    if user is None or not user.is_active or password_fingerprint(user.password_hash) != data.get("pwf"):
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    user.password_hash = get_password_hash(payload.new_password)
    session.add(user)
    await session.commit()
    return {"message": "Your password has been reset. You can now log in with your new password."}


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, session: AsyncSession = Depends(get_session)):
    # Check if user exists
    result = await session.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Self-registration is restricted to the 'analyst' role. Admin accounts are
    # provisioned by an existing admin, never via public sign-up.
    if payload.role != "analyst":
        raise HTTPException(status_code=400, detail="Invalid role for self-registration")

    new_user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()

    access_token = create_access_token(data={"sub": str(user.user_id), "role": user.role})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    # Decode token just to get the 'exp' to return to client (or assume 3600 per contract)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "department_id": user.department_id,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at
        }
    }


@router.post("/auth/refresh")
async def refresh_token(payload: RefreshTokenRequest, session: AsyncSession = Depends(get_session)):
    import hashlib
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()

    # Check denylist (only if not expired, though the background cleanup handles this too)
    stmt = select(TokenDenylist).where(
        TokenDenylist.token == token_hash,
        TokenDenylist.expires_at > datetime.now(timezone.utc)
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        token_payload = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = token_payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    try:
        user_id_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await session.execute(select(User).where(User.user_id == user_id_uuid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(data={"sub": str(user.user_id), "role": user.role})
    return {
        "access_token": access_token,
        "expires_in": 3600
    }


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest, 
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    import hashlib
    try:
        # We need the expiration time to store in the denylist
        token_payload = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = token_payload.get("exp")
        if exp is None:
            return # Invalid token anyway
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    except JWTError:
        return # If it's invalid or expired, it's effectively logged out

    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    denylist_entry = TokenDenylist(token=token_hash, expires_at=expires_at)
    session.add(denylist_entry)
    await session.commit()
    return


@router.get("/auth/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User).where(User.user_id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/auth/me", response_model=UserResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User).where(User.user_id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Password change: require current password verification
    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="current_password is required to set a new password")
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.password_hash = get_password_hash(payload.new_password)

    # Email uniqueness check
    if payload.email and payload.email != user.email:
        existing = await session.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = payload.email

    if payload.full_name:
        user.full_name = payload.full_name

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/auth/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    payload: AdminCreateUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await session.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.temp_password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user
