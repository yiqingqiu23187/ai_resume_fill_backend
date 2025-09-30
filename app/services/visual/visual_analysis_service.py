"""
视觉分析主服务

整合截图服务和BBOX提取服务，提供完整的视觉分析功能
"""

import logging
from typing import Dict, List, Any, Optional
import json
from pathlib import Path

from .screenshot_service import screenshot_service
from .bbox_service import bbox_service

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

            logger.info(f"🔍 开始视觉分析流程 - 网站: {website_url}, HTML长度: {len(html_content)}")

            # 阶段1: 生成截图
            logger.info("📸 阶段1: 生成页面截图...")
            screenshot_result = await self.screenshot_service.take_screenshot_from_html(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080),
                full_page=analysis_config.get('full_page', True),
                wait_timeout=analysis_config.get('screenshot_timeout', 5000)
            )

            # 阶段2: 提取BBOX坐标
            logger.info("📊 阶段2: 提取元素坐标信息...")
            bbox_result = await self.bbox_service.extract_element_bboxes(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080)
            )

            if not bbox_result.get('success'):
                logger.error(f"❌ BBOX提取失败: {bbox_result.get('error')}")
                return {
                    'success': False,
                    'error': f"BBOX提取失败: {bbox_result.get('error')}",
                    'screenshot_result': screenshot_result
                }

            # 阶段3: 分析元素关系
            logger.info("🔗 阶段3: 分析元素空间关系...")
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
                'relationships': relationship_result,
                'phase': 'bbox_analysis',  # 当前实现阶段标识
                'next_phases': ['xy_cut_algorithm', 'morphology_clustering', 'semantic_enhancement']
            }

            # 生成分析摘要
            summary = self._generate_analysis_summary(final_result)
            final_result['summary'] = summary

            logger.info(f"✅ 视觉分析完成 - 识别元素: {bbox_result['total_elements']}个, 关系对: {relationship_result.get('total_relationships', 0)}个")

            return final_result

        except Exception as e:
            logger.error(f"❌ 视觉分析失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"视觉分析服务错误: {str(e)}",
                'phase': 'error'
            }

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认的分析配置
        """
        return {
            'viewport_width': 1920,
            'viewport_height': 1080,
            'full_page': True,
            'screenshot_timeout': 5000,
            'xy_cut_threshold': 10,
            'morphology_kernel_size': 20,
            'min_region_size': 50,
            'similarity_threshold': 0.8
        }

    def _generate_analysis_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成分析结果摘要

        Args:
            analysis_result: 完整的分析结果

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
                'quality_metrics': {
                    'labeling_rate': round(labeled_fields / len(elements_list) * 100, 1) if elements_list else 0,
                    'fill_rate': round(filled_fields / len(elements_list) * 100, 1) if elements_list else 0,
                    'structure_complexity': self._assess_structure_complexity(elements_list, relationships_data)
                }
            }

        except Exception as e:
            logger.warning(f"⚠️ 生成分析摘要时出错: {str(e)}")
            return {'error': str(e)}

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
