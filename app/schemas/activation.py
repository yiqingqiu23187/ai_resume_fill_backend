"""
激活码相关的Pydantic模型
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.models.activation import ActivationCodeStatus


class ActivationCodeBase(BaseModel):
    """激活码基础模型"""
    code: str
    total_uses: int = 5


class ActivationCodeCreate(ActivationCodeBase):
    """激活码创建模型"""
    expires_at: Optional[datetime] = None


class ActivationCodeUpdate(BaseModel):
    """激活码更新模型"""
    total_uses: Optional[int] = None
    status: Optional[ActivationCodeStatus] = None
    expires_at: Optional[datetime] = None


class ActivationCode(ActivationCodeBase):
    """激活码响应模型"""
    id: UUID
    used_count: int
    status: ActivationCodeStatus
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserActivationBase(BaseModel):
    """用户激活记录基础模型"""
    user_id: UUID
    activation_code_id: UUID
    remaining_uses: int = 5


class UserActivationCreate(BaseModel):
    """用户激活记录创建模型"""
    code: str


class UserActivation(UserActivationBase):
    """用户激活记录响应模型"""
    id: UUID
    activated_at: datetime

    class Config:
        from_attributes = True


class ActivationValidateRequest(BaseModel):
    """激活码验证请求模型"""
    code: str


class ActivationValidateResponse(BaseModel):
    """激活码验证响应模型"""
    valid: bool
    message: str
    remaining_uses: Optional[int] = None


class UsageStatsResponse(BaseModel):
    """使用统计响应模型"""
    remaining_uses: int
    total_activations: int
