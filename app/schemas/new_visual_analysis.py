"""
新视觉分析方案专用的数据模型

基于new_visual_analysis_service.py中实际使用的数据结构定义Pydantic模型
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class FieldType(str, Enum):
    """字段类型枚举"""
    TEXT = "text"
    EMAIL = "email"
    TEL = "tel"
    PASSWORD = "password"
    URL = "url"
    NUMBER = "number"
    TEXTAREA = "textarea"
    SELECT = "select"
    SELECT_ONE = "select-one"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    SUBMIT = "submit"
    BUTTON = "button"


class MatchType(str, Enum):
    """匹配类型枚举"""
    EXACT = "exact"
    SYNONYM = "synonym"
    CONTAIN = "contain"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"


# ============ FormField 相关 ============

class AssociatedLabel(BaseModel):
    """关联标签信息"""
    text: str = Field(..., description="标签文本")
    association_type: str = Field(..., description="关联类型")


class SelectOption(BaseModel):
    """下拉选择选项"""
    value: str = Field(..., description="选项值")
    text: str = Field(..., description="选项显示文本")
    selected: bool = Field(default=False, description="是否已选中")


class FormField(BaseModel):
    """表单字段信息"""
    selector: str = Field(..., description="CSS选择器")
    type: str = Field(..., description="字段类型")  # 保持字符串，兼容现有代码
    label: str = Field(..., description="字段标签")
    required: bool = Field(default=False, description="是否必填")
    name: str = Field(default="", description="name属性")
    id: str = Field(default="", description="id属性")
    placeholder: str = Field(default="", description="placeholder属性")
    value: str = Field(default="", description="当前值")
    disabled: bool = Field(default=False, description="是否禁用")
    readonly: bool = Field(default=False, description="是否只读")
    associated_labels: List[AssociatedLabel] = Field(default_factory=list, description="关联的标签")
    options: List[SelectOption] = Field(default_factory=list, description="下拉选项（仅select类型）")


# ============ Phase 2: 字段提取结果 ============

class FieldExtractionResult(BaseModel):
    """Phase 2: 字段提取结果"""
    success: bool = Field(..., description="是否成功")
    fields: List[FormField] = Field(default_factory=list, description="提取的字段列表")
    error: Optional[str] = Field(default=None, description="错误信息")


# ============ Phase 3: 视觉大模型分析结果 ============

class VisualLLMResult(BaseModel):
    """Phase 3: 视觉大模型分析结果"""
    success: bool = Field(..., description="是否成功")
    field_mappings: Dict[str, str] = Field(default_factory=dict, description="识别的字段映射")
    analysis_confidence: float = Field(default=0.0, description="分析置信度", ge=0.0, le=1.0)
    raw_response: str = Field(default="", description="原始响应内容")
    error: Optional[str] = Field(default=None, description="错误信息")


# ============ Phase 4: 标签匹配结果 ============

class FieldMatchResult(BaseModel):
    """单个字段匹配结果"""
    selector: str = Field(..., description="CSS选择器")
    type: str = Field(..., description="字段类型")
    llm_label: str = Field(..., description="大模型识别的标签")
    form_label: str = Field(..., description="表单字段标签")
    value: str = Field(..., description="填写值")
    match_type: str = Field(..., description="匹配类型")
    confidence: float = Field(..., description="匹配置信度", ge=0.0, le=1.0)
    required: bool = Field(default=False, description="是否必填")


class UnmatchedField(BaseModel):
    """未匹配的字段"""
    label: str = Field(..., description="字段标签")
    value: Optional[str] = Field(default=None, description="字段值")
    selector: Optional[str] = Field(default=None, description="CSS选择器")


class MatchingStatistics(BaseModel):
    """匹配统计信息"""
    total_llm_fields: int = Field(..., description="大模型识别字段总数")
    total_form_fields: int = Field(..., description="表单字段总数")
    matched_count: int = Field(..., description="成功匹配数量")
    match_rate: float = Field(..., description="匹配率", ge=0.0, le=1.0)
    unmatched_llm_count: int = Field(..., description="未匹配的大模型字段数")
    unmatched_form_count: int = Field(..., description="未匹配的表单字段数")


class LabelMatchingResult(BaseModel):
    """Phase 4: 标签匹配结果"""
    success: bool = Field(..., description="是否成功")
    matching_results: List[FieldMatchResult] = Field(default_factory=list, description="匹配结果列表")
    unmatched_llm_fields: List[UnmatchedField] = Field(default_factory=list, description="未匹配的大模型字段")
    unmatched_form_fields: List[UnmatchedField] = Field(default_factory=list, description="未匹配的表单字段")
    statistics: MatchingStatistics = Field(..., description="匹配统计信息")
    error: Optional[str] = Field(default=None, description="错误信息")


# ============ Phase 5: 表单填写结果 ============

class FillResult(BaseModel):
    """单个字段填写结果"""
    success: bool = Field(..., description="是否成功")
    selector: str = Field(..., description="CSS选择器")
    value: str = Field(..., description="填写的值")
    type: str = Field(..., description="字段类型")
    label: str = Field(..., description="字段标签")
    error: Optional[str] = Field(default=None, description="错误信息")


class FormFillingResult(BaseModel):
    """Phase 5: 表单填写结果"""
    success: bool = Field(..., description="是否成功")
    total_fields: int = Field(..., description="总字段数")
    successful_fills: int = Field(..., description="成功填写数")
    failed_fills: int = Field(..., description="失败填写数")
    fill_results: List[FillResult] = Field(default_factory=list, description="填写结果详情")
    fill_script: Optional[str] = Field(default=None, description="生成的填写脚本")
    fill_rate: float = Field(..., description="填写成功率", ge=0.0, le=1.0)
    error: Optional[str] = Field(default=None, description="错误信息")


# ============ 各Phase结果汇总 ============

class PhaseResult(BaseModel):
    """单个Phase结果（灵活结构）"""
    success: bool = Field(..., description="是否成功")
    # 其他字段使用动态字典，保持灵活性
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="额外数据")

    def __init__(self, **data):
        # 将所有非success的字段放入extra_data
        success = data.pop('success')
        extra_data = data
        super().__init__(success=success, extra_data=extra_data)

    def __getitem__(self, key):
        """支持字典式访问"""
        if key == 'success':
            return self.success
        return self.extra_data.get(key)

    def get(self, key, default=None):
        """支持get方法"""
        if key == 'success':
            return self.success
        return self.extra_data.get(key, default)


class PhaseResults(BaseModel):
    """所有Phase结果"""
    phase1_screenshot: PhaseResult = Field(..., description="Phase 1: 截图结果")
    phase2_field_extraction: PhaseResult = Field(..., description="Phase 2: 字段提取结果")
    phase3_visual_llm: PhaseResult = Field(..., description="Phase 3: 视觉大模型结果")
    phase4_label_matching: PhaseResult = Field(..., description="Phase 4: 标签匹配结果")
    phase5_form_filling: PhaseResult = Field(..., description="Phase 5: 表单填写结果")


class AnalysisStatistics(BaseModel):
    """分析统计信息"""
    total_form_fields: int = Field(..., description="表单字段总数")
    llm_recognized_fields: int = Field(..., description="大模型识别字段数")
    successfully_matched_fields: int = Field(..., description="成功匹配字段数")
    fill_success_rate: float = Field(..., description="填写成功率", ge=0.0, le=1.0)
    overall_success_rate: float = Field(..., description="总体成功率", ge=0.0, le=1.0)
    analysis_time_seconds: float = Field(..., description="分析耗时（秒）")


class DebugInfo(BaseModel):
    """调试信息"""
    extracted_fields: List[FormField] = Field(default_factory=list, description="提取的字段")
    llm_raw_response: str = Field(default="", description="大模型原始响应")
    unmatched_llm_fields: List[UnmatchedField] = Field(default_factory=list, description="未匹配的大模型字段")
    unmatched_form_fields: List[UnmatchedField] = Field(default_factory=list, description="未匹配的表单字段")


# ============ 完整的视觉分析结果 ============

class VisualAnalysisResult(BaseModel):
    """完整的视觉分析结果"""
    success: bool = Field(..., description="是否成功")
    website_url: str = Field(default="", description="网站URL")
    analysis_time: float = Field(..., description="分析耗时（秒）")
    phase_results: PhaseResults = Field(..., description="各Phase结果")
    statistics: AnalysisStatistics = Field(..., description="统计信息")
    fill_script: Optional[str] = Field(default=None, description="填写脚本")
    debug_info: DebugInfo = Field(..., description="调试信息")
    error: Optional[str] = Field(default=None, description="错误信息")
    phase: Optional[str] = Field(default=None, description="失败的阶段")


# ============ 配置 ============

class AnalysisConfig(BaseModel):
    """分析配置"""
    viewport_width: int = Field(default=1200, description="视口宽度")
    viewport_height: int = Field(default=1400, description="视口高度")
    enable_form_filling: bool = Field(default=True, description="是否启用表单填写")
    save_screenshot: bool = Field(default=True, description="是否保存截图")
    save_analysis_result: bool = Field(default=True, description="是否保存分析结果")
