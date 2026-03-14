from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserInvite(BaseModel):
    email: EmailStr
    full_name: str | None = None


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
