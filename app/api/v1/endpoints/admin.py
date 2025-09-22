"""
管理员API端点
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_db
from app.schemas.activation import ActivationCode, ActivationCodeCreate
from app.services.activation_service import ActivationService

router = APIRouter()


@router.post("/activation-codes", response_model=ActivationCode, status_code=status.HTTP_201_CREATED)
async def create_activation_code(
    total_uses: int = 5,
    expires_in_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的激活码
    """
    # 生成激活码
    code = ActivationService.generate_activation_code()

    # 设置过期时间
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    activation_create = ActivationCodeCreate(
        code=code,
        total_uses=total_uses,
        expires_at=expires_at
    )

    try:
        activation_code = await ActivationService.create_activation_code(db, activation_create)
        return activation_code
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/activation-codes/batch", response_model=List[ActivationCode])
async def create_batch_activation_codes(
    count: int = 10,
    total_uses: int = 5,
    expires_in_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    批量创建激活码
    """
    if count > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次最多创建100个激活码"
        )

    activation_codes = []
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    for _ in range(count):
        code = ActivationService.generate_activation_code()
        activation_create = ActivationCodeCreate(
            code=code,
            total_uses=total_uses,
            expires_at=expires_at
        )

        try:
            activation_code = await ActivationService.create_activation_code(db, activation_create)
            activation_codes.append(activation_code)
        except ValueError:
            # 如果激活码重复，重新生成
            continue

    return activation_codes
