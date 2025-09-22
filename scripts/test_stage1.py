#!/usr/bin/env python3
"""
第一阶段功能测试脚本
测试用户认证和激活码系统
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Base, User, ActivationCode, UserActivation
from app.services.user_service import UserService
from app.services.activation_service import ActivationService
from app.schemas.user import UserCreate
from app.schemas.activation import ActivationCodeCreate

# 创建异步数据库会话
async_engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def create_tables():
    """创建数据库表"""
    print("=== 创建数据库表 ===")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建成功")

async def test_user_operations():
    """测试用户操作"""
    print("\n=== 测试用户操作 ===")

    async with AsyncSessionLocal() as db:
        # 测试用户注册
        user_create = UserCreate(
            email="test@example.com",
            password="testpassword123"
        )

        try:
            user = await UserService.create_user(db, user_create)
            print(f"✅ 用户注册成功: {user.email} (ID: {user.id})")
        except ValueError as e:
            print(f"❌ 用户注册失败: {e}")
            return None

        # 测试用户认证
        authenticated_user = await UserService.authenticate_user(
            db, "test@example.com", "testpassword123"
        )
        if authenticated_user:
            print(f"✅ 用户认证成功: {authenticated_user.email}")
        else:
            print("❌ 用户认证失败")
            return None

        # 测试错误密码
        wrong_auth = await UserService.authenticate_user(
            db, "test@example.com", "wrongpassword"
        )
        if not wrong_auth:
            print("✅ 错误密码认证正确拒绝")
        else:
            print("❌ 错误密码认证未被拒绝")

        return user

async def test_activation_operations(user):
    """测试激活码操作"""
    print("\n=== 测试激活码操作 ===")

    async with AsyncSessionLocal() as db:
        # 创建激活码
        code = ActivationService.generate_activation_code()
        activation_create = ActivationCodeCreate(
            code=code,
            total_uses=5
        )

        try:
            activation_code = await ActivationService.create_activation_code(
                db, activation_create
            )
            print(f"✅ 激活码创建成功: {activation_code.code}")
        except ValueError as e:
            print(f"❌ 激活码创建失败: {e}")
            return

        # 验证激活码
        is_valid, message, remaining = await ActivationService.validate_activation_code(
            db, code
        )
        if is_valid:
            print(f"✅ 激活码验证成功: {message}, 剩余使用次数: {remaining}")
        else:
            print(f"❌ 激活码验证失败: {message}")
            return

        # 用户激活激活码
        success, message, user_activation = await ActivationService.activate_user(
            db, user.id, code
        )
        if success:
            print(f"✅ 用户激活成功: {message}")
        else:
            print(f"❌ 用户激活失败: {message}")
            return

        # 获取用户使用统计
        remaining_uses, total_activations = await ActivationService.get_usage_stats(
            db, user.id
        )
        print(f"✅ 用户统计 - 剩余次数: {remaining_uses}, 总激活数: {total_activations}")

        # 测试使用激活次数
        use_success, use_message = await ActivationService.use_activation(db, user.id)
        if use_success:
            print(f"✅ 使用次数扣减成功: {use_message}")
        else:
            print(f"❌ 使用次数扣减失败: {use_message}")

        # 再次获取统计
        remaining_uses, total_activations = await ActivationService.get_usage_stats(
            db, user.id
        )
        print(f"✅ 扣减后统计 - 剩余次数: {remaining_uses}")

async def cleanup():
    """清理测试数据"""
    print("\n=== 清理测试数据 ===")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✅ 测试数据清理完成")

async def main():
    """主测试函数"""
    print("🧪 开始第一阶段功能测试...")

    try:
        # 创建表
        await create_tables()

        # 测试用户功能
        user = await test_user_operations()
        if not user:
            return

        # 测试激活码功能
        await test_activation_operations(user)

        print("\n🎉 第一阶段功能测试完成！")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        await cleanup()
        await async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
