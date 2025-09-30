"""
Phase 5: 大模型数据格式转换服务

将Phase 4的结构化数据转换为适合大模型理解的简洁格式
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class LLMDataFormatter:
    """大模型数据格式转换器"""

    def __init__(self):
        """初始化格式转换器"""
        logger.info("🔄 初始化LLM数据格式转换器")

    def format_for_llm(self, phase4_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将Phase 4结果转换为大模型友好的格式

        Args:
            phase4_result: Phase 4的结构化分析结果

        Returns:
            适合大模型的简洁数据格式
        """
        try:
            logical_groups = phase4_result.get('logical_groups', [])

            # 构建简洁的大模型输入格式
            llm_data = {
                'form_structure': {
                    'groups': []
                },
                'metadata': {
                    'total_groups': len(logical_groups),
                    'total_fields': phase4_result.get('input_fields', 0),
                    'analysis_quality': phase4_result.get('phase4_quality', {}).get('level', 'unknown')
                }
            }

            # 处理每个逻辑分组
            for group in logical_groups:
                formatted_group = self._format_group_for_llm(group)
                if formatted_group:  # 只添加有效的分组
                    llm_data['form_structure']['groups'].append(formatted_group)

            logger.info(f"✅ 格式转换完成: {len(logical_groups)}个分组 → {len(llm_data['form_structure']['groups'])}个有效分组")
            return llm_data

        except Exception as e:
            logger.error(f"❌ 数据格式转换失败: {str(e)}")
            return self._create_empty_format()

    def _format_group_for_llm(self, group: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        格式化单个分组

        Args:
            group: 原始分组数据

        Returns:
            格式化后的分组数据
        """
        fields = group.get('fields', [])
        if not fields:
            return None

        formatted_group = {
            'title': group.get('title', '未知分组'),
            'fields': []
        }

        # 如果是可重复分组，添加标记
        if group.get('is_repeatable', False):
            formatted_group['is_repeatable'] = True

        # 处理分组内的字段
        for field in fields:
            formatted_field = self._format_field_for_llm(field, group.get('is_repeatable', False))
            if formatted_field:
                formatted_group['fields'].append(formatted_field)

        return formatted_group if formatted_group['fields'] else None

    def _format_field_for_llm(self, field: Dict[str, Any], is_in_repeatable_group: bool) -> Optional[Dict[str, Any]]:
        """
        格式化单个字段

        Args:
            field: 原始字段数据
            is_in_repeatable_group: 是否在可重复分组中

        Returns:
            格式化后的字段数据
        """
        selector = field.get('selector', '')
        label = field.get('label', '')

        if not selector or not label:
            return None

        formatted_field = {
            'selector': selector,
            'label': label
        }

        # 如果在可重复分组中且有数组索引，添加索引信息
        if is_in_repeatable_group and field.get('array_index') is not None:
            formatted_field['array_index'] = field.get('array_index')

        # 添加字段类型信息（如果有用）
        field_type = field.get('type', 'text')
        if field_type in ['select', 'radio', 'checkbox', 'textarea']:
            formatted_field['type'] = field_type

        return formatted_field

    def _create_empty_format(self) -> Dict[str, Any]:
        """创建空的格式"""
        return {
            'form_structure': {
                'groups': []
            },
            'metadata': {
                'total_groups': 0,
                'total_fields': 0,
                'analysis_quality': 'error'
            }
        }

    def extract_structure_summary(self, llm_data: Dict[str, Any]) -> str:
        """
        提取结构摘要，用于提示词生成

        Args:
            llm_data: 格式化后的数据

        Returns:
            结构摘要文本
        """
        groups = llm_data.get('form_structure', {}).get('groups', [])
        if not groups:
            return "表单结构为空"

        summary_parts = []

        for i, group in enumerate(groups, 1):
            title = group.get('title', f'分组{i}')
            field_count = len(group.get('fields', []))
            is_repeatable = group.get('is_repeatable', False)

            if is_repeatable:
                summary_parts.append(f"{title}({field_count}个字段,可重复)")
            else:
                summary_parts.append(f"{title}({field_count}个字段)")

        return "表单包含: " + "、".join(summary_parts)

    def get_total_field_count(self, llm_data: Dict[str, Any]) -> int:
        """获取总字段数"""
        total = 0
        groups = llm_data.get('form_structure', {}).get('groups', [])
        for group in groups:
            total += len(group.get('fields', []))
        return total

    def get_repeatable_groups(self, llm_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取可重复的分组"""
        groups = llm_data.get('form_structure', {}).get('groups', [])
        return [group for group in groups if group.get('is_repeatable', False)]
