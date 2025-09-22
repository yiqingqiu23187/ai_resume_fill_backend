"""
用户服务模块
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserStatus
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    """用户服务类"""

    @staticmethod
    async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
        """创建新用户"""
        # 检查邮箱是否已存在
        existing_user = await UserService.get_user_by_email(db, user_create.email)
        if existing_user:
            raise ValueError("邮箱已存在")

        # 创建新用户
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            email=user_create.email,
            password_hash=hashed_password,
            status=UserStatus.ACTIVE
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        """根据ID获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """验证用户登录"""
        user = await UserService.get_user_by_email(db, email)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if user.status != UserStatus.ACTIVE:
            return None

        return user

    @staticmethod
    async def update_user(
        db: AsyncSession, user_id: UUID, user_update: UserUpdate
    ) -> Optional[User]:
        """更新用户信息"""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data["password"])
            del update_data["password"]

        for field, value in update_data.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: UUID) -> bool:
        """停用用户"""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return False

        user.status = UserStatus.INACTIVE
        await db.commit()
        return True
