"""
Phase 4: 语义分组分析器

将Phase 2识别的平铺字段转换为有结构的逻辑分组
基于配置驱动的智能匹配，避免硬编码
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .fuzzy_matcher import FuzzyMatcher

logger = logging.getLogger(__name__)


class SemanticGroupAnalyzer:
    """语义分组分析器 - Phase 4核心模块"""

    def __init__(self, config_path: str = None):
        """
        初始化语义分组分析器

        Args:
            config_path: 语义配置文件路径
        """
        if not config_path:
            config_path = Path(__file__).parent.parent.parent / "config" / "semantic_groups.json"

        self.fuzzy_matcher = FuzzyMatcher(str(config_path))
        logger.info("🎯 Phase 4语义分组分析器初始化完成")

    def analyze_structure(self, phase2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析Phase 2结果，生成结构化分组

        Args:
            phase2_result: Phase 2的分析结果

        Returns:
            结构化分组结果
        """
        try:
            logger.info("🔍 Phase 4开始结构分析...")

            # 提取Phase 2的字段数据
            elements_data = phase2_result.get('elements', {})
            fields = elements_data.get('elements_data', [])
            relationships = phase2_result.get('relationships', {})

            if not fields:
                logger.warning("⚠️ 没有找到字段数据，跳过结构分析")
                return self._create_empty_result()

            logger.info(f"📊 开始分析 {len(fields)} 个字段")

            # 第1步: 为每个字段进行语义匹配
            matched_fields = self._match_fields_semantically(fields)

            # 第2步: 检测和分组数组字段
            array_analysis = self._analyze_array_patterns(matched_fields)

            # 第3步: 构建逻辑分组
            logical_groups = self._build_logical_groups(array_analysis, relationships)

            # 第4步: 生成最终结构模板
            structure_template = self._generate_structure_template(logical_groups)

            # 第5步: 验证和优化结构
            validated_structure = self._validate_and_optimize_structure(structure_template)

            result = {
                'success': True,
                'phase': 'phase4_structure_recognition',
                'input_fields': len(fields),
                'logical_groups': validated_structure['groups'],
                'structure_template': validated_structure['template'],
                'analysis_summary': validated_structure['summary'],
                'ready_for_phase5': True
            }

            logger.info(f"✅ Phase 4结构分析完成: {len(validated_structure['groups'])}个逻辑分组")
            return result

        except Exception as e:
            logger.error(f"❌ Phase 4结构分析失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Phase 4结构分析错误: {str(e)}",
                'phase': 'phase4_structure_recognition_error'
            }

    def _match_fields_semantically(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为每个字段进行语义匹配

        Args:
            fields: 字段列表

        Returns:
            带有语义匹配信息的字段列表
        """
        matched_fields = []

        for field in fields:
            # 提取字段信息
            field_label = self._extract_field_label(field)
            field_name = field.get('name', '') or field.get('selector', '')

            # 进行语义匹配
            match_result = self.fuzzy_matcher.find_best_match(
                field_label=field_label,
                field_name=field_name
            )

            # 保存匹配结果
            enhanced_field = field.copy()
            if match_result:
                enhanced_field['semantic_match'] = match_result
                logger.info(f"✅ 匹配成功: '{field_label}' → {match_result['group_title']}.{match_result.get('field_type')} (得分: {match_result['score']:.2f})")
            else:
                enhanced_field['semantic_match'] = None
                logger.info(f"⚠️ 未找到匹配: '{field_label}' (name: {field_name})")

            matched_fields.append(enhanced_field)

        # 统计匹配结果
        matched_count = sum(1 for f in matched_fields if f.get('semantic_match'))
        logger.info(f"📊 语义匹配完成: {matched_count}/{len(fields)} 个字段匹配成功")

        return matched_fields

    def _analyze_array_patterns(self, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析数组模式字段

        Args:
            fields: 带有语义匹配的字段列表

        Returns:
            数组分析结果
        """
        # 使用模糊匹配器的数组分组功能
        grouping_result = self.fuzzy_matcher.group_array_fields(fields)

        array_groups = grouping_result['array_groups']
        single_fields = grouping_result['single_fields']

        # 分析数组组的语义一致性
        validated_arrays = {}
        for base_name, group_fields in array_groups.items():
            if self._validate_array_semantic_consistency(group_fields):
                validated_arrays[base_name] = {
                    'fields': group_fields,
                    'count': len(group_fields),
                    'base_name': base_name,
                    'is_repeatable': True
                }
                logger.info(f"📋 检测到重复结构: {base_name} ({len(group_fields)}个实例)")
            else:
                # 语义不一致的数组，拆分为单个字段
                single_fields.extend(group_fields)

        return {
            'array_groups': validated_arrays,
            'single_fields': single_fields,
            'total_arrays': len(validated_arrays)
        }

    def _validate_array_semantic_consistency(self, group_fields: List[Dict[str, Any]]) -> bool:
        """
        验证数组字段的语义一致性

        Args:
            group_fields: 数组分组的字段列表

        Returns:
            是否语义一致
        """
        if len(group_fields) < 2:
            return False

        # 检查语义匹配的一致性
        semantic_groups = set()
        for field in group_fields:
            match = field.get('semantic_match')
            if match:
                semantic_groups.add(match['group_id'])

        # 如果所有字段都属于同一个语义分组，认为是一致的
        return len(semantic_groups) <= 1

    def _build_logical_groups(self, array_analysis: Dict[str, Any], relationships: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        构建逻辑分组

        Args:
            array_analysis: 数组分析结果
            relationships: 字段关系信息

        Returns:
            逻辑分组列表
        """
        logical_groups = []

        # 处理单个字段 - 按语义分组
        single_fields = array_analysis['single_fields']
        single_groups = self._group_single_fields_by_semantics(single_fields)

        # 处理数组字段 - 每个数组成为独立分组
        array_groups = array_analysis['array_groups']
        array_logical_groups = self._convert_arrays_to_logical_groups(array_groups)

        # 合并所有分组
        all_groups = single_groups + array_logical_groups

        # 按优先级排序
        all_groups.sort(key=lambda x: x.get('priority', 999))

        return all_groups

    def _group_single_fields_by_semantics(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将单个字段按语义分组

        Args:
            fields: 单个字段列表

        Returns:
            语义分组列表
        """
        semantic_groups = {}
        unmatched_fields = []

        for field in fields:
            match = field.get('semantic_match')
            if match:
                group_id = match['group_id']
                if group_id not in semantic_groups:
                    semantic_groups[group_id] = {
                        'group_id': group_id,
                        'title': match['group_title'],
                        'priority': match['priority'],
                        'is_repeatable': False,
                        'fields': [],
                        'field_types': set()
                    }

                semantic_groups[group_id]['fields'].append(field)
                semantic_groups[group_id]['field_types'].add(match.get('field_type', 'unknown'))
            else:
                unmatched_fields.append(field)

        # 转换为列表
        groups = list(semantic_groups.values())

        # 处理未匹配字段
        if unmatched_fields:
            groups.append({
                'group_id': 'unmatched',
                'title': '其他字段',
                'priority': 999,
                'is_repeatable': False,
                'fields': unmatched_fields,
                'field_types': set(['unknown'])
            })

        return groups

    def _convert_arrays_to_logical_groups(self, array_groups: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        将数组转换为逻辑分组

        Args:
            array_groups: 数组分组

        Returns:
            逻辑分组列表
        """
        logical_groups = []

        for base_name, array_info in array_groups.items():
            fields = array_info['fields']

            # 获取第一个字段的语义匹配信息作为组的语义
            first_field = fields[0] if fields else {}
            semantic_match = first_field.get('semantic_match') or {}

            # 安全地获取语义信息，提供默认值
            group_title = semantic_match.get('group_title', f"{base_name}列表")
            priority = semantic_match.get('priority', 500)
            field_type = semantic_match.get('field_type', 'unknown')

            group = {
                'group_id': f"array_{base_name}",
                'title': group_title,
                'priority': priority,
                'is_repeatable': True,
                'array_base_name': base_name,
                'array_count': len(fields),
                'fields': fields,
                'field_types': set([field_type])
            }

            logical_groups.append(group)

        return logical_groups

    def _generate_structure_template(self, logical_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成结构化模板

        Args:
            logical_groups: 逻辑分组列表

        Returns:
            结构化模板
        """
        template = {
            'groups': [],
            'metadata': {
                'total_groups': len(logical_groups),
                'repeatable_groups': 0,
                'single_groups': 0,
                'total_fields': 0
            }
        }

        for group in logical_groups:
            group_template = {
                'id': group['group_id'],
                'title': group['title'],
                'priority': group['priority'],
                'is_repeatable': group['is_repeatable'],
                'field_count': len(group['fields']),
                'fields': []
            }

            # 处理字段
            for field in group['fields']:
                field_template = {
                    'selector': field.get('selector', ''),
                    'type': field.get('type', 'unknown'),
                    'label': self._extract_field_label(field),
                    'required': field.get('required', False),
                    'bbox': field.get('bbox', {}),
                    'semantic_type': None
                }

                # 添加语义信息
                semantic_match = field.get('semantic_match')
                if semantic_match:
                    field_template['semantic_type'] = semantic_match.get('field_type')
                    field_template['semantic_group'] = semantic_match.get('group_id')
                    field_template['match_score'] = semantic_match.get('score', 0)

                # 添加数组信息
                array_info = field.get('array_info')
                if array_info and array_info.get('is_array'):
                    field_template['array_index'] = array_info.get('index', 0)
                    field_template['array_base_name'] = array_info.get('base_name', '')

                group_template['fields'].append(field_template)

            template['groups'].append(group_template)

            # 更新元数据
            if group['is_repeatable']:
                template['metadata']['repeatable_groups'] += 1
            else:
                template['metadata']['single_groups'] += 1

            template['metadata']['total_fields'] += len(group['fields'])

        return template

    def _validate_and_optimize_structure(self, structure_template: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和优化结构

        Args:
            structure_template: 结构模板

        Returns:
            验证和优化后的结构
        """
        groups = structure_template['groups']

        # 验证分组质量
        quality_metrics = self._calculate_structure_quality(groups)

        # 生成分析摘要
        summary = {
            'structure_quality': quality_metrics,
            'group_distribution': self._analyze_group_distribution(groups),
            'field_coverage': self._analyze_field_coverage(groups),
            'recommendations': self._generate_recommendations(quality_metrics, groups)
        }

        return {
            'groups': groups,
            'template': structure_template,
            'summary': summary
        }

    def _calculate_structure_quality(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算结构质量指标

        Args:
            groups: 分组列表

        Returns:
            质量指标
        """
        total_fields = sum(group['field_count'] for group in groups)
        matched_fields = 0
        high_confidence_matches = 0

        for group in groups:
            for field in group['fields']:
                if field.get('semantic_type'):
                    matched_fields += 1
                    if field.get('match_score', 0) > 0.8:
                        high_confidence_matches += 1

        return {
            'total_fields': total_fields,
            'semantic_match_rate': matched_fields / total_fields if total_fields > 0 else 0,
            'high_confidence_rate': high_confidence_matches / total_fields if total_fields > 0 else 0,
            'group_count': len(groups),
            'average_group_size': total_fields / len(groups) if groups else 0
        }

    def _analyze_group_distribution(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析分组分布

        Args:
            groups: 分组列表

        Returns:
            分布分析结果
        """
        group_sizes = [group['field_count'] for group in groups]
        repeatable_count = sum(1 for group in groups if group['is_repeatable'])

        return {
            'total_groups': len(groups),
            'repeatable_groups': repeatable_count,
            'single_groups': len(groups) - repeatable_count,
            'min_group_size': min(group_sizes) if group_sizes else 0,
            'max_group_size': max(group_sizes) if group_sizes else 0,
            'average_group_size': sum(group_sizes) / len(group_sizes) if group_sizes else 0
        }

    def _analyze_field_coverage(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析字段覆盖情况

        Args:
            groups: 分组列表

        Returns:
            覆盖分析结果
        """
        semantic_types = set()
        group_types = set()

        for group in groups:
            group_types.add(group['id'])
            for field in group['fields']:
                if field.get('semantic_type'):
                    semantic_types.add(field['semantic_type'])

        return {
            'unique_semantic_types': len(semantic_types),
            'unique_group_types': len(group_types),
            'semantic_types': list(semantic_types),
            'group_types': list(group_types)
        }

    def _generate_recommendations(self, quality_metrics: Dict[str, Any], groups: List[Dict[str, Any]]) -> List[str]:
        """
        生成优化建议

        Args:
            quality_metrics: 质量指标
            groups: 分组列表

        Returns:
            建议列表
        """
        recommendations = []

        # 基于语义匹配率的建议
        match_rate = quality_metrics['semantic_match_rate']
        if match_rate < 0.8:
            recommendations.append(f"语义匹配率偏低 ({match_rate:.1%})，建议扩展语义配置")

        # 基于分组数量的建议
        group_count = quality_metrics['group_count']
        if group_count > 8:
            recommendations.append("分组数量较多，可能需要进一步合并相关分组")
        elif group_count < 3:
            recommendations.append("分组数量较少，可能存在过度合并")

        # 基于分组大小的建议
        avg_size = quality_metrics['average_group_size']
        if avg_size > 10:
            recommendations.append("平均分组大小较大，考虑进一步细分")
        elif avg_size < 2:
            recommendations.append("平均分组大小较小，可能过度细分")

        return recommendations

    def _extract_field_label(self, field: Dict[str, Any]) -> str:
        """
        提取字段标签文本 - 优化版

        Args:
            field: 字段数据

        Returns:
            字段标签
        """
        # 从关联标签中提取 - 使用第一个（优先级最高的）标签
        labels = field.get('associated_labels', [])
        if labels:
            # 获取第一个有效标签（已经按优先级排序）
            for label in labels:
                label_text = label.get('text', '').strip()
                if label_text and label_text not in ['unknown', 'input', 'text']:
                    return label_text

        # fallback到其他属性
        fallback_value = (field.get('placeholder', '') or
                         field.get('title', '') or
                         field.get('name', '') or
                         field.get('id', '') or
                         'unknown').strip()

        return fallback_value

    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空结果"""
        return {
            'success': True,
            'phase': 'phase4_structure_recognition',
            'input_fields': 0,
            'logical_groups': [],
            'structure_template': {'groups': [], 'metadata': {}},
            'analysis_summary': {},
            'ready_for_phase5': False,
            'warning': '没有字段数据可分析'
        }
