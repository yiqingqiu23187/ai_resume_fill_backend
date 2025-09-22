"""
简历相关的Pydantic模型 - 灵活的key-value结构
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class ResumeFieldSchema(BaseModel):
    """单个简历字段"""
    key: str = Field(..., description="字段名称", min_length=1, max_length=100)
    value: str = Field(..., description="字段值", max_length=1000)
    category: Optional[str] = Field(None, description="字段分类", max_length=50)
    display_order: Optional[int] = Field(None, description="显示顺序")


class ResumeBase(BaseModel):
    """简历基础模型"""
    title: Optional[str] = Field(None, description="简历标题", max_length=200)
    fields: Dict[str, str] = Field(default_factory=dict, description="简历字段数据")


class ResumeCreate(ResumeBase):
    """简历创建模型"""
    pass


class ResumeUpdate(BaseModel):
    """简历更新模型"""
    title: Optional[str] = Field(None, description="简历标题", max_length=200)
    fields: Optional[Dict[str, str]] = Field(None, description="简历字段数据")


class Resume(ResumeBase):
    """简历响应模型"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeListItem(BaseModel):
    """简历列表项模型"""
    id: UUID
    user_id: UUID
    title: Optional[str] = None
    field_count: int = Field(0, description="字段数量")
    updated_at: datetime

    class Config:
        from_attributes = True


class PresetFieldSchema(BaseModel):
    """预设字段模板"""
    key: str = Field(..., description="字段名称")
    label: str = Field(..., description="显示标签")
    category: str = Field(..., description="分类")
    placeholder: Optional[str] = Field(None, description="占位符")
    required: bool = Field(False, description="是否必填")


class ResumeTemplateSchema(BaseModel):
    """简历模板"""
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    preset_fields: List[PresetFieldSchema] = Field(..., description="预设字段")


# 预定义的常用字段模板
COMMON_RESUME_FIELDS = {
    "personal": [
        {"key": "name", "label": "姓名", "category": "个人信息", "required": True},
        {"key": "email", "label": "邮箱", "category": "个人信息", "required": True},
        {"key": "phone", "label": "电话", "category": "个人信息", "required": True},
        {"key": "address", "label": "地址", "category": "个人信息"},
        {"key": "birth_date", "label": "出生日期", "category": "个人信息"},
        {"key": "gender", "label": "性别", "category": "个人信息"},
        {"key": "id_card", "label": "身份证号", "category": "个人信息"},
    ],
    "education": [
        {"key": "university", "label": "毕业院校", "category": "教育经历"},
        {"key": "degree", "label": "学历", "category": "教育经历"},
        {"key": "major", "label": "专业", "category": "教育经历"},
        {"key": "graduation_date", "label": "毕业时间", "category": "教育经历"},
        {"key": "gpa", "label": "GPA", "category": "教育经历"},
        {"key": "undergraduate_school", "label": "本科学校", "category": "教育经历"},
        {"key": "graduate_school", "label": "研究生学校", "category": "教育经历"},
    ],
    "experience": [
        {"key": "current_company", "label": "当前公司", "category": "工作经验"},
        {"key": "current_position", "label": "当前职位", "category": "工作经验"},
        {"key": "work_years", "label": "工作年限", "category": "工作经验"},
        {"key": "previous_company", "label": "上一家公司", "category": "工作经验"},
        {"key": "previous_position", "label": "上一个职位", "category": "工作经验"},
        {"key": "salary_expectation", "label": "期望薪资", "category": "工作经验"},
    ],
    "skills": [
        {"key": "programming_languages", "label": "编程语言", "category": "技能证书"},
        {"key": "frameworks", "label": "技术框架", "category": "技能证书"},
        {"key": "languages", "label": "语言能力", "category": "技能证书"},
        {"key": "certifications", "label": "专业证书", "category": "技能证书"},
        {"key": "soft_skills", "label": "软技能", "category": "技能证书"},
    ]
}


def get_preset_fields() -> List[PresetFieldSchema]:
    """获取所有预设字段"""
    all_fields = []
    for category_fields in COMMON_RESUME_FIELDS.values():
        for field_data in category_fields:
            all_fields.append(PresetFieldSchema(**field_data))
    return all_fields


def get_preset_fields_by_category(category: str) -> List[PresetFieldSchema]:
    """根据分类获取预设字段"""
    if category in COMMON_RESUME_FIELDS:
        return [PresetFieldSchema(**field) for field in COMMON_RESUME_FIELDS[category]]
    return []
