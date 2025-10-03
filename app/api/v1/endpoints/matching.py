"""
智能字段匹配相关API端点
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.services.matching_service import MatchingService
from app.schemas.matching import (
    HTMLAnalysisRequest,
    HTMLAnalysisResponse,
    FieldMatchRequest,
    FieldMatchResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)






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


@router.post("/analyze-html", response_model=HTMLAnalysisResponse)
async def analyze_html_form(
    request: HTMLAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    🎯 新功能：使用大模型分析HTML并识别表单结构
    """
    # 接口调用确认
    logger.info(f"🔥 ANALYZE HTML API CALLED - 用户:{current_user.id}, 简历:{request.resume_id}, HTML长度:{len(request.html_content)}")

    logger.info(f"🚀 API接收HTML分析请求 - 用户:{current_user.id}, 简历:{request.resume_id}, 网站:{request.website_url}")
    logger.debug(f"📄 请求参数 - HTML长度:{len(request.html_content)}")

    try:
        # 调用HTML分析服务
        logger.info(f"📞 调用MatchingService.analyze_html_with_llm - 用户:{current_user.id}")
        success, analyzed_fields, form_structure, error_message = await MatchingService.analyze_html_with_llm(
            db=db,
            user_id=current_user.id,
            resume_id=request.resume_id,
            html_content=request.html_content,
            website_url=request.website_url
        )

        logger.info(f"🔄 服务层返回结果 - 用户:{current_user.id}, 成功:{success}")

        if not success:
            logger.warning(f"⚠️ 服务层返回失败 - 用户:{current_user.id}, 错误:{error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # 统计匹配结果
        total_fields = len(analyzed_fields) if analyzed_fields else 0
        matched_fields = len([f for f in analyzed_fields if f.get('matched_value')]) if analyzed_fields else 0

        logger.info(f"📊 统计完成 - 用户:{current_user.id}, 总字段:{total_fields}, 匹配字段:{matched_fields}")

        response = HTMLAnalysisResponse(
            success=True,
            analyzed_fields=analyzed_fields,
            total_fields=total_fields,
            matched_fields=matched_fields,
            form_structure=form_structure,
            error_message=None
        )

        logger.info(f"✅ API请求成功 - 用户:{current_user.id}, 返回字段数:{total_fields}")
        return response

    except HTTPException as he:
        logger.warning(f"⚠️ HTTP异常 - 用户:{current_user.id}, 状态码:{he.status_code}, 详情:{he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ API异常 - 用户:{current_user.id}, 异常类型:{type(e).__name__}, 异常信息:{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HTML分析失败: {str(e)}"
        )


@router.post("/match-fields", response_model=FieldMatchResponse)
async def match_fields(
    request: FieldMatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    🎯 新功能：字段智能匹配（方案二）
    前端扫描字段后，发送字段列表，后端用AI匹配简历数据
    """
    logger.info(f"🚀 字段匹配请求 - 用户:{current_user.id}, 简历:{request.resume_id}, 字段数:{len(request.fields)}")

    try:
        # 调用字段匹配服务
        success, matched_fields, error_message = await MatchingService.match_fields_with_llm(
            db=db,
            user_id=current_user.id,
            resume_id=request.resume_id,
            fields=request.fields
        )

        if not success:
            logger.warning(f"⚠️ 字段匹配失败 - 用户:{current_user.id}, 错误:{error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        logger.info(f"✅ 字段匹配成功 - 用户:{current_user.id}, 匹配字段数:{len(matched_fields)}")

        return FieldMatchResponse(
            success=True,
            matched_fields=matched_fields,
            error_message=None
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ 字段匹配异常 - 用户:{current_user.id}, 异常:{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"字段匹配失败: {str(e)}"
        )
