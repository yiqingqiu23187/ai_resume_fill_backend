"""
基于HTML结构的智能分组分析器

完全基于网页的自然结构进行分组，无需预定义语义配置
"""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class HtmlStructureAnalyzer:
    """基于HTML结构的分组分析器"""

    def __init__(self):
        """初始化结构分析器"""
        self.group_title_mappings = {
            # 常见的分组标题映射
            '基本信息': ['基本信息', '个人信息', '基础信息', '基本资料'],
            '教育背景': ['教育背景', '教育经历', '学历信息', '教育信息'],
            '工作经历': ['工作经历', '工作经验', '职业经历', '实习经历'],
            '技能特长': ['技能特长', '专业技能', '技能与特长', '技能信息'],
            '联系方式': ['联系方式', '联系信息', '通讯地址'],
            '家庭信息': ['家庭信息', '家庭成员', '家庭背景'],
            '证书资质': ['证书资质', '资格证书', '证书信息', '获奖情况'],
            '其他信息': ['其他信息', '补充信息', '备注']
        }
        logger.info("🏗️ HTML结构分析器初始化完成")

    def analyze_structure(self, phase2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于HTML结构分析字段分组

        Args:
            phase2_result: Phase 2的分析结果

        Returns:
            结构化分组结果
        """
        try:
            print("🏗️ [DEBUG] HTML结构分析器开始运行...")
            logger.info("🏗️ 开始基于HTML结构进行分组分析...")

            # 提取字段数据
            elements_data = phase2_result.get('elements', {})
            fields = elements_data.get('elements_data', [])

            if not fields:
                print(f"⚠️ [DEBUG] 没有找到字段数据，elements_data: {elements_data}")
                logger.warning("⚠️ 没有找到字段数据")
                return self._create_empty_result()

            print(f"📊 [DEBUG] 开始分析 {len(fields)} 个字段")
            logger.info(f"📊 开始分析 {len(fields)} 个字段")

            # 第1步: 基于容器信息进行分组
            container_groups = self._group_by_containers(fields)

            # 第2步: 检测和处理数组字段
            array_analysis = self._analyze_array_patterns(container_groups)

            # 第3步: 构建最终的逻辑分组
            logical_groups = self._build_logical_groups(array_analysis)

            # 第4步: 生成结构模板
            structure_template = self._generate_structure_template(logical_groups)

            result = {
                'success': True,
                'phase': 'phase4_html_structure_analysis',
                'input_fields': len(fields),
                'logical_groups': logical_groups,
                'structure_template': structure_template,
                'analysis_summary': {
                    'total_groups': len(logical_groups),
                    'grouped_fields': sum(len(group['fields']) for group in logical_groups),
                    'grouping_method': 'html_structure',
                    'coverage_rate': sum(len(group['fields']) for group in logical_groups) / len(fields) if fields else 0
                },
                'ready_for_phase5': True
            }

            logger.info(f"✅ HTML结构分析完成: {len(logical_groups)}个分组")
            return result

        except Exception as e:
            logger.error(f"❌ HTML结构分析失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"HTML结构分析错误: {str(e)}",
                'phase': 'phase4_html_structure_error'
            }

    def _group_by_containers(self, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于容器信息进行分组

        Args:
            fields: 字段列表

        Returns:
            容器分组结果
        """
        groups = defaultdict(list)
        ungrouped_fields = []

        for field in fields:
            container_info = field.get('container_info', {})
            group_title = container_info.get('groupTitle')

            if group_title:
                # 标准化分组标题
                normalized_title = self._normalize_group_title(group_title)
                field['normalized_group_title'] = normalized_title
                groups[normalized_title].append(field)
                logger.info(f"📦 字段分组: '{self._get_field_label(field)}' → '{normalized_title}'")
            else:
                ungrouped_fields.append(field)

        # 处理未分组的字段 - 尝试基于位置进行分组
        if ungrouped_fields:
            position_groups = self._group_by_position(ungrouped_fields)
            for group_name, group_fields in position_groups.items():
                groups[group_name].extend(group_fields)

        return {
            'container_groups': dict(groups),
            'ungrouped_fields': []  # 所有字段都应该被分组
        }

    def _normalize_group_title(self, title: str) -> str:
        """
        标准化分组标题

        Args:
            title: 原始标题

        Returns:
            标准化后的标题
        """
        if not title:
            return '其他信息'

        title = title.strip()

        # 映射到标准分组名称
        for standard_title, variations in self.group_title_mappings.items():
            if any(variation in title for variation in variations):
                return standard_title

        # 如果没有匹配，返回清理后的原标题
        return title

    def _group_by_position(self, fields: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        基于位置信息进行分组（未分组字段的fallback）

        Args:
            fields: 未分组的字段列表

        Returns:
            位置分组结果
        """
        # 按Y坐标排序
        sorted_fields = sorted(fields, key=lambda f: f.get('bbox', {}).get('y', 0))

        position_groups = {}
        current_group = []
        last_y = None
        group_counter = 1

        for field in sorted_fields:
            y = field.get('bbox', {}).get('y', 0)

            # 如果Y坐标差距较大，开始新分组
            if last_y is not None and abs(y - last_y) > 100:  # 100像素阈值
                if current_group:
                    position_groups[f'区域{group_counter}'] = current_group
                    group_counter += 1
                    current_group = []

            current_group.append(field)
            last_y = y

        # 处理最后一组
        if current_group:
            position_groups[f'区域{group_counter}'] = current_group

        return position_groups

    def _analyze_array_patterns(self, container_groups: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析数组模式

        Args:
            container_groups: 容器分组结果

        Returns:
            数组分析结果
        """
        array_groups = {}
        single_groups = {}

        for group_name, group_fields in container_groups['container_groups'].items():
            # 检测数组模式
            array_info = self._detect_group_array_pattern(group_fields)

            if array_info['is_array']:
                array_groups[group_name] = {
                    'fields': group_fields,
                    'array_info': array_info
                }
                logger.info(f"🔄 检测到数组分组: '{group_name}' ({len(group_fields)}个字段)")
            else:
                single_groups[group_name] = group_fields

        return {
            'array_groups': array_groups,
            'single_groups': single_groups
        }

    def _detect_group_array_pattern(self, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        检测分组是否为数组模式

        Args:
            fields: 分组中的字段列表

        Returns:
            数组模式信息
        """
        if len(fields) < 2:
            return {'is_array': False}

        # 检查字段名称是否有数组模式
        array_patterns = []
        for field in fields:
            field_name = field.get('name', '') or field.get('selector', '')
            if field_name:
                # 检测常见的数组模式
                import re
                if re.search(r'_\d+$|_\d+_|\[\d+\]', field_name):
                    array_patterns.append(True)
                else:
                    array_patterns.append(False)

        # 如果超过一半的字段有数组模式，认为是数组分组
        array_ratio = sum(array_patterns) / len(array_patterns) if array_patterns else 0
        is_array = array_ratio > 0.5

        return {
            'is_array': is_array,
            'array_ratio': array_ratio,
            'total_fields': len(fields)
        }

    def _build_logical_groups(self, array_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        构建最终的逻辑分组

        Args:
            array_analysis: 数组分析结果

        Returns:
            逻辑分组列表
        """
        logical_groups = []

        # 处理单个分组
        for group_name, group_fields in array_analysis['single_groups'].items():
            logical_groups.append({
                'group_id': f'single_{group_name}',
                'title': group_name,
                'is_repeatable': False,
                'fields': group_fields,
                'field_count': len(group_fields),
                'grouping_method': 'html_structure'
            })

        # 处理数组分组
        for group_name, group_info in array_analysis['array_groups'].items():
            logical_groups.append({
                'group_id': f'array_{group_name}',
                'title': group_name,
                'is_repeatable': True,
                'fields': group_info['fields'],
                'field_count': len(group_info['fields']),
                'array_info': group_info['array_info'],
                'grouping_method': 'html_structure'
            })

        # 按字段数量排序（重要分组在前）
        logical_groups.sort(key=lambda x: x['field_count'], reverse=True)

        return logical_groups

    def _generate_structure_template(self, logical_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成结构模板

        Args:
            logical_groups: 逻辑分组列表

        Returns:
            结构模板
        """
        template = {
            'groups': [],
            'metadata': {
                'total_groups': len(logical_groups),
                'total_fields': sum(group['field_count'] for group in logical_groups),
                'repeatable_groups': sum(1 for group in logical_groups if group['is_repeatable']),
                'single_groups': sum(1 for group in logical_groups if not group['is_repeatable']),
                'generation_method': 'html_structure_based'
            }
        }

        for group in logical_groups:
            group_template = {
                'id': group['group_id'],
                'title': group['title'],
                'is_repeatable': group['is_repeatable'],
                'field_count': group['field_count'],
                'fields': []
            }

            # 处理字段
            for field in group['fields']:
                field_template = {
                    'selector': field.get('selector', ''),
                    'type': field.get('type', 'unknown'),
                    'label': self._get_field_label(field),
                    'required': field.get('required', False),
                    'bbox': field.get('bbox', {}),
                    'container_group': group['title']
                }

                group_template['fields'].append(field_template)

            template['groups'].append(group_template)

        return template

    def _get_field_label(self, field: Dict[str, Any]) -> str:
        """
        获取字段标签

        Args:
            field: 字段数据

        Returns:
            字段标签
        """
        # 从关联标签中获取
        labels = field.get('associated_labels', [])
        if labels:
            first_label = labels[0].get('text', '').strip()
            if first_label:
                return first_label

        # fallback到其他属性
        return (field.get('placeholder', '') or
                field.get('title', '') or
                field.get('name', '') or
                field.get('id', '') or
                'unknown').strip()

    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空结果"""
        return {
            'success': True,
            'phase': 'phase4_html_structure_empty',
            'logical_groups': [],
            'structure_template': {
                'groups': [],
                'metadata': {'total_groups': 0, 'total_fields': 0}
            },
            'analysis_summary': {
                'total_groups': 0,
                'grouped_fields': 0,
                'coverage_rate': 0
            },
            'ready_for_phase5': True
        }
