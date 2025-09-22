"""
数据库初始化脚本
"""

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models import Base  # 导入所有模型


async def init_db():
    """初始化数据库表"""
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
