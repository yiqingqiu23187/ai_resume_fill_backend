"""
简历服务模块 - 支持灵活的key-value结构
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeCreate, ResumeUpdate, ResumeListItem


class ResumeService:
    """简历服务类"""

    @staticmethod
    async def create_resume(
        db: AsyncSession,
        user_id: UUID,
        resume_create: ResumeCreate
    ) -> Resume:
        """创建新简历"""
        db_resume = Resume(
            user_id=user_id,
            title=resume_create.title,
            fields=resume_create.fields
        )

        db.add(db_resume)
        await db.commit()
        await db.refresh(db_resume)
        return db_resume

    @staticmethod
    async def get_resume_by_id(
        db: AsyncSession,
        resume_id: UUID,
        user_id: UUID
    ) -> Optional[Resume]:
        """根据ID获取简历（限制用户只能获取自己的简历）"""
        stmt = select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_resumes(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 10
    ) -> List[Resume]:
        """获取用户的所有简历"""
        stmt = select(Resume).where(
            Resume.user_id == user_id
        ).offset(skip).limit(limit).order_by(Resume.updated_at.desc())

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_resumes_list(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 10
    ) -> List[ResumeListItem]:
        """获取用户的简历列表（简化信息）"""
        resumes = await ResumeService.get_user_resumes(db, user_id, skip, limit)

        resume_list = []
        for resume in resumes:
            # 计算字段数量
            field_count = len(resume.fields) if resume.fields else 0

            resume_list.append(ResumeListItem(
                id=resume.id,
                user_id=resume.user_id,
                title=resume.title,
                field_count=field_count,
                updated_at=resume.updated_at
            ))

        return resume_list

    @staticmethod
    async def update_resume(
        db: AsyncSession,
        resume_id: UUID,
        user_id: UUID,
        resume_update: ResumeUpdate
    ) -> Optional[Resume]:
        """更新简历"""
        resume = await ResumeService.get_resume_by_id(db, resume_id, user_id)
        if not resume:
            return None

        update_data = resume_update.model_dump(exclude_unset=True)

        # 更新标题
        if "title" in update_data:
            resume.title = update_data["title"]

        # 更新字段数据
        if "fields" in update_data:
            resume.fields = update_data["fields"]

        await db.commit()
        await db.refresh(resume)
        return resume

    @staticmethod
    async def update_resume_fields(
        db: AsyncSession,
        resume_id: UUID,
        user_id: UUID,
        fields_update: dict
    ) -> Optional[Resume]:
        """部分更新简历字段"""
        resume = await ResumeService.get_resume_by_id(db, resume_id, user_id)
        if not resume:
            return None

        # 合并字段数据
        current_fields = resume.fields or {}
        current_fields.update(fields_update)
        resume.fields = current_fields

        await db.commit()
        await db.refresh(resume)
        return resume

    @staticmethod
    async def delete_resume(
        db: AsyncSession,
        resume_id: UUID,
        user_id: UUID
    ) -> bool:
        """删除简历"""
        resume = await ResumeService.get_resume_by_id(db, resume_id, user_id)
        if not resume:
            return False

        await db.delete(resume)
        await db.commit()
        return True

    @staticmethod
    async def delete_resume_field(
        db: AsyncSession,
        resume_id: UUID,
        user_id: UUID,
        field_key: str
    ) -> Optional[Resume]:
        """删除简历中的指定字段"""
        resume = await ResumeService.get_resume_by_id(db, resume_id, user_id)
        if not resume:
            return None

        current_fields = resume.fields or {}
        if field_key in current_fields:
            del current_fields[field_key]
            resume.fields = current_fields

            await db.commit()
            await db.refresh(resume)

        return resume

    @staticmethod
    async def get_resume_count_by_user(
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """获取用户的简历数量"""
        from sqlalchemy import func

        stmt = select(func.count(Resume.id)).where(Resume.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    def get_resume_data(resume: Resume) -> dict:
        """获取简历数据，直接返回JSON格式供AI使用"""
        return resume.fields or {}
