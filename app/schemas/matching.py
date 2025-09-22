"""
智能字段匹配相关的Pydantic模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class FormFieldSchema(BaseModel):
    """表单字段模型"""
    name: str = Field(..., description="字段名称")
    type: str = Field(..., description="字段类型: text, select, date, email, tel等")
    label: Optional[str] = Field(None, description="字段标签")
    placeholder: Optional[str] = Field(None, description="占位符文本")
    required: bool = Field(False, description="是否必填")
    options: Optional[List[str]] = Field(None, description="选择器选项")
    selector: Optional[str] = Field(None, description="CSS选择器")
    xpath: Optional[str] = Field(None, description="XPath路径")


class FieldMatchResult(BaseModel):
    """字段匹配结果"""
    field_name: str = Field(..., description="字段名称")
    field_type: str = Field(..., description="字段类型")
    matched_value: str = Field(..., description="匹配的值")


class FieldMatchRequest(BaseModel):
    """字段匹配请求"""
    resume_id: UUID = Field(..., description="简历ID")
    form_fields: List[FormFieldSchema] = Field(..., description="表单字段列表")
    website_url: Optional[str] = Field(None, description="网站URL")


class FieldMatchResponse(BaseModel):
    """字段匹配响应"""
    success: bool = Field(..., description="匹配是否成功")
    matches: List[FieldMatchResult] = Field(..., description="匹配结果")
    total_fields: int = Field(..., description="总字段数")
    matched_fields: int = Field(..., description="成功匹配的字段数")
    error_message: Optional[str] = Field(None, description="错误信息")


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
