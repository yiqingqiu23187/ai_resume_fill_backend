"""
激活码服务模块
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activation import ActivationCode, UserActivation, ActivationCodeStatus
from app.models.user import User
from app.schemas.activation import ActivationCodeCreate, ActivationCodeUpdate
from app.core.config import settings


class ActivationService:
    """激活码服务类"""

    @staticmethod
    def generate_activation_code(length: int = 16) -> str:
        """生成激活码"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    @staticmethod
    async def create_activation_code(
        db: AsyncSession,
        activation_create: ActivationCodeCreate
    ) -> ActivationCode:
        """创建激活码"""
        # 检查激活码是否已存在
        existing_code = await ActivationService.get_activation_code_by_code(
            db, activation_create.code
        )
        if existing_code:
            raise ValueError("激活码已存在")

        db_activation_code = ActivationCode(
            code=activation_create.code,
            total_uses=activation_create.total_uses,
            expires_at=activation_create.expires_at,
            status=ActivationCodeStatus.ACTIVE
        )

        db.add(db_activation_code)
        await db.commit()
        await db.refresh(db_activation_code)
        return db_activation_code

    @staticmethod
    async def get_activation_code_by_id(
        db: AsyncSession,
        code_id: UUID
    ) -> Optional[ActivationCode]:
        """根据ID获取激活码"""
        stmt = select(ActivationCode).where(ActivationCode.id == code_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_activation_code_by_code(
        db: AsyncSession,
        code: str
    ) -> Optional[ActivationCode]:
        """根据激活码字符串获取激活码"""
        stmt = select(ActivationCode).where(ActivationCode.code == code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def validate_activation_code(
        db: AsyncSession,
        code: str
    ) -> Tuple[bool, str, Optional[int]]:
        """验证激活码是否有效"""
        activation_code = await ActivationService.get_activation_code_by_code(db, code)

        if not activation_code:
            return False, "激活码不存在", None

        # 检查状态
        if activation_code.status != ActivationCodeStatus.ACTIVE:
            return False, "激活码已失效", None

        # 检查是否过期
        if activation_code.expires_at and activation_code.expires_at < datetime.utcnow():
            return False, "激活码已过期", None

        # 检查使用次数
        if activation_code.used_count >= activation_code.total_uses:
            return False, "激活码使用次数已用完", None

        remaining_uses = activation_code.total_uses - activation_code.used_count
        return True, "激活码有效", remaining_uses

    @staticmethod
    async def activate_user(
        db: AsyncSession,
        user_id: UUID,
        code: str
    ) -> Tuple[bool, str, Optional[UserActivation]]:
        """为用户激活激活码"""
        # 验证激活码
        is_valid, message, remaining_uses = await ActivationService.validate_activation_code(
            db, code
        )

        if not is_valid:
            return False, message, None

        activation_code = await ActivationService.get_activation_code_by_code(db, code)

        # 检查用户是否已激活过此激活码
        existing_activation = await ActivationService.get_user_activation(
            db, user_id, activation_code.id
        )
        if existing_activation:
            return False, "此激活码已被激活", None

        # 创建用户激活记录
        user_activation = UserActivation(
            user_id=user_id,
            activation_code_id=activation_code.id,
            remaining_uses=settings.DEFAULT_ACTIVATION_USES
        )

        # 更新激活码使用次数
        activation_code.used_count += 1
        if activation_code.used_count >= activation_code.total_uses:
            activation_code.status = ActivationCodeStatus.USED

        db.add(user_activation)
        await db.commit()
        await db.refresh(user_activation)

        return True, "激活成功", user_activation

    @staticmethod
    async def get_user_activation(
        db: AsyncSession,
        user_id: UUID,
        activation_code_id: UUID
    ) -> Optional[UserActivation]:
        """获取用户激活记录"""
        stmt = select(UserActivation).where(
            and_(
                UserActivation.user_id == user_id,
                UserActivation.activation_code_id == activation_code_id
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_activations(
        db: AsyncSession,
        user_id: UUID
    ) -> List[UserActivation]:
        """获取用户所有激活记录"""
        stmt = select(UserActivation).where(UserActivation.user_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_total_remaining_uses(
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """获取用户总剩余使用次数"""
        stmt = select(func.sum(UserActivation.remaining_uses)).where(
            UserActivation.user_id == user_id
        )
        result = await db.execute(stmt)
        total = result.scalar()
        return total or 0

    @staticmethod
    async def use_activation(
        db: AsyncSession,
        user_id: UUID
    ) -> Tuple[bool, str]:
        """使用一次激活次数"""
        # 找到第一个有剩余次数的激活记录
        stmt = select(UserActivation).where(
            and_(
                UserActivation.user_id == user_id,
                UserActivation.remaining_uses > 0
            )
        ).order_by(UserActivation.activated_at)

        result = await db.execute(stmt)
        user_activation = result.scalar_one_or_none()

        if not user_activation:
            return False, "没有可用的使用次数"

        # 扣减次数
        user_activation.remaining_uses -= 1
        await db.commit()

        return True, "使用成功"

    @staticmethod
    async def get_usage_stats(
        db: AsyncSession,
        user_id: UUID
    ) -> Tuple[int, int]:
        """获取用户使用统计"""
        # 获取总剩余次数
        remaining_uses = await ActivationService.get_user_total_remaining_uses(
            db, user_id
        )

        # 获取总激活次数
        stmt = select(func.count(UserActivation.id)).where(
            UserActivation.user_id == user_id
        )
        result = await db.execute(stmt)
        total_activations = result.scalar() or 0

        return remaining_uses, total_activations
