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
    def extract_resume_text(resume: Resume) -> str:
        """提取简历的文本内容，用于AI匹配"""
        if not resume.fields:
            return ""

        text_parts = []

        # 遍历所有字段，生成文本
        for key, value in resume.fields.items():
            if value and str(value).strip():
                text_parts.append(f"{key}: {value}")

        return "\n".join(text_parts)

    @staticmethod
    def search_resumes_by_field(
        resumes: List[Resume],
        field_key: str,
        field_value: str
    ) -> List[Resume]:
        """在简历列表中搜索包含特定字段值的简历"""
        matching_resumes = []

        for resume in resumes:
            if resume.fields and field_key in resume.fields:
                if field_value.lower() in resume.fields[field_key].lower():
                    matching_resumes.append(resume)

        return matching_resumes

    @staticmethod
    def get_resume_fields_by_category(resume: Resume) -> dict:
        """根据常见字段分类返回分组的字段数据"""
        if not resume.fields:
            return {}

        from app.schemas.resume import COMMON_RESUME_FIELDS

        categorized = {}
        remaining_fields = resume.fields.copy()

        # 按预定义分类整理字段
        for category, preset_fields in COMMON_RESUME_FIELDS.items():
            categorized[category] = {}
            for field_info in preset_fields:
                field_key = field_info["key"]
                if field_key in resume.fields:
                    categorized[category][field_key] = resume.fields[field_key]
                    remaining_fields.pop(field_key, None)

        # 处理未分类的字段
        if remaining_fields:
            categorized["其他"] = remaining_fields

        return categorized
