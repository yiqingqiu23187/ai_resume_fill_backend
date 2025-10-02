"""
新视觉分析API的请求和响应模型
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


# ============ 请求模型 ============

class AnalysisConfigRequest(BaseModel):
    """分析配置请求模型"""
    viewport_width: int = Field(default=1200, description="视口宽度")
    viewport_height: int = Field(default=1400, description="视口高度")
    enable_form_filling: bool = Field(default=True, description="是否启用表单填写")
    save_screenshot: bool = Field(default=True, description="是否保存截图")
    save_analysis_result: bool = Field(default=True, description="是否保存分析结果")


class VisualAnalysisRequest(BaseModel):
    """完整视觉分析请求模型"""
    html_content: str = Field(..., description="HTML页面内容", min_length=1)
    resume_data: Dict[str, Any] = Field(..., description="简历数据（JSON格式）")
    website_url: str = Field(default="", description="网站URL")
    config: Optional[AnalysisConfigRequest] = Field(default=None, description="分析配置")




# ============ 响应模型 ============

class ApiResponse(BaseModel):
    """API通用响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="响应消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    timestamp: str = Field(..., description="响应时间戳")


class PhaseStatus(BaseModel):
    """阶段状态模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="阶段信息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="阶段数据")


class AnalysisStatistics(BaseModel):
    """分析统计信息"""
    total_form_fields: int = Field(..., description="表单字段总数")
    llm_recognized_fields: int = Field(..., description="大模型识别字段数")
    successfully_matched_fields: int = Field(..., description="成功匹配字段数")
    fill_success_rate: float = Field(..., description="填写成功率", ge=0.0, le=1.0)
    overall_success_rate: float = Field(..., description="总体成功率", ge=0.0, le=1.0)
    analysis_time_seconds: float = Field(..., description="分析耗时（秒）")


class FieldMatchSummary(BaseModel):
    """字段匹配摘要"""
    form_label: str = Field(..., description="表单字段标签")
    value: str = Field(..., description="填写值")
    match_type: str = Field(..., description="匹配类型")
    confidence: float = Field(..., description="匹配置信度", ge=0.0, le=1.0)


class VisualAnalysisResponse(BaseModel):
    """完整视觉分析响应模型"""
    success: bool = Field(..., description="是否成功")
    website_url: str = Field(default="", description="网站URL")
    analysis_time: float = Field(..., description="分析耗时（秒）")

    # 各阶段状态
    phase_status: Dict[str, PhaseStatus] = Field(..., description="各阶段执行状态")

    # 核心统计
    statistics: AnalysisStatistics = Field(..., description="分析统计信息")

    # 匹配结果摘要
    matched_fields: List[FieldMatchSummary] = Field(default_factory=list, description="匹配字段摘要")

    # 可用脚本
    fill_script: Optional[str] = Field(default=None, description="填写脚本")

    # 错误信息
    error: Optional[str] = Field(default=None, description="错误信息")
    failed_phase: Optional[str] = Field(default=None, description="失败的阶段")
