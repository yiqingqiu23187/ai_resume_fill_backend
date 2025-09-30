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
        执行HTML视觉分析流程 - 简化版

        专注于字段识别和标签关联，移除复杂的区域分组逻辑

        Args:
            html_content: HTML页面内容
            website_url: 网站URL（可选，用于日志记录）
            analysis_config: 分析配置参数

        Returns:
            视觉分析结果（专注字段识别）
        """
        try:
            # 设置默认配置
            if analysis_config is None:
                analysis_config = self._get_default_config()

            logger.info(f"🔍 Phase 2简化版视觉分析 - 网站: {website_url}, HTML长度: {len(html_content)}")

            # 阶段1: 生成截图
            logger.info("📸 阶段1: 生成页面截图...")
            screenshot_result = await self.screenshot_service.take_screenshot_from_html(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080),
                full_page=analysis_config.get('full_page', True),
                wait_timeout=analysis_config.get('screenshot_timeout', 5000)
            )

            # 阶段2: 提取BBOX坐标和字段信息
            logger.info("📊 阶段2: 提取元素坐标和标签关联...")
            bbox_result = await self.bbox_service.extract_element_bboxes(
                html_content=html_content,
                viewport_width=analysis_config.get('viewport_width', 1920),
                viewport_height=analysis_config.get('viewport_height', 1080)
            )

            if not bbox_result.get('success'):
                raise Exception(f"BBOX提取失败: {bbox_result.get('error')}")

            # 阶段3: 基础空间关系分析
            logger.info("🔗 阶段3: 分析基础空间关系...")
            relationship_result = self.bbox_service.analyze_element_relationships(bbox_result)

            # 整合最终结果 - 简化版
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
                'phase': 'field_identification_complete',  # 简化阶段标识
                'ready_for_phase4': True,  # 准备好进行Phase 4结构识别
                'next_phases': ['structure_recognition', 'template_generation']
            }

            # 生成分析摘要
            summary = self._generate_analysis_summary(final_result)
            final_result['summary'] = summary

            logger.info(f"✅ Phase 2简化版完成 - 元素: {bbox_result['total_elements']}个, 关系: {relationship_result.get('total_relationships', 0)}个")
            logger.info(f"🎯 标签覆盖率: {summary.get('quality_metrics', {}).get('labeling_rate', 0)}% - 准备进入Phase 4")

            return final_result

        except Exception as e:
            logger.error(f"❌ Phase 2简化版分析失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Phase 2简化版错误: {str(e)}",
                'phase': 'field_identification_error'
            }


    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认的分析配置（简化版）
        专注于基础视觉分析配置
        """
        return {
            # 基础截图配置
            'viewport_width': 1920,
            'viewport_height': 1080,
            'full_page': True,
            'screenshot_timeout': 5000
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
