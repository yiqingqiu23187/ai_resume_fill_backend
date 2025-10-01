"""
统一视觉驱动表单分析API接口

提供前端调用的标准化API，整合所有Phase的处理能力
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Body
from pydantic import BaseModel

from ....core.deps import get_current_active_user
from ....models.user import User
from ....services.unified_visual_analysis_service import unified_visual_analysis_service
from ....services.resume_service import ResumeService
from ....schemas.visual_analysis_schemas import UnifiedAnalysisResult
from ....core.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class VisualAnalysisRequestBody(BaseModel):
    """视觉分析请求体"""
    resume_id: str
    html_content: str
    website_url: str


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_visual_form(
    request_body: VisualAnalysisRequestBody,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    🚀 统一视觉驱动表单分析 - 主API接口

    整合Phase 1-5的完整处理流程，为前端提供一站式表单分析服务

    **功能特点:**
    - 🔍 视觉驱动分析: 基于截图和CV算法的表单理解
    - 🏗️ 结构识别: 自动识别表单的逻辑分组和重复结构
    - 🤖 智能匹配: 大模型驱动的高质量字段匹配
    - 🔧 质量验证: 全面的结果验证和质量评估
    - ⚡ 性能优化: 支持缓存和增量处理

    **输出说明:**
    - final_matching_results: 前端直接使用的匹配结果
    - final_quality_assessment: 整体质量评估
    - phase*_result: 各阶段的详细处理结果(调试用)
    """
    try:
        logger.info(f"🚀 接收视觉分析请求 - 用户:{current_user.id}, 简历:{request_body.resume_id}")
        logger.info(f"📊 请求参数: 网站={request_body.website_url}, HTML长度={len(request_body.html_content)}")

        # 1. 获取简历数据
        logger.info(f"📄 获取简历数据 - 用户:{current_user.id}, 简历:{request_body.resume_id}")
        resume = await ResumeService.get_resume_by_id(db, request_body.resume_id, current_user.id)
        if not resume:
            logger.warning(f"❌ 简历不存在 - 用户:{current_user.id}, 简历:{request_body.resume_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"简历不存在: {request_body.resume_id}"
            )

        # 2. 执行完整分析流水线
        logger.info(f"🔄 开始执行视觉分析流水线...")
        result = await unified_visual_analysis_service.analyze_complete_pipeline(
            html_content=request_body.html_content,
            website_url=request_body.website_url,
            resume_data=resume.fields or {}  # 直接使用原始JSON数据
        )

        # 6. 处理结果
        if result.success:
            logger.info(f"✅ 视觉分析成功 - 请求ID:{result.request_id}")
            logger.info(f"📊 匹配结果: {len(result.final_matching_results)}个字段")

            # 返回简化结果 - 只有前端需要的核心数据
            return {
                "success": True,
                "matching_results": [
                    {"selector": mr.selector, "value": mr.value}
                    for mr in result.final_matching_results
                ]
            }
        else:
            logger.error(f"❌ 视觉分析失败 - 错误:{result.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"视觉分析失败: {result.error}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API调用失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务内部错误: {str(e)}"
        )


@router.get("/status/{request_id}")
async def get_analysis_status(
    request_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    📊 获取分析状态

    用于查询长时间运行的分析任务状态
    """
    try:
        status_info = await unified_visual_analysis_service.get_analysis_status(request_id)
        return {
            "success": True,
            "request_id": request_id,
            "status": status_info
        }
    except Exception as e:
        logger.error(f"❌ 获取状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取状态失败: {str(e)}"
        )


