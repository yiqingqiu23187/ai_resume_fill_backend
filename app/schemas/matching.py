"""
智能字段匹配相关的Pydantic模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
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


# 🎯 新增：支持嵌套结构的数据模型

class BaseFormStructure(BaseModel):
    """表单结构基类"""
    type: str = Field(..., description="结构类型: object, array, text, select等")


class SimpleFieldStructure(BaseFormStructure):
    """简单字段结构"""
    type: str = Field(..., description="字段类型")
    selector: str = Field(..., description="CSS选择器")
    label: Optional[str] = Field(None, description="字段标签")
    placeholder: Optional[str] = Field(None, description="占位符")
    required: bool = Field(False, description="是否必填")
    options: Optional[List[str]] = Field(None, description="选择器选项")


class ObjectStructure(BaseFormStructure):
    """对象结构"""
    type: str = Field(default="object", description="对象类型")
    fields: Dict[str, Union['ObjectStructure', 'ArrayStructure', 'SimpleFieldStructure']] = Field(..., description="对象字段")


class ArrayStructure(BaseFormStructure):
    """数组结构"""
    type: str = Field(default="array", description="数组类型")
    add_button: str = Field(..., description="添加按钮选择器")
    container: str = Field(..., description="容器选择器")
    existing_items_count: int = Field(default=0, description="现有项目数量")
    item_structure: Union[ObjectStructure, SimpleFieldStructure] = Field(..., description="数组项结构")
    save_button: Optional[str] = Field(None, description="保存按钮选择器")


class NestedFormStructure(BaseModel):
    """嵌套表单结构"""
    fields: Dict[str, Union[ObjectStructure, ArrayStructure, SimpleFieldStructure]] = Field(..., description="表单字段结构")


class NestedFieldMatchRequest(BaseModel):
    """嵌套字段匹配请求"""
    resume_id: UUID = Field(..., description="简历ID")
    form_structure: NestedFormStructure = Field(..., description="嵌套表单结构")
    website_url: Optional[str] = Field(None, description="网站URL")


class NestedFieldMatchResponse(BaseModel):
    """嵌套字段匹配响应"""
    success: bool = Field(..., description="匹配是否成功")
    matched_data: Dict[str, Any] = Field(..., description="匹配的结构化数据")
    total_fields: int = Field(..., description="总字段数")
    matched_fields: int = Field(..., description="成功匹配的字段数")
    error_message: Optional[str] = Field(None, description="错误信息")


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
