"""
新视觉分析API路由
提供基于视觉大模型的智能表单分析和填写服务

核心接口：
- POST /analyze - 完整的智能表单分析和填写
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ...schemas.api_models import (
    VisualAnalysisRequest,
    VisualAnalysisResponse,
    PhaseStatus, AnalysisStatistics, FieldMatchSummary
)
from ...services.new_visual_analysis_service import new_visual_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=VisualAnalysisResponse,
    summary="完整的智能表单分析",
    description="""
    使用视觉大模型进行完整的表单分析流程：

    **流程步骤：**
    1. **Phase 1**: 网页截图
    2. **Phase 2**: 表单字段提取
    3. **Phase 3**: 视觉大模型语义理解
    4. **Phase 4**: 智能标签匹配

    **返回结果：**
    - 匹配的字段信息（包含selector和value）
    - 由前端执行表单填写操作

    **适用场景：**
    - 招聘网站表单分析
    - 表单数据智能匹配
    - 批量表单处理

    **注意事项：**
    - 需要配置 DASHSCOPE_API_KEY 环境变量
    - HTML内容应包含完整的表单结构
    - 简历数据格式应为标准JSON
    """
)
async def analyze_form(request: VisualAnalysisRequest) -> VisualAnalysisResponse:
    """
    执行完整的表单分析和填写

    Args:
        request: 分析请求，包含HTML内容、简历数据等

    Returns:
        完整的分析结果，包含各阶段状态、统计信息和匹配结果

    Raises:
        HTTPException: 当请求参数无效或系统异常时
    """
    try:
        logger.info(f"🚀 接收到视觉分析请求: {request.website_url}")

        # 转换配置
        config_dict = None
        if request.config:
            config_dict = request.config.model_dump()

        # 调用服务层
        result = await new_visual_analysis_service.analyze_and_fill_form(
            html_content=request.html_content,
            resume_data=request.resume_data,
            website_url=request.website_url,
            config=config_dict
        )

        # 处理不同的返回格式（兼容当前实现）
        if isinstance(result, dict):
            # 当前返回字典格式的情况
            if result.get('success'):
                return _convert_dict_to_response(result)
            else:
                # 处理错误情况
                error_response = VisualAnalysisResponse(
                    success=False,
                    website_url=request.website_url,
                    analysis_time=result.get('analysis_time', 0),
                    phase_status={},
                    statistics=AnalysisStatistics(
                        total_form_fields=0,
                        llm_recognized_fields=0,
                        successfully_matched_fields=0,
                        fill_success_rate=0.0,
                        overall_success_rate=0.0,
                        analysis_time_seconds=result.get('analysis_time', 0)
                    ),
                    error=result.get('error', '未知错误'),
                    failed_phase=result.get('phase', 'unknown')
                )
                return error_response
        else:
            # 如果返回的是Pydantic模型，直接转换
            return _convert_pydantic_to_response(result)

    except Exception as e:
        logger.error(f"❌ 视觉分析API异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )




def _convert_dict_to_response(result_dict: Dict[str, Any]) -> VisualAnalysisResponse:
    """
    将服务层返回的字典转换为API响应模型

    Args:
        result_dict: 服务层返回的字典结果

    Returns:
        API响应模型
    """
    try:
        # 提取各阶段状态
        phase_results = result_dict.get('phase_results', {})
        phase_status = {}

        for phase_name, phase_data in phase_results.items():
            if isinstance(phase_data, dict):
                phase_status[phase_name] = PhaseStatus(
                    success=phase_data.get('success', False),
                    message=_get_phase_message(phase_name, phase_data),
                    data=phase_data
                )

        # 提取统计信息
        stats_dict = result_dict.get('statistics', {})
        statistics = AnalysisStatistics(
            total_form_fields=stats_dict.get('total_form_fields', 0),
            llm_recognized_fields=stats_dict.get('llm_recognized_fields', 0),
            successfully_matched_fields=stats_dict.get('successfully_matched_fields', 0),
            fill_success_rate=stats_dict.get('fill_success_rate', 0.0),
            overall_success_rate=stats_dict.get('overall_success_rate', 0.0),
            analysis_time_seconds=stats_dict.get('analysis_time_seconds', 0.0)
        )

        # 提取匹配字段摘要
        matched_fields = []
        matching_results = phase_results.get('phase4_label_matching', {}).get('matching_results', [])

        for match in matching_results:
            if hasattr(match, 'form_label'):
                # Pydantic对象
                matched_fields.append(FieldMatchSummary(
                    form_label=match.form_label,
                    value=match.value,
                    match_type=match.match_type,
                    confidence=match.confidence
                ))
            elif isinstance(match, dict):
                # 字典对象
                matched_fields.append(FieldMatchSummary(
                    form_label=match.get('form_label', ''),
                    value=match.get('value', ''),
                    match_type=match.get('match_type', ''),
                    confidence=match.get('confidence', 0.0)
                ))

        return VisualAnalysisResponse(
            success=result_dict.get('success', False),
            website_url=result_dict.get('website_url', ''),
            analysis_time=result_dict.get('analysis_time', 0.0),
            phase_status=phase_status,
            statistics=statistics,
            matched_fields=matched_fields,
            fill_script=result_dict.get('fill_script')
        )

    except Exception as e:
        logger.error(f"❌ 响应转换失败: {str(e)}")
        # 返回基本错误响应
        return VisualAnalysisResponse(
            success=False,
            website_url="",
            analysis_time=0.0,
            phase_status={},
            statistics=AnalysisStatistics(
                total_form_fields=0,
                llm_recognized_fields=0,
                successfully_matched_fields=0,
                fill_success_rate=0.0,
                overall_success_rate=0.0,
                analysis_time_seconds=0.0
            ),
            error=f"响应格式转换失败: {str(e)}"
        )


def _convert_pydantic_to_response(result) -> VisualAnalysisResponse:
    """
    将Pydantic模型转换为API响应模型（为未来扩展预留）

    Args:
        result: Pydantic模型结果

    Returns:
        API响应模型
    """
    # TODO: 当服务层完全返回Pydantic模型时实现此方法
    pass


def _get_phase_message(phase_name: str, phase_data: Dict[str, Any]) -> str:
    """
    根据阶段名称和数据生成状态消息

    Args:
        phase_name: 阶段名称
        phase_data: 阶段数据

    Returns:
        状态消息
    """
    if not phase_data.get('success', False):
        return f"{phase_name}执行失败"

    messages = {
        'phase1_screenshot': f"截图完成，大小: {phase_data.get('screenshot_size', 0)} bytes",
        'phase2_field_extraction': f"提取到 {phase_data.get('total_fields', 0)} 个表单字段",
        'phase3_visual_llm': f"识别到 {phase_data.get('recognized_fields', 0)} 个字段映射",
        'phase4_label_matching': f"匹配成功 {phase_data.get('matched_fields', 0)} 个字段",
        'phase5_form_filling': "表单填写完成"
    }

    return messages.get(phase_name, f"{phase_name}执行成功")
