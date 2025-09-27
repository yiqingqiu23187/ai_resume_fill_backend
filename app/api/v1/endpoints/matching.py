"""
智能字段匹配相关API端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.services.matching_service import MatchingService
from app.schemas.matching import (
    FieldMatchRequest,
    FieldMatchResponse,
    FieldMatchResult,
    NestedFieldMatchRequest,
    NestedFieldMatchResponse
)

router = APIRouter()


@router.post("/match-fields", response_model=FieldMatchResponse)
async def match_resume_fields(
    request: FieldMatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    智能匹配简历字段到表单（旧版本，向后兼容）
    """
    # 验证表单字段格式
    is_valid, error_msg = MatchingService.validate_form_fields(request.form_fields)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # 执行字段匹配
    success, matches, error_message = await MatchingService.match_resume_fields(
        db=db,
        user_id=current_user.id,
        resume_id=request.resume_id,
        form_fields=request.form_fields,
        website_url=request.website_url
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    return FieldMatchResponse(
        success=True,
        matches=matches,
        total_fields=len(request.form_fields),
        matched_fields=len([m for m in matches if m.matched_value]),
        error_message=None
    )


@router.post("/match-nested-fields", response_model=NestedFieldMatchResponse)
async def match_nested_resume_fields(
    request: NestedFieldMatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    智能匹配简历字段到嵌套表单结构
    """
    # 执行嵌套字段匹配
    success, matched_data, total_fields, matched_fields, error_message = await MatchingService.match_nested_form_fields(
        db=db,
        user_id=current_user.id,
        resume_id=request.resume_id,
        form_structure=request.form_structure,
        website_url=request.website_url
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    return NestedFieldMatchResponse(
        success=True,
        matched_data=matched_data,
        total_fields=total_fields,
        matched_fields=matched_fields,
        error_message=None
    )


@router.get("/match-stats")
async def get_match_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的匹配统计信息
    """
    try:
        from sqlalchemy import select, func
        from app.models.usage_log import UsageLog

        # 查询使用统计
        stmt = select(
            func.count(UsageLog.id).label("total_uses"),
            func.sum(UsageLog.fields_count).label("total_fields"),
            func.sum(UsageLog.success_count).label("total_successes")
        ).where(UsageLog.user_id == current_user.id)

        result = await db.execute(stmt)
        stats = result.first()

        total_uses = stats.total_uses or 0
        total_fields = stats.total_fields or 0
        total_successes = stats.total_successes or 0

        success_rate = (total_successes / total_fields) if total_fields > 0 else 0

        return {
            "total_uses": total_uses,
            "total_fields": total_fields,
            "total_successes": total_successes,
            "success_rate": round(success_rate, 2)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.get("/supported-field-types")
async def get_supported_field_types():
    """
    获取支持的表单字段类型
    """
    return {
        "field_types": [
            {
                "type": "text",
                "name": "文本输入",
                "description": "单行文本输入框"
            },
            {
                "type": "textarea",
                "name": "多行文本",
                "description": "多行文本输入框"
            },
            {
                "type": "select",
                "name": "下拉选择",
                "description": "下拉选择器，需要提供选项"
            },
            {
                "type": "radio",
                "name": "单选按钮",
                "description": "单选按钮组"
            },
            {
                "type": "checkbox",
                "name": "复选框",
                "description": "复选框"
            },
            {
                "type": "date",
                "name": "日期",
                "description": "日期选择器"
            },
            {
                "type": "email",
                "name": "邮箱",
                "description": "邮箱输入框"
            },
            {
                "type": "tel",
                "name": "电话",
                "description": "电话号码输入框"
            },
            {
                "type": "number",
                "name": "数字",
                "description": "数字输入框"
            },
            {
                "type": "url",
                "name": "网址",
                "description": "URL输入框"
            }
        ]
    }
