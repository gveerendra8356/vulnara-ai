"""
auth.py

Pydantic schemas for authentication and user management.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return value


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str = "client"

    _password_bytes = field_validator("password")(validate_password_bytes)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    temp_password: str = Field(min_length=8)

    _password_bytes = field_validator("temp_password")(validate_password_bytes)


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime
    last_login_at: datetime | None = None


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8)

    @field_validator("new_password")
    @classmethod
    def new_password_bytes(cls, value: str | None) -> str | None:
        return validate_password_bytes(value) if value is not None else None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
