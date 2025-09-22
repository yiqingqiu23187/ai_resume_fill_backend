"""
激活码管理相关API端点
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.activation import (
    ActivationValidateRequest,
    ActivationValidateResponse,
    UserActivationCreate,
    UserActivation,
    UsageStatsResponse
)
from app.services.activation_service import ActivationService

router = APIRouter()


@router.post("/validate", response_model=ActivationValidateResponse)
async def validate_activation_code(
    request: ActivationValidateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    验证激活码是否有效
    """
    is_valid, message, remaining_uses = await ActivationService.validate_activation_code(
        db, request.code
    )

    return ActivationValidateResponse(
        valid=is_valid,
        message=message,
        remaining_uses=remaining_uses
    )


@router.post("/activate", response_model=UserActivation, status_code=status.HTTP_201_CREATED)
async def activate_code(
    activation_create: UserActivationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    激活激活码，为用户账户增加使用次数
    """
    success, message, user_activation = await ActivationService.activate_user(
        db, current_user.id, activation_create.code
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return user_activation


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户使用统计
    """
    remaining_uses, total_activations = await ActivationService.get_usage_stats(
        db, current_user.id
    )

    return UsageStatsResponse(
        remaining_uses=remaining_uses,
        total_activations=total_activations
    )


@router.get("/my-activations", response_model=List[UserActivation])
async def get_my_activations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的所有激活记录
    """
    activations = await ActivationService.get_user_activations(db, current_user.id)
    return activations


@router.post("/use", status_code=status.HTTP_200_OK)
async def use_activation(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    使用一次激活次数（内部API，由匹配服务调用）
    """
    success, message = await ActivationService.use_activation(db, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return {"message": message}
