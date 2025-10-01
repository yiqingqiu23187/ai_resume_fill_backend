"""
视觉分析主服务

Phase 2 简化版: 专注于字段识别和标签关联，为Phase 4结构识别做准备
移除了复杂的CV算法融合，保留高质量的基础功能
"""

import logging
from typing import Dict, List, Any, Optional
import json
from pathlib import Path

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
        执行HTML视觉分析流程 - 完整版

        集成XY-Cut算法、形态学聚类、算法融合的完整CV分析流程
        包含增强的标签关联逻辑，提供高质量的视觉分析结果

        Args:
            html_content: HTML页面内容
            website_url: 网站URL（可选，用于日志记录）
            analysis_config: 分析配置参数

        Returns:
            完整的视觉分析结果，包含CV算法分析的区域信息
        """
        try:
            # 设置默认配置
            if analysis_config is None:
                analysis_config = self._get_default_config()

            logger.info(f"🔍 Phase 2完整版视觉分析 - 网站: {website_url}, HTML长度: {len(html_content)}")

            # 阶段1: 生成截图
            logger.info("📸 阶段1: 生成页面截图...")
            screenshot_result = await self.screenshot_service.take_screenshot_from_html(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080),
                full_page=analysis_config.get('full_page', True),
                wait_timeout=analysis_config.get('screenshot_timeout', 5000)
            )

            if not screenshot_result.get('success'):
                raise Exception(f"截图生成失败: {screenshot_result.get('error')}")

            # 阶段2: 提取BBOX坐标和增强标签关联
            logger.info("📊 阶段2: 提取元素坐标和增强标签关联...")
            bbox_result = await self.bbox_service.extract_element_bboxes(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080)
            )

            if not bbox_result.get('success'):
                raise Exception(f"BBOX提取失败: {bbox_result.get('error')}")

            # 详细打印阶段2结果
            logger.info("📊 阶段2详细结果分析:")
            logger.info("=" * 80)
            elements_data = bbox_result.get('bbox_data', {}).get('elements', [])
            logger.info(f"总共提取到 {len(elements_data)} 个元素")

            # 统计标签关联情况
            labeled_count = 0
            unlabeled_count = 0
            label_types = {}

            for i, element in enumerate(elements_data):
                selector = element.get('selector', 'unknown')
                element_type = element.get('type', 'unknown')
                associated_labels = element.get('associated_labels', [])

                if associated_labels:
                    labeled_count += 1
                    # 统计标签类型
                    for label in associated_labels:
                        label_type = label.get('association_type', 'unknown')
                        label_types[label_type] = label_types.get(label_type, 0) + 1
                else:
                    unlabeled_count += 1

                # 打印前20个元素的详细信息
                if i < 20:
                    logger.info(f"元素 {i+1}: {selector} ({element_type})")
                    if associated_labels:
                        for j, label in enumerate(associated_labels):
                            label_text = label.get('text', '')
                            label_type = label.get('association_type', 'unknown')
                            logger.info(f"  标签{j+1}: '{label_text}' (类型: {label_type})")
                    else:
                        logger.info("  ❌ 无关联标签")

                    # 新增：打印容器信息
                    container_info = element.get('container_info', {})
                    if container_info.get('groupTitle'):
                        logger.info(f"  📦 容器分组: '{container_info['groupTitle']}' ({container_info.get('groupType', 'unknown')})")
                    else:
                        logger.info(f"  📦 容器分组: ❌ 无分组信息")
                    logger.info("")

            if len(elements_data) > 20:
                logger.info(f"... 还有 {len(elements_data) - 20} 个元素未显示")

            logger.info(f"📈 标签关联统计:")
            logger.info(f"  ✅ 有标签的元素: {labeled_count} 个")
            logger.info(f"  ❌ 无标签的元素: {unlabeled_count} 个")
            logger.info(f"  📊 覆盖率: {labeled_count/len(elements_data)*100:.1f}%")
            logger.info(f"  🏷️ 标签类型分布: {label_types}")
            logger.info("=" * 80)

            # 阶段3: 计算机视觉布局分析 (XY-Cut + 形态学聚类)
            logger.info("🤖 阶段3: 执行CV算法布局分析...")
            visual_layout_result = self._analyze_visual_layout(
                screenshot_result, bbox_result, analysis_config
            )

            # 阶段4: 空间关系分析
            logger.info("🔗 阶段4: 分析元素空间关系...")
            relationship_result = self.bbox_service.analyze_element_relationships(bbox_result)

            # 整合最终结果 - 完整版
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
                'visual_layout': visual_layout_result,  # 新增：完整的视觉布局分析
                'relationships': relationship_result,
                'phase': 'complete_visual_analysis',  # 完整版阶段标识
                'ready_for_phase4': True,  # 准备好进行Phase 4结构识别
                'next_phases': ['structure_recognition', 'template_generation']
            }

            # 生成增强分析摘要
            summary = self._generate_analysis_summary(final_result)
            final_result['summary'] = summary

            logger.info(f"✅ Phase 2完整版完成 - 元素: {bbox_result['total_elements']}个, 关系: {relationship_result.get('total_relationships', 0)}个")
            if visual_layout_result.get('success'):
                logger.info(f"🎯 视觉区域: {visual_layout_result.get('total_regions', 0)}个, 算法: {visual_layout_result.get('algorithm', 'unknown')}")
            logger.info(f"🏷️ 标签覆盖率: {summary.get('quality_metrics', {}).get('labeling_rate', 0)}% - 准备进入Phase 4")

            return final_result

        except Exception as e:
            logger.error(f"❌ Phase 2完整版分析失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Phase 2完整版错误: {str(e)}",
                'phase': 'complete_visual_analysis_error'
            }


    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认的分析配置（完整版）
        包含CV算法的完整配置参数
        """
        return {
            # 基础截图配置
            'viewport_width': 1920,
            'viewport_height': 1080,
            'full_page': True,
            'screenshot_timeout': 5000,

            # CV算法配置
            'use_xy_cut': True,
            'use_morphology': True,
            'fusion_mode': 'hybrid',  # 'xy_cut', 'morphology', 'hybrid'

            # XY-Cut算法配置
            'xy_cut_config': {
                'xy_cut_threshold': 12,
                'min_region_width': 80,
                'min_region_height': 40,
                'max_recursion_depth': 4,
                'merge_close_cuts': True,
                'cut_merge_threshold': 20
            },

            # 形态学聚类配置
            'morphology_config': {
                'morphology_kernel_size': 25,
                'min_cluster_size': 2,
                'max_cluster_distance': 100,
                'erosion_iterations': 1,
                'dilation_iterations': 2,
                'use_dbscan': True,
                'dbscan_eps': 90,
                'dbscan_min_samples': 2,
                'filter_small_components': True,
                'min_component_area': 1000
            },

            # 算法融合配置
            'fusion_config': {
                'overlap_threshold': 0.3,
                'merge_similar_regions': True,
                'similarity_threshold': 0.7,
                'min_final_region_area': 1200,
                'region_priority_weights': {
                    'xy_cut': 0.6,
                    'morphology': 0.4
                }
            }
        }

    def _generate_analysis_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成分析结果摘要（简化版）

        专注于字段识别和标签关联的质量评估

        Args:
            analysis_result: 分析结果

        Returns:
            分析摘要
        """
        try:
            elements_data = analysis_result.get('elements', {})
            relationships_data = analysis_result.get('relationships', {})

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

            # 处理视觉布局分析数据
            visual_layout_data = analysis_result.get('visual_layout', {})
            visual_layout_summary = {
                'available': visual_layout_data.get('success', False),
                'algorithm': visual_layout_data.get('algorithm', 'none'),
                'total_regions': visual_layout_data.get('total_regions', 0)
            }

            if visual_layout_data.get('success'):
                # 添加CV算法的详细信息
                if 'fusion_statistics' in visual_layout_data:
                    fusion_stats = visual_layout_data['fusion_statistics']
                    visual_layout_summary.update({
                        'layout_quality': 'excellent' if visual_layout_data.get('total_regions', 0) > 0 else 'poor',
                        'algorithm_contributions': {
                            'xy_cut_regions': fusion_stats.get('input_regions', {}).get('xy_cut', 0),
                            'morphology_regions': fusion_stats.get('input_regions', {}).get('morphology', 0),
                            'final_regions': fusion_stats.get('output_regions', 0),
                            'fusion_efficiency': fusion_stats.get('fusion_efficiency', {})
                        }
                    })

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
                'visual_layout': visual_layout_summary,  # 新增：视觉布局摘要
                'quality_metrics': {
                    'labeling_rate': round(labeled_fields / len(elements_list) * 100, 1) if elements_list else 0,
                    'fill_rate': round(filled_fields / len(elements_list) * 100, 1) if elements_list else 0,
                    'structure_complexity': self._assess_structure_complexity(elements_list, relationships_data),
                    'cv_analysis_quality': 'excellent' if visual_layout_summary['available'] and visual_layout_summary['total_regions'] > 0 else 'basic'
                }
            }

        except Exception as e:
            logger.warning(f"⚠️ 生成分析摘要时出错: {str(e)}")
            return {'error': str(e)}

    def _analyze_visual_layout(
        self,
        screenshot_result: Dict[str, Any],
        bbox_result: Dict[str, Any],
        analysis_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行CV算法的视觉布局分析

        Args:
            screenshot_result: 截图结果
            bbox_result: BBOX提取结果
            analysis_config: 分析配置

        Returns:
            视觉布局分析结果
        """
        try:
            # 创建视觉布局分析器
            visual_analyzer = VisualLayoutAnalyzer(
                screenshot_path=screenshot_result['screenshot_path'],
                bbox_data=bbox_result,
                config=analysis_config
            )

            # 执行布局分析
            layout_result = visual_analyzer.analyze_layout()

            if layout_result.get('success'):
                logger.info(f"✅ CV算法分析成功 - 模式: {layout_result.get('algorithm', 'unknown')}")
                if layout_result.get('total_regions'):
                    logger.info(f"📊 识别区域: {layout_result['total_regions']}个")
            else:
                logger.warning(f"⚠️ CV算法分析失败: {layout_result.get('error')}")

            return layout_result

        except Exception as e:
            logger.error(f"❌ 视觉布局分析异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"视觉布局分析错误: {str(e)}",
                'algorithm': 'error'
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
