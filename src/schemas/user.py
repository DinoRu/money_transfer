import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = 'admin'
    USER = 'user'
    AGENT = 'agent'


class UserBase(BaseModel):
    full_name: str
    phone: str
    email: EmailStr
    country: Optional[str] = None
    profile_picture_url: Optional[str] = None
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str



class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    credential: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    country: Optional[str] = None
    profile_picture_url: Optional[str] = None


class UserWithToken(UserRead):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class EmailModel(BaseModel):
    addresses: List[str]


class PasswordResetRequestModel(BaseModel):
    email: str


class PasswordResetConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str


