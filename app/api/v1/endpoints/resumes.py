"""
简历管理相关API端点
"""

from typing import List, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.resume import Resume, ResumeCreate, ResumeUpdate, ResumeListItem
from app.services.resume_service import ResumeService

router = APIRouter()


@router.post("", response_model=Resume, status_code=status.HTTP_201_CREATED)
async def create_resume(
    resume_create: ResumeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新简历
    """
    try:
        resume = await ResumeService.create_resume(db, current_user.id, resume_create)
        return resume
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建简历失败: {str(e)}"
        )


@router.get("", response_model=List[ResumeListItem])
async def get_my_resumes(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的简历列表
    """
    resumes = await ResumeService.get_user_resumes_list(
        db, current_user.id, skip, limit
    )
    return resumes


@router.get("/{resume_id}", response_model=Resume)
async def get_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定简历详情
    """
    resume = await ResumeService.get_resume_by_id(db, resume_id, current_user.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历未找到"
        )
    return resume


@router.put("/{resume_id}", response_model=Resume)
async def update_resume(
    resume_id: UUID,
    resume_update: ResumeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新指定简历
    """
    resume = await ResumeService.update_resume(
        db, resume_id, current_user.id, resume_update
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历未找到"
        )
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除指定简历
    """
    success = await ResumeService.delete_resume(db, resume_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历未找到"
        )


@router.get("/stats/count")
async def get_resume_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的简历数量统计
    """
    count = await ResumeService.get_resume_count_by_user(db, current_user.id)
    return {"count": count}


@router.patch("/{resume_id}/fields")
async def update_resume_fields(
    resume_id: UUID,
    fields_update: Dict[str, str],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    部分更新简历字段
    """
    if not fields_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="字段更新数据不能为空"
        )

    resume = await ResumeService.update_resume_fields(
        db, resume_id, current_user.id, fields_update
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历未找到"
        )
    return resume


@router.delete("/{resume_id}/fields/{field_key}")
async def delete_resume_field(
    resume_id: UUID,
    field_key: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除简历中的指定字段
    """
    resume = await ResumeService.delete_resume_field(
        db, resume_id, current_user.id, field_key
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历未找到"
        )
    return {"message": f"字段 '{field_key}' 删除成功"}


@router.get("/{resume_id}/categories")
async def get_resume_fields_by_category(
    resume_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    按分类获取简历字段数据
    """
    resume = await ResumeService.get_resume_by_id(db, resume_id, current_user.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历未找到"
        )

    categorized_fields = ResumeService.get_resume_fields_by_category(resume)
    return categorized_fields


@router.get("/templates/preset-fields")
async def get_preset_fields():
    """
    获取预设字段模板
    """
    from app.schemas.resume import get_preset_fields, get_preset_fields_by_category, COMMON_RESUME_FIELDS

    return {
        "all_fields": [field.model_dump() for field in get_preset_fields()],
        "categories": list(COMMON_RESUME_FIELDS.keys()),
        "fields_by_category": {
            category: [field.model_dump() for field in get_preset_fields_by_category(category)]
            for category in COMMON_RESUME_FIELDS.keys()
        }
    }
