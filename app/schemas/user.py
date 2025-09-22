"""
用户相关的Pydantic模型
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.user import UserStatus


class UserBase(BaseModel):
    """用户基础模型"""
    email: EmailStr


class UserCreate(UserBase):
    """用户注册模型"""
    password: str


class UserLogin(BaseModel):
    """用户登录模型"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: UUID
    password_hash: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(UserBase):
    """用户响应模型"""
    id: UUID
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT Token响应模型"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[UUID] = None
