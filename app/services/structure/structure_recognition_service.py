"""
Phase 4: 结构识别服务

集成语义分组分析器，提供结构识别的统一服务接口
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .html_structure_analyzer import HtmlStructureAnalyzer

logger = logging.getLogger(__name__)


class StructureRecognitionService:
    """结构识别服务 - Phase 4主服务"""

    def __init__(self):
        """初始化结构识别服务"""
        # 加载HTML结构分析器
        self.html_analyzer = HtmlStructureAnalyzer()
        logger.info("🚀 Phase 4结构识别服务初始化完成")

    async def recognize_structure(self, phase2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行结构识别 - Phase 4主入口

        Args:
            phase2_result: Phase 2的分析结果

        Returns:
            结构识别结果
        """
        try:
            logger.info("🔍 Phase 4结构识别开始...")

            # 验证Phase 2输入
            if not self._validate_phase2_input(phase2_result):
                return {
                    'success': False,
                    'error': 'Phase 2输入数据无效',
                    'phase': 'phase4_input_validation_error'
                }

            # 执行HTML结构分析
            structure_result = self.html_analyzer.analyze_structure(phase2_result)

            if structure_result.get('success'):
                # 增强结果信息
                enhanced_result = self._enhance_structure_result(structure_result, phase2_result)
                logger.info("✅ Phase 4结构识别成功完成")
                return enhanced_result
            else:
                logger.error(f"❌ 结构识别失败: {structure_result.get('error')}")
                return structure_result

        except Exception as e:
            logger.error(f"❌ Phase 4结构识别服务错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Phase 4服务错误: {str(e)}",
                'phase': 'phase4_service_error'
            }

    def _validate_phase2_input(self, phase2_result: Dict[str, Any]) -> bool:
        """
        验证Phase 2输入数据

        Args:
            phase2_result: Phase 2结果

        Returns:
            是否有效
        """
        if not phase2_result:
            return False

        # 检查基本结构
        if not phase2_result.get('success'):
            logger.warning("⚠️ Phase 2结果显示失败状态")
            return False

        # 检查字段数据
        elements = phase2_result.get('elements', {})
        fields = elements.get('elements_data', [])

        if not fields:
            logger.warning("⚠️ 没有找到字段数据")
            return False

        logger.info(f"✅ Phase 2输入验证通过: {len(fields)}个字段")
        return True

    def _enhance_structure_result(self, structure_result: Dict[str, Any], phase2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强结构识别结果

        Args:
            structure_result: 结构识别结果
            phase2_result: Phase 2原始结果

        Returns:
            增强后的结果
        """
        enhanced = structure_result.copy()

        # 添加Phase 2的源信息
        enhanced['source_phase2'] = {
            'total_elements': phase2_result.get('elements', {}).get('total_count', 0),
            'screenshot_path': phase2_result.get('screenshot', {}).get('path', ''),
            'relationships_count': phase2_result.get('relationships', {}).get('total_relationships', 0)
        }

        # 添加转换统计
        logical_groups = structure_result.get('logical_groups', [])
        enhanced['conversion_stats'] = {
            'input_flat_fields': phase2_result.get('elements', {}).get('total_count', 0),
            'output_logical_groups': len(logical_groups),
            'structure_reduction_ratio': self._calculate_reduction_ratio(
                phase2_result.get('elements', {}).get('total_count', 0),
                len(logical_groups)
            ),
            'semantic_coverage': self._calculate_semantic_coverage(logical_groups)
        }

        # 添加Phase 4特定的成功指标
        enhanced['phase4_quality'] = self._assess_phase4_quality(logical_groups)

        return enhanced

    def _calculate_reduction_ratio(self, input_fields: int, output_groups: int) -> float:
        """
        计算结构简化比例

        Args:
            input_fields: 输入字段数
            output_groups: 输出分组数

        Returns:
            简化比例
        """
        if input_fields == 0:
            return 0
        return 1 - (output_groups / input_fields)

    def _calculate_semantic_coverage(self, logical_groups: List[Dict[str, Any]]) -> float:
        """
        计算语义覆盖率

        Args:
            logical_groups: 逻辑分组列表

        Returns:
            语义覆盖率
        """
        if not logical_groups:
            return 0

        total_fields = 0
        matched_fields = 0

        for group in logical_groups:
            for field in group.get('fields', []):
                total_fields += 1
                if field.get('semantic_type'):
                    matched_fields += 1

        return matched_fields / total_fields if total_fields > 0 else 0

    def _assess_phase4_quality(self, logical_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估Phase 4质量

        Args:
            logical_groups: 逻辑分组列表

        Returns:
            质量评估
        """
        if not logical_groups:
            return {'overall_score': 0, 'level': 'poor'}

        # 计算多个质量指标
        semantic_coverage = self._calculate_semantic_coverage(logical_groups)
        group_balance = self._assess_group_balance(logical_groups)
        structure_complexity = self._assess_structure_complexity(logical_groups)

        # 综合评分
        overall_score = (semantic_coverage * 0.4 +
                        group_balance * 0.3 +
                        structure_complexity * 0.3)

        # 评级
        if overall_score >= 0.85:
            level = 'excellent'
        elif overall_score >= 0.70:
            level = 'good'
        elif overall_score >= 0.55:
            level = 'fair'
        else:
            level = 'poor'

        return {
            'overall_score': overall_score,
            'level': level,
            'semantic_coverage': semantic_coverage,
            'group_balance': group_balance,
            'structure_complexity': structure_complexity
        }

    def _assess_group_balance(self, logical_groups: List[Dict[str, Any]]) -> float:
        """
        评估分组平衡性

        Args:
            logical_groups: 逻辑分组列表

        Returns:
            平衡性评分 (0-1)
        """
        if not logical_groups:
            return 0

        group_sizes = [len(group.get('fields', [])) for group in logical_groups]

        if not group_sizes:
            return 0

        # 计算分组大小的标准差
        avg_size = sum(group_sizes) / len(group_sizes)
        variance = sum((size - avg_size) ** 2 for size in group_sizes) / len(group_sizes)
        std_dev = variance ** 0.5

        # 标准差越小，平衡性越好
        max_std = avg_size  # 最大可能的标准差
        if max_std == 0:
            return 1.0

        balance_score = 1 - min(std_dev / max_std, 1.0)
        return balance_score

    def _assess_structure_complexity(self, logical_groups: List[Dict[str, Any]]) -> float:
        """
        评估结构复杂度适中性

        Args:
            logical_groups: 逻辑分组列表

        Returns:
            复杂度评分 (0-1)
        """
        group_count = len(logical_groups)

        # 理想的分组数量在3-6个之间
        if 3 <= group_count <= 6:
            return 1.0
        elif 2 <= group_count <= 8:
            return 0.8
        elif 1 <= group_count <= 10:
            return 0.6
        else:
            return 0.3


# 全局结构识别服务实例
structure_recognition_service = StructureRecognitionService()
