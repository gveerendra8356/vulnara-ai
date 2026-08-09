"""
api/routes/auth.py

Implements Task 2 API Contract Section 1: Auth
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.auth import CurrentUser, get_current_user, oauth2_scheme
from app.core.db import get_session
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM
from app.models.user import User
from app.models.token_denylist import TokenDenylist
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    AdminCreateUserRequest,
    TokenResponse,
    UserResponse
)

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, session: AsyncSession = Depends(get_session)):
    # Check if user exists
    result = await session.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Only 'client' or 'analyst' allowed for self-registration context per contract
    if payload.role not in ["client", "analyst"]:
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
    
    if not user or not verify_password(payload.password, user.password_hash):
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
    if not user:
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
