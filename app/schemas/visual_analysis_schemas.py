"""
视觉驱动表单分析 - 数据Schema定义

定义各个Phase之间的标准数据格式，确保数据流转的一致性和可维护性
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# 公共枚举和基础类型
# ============================================================================

class ProcessingPhase(str, Enum):
    """处理阶段枚举"""
    PHASE1_SCREENSHOT = "phase1_screenshot"
    PHASE2_CV_ANALYSIS = "phase2_cv_analysis"
    PHASE3_SEMANTIC_ENHANCEMENT = "phase3_semantic_enhancement"
    PHASE4_STRUCTURE_RECOGNITION = "phase4_structure_recognition"
    PHASE5_LLM_INTEGRATION = "phase5_llm_integration"


class QualityLevel(str, Enum):
    """质量等级枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class FieldType(str, Enum):
    """字段类型枚举"""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    NUMBER = "number"
    SELECT = "select"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"


# ============================================================================
# Phase 1: 截图和BBOX数据Schema
# ============================================================================

class BoundingBox(BaseModel):
    """边界框坐标"""
    x: float = Field(..., description="左上角X坐标")
    y: float = Field(..., description="左上角Y坐标")
    width: float = Field(..., description="宽度")
    height: float = Field(..., description="高度")


class FormElement(BaseModel):
    """表单元素信息"""
    selector: str = Field(..., description="CSS选择器")
    type: FieldType = Field(..., description="元素类型")
    bbox: BoundingBox = Field(..., description="边界框坐标")
    text_content: Optional[str] = Field(None, description="元素文本内容")
    placeholder: Optional[str] = Field(None, description="占位符文本")
    value: Optional[str] = Field(None, description="当前值")
    required: bool = Field(False, description="是否必填")
    associated_labels: List[str] = Field(default_factory=list, description="关联的标签文本")


class ViewportInfo(BaseModel):
    """视口信息"""
    width: int = Field(..., description="视口宽度")
    height: int = Field(..., description="视口高度")


class Phase1Result(BaseModel):
    """Phase 1 输出Schema"""
    success: bool = Field(..., description="是否成功")
    phase: ProcessingPhase = Field(ProcessingPhase.PHASE1_SCREENSHOT, description="处理阶段")
    screenshot_url: Optional[str] = Field(None, description="截图URL")
    viewport: ViewportInfo = Field(..., description="视口信息")
    elements: Dict[str, Any] = Field(..., description="元素数据")
    processing_time: float = Field(..., description="处理时间(秒)")
    error: Optional[str] = Field(None, description="错误信息")


# ============================================================================
# Phase 2: 计算机视觉分析Schema
# ============================================================================

class VisualRegion(BaseModel):
    """视觉区块"""
    id: str = Field(..., description="区块ID")
    bbox: BoundingBox = Field(..., description="区块边界框")
    elements: List[str] = Field(..., description="包含的元素选择器列表")
    algorithm_source: str = Field(..., description="生成算法来源(xy_cut/morphology/fusion)")
    confidence_score: float = Field(..., description="区块置信度")


class AlgorithmConfig(BaseModel):
    """算法配置"""
    xy_cut_threshold: int = Field(10, description="XY-Cut阈值")
    morphology_kernel_size: int = Field(20, description="形态学核大小")
    min_region_size: int = Field(50, description="最小区域大小")
    similarity_threshold: float = Field(0.8, description="相似度阈值")


class Phase2Result(BaseModel):
    """Phase 2 输出Schema"""
    success: bool = Field(..., description="是否成功")
    phase: ProcessingPhase = Field(ProcessingPhase.PHASE2_CV_ANALYSIS, description="处理阶段")
    visual_regions: List[VisualRegion] = Field(..., description="视觉区块列表")
    algorithm_config: AlgorithmConfig = Field(..., description="使用的算法配置")
    cv_quality: Dict[str, Any] = Field(..., description="CV分析质量评估")
    processing_time: float = Field(..., description="处理时间(秒)")
    error: Optional[str] = Field(None, description="错误信息")


# ============================================================================
# Phase 3: 语义增强Schema
# ============================================================================

class EnhancedField(BaseModel):
    """语义增强后的字段"""
    selector: str = Field(..., description="CSS选择器")
    type: FieldType = Field(..., description="字段类型")
    label: str = Field(..., description="字段标签")
    semantic_context: Dict[str, Any] = Field(..., description="语义上下文")
    container_info: Optional[Dict[str, str]] = Field(None, description="容器信息")
    label_associations: List[str] = Field(default_factory=list, description="标签关联")


class SemanticRegion(BaseModel):
    """语义增强的区块"""
    id: str = Field(..., description="区块ID")
    title: Optional[str] = Field(None, description="区块标题")
    bbox: BoundingBox = Field(..., description="区块边界框")
    fields: List[EnhancedField] = Field(..., description="增强字段列表")
    semantic_category: Optional[str] = Field(None, description="语义分类")


class Phase3Result(BaseModel):
    """Phase 3 输出Schema"""
    success: bool = Field(..., description="是否成功")
    phase: ProcessingPhase = Field(ProcessingPhase.PHASE3_SEMANTIC_ENHANCEMENT, description="处理阶段")
    semantic_regions: List[SemanticRegion] = Field(..., description="语义增强区块")
    total_enhanced_fields: int = Field(..., description="增强字段总数")
    semantic_quality: Dict[str, Any] = Field(..., description="语义质量评估")
    processing_time: float = Field(..., description="处理时间(秒)")
    error: Optional[str] = Field(None, description="错误信息")


# ============================================================================
# Phase 4: 结构识别Schema
# ============================================================================

class StructuredField(BaseModel):
    """结构化字段"""
    selector: str = Field(..., description="CSS选择器")
    type: FieldType = Field(..., description="字段类型")
    label: str = Field(..., description="字段标签")
    array_index: Optional[int] = Field(None, description="数组索引(重复结构)")
    required: bool = Field(False, description="是否必填")


class LogicalGroup(BaseModel):
    """逻辑分组"""
    id: str = Field(..., description="分组ID")
    title: str = Field(..., description="分组标题")
    is_repeatable: bool = Field(False, description="是否可重复")
    fields: List[StructuredField] = Field(..., description="字段列表")
    structure_signature: Optional[str] = Field(None, description="结构签名")


class Phase4Quality(BaseModel):
    """Phase 4质量评估"""
    level: QualityLevel = Field(..., description="质量等级")
    score: float = Field(..., description="质量得分")
    detected_patterns: List[str] = Field(..., description="检测到的模式")
    structure_complexity: str = Field(..., description="结构复杂度")


class Phase4Result(BaseModel):
    """Phase 4 输出Schema"""
    success: bool = Field(..., description="是否成功")
    phase: ProcessingPhase = Field(ProcessingPhase.PHASE4_STRUCTURE_RECOGNITION, description="处理阶段")
    logical_groups: List[LogicalGroup] = Field(..., description="逻辑分组列表")
    input_fields: int = Field(..., description="输入字段数")
    phase4_quality: Phase4Quality = Field(..., description="质量评估")
    processing_time: float = Field(..., description="处理时间(秒)")
    error: Optional[str] = Field(None, description="错误信息")


# ============================================================================
# Phase 5: LLM集成Schema
# ============================================================================

class MatchingResult(BaseModel):
    """字段匹配结果"""
    selector: str = Field(..., description="CSS选择器")
    value: str = Field(..., description="填写值")


class ValidationStatistics(BaseModel):
    """验证统计"""
    total_fields: int = Field(..., description="总字段数")
    valid_fields: int = Field(..., description="有效字段数")
    warning_fields: int = Field(..., description="警告字段数")
    error_fields: int = Field(..., description="错误字段数")


class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool = Field(..., description="是否有效")
    overall_score: float = Field(..., description="总体得分")
    issues: List[str] = Field(..., description="问题列表")
    suggestions: List[str] = Field(..., description="建议列表")
    statistics: ValidationStatistics = Field(..., description="验证统计")


class ProcessingStatistics(BaseModel):
    """处理统计"""
    input_groups: int = Field(..., description="输入分组数")
    input_fields: int = Field(..., description="输入字段数")
    matched_fields: int = Field(..., description="匹配字段数")
    valid_matches: int = Field(..., description="有效匹配数")
    match_rate: float = Field(..., description="匹配率")
    validation_score: float = Field(..., description="验证得分")


class QualityAssessment(BaseModel):
    """质量评估"""
    overall_quality: QualityLevel = Field(..., description="总体质量")
    structure_quality: Optional[Dict[str, Any]] = Field(None, description="结构质量")
    matching_quality: float = Field(..., description="匹配质量")
    recommendations: List[str] = Field(..., description="改进建议")


class ProcessingMetadata(BaseModel):
    """处理元数据"""
    structure_summary: str = Field(..., description="结构摘要")
    complexity: str = Field(..., description="复杂度")
    repeatable_groups: int = Field(..., description="可重复分组数")
    phase4_source: Dict[str, Any] = Field(..., description="Phase4来源信息")


class Phase5Result(BaseModel):
    """Phase 5 输出Schema"""
    success: bool = Field(..., description="是否成功")
    phase: ProcessingPhase = Field(ProcessingPhase.PHASE5_LLM_INTEGRATION, description="处理阶段")
    matching_results: List[MatchingResult] = Field(..., description="匹配结果列表")
    validation_result: ValidationResult = Field(..., description="验证结果")
    statistics: ProcessingStatistics = Field(..., description="处理统计")
    quality_assessment: QualityAssessment = Field(..., description="质量评估")
    metadata: ProcessingMetadata = Field(..., description="处理元数据")
    processing_time: float = Field(..., description="处理时间(秒)")
    error: Optional[str] = Field(None, description="错误信息")


# ============================================================================
# 统一API请求和响应Schema
# ============================================================================

class AnalysisRequest(BaseModel):
    """统一分析请求"""
    resume_id: str = Field(..., description="简历ID")
    html_content: str = Field(..., description="HTML内容")
    website_url: str = Field(..., description="网站URL")
    analysis_config: Optional[Dict[str, Any]] = Field(None, description="分析配置")
    force_phase: Optional[ProcessingPhase] = Field(None, description="强制指定处理阶段")


class UnifiedAnalysisResult(BaseModel):
    """统一分析结果"""
    success: bool = Field(..., description="是否成功")
    request_id: str = Field(..., description="请求ID")
    total_processing_time: float = Field(..., description="总处理时间(秒)")

    # 各阶段结果
    phase1_result: Optional[Phase1Result] = Field(None, description="Phase 1结果")
    phase2_result: Optional[Phase2Result] = Field(None, description="Phase 2结果")
    phase3_result: Optional[Phase3Result] = Field(None, description="Phase 3结果")
    phase4_result: Optional[Phase4Result] = Field(None, description="Phase 4结果")
    phase5_result: Optional[Phase5Result] = Field(None, description="Phase 5结果")

    # 最终输出 (前端直接使用)
    final_matching_results: List[MatchingResult] = Field(..., description="最终匹配结果")
    final_quality_assessment: QualityAssessment = Field(..., description="最终质量评估")
    final_recommendations: List[str] = Field(..., description="最终建议")

    # 错误信息
    error: Optional[str] = Field(None, description="错误信息")
    failed_phase: Optional[ProcessingPhase] = Field(None, description="失败阶段")


# ============================================================================
# 简历数据Schema
# ============================================================================

class BasicInfo(BaseModel):
    """基本信息"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    address: Optional[str] = None


class Education(BaseModel):
    """教育经历"""
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None


class WorkExperience(BaseModel):
    """工作经历"""
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None


class ResumeData(BaseModel):
    """简历数据"""
    basic_info: Optional[BasicInfo] = None
    education: List[Education] = Field(default_factory=list)
    work_experience: List[WorkExperience] = Field(default_factory=list)
    skills: Optional[Dict[str, Any]] = None
