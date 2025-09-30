"""
视觉分析相关的Pydantic模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class VisualAnalysisConfig(BaseModel):
    """视觉分析配置参数"""
    viewport_width: int = Field(default=1920, description="视窗宽度", ge=800, le=3840)
    viewport_height: int = Field(default=1080, description="视窗高度", ge=600, le=2160)
    full_page: bool = Field(default=True, description="是否截取完整页面")
    screenshot_timeout: int = Field(default=5000, description="截图等待时间(ms)", ge=1000, le=30000)
    xy_cut_threshold: int = Field(default=10, description="XY-Cut算法阈值", ge=1, le=100)
    morphology_kernel_size: int = Field(default=20, description="形态学算子核大小", ge=5, le=100)
    min_region_size: int = Field(default=50, description="最小区域大小", ge=10, le=500)
    similarity_threshold: float = Field(default=0.8, description="相似度阈值", ge=0.1, le=1.0)


class VisualAnalysisRequest(BaseModel):
    """视觉分析请求"""
    resume_id: UUID = Field(..., description="简历ID")
    html_content: str = Field(..., description="页面HTML内容")
    website_url: Optional[str] = Field(None, description="网站URL")
    analysis_config: Optional[VisualAnalysisConfig] = Field(None, description="分析配置参数")


class BoundingBox(BaseModel):
    """边界框坐标信息"""
    x: int = Field(..., description="X坐标")
    y: int = Field(..., description="Y坐标")
    width: int = Field(..., description="宽度")
    height: int = Field(..., description="高度")
    left: int = Field(..., description="左边界")
    top: int = Field(..., description="上边界")
    right: int = Field(..., description="右边界")
    bottom: int = Field(..., description="下边界")


class AssociatedLabel(BaseModel):
    """关联标签信息"""
    text: str = Field(..., description="标签文本")
    association_type: str = Field(..., description="关联类型：for_attribute/parent_label/sibling_text")


class SelectOption(BaseModel):
    """下拉选项信息"""
    value: str = Field(..., description="选项值")
    text: str = Field(..., description="选项文本")
    selected: bool = Field(..., description="是否选中")


class FormElement(BaseModel):
    """表单元素信息"""
    selector: str = Field(..., description="CSS选择器")
    tag: str = Field(..., description="标签名")
    type: str = Field(..., description="元素类型")
    name: str = Field(..., description="name属性")
    id: str = Field(..., description="id属性")
    class_name: str = Field(alias="class", default="", description="class属性")
    placeholder: str = Field(..., description="placeholder文本")
    value: str = Field(..., description="当前值")
    text_content: str = Field(..., description="文本内容")
    required: bool = Field(..., description="是否必填")
    disabled: bool = Field(..., description="是否禁用")
    readonly: bool = Field(..., description="是否只读")
    bbox: BoundingBox = Field(..., description="边界框坐标")
    associated_labels: List[AssociatedLabel] = Field(..., description="关联的标签")
    element_index: int = Field(..., description="元素索引")
    options: Optional[List[SelectOption]] = Field(None, description="下拉选项(仅select元素)")

    class Config:
        allow_population_by_field_name = True


class ViewportInfo(BaseModel):
    """视窗信息"""
    width: int = Field(..., description="视窗宽度")
    height: int = Field(..., description="视窗高度")
    scroll_width: int = Field(alias="scrollWidth", description="可滚动宽度")
    scroll_height: int = Field(alias="scrollHeight", description="可滚动高度")

    class Config:
        allow_population_by_field_name = True


class ScreenshotInfo(BaseModel):
    """截图信息"""
    path: str = Field(..., description="截图文件路径")
    filename: str = Field(..., description="文件名")
    viewport: Dict[str, int] = Field(..., description="视窗尺寸")
    actual_size: Dict[str, int] = Field(..., description="页面实际尺寸")
    file_size: int = Field(..., description="文件大小(字节)")
    timestamp: str = Field(..., description="生成时间戳")


class ElementRelationship(BaseModel):
    """元素关系信息"""
    element1_selector: str = Field(..., description="元素1选择器")
    element2_selector: str = Field(..., description="元素2选择器")
    distance: float = Field(..., description="距离")
    relationship: str = Field(..., description="空间关系")
    alignment: str = Field(..., description="对齐关系")


class RelationshipAnalysis(BaseModel):
    """关系分析结果"""
    total_relationships: int = Field(..., description="关系总数")
    close_relationships: List[ElementRelationship] = Field(..., description="距离较近的关系")
    aligned_elements: List[ElementRelationship] = Field(..., description="对齐的元素")
    summary: Dict[str, int] = Field(..., description="关系摘要")


class FieldStatus(BaseModel):
    """字段状态统计"""
    required_fields: int = Field(..., description="必填字段数")
    filled_fields: int = Field(..., description="已填字段数")
    empty_fields: int = Field(..., description="空字段数")
    labeled_fields: int = Field(..., description="有标签字段数")
    unlabeled_fields: int = Field(..., description="无标签字段数")


class SpatialAnalysis(BaseModel):
    """空间分析结果"""
    total_relationships: int = Field(..., description="关系总数")
    nearby_elements: int = Field(..., description="邻近元素数")
    aligned_elements: int = Field(..., description="对齐元素数")
    vertical_groups: int = Field(..., description="垂直分组数")


class QualityMetrics(BaseModel):
    """质量评估指标"""
    labeling_rate: float = Field(..., description="标签覆盖率")
    fill_rate: float = Field(..., description="填写率")
    structure_complexity: str = Field(..., description="结构复杂度")


class AnalysisSummary(BaseModel):
    """分析结果摘要"""
    total_elements: int = Field(..., description="元素总数")
    element_types: Dict[str, int] = Field(..., description="元素类型统计")
    field_status: FieldStatus = Field(..., description="字段状态")
    spatial_analysis: SpatialAnalysis = Field(..., description="空间分析")
    quality_metrics: QualityMetrics = Field(..., description="质量指标")


class ElementsData(BaseModel):
    """元素数据"""
    total_count: int = Field(..., description="元素总数")
    elements_data: List[FormElement] = Field(..., description="元素详细信息")
    viewport_info: ViewportInfo = Field(..., description="视窗信息")
    html_analysis: Dict[str, Any] = Field(..., description="HTML分析结果")


class VisualAnalysisResponse(BaseModel):
    """视觉分析响应"""
    success: bool = Field(..., description="分析是否成功")
    website_url: Optional[str] = Field(None, description="网站URL")
    analysis_config: VisualAnalysisConfig = Field(..., description="使用的分析配置")
    screenshot: ScreenshotInfo = Field(..., description="截图信息")
    elements: ElementsData = Field(..., description="元素数据")
    relationships: RelationshipAnalysis = Field(..., description="关系分析")
    summary: AnalysisSummary = Field(..., description="分析摘要")
    phase: str = Field(..., description="当前实现阶段")
    next_phases: List[str] = Field(..., description="后续实现阶段")
    error_message: Optional[str] = Field(None, description="错误信息")


class VisualAnalysisErrorResponse(BaseModel):
    """视觉分析错误响应"""
    success: bool = Field(False, description="分析失败")
    error: str = Field(..., description="错误信息")
    phase: str = Field(..., description="出错阶段")
    screenshot_result: Optional[Dict[str, Any]] = Field(None, description="截图结果(如果已生成)")
