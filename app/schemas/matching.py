"""
智能字段匹配相关的Pydantic模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# 注意：已删除旧的 FormFieldSchema、FieldMatchResult、FieldMatchRequest、FieldMatchResponse
# 现在只保留 HTML 分析功能相关的 schema


class MatchStatisticsResponse(BaseModel):
    """匹配统计响应"""
    total_uses: int = Field(..., description="总使用次数")
    total_fields: int = Field(..., description="总字段数")
    total_successes: int = Field(..., description="成功匹配数")
    success_rate: float = Field(..., description="成功率")


class FieldTypeInfo(BaseModel):
    """字段类型信息"""
    type: str = Field(..., description="字段类型")
    name: str = Field(..., description="显示名称")
    description: str = Field(..., description="描述")


class SupportedFieldTypesResponse(BaseModel):
    """支持的字段类型响应"""
    field_types: List[FieldTypeInfo] = Field(..., description="支持的字段类型列表")


# 🎯 新增：HTML分析相关的Schema
class HTMLAnalysisRequest(BaseModel):
    """HTML分析请求"""
    resume_id: UUID = Field(..., description="简历ID")
    html_content: str = Field(..., description="页面HTML内容")
    website_url: Optional[str] = Field(None, description="网站URL")


class AnalyzedField(BaseModel):
    """分析出的字段信息"""
    name: str = Field(..., description="字段名称")
    type: str = Field(..., description="字段类型")
    label: str = Field(..., description="字段标签")
    selector: str = Field(..., description="CSS选择器")
    required: bool = Field(False, description="是否必填")
    category: Optional[str] = Field(None, description="字段分类：基本信息/教育经历/工作经验等")
    matched_value: Optional[str] = Field(None, description="匹配的简历值")


class HTMLAnalysisResponse(BaseModel):
    """HTML分析响应"""
    success: bool = Field(..., description="分析是否成功")
    analyzed_fields: List[AnalyzedField] = Field(..., description="分析出的字段列表")
    total_fields: int = Field(..., description="识别的字段总数")
    matched_fields: int = Field(..., description="成功匹配的字段数")
    form_structure: Optional[Dict[str, Any]] = Field(None, description="表单结构分析结果")
    error_message: Optional[str] = Field(None, description="错误信息")


# 🎯 新增：字段匹配相关的Schema（方案二）
class FieldInfo(BaseModel):
    """前端扫描的字段信息"""
    selector: str = Field(..., description="CSS选择器")
    label: str = Field(..., description="字段标签")
    placeholder: Optional[str] = Field(None, description="占位符")
    options: Optional[List[str]] = Field(None, description="select字段的选项列表（文本数组）")


class FieldMatchRequest(BaseModel):
    """字段匹配请求"""
    fields: List[FieldInfo] = Field(..., description="前端扫描的字段列表")
    resume_id: UUID = Field(..., description="简历ID")


class MatchedField(BaseModel):
    """匹配后的字段"""
    selector: str = Field(..., description="CSS选择器")
    matched_value: Any = Field(..., description="匹配到的值")


class FieldMatchResponse(BaseModel):
    """字段匹配响应"""
    success: bool = Field(..., description="匹配是否成功")
    matched_fields: List[MatchedField] = Field(..., description="匹配结果列表")
    error_message: Optional[str] = Field(None, description="错误信息")
