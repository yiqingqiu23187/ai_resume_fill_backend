"""
视觉分析主服务

Phase 2: 整合截图服务、BBOX提取服务和CV算法，提供完整的视觉分析功能
"""

import logging
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
import asyncio
import cv2
import numpy as np

from .screenshot_service import screenshot_service
from .bbox_service import bbox_service
from ..cv.visual_analyzer import VisualLayoutAnalyzer

logger = logging.getLogger(__name__)


class VisualAnalysisService:
    """视觉分析主服务类"""

    def __init__(self):
        """初始化视觉分析服务"""
        self.screenshot_service = screenshot_service
        self.bbox_service = bbox_service

    async def analyze_html_visual(
        self,
        html_content: str,
        website_url: Optional[str] = None,
        analysis_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的HTML视觉分析流程

        Phase 2: 集成XY-Cut算法和形态学聚类，实现高级视觉布局分析

        Args:
            html_content: HTML页面内容
            website_url: 网站URL（可选，用于日志记录）
            analysis_config: 分析配置参数

        Returns:
            完整的视觉分析结果
        """
        try:
            # 设置默认配置
            if analysis_config is None:
                analysis_config = self._get_default_config()

            logger.info(f"🔍 Phase 2视觉分析流程 - 网站: {website_url}, HTML长度: {len(html_content)}")

            # 阶段1: 生成截图
            logger.info("📸 阶段1: 生成页面截图...")
            screenshot_result = await self.screenshot_service.take_screenshot_from_html(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080),
                full_page=analysis_config.get('full_page', True),
                wait_timeout=analysis_config.get('screenshot_timeout', 5000)
            )

            # 截图服务成功时直接返回结果，失败时抛出异常
            # 所以这里不需要检查success字段

            # 阶段2: 提取BBOX坐标
            logger.info("📊 阶段2: 提取元素坐标信息...")
            bbox_result = await self.bbox_service.extract_element_bboxes(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080)
            )

            if not bbox_result.get('success'):
                raise Exception(f"BBOX提取失败: {bbox_result.get('error')}")

            # 阶段3: Phase 2新增 - 视觉布局分析
            logger.info("🎯 阶段3: 执行视觉布局分析（XY-Cut + 形态学聚类）...")
            layout_result = await self._perform_visual_layout_analysis(
                screenshot_result['screenshot_path'],
                bbox_result,
                analysis_config
            )

            # 阶段4: 分析元素关系
            logger.info("🔗 阶段4: 分析元素空间关系...")
            relationship_result = self.bbox_service.analyze_element_relationships(bbox_result)

            # 整合最终结果
            final_result = {
                'success': True,
                'website_url': website_url,
                'analysis_config': analysis_config,
                'screenshot': {
                    'path': screenshot_result['screenshot_path'],
                    'filename': screenshot_result['filename'],
                    'viewport': screenshot_result['viewport'],
                    'actual_size': screenshot_result['actual_size'],
                    'file_size': screenshot_result['file_size'],
                    'timestamp': screenshot_result['timestamp']
                },
                'elements': {
                    'total_count': bbox_result['total_elements'],
                    'elements_data': bbox_result['bbox_data']['elements'],
                    'viewport_info': bbox_result['viewport_info'],
                    'html_analysis': bbox_result['html_analysis']
                },
                'visual_layout': layout_result,  # Phase 2新增
                'relationships': relationship_result,
                'phase': 'cv_algorithm_integration',  # Phase 2阶段标识
                'next_phases': ['semantic_enhancement', 'structure_detection', 'template_generation']
            }

            # 生成分析摘要（包含视觉布局信息）
            summary = self._generate_analysis_summary(final_result)
            final_result['summary'] = summary

            regions_count = layout_result.get('total_regions', 0) if layout_result.get('success') else 0
            logger.info(f"✅ Phase 2视觉分析完成 - 元素: {bbox_result['total_elements']}个, 区域: {regions_count}个, 关系: {relationship_result.get('total_relationships', 0)}个")

            return final_result

        except Exception as e:
            logger.error(f"❌ Phase 2视觉分析失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Phase 2视觉分析服务错误: {str(e)}",
                'phase': 'cv_algorithm_integration_error'
            }

    async def _perform_visual_layout_analysis(self,
                                          screenshot_path: str,
                                          bbox_result: Dict[str, Any],
                                          analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行视觉布局分析（XY-Cut + 形态学聚类）

        Args:
            screenshot_path: 截图文件路径
            bbox_result: BBOX提取结果
            analysis_config: 分析配置

        Returns:
            视觉布局分析结果
        """
        try:
            # 构建CV算法配置
            cv_config = {
                'use_xy_cut': analysis_config.get('use_xy_cut', True),
                'use_morphology': analysis_config.get('use_morphology', True),
                'fusion_mode': analysis_config.get('fusion_mode', 'hybrid'),

                'xy_cut_config': {
                    'xy_cut_threshold': analysis_config.get('xy_cut_threshold', 10),
                    'min_region_width': analysis_config.get('min_region_width', 50),
                    'min_region_height': analysis_config.get('min_region_height', 30),
                    'max_recursion_depth': analysis_config.get('max_recursion_depth', 5),
                    'merge_close_cuts': analysis_config.get('merge_close_cuts', True),
                    'cut_merge_threshold': analysis_config.get('cut_merge_threshold', 20)
                },

                'morphology_config': {
                    'morphology_kernel_size': analysis_config.get('morphology_kernel_size', 20),
                    'min_cluster_size': analysis_config.get('min_cluster_size', 2),
                    'erosion_iterations': analysis_config.get('erosion_iterations', 1),
                    'dilation_iterations': analysis_config.get('dilation_iterations', 2),
                    'use_dbscan': analysis_config.get('use_dbscan', True),
                    'dbscan_eps': analysis_config.get('dbscan_eps', 80),
                    'dbscan_min_samples': analysis_config.get('dbscan_min_samples', 2),
                    'filter_small_components': analysis_config.get('filter_small_components', True),
                    'min_component_area': analysis_config.get('min_component_area', 500)
                },

                'fusion_config': {
                    'overlap_threshold': analysis_config.get('overlap_threshold', 0.3),
                    'merge_similar_regions': analysis_config.get('merge_similar_regions', True),
                    'similarity_threshold': analysis_config.get('similarity_threshold', 0.7),
                    'min_final_region_area': analysis_config.get('min_final_region_area', 1000),
                }
            }

            # 创建视觉布局分析器
            visual_analyzer = VisualLayoutAnalyzer(
                screenshot_path=screenshot_path,
                bbox_data=bbox_result,
                config=cv_config
            )

            # 执行分析
            layout_result = visual_analyzer.analyze_layout()

            # 添加执行信息
            if layout_result.get('success'):
                layout_result['execution_info'] = {
                    'screenshot_path': screenshot_path,
                    'config_used': cv_config,
                    'phase': 'Phase 2 - CV算法集成'
                }

            return layout_result

        except Exception as e:
            logger.error(f"❌ 视觉布局分析失败: {str(e)}")
            return {
                'success': False,
                'error': f"视觉布局分析错误: {str(e)}",
                'algorithm': 'visual_layout_analyzer'
            }

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认的分析配置（Phase 2增强版）
        """
        return {
            'viewport_width': 1920,
            'viewport_height': 1080,
            'full_page': True,
            'screenshot_timeout': 5000,

            # Phase 2新增: CV算法配置
            'use_xy_cut': True,
            'use_morphology': True,
            'fusion_mode': 'hybrid',

            # XY-Cut配置
            'xy_cut_threshold': 10,
            'min_region_width': 50,
            'min_region_height': 30,
            'max_recursion_depth': 5,
            'merge_close_cuts': True,
            'cut_merge_threshold': 20,

            # 形态学聚类配置
            'morphology_kernel_size': 20,
            'min_cluster_size': 2,
            'erosion_iterations': 1,
            'dilation_iterations': 2,
            'use_dbscan': True,
            'dbscan_eps': 80,
            'dbscan_min_samples': 2,
            'filter_small_components': True,
            'min_component_area': 500,

            # 融合优化配置
            'overlap_threshold': 0.3,
            'merge_similar_regions': True,
            'similarity_threshold': 0.7,
            'min_final_region_area': 1000
        }

    def _generate_analysis_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成分析结果摘要（Phase 2增强版）

        Args:
            analysis_result: 完整的分析结果

        Returns:
            分析摘要
        """
        try:
            elements_data = analysis_result.get('elements', {})
            relationships_data = analysis_result.get('relationships', {})
            visual_layout_data = analysis_result.get('visual_layout', {})  # Phase 2新增

            # 统计元素类型
            elements_list = elements_data.get('elements_data', [])
            element_types = {}
            required_fields = 0
            filled_fields = 0

            for element in elements_list:
                elem_type = element.get('type', 'unknown')
                element_types[elem_type] = element_types.get(elem_type, 0) + 1

                if element.get('required'):
                    required_fields += 1

                if element.get('value') and element['value'].strip():
                    filled_fields += 1

            # 统计标签关联情况
            labeled_fields = 0
            unlabeled_fields = 0

            for element in elements_list:
                labels = element.get('associated_labels', [])
                if labels and any(label.get('text', '').strip() for label in labels):
                    labeled_fields += 1
                else:
                    unlabeled_fields += 1

            # Phase 2新增: 视觉布局分析统计
            visual_analysis = self._analyze_visual_layout_summary(visual_layout_data)

            return {
                'total_elements': len(elements_list),
                'element_types': element_types,
                'field_status': {
                    'required_fields': required_fields,
                    'filled_fields': filled_fields,
                    'empty_fields': len(elements_list) - filled_fields,
                    'labeled_fields': labeled_fields,
                    'unlabeled_fields': unlabeled_fields
                },
                'spatial_analysis': {
                    'total_relationships': relationships_data.get('total_relationships', 0),
                    'nearby_elements': len(relationships_data.get('close_relationships', [])),
                    'aligned_elements': len(relationships_data.get('aligned_elements', [])),
                    'vertical_groups': relationships_data.get('summary', {}).get('vertical_groups', 0)
                },
                'visual_layout': visual_analysis,  # Phase 2新增
                'quality_metrics': {
                    'labeling_rate': round(labeled_fields / len(elements_list) * 100, 1) if elements_list else 0,
                    'fill_rate': round(filled_fields / len(elements_list) * 100, 1) if elements_list else 0,
                    'structure_complexity': self._assess_structure_complexity(elements_list, relationships_data),
                    'layout_quality': visual_analysis.get('layout_quality', 'unknown')  # Phase 2新增
                }
            }

        except Exception as e:
            logger.warning(f"⚠️ 生成分析摘要时出错: {str(e)}")
            return {'error': str(e)}

    def _analyze_visual_layout_summary(self, visual_layout_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析视觉布局数据，生成摘要信息

        Args:
            visual_layout_data: 视觉布局分析结果

        Returns:
            视觉布局摘要
        """
        try:
            if not visual_layout_data.get('success'):
                return {
                    'available': False,
                    'error': visual_layout_data.get('error', '未知错误'),
                    'layout_quality': 'unavailable'
                }

            regions = visual_layout_data.get('regions', [])
            total_regions = visual_layout_data.get('total_regions', 0)

            # 分析算法贡献
            algorithm_stats = {}
            element_coverage = 0
            total_elements_in_regions = 0

            for region in regions:
                algorithm = region.get('algorithm', 'unknown')
                algorithm_stats[algorithm] = algorithm_stats.get(algorithm, 0) + 1

                # 统计区域内元素
                region_elements = len(region.get('elements', []))
                total_elements_in_regions += region_elements

            # 融合统计信息
            fusion_stats = visual_layout_data.get('fusion_statistics', {})

            # 评估布局质量
            layout_quality = 'good'
            if total_regions == 0:
                layout_quality = 'poor'
            elif total_regions > 20:
                layout_quality = 'fragmented'
            elif total_regions < 3:
                layout_quality = 'simple'

            return {
                'available': True,
                'total_regions': total_regions,
                'algorithm_contributions': algorithm_stats,
                'elements_in_regions': total_elements_in_regions,
                'fusion_statistics': fusion_stats,
                'layout_quality': layout_quality,
                'analysis_mode': visual_layout_data.get('algorithm', 'unknown')
            }

        except Exception as e:
            logger.warning(f"⚠️ 分析视觉布局摘要时出错: {str(e)}")
            return {
                'available': False,
                'error': str(e),
                'layout_quality': 'error'
            }

    def _assess_structure_complexity(self, elements: List[Dict], relationships: Dict) -> str:
        """
        评估表单结构复杂度
        """
        try:
            total_elements = len(elements)
            total_relationships = relationships.get('total_relationships', 0)

            if total_elements == 0:
                return 'empty'
            elif total_elements <= 5:
                return 'simple'
            elif total_elements <= 15:
                return 'moderate'
            elif total_elements <= 30:
                return 'complex'
            else:
                return 'very_complex'

        except:
            return 'unknown'

    async def cleanup_resources(self):
        """
        清理服务资源
        """
        try:
            await self.screenshot_service.close()
            await self.bbox_service.close()
            logger.info("🧹 视觉分析服务资源清理完成")
        except Exception as e:
            logger.warning(f"⚠️ 清理资源时出错: {str(e)}")


# 全局视觉分析服务实例
visual_analysis_service = VisualAnalysisService()
