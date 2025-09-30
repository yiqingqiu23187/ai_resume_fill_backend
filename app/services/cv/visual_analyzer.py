"""
视觉布局分析器

整合XY-Cut算法和形态学聚类算法，进行结果融合优化，生成最终的视觉区块
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
from pathlib import Path

from .xy_cut import XYCutAnalyzer
from .morphology_cluster import MorphologyCluster

logger = logging.getLogger(__name__)


class VisualLayoutAnalyzer:
    """视觉布局分析器"""

    def __init__(self, screenshot_path: str, bbox_data: Dict[str, Any], config: Optional[Dict] = None):
        """
        初始化视觉布局分析器

        Args:
            screenshot_path: 截图文件路径
            bbox_data: BBOX数据
            config: 配置参数
        """
        self.screenshot_path = screenshot_path
        self.bbox_data = bbox_data
        self.config = config or self._get_default_config()

        # 获取图像信息
        self.image = cv2.imread(screenshot_path)
        if self.image is None:
            raise ValueError(f"无法加载截图: {screenshot_path}")

        self.image_height, self.image_width = self.image.shape[:2]

        # 初始化子分析器
        self.xy_cut = None
        self.morph_cluster = None

        logger.info(f"🔍 视觉布局分析器初始化完成 - 图像尺寸: {self.image_width}x{self.image_height}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            # 算法选择
            'use_xy_cut': True,
            'use_morphology': True,
            'fusion_mode': 'hybrid',  # 'xy_cut', 'morphology', 'hybrid'

            # XY-Cut配置
            'xy_cut_config': {
                'xy_cut_threshold': 10,
                'min_region_width': 50,
                'min_region_height': 30,
                'max_recursion_depth': 5,
                'merge_close_cuts': True,
                'cut_merge_threshold': 20
            },

            # 形态学配置
            'morphology_config': {
                'morphology_kernel_size': 20,
                'min_cluster_size': 2,
                'max_cluster_distance': 100,
                'erosion_iterations': 1,
                'dilation_iterations': 2,
                'use_dbscan': True,
                'dbscan_eps': 80,
                'dbscan_min_samples': 2,
                'filter_small_components': True,
                'min_component_area': 500
            },

            # 融合优化配置
            'fusion_config': {
                'overlap_threshold': 0.3,      # 重叠阈值
                'merge_similar_regions': True, # 合并相似区域
                'similarity_threshold': 0.7,   # 相似度阈值
                'min_final_region_area': 1000, # 最小最终区域面积
                'region_priority_weights': {   # 区域优先级权重
                    'xy_cut': 0.6,
                    'morphology': 0.4
                }
            }
        }

    def _initialize_analyzers(self):
        """初始化子分析器"""
        try:
            if self.config['use_xy_cut']:
                self.xy_cut = XYCutAnalyzer(
                    self.screenshot_path,
                    self.bbox_data,
                    self.config['xy_cut_config']
                )
                logger.debug("✅ XY-Cut分析器初始化完成")

            if self.config['use_morphology']:
                image_size = (self.image_height, self.image_width)
                self.morph_cluster = MorphologyCluster(
                    self.bbox_data,
                    image_size,
                    self.config['morphology_config']
                )
                logger.debug("✅ 形态学聚类分析器初始化完成")

        except Exception as e:
            logger.error(f"❌ 子分析器初始化失败: {str(e)}")
            raise

    def analyze_layout(self) -> Dict[str, Any]:
        """
        执行完整的视觉布局分析

        Returns:
            分析结果
        """
        try:
            logger.info(f"🚀 开始视觉布局分析 - 模式: {self.config['fusion_mode']}")

            # 初始化子分析器
            self._initialize_analyzers()

            # 执行各算法分析
            xy_cut_result = None
            morphology_result = None

            if self.xy_cut:
                logger.info("📐 执行XY-Cut算法...")
                xy_cut_result = self.xy_cut.analyze_layout()

            if self.morph_cluster:
                logger.info("🔗 执行形态学聚类...")
                clusters = self.morph_cluster.dilate_and_cluster()
                morphology_result = self.morph_cluster.analyze_clusters(clusters)

            # 融合结果
            logger.info("🔀 融合分析结果...")
            fusion_result = self._fuse_results(xy_cut_result, morphology_result)

            # 优化最终结果
            logger.info("✨ 优化最终结果...")
            final_result = self._optimize_results(fusion_result)

            return final_result

        except Exception as e:
            logger.error(f"❌ 视觉布局分析失败: {str(e)}")
            return {
                'success': False,
                'algorithm': 'visual_analyzer',
                'error': str(e)
            }

    def _fuse_results(self, xy_cut_result: Optional[Dict], morphology_result: Optional[Dict]) -> Dict[str, Any]:
        """
        融合XY-Cut和形态学聚类的结果

        Args:
            xy_cut_result: XY-Cut分析结果
            morphology_result: 形态学聚类结果

        Returns:
            融合后的结果
        """
        try:
            fusion_mode = self.config['fusion_mode']

            if fusion_mode == 'xy_cut' and xy_cut_result and xy_cut_result.get('success'):
                return self._adapt_xy_cut_result(xy_cut_result)

            elif fusion_mode == 'morphology' and morphology_result and morphology_result.get('success'):
                return self._adapt_morphology_result(morphology_result)

            elif fusion_mode == 'hybrid':
                return self._hybrid_fusion(xy_cut_result, morphology_result)

            else:
                logger.warning("⚠️ 无有效结果可融合，返回空结果")
                return {
                    'success': False,
                    'algorithm': 'fusion',
                    'error': '无有效分析结果'
                }

        except Exception as e:
            logger.error(f"❌ 结果融合失败: {str(e)}")
            return {
                'success': False,
                'algorithm': 'fusion',
                'error': str(e)
            }

    def _adapt_xy_cut_result(self, xy_cut_result: Dict) -> Dict[str, Any]:
        """
        适配XY-Cut结果格式

        Args:
            xy_cut_result: XY-Cut原始结果

        Returns:
            标准化的区域结果
        """
        try:
            regions = []

            for region in xy_cut_result.get('regions', []):
                adapted_region = {
                    'region_id': f"xy_cut_{len(regions)}",
                    'bbox': region['bbox'],
                    'area': region['area'],
                    'algorithm': 'xy_cut',
                    'confidence': 0.8,  # XY-Cut的基础置信度
                    'depth': region.get('depth', 0),
                    'stop_reason': region.get('stop_reason', 'unknown'),
                    'elements': self._get_elements_in_region(region['bbox']),
                    'visual_features': {
                        'recursion_depth': region.get('depth', 0),
                        'cut_pattern': region.get('stop_reason', 'unknown')
                    }
                }
                regions.append(adapted_region)

            return {
                'success': True,
                'algorithm': 'xy_cut_adapted',
                'total_regions': len(regions),
                'regions': regions,
                'source_statistics': xy_cut_result.get('statistics', {})
            }

        except Exception as e:
            logger.error(f"❌ XY-Cut结果适配失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _adapt_morphology_result(self, morphology_result: Dict) -> Dict[str, Any]:
        """
        适配形态学聚类结果格式

        Args:
            morphology_result: 形态学聚类原始结果

        Returns:
            标准化的区域结果
        """
        try:
            regions = []

            for cluster in morphology_result.get('clusters', []):
                adapted_region = {
                    'region_id': cluster['cluster_id'],
                    'bbox': cluster['bbox'],
                    'area': cluster['area'],
                    'algorithm': 'morphology',
                    'confidence': 0.7,  # 形态学聚类的基础置信度
                    'element_count': cluster['element_count'],
                    'centroid': cluster['centroid'],
                    'elements': cluster['elements'],
                    'visual_features': {
                        'cluster_source': cluster['source'],
                        'element_density': cluster['element_count'] / cluster['area'] if cluster['area'] > 0 else 0
                    }
                }
                regions.append(adapted_region)

            return {
                'success': True,
                'algorithm': 'morphology_adapted',
                'total_regions': len(regions),
                'regions': regions,
                'source_statistics': morphology_result.get('statistics', {})
            }

        except Exception as e:
            logger.error(f"❌ 形态学结果适配失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _hybrid_fusion(self, xy_cut_result: Optional[Dict], morphology_result: Optional[Dict]) -> Dict[str, Any]:
        """
        混合融合算法

        Args:
            xy_cut_result: XY-Cut结果
            morphology_result: 形态学聚类结果

        Returns:
            融合后的结果
        """
        try:
            all_regions = []

            # 收集XY-Cut区域
            xy_cut_regions = []
            if xy_cut_result and xy_cut_result.get('success'):
                adapted_xy = self._adapt_xy_cut_result(xy_cut_result)
                if adapted_xy.get('success'):
                    xy_cut_regions = adapted_xy['regions']
                    all_regions.extend(xy_cut_regions)

            # 收集形态学聚类区域
            morphology_regions = []
            if morphology_result and morphology_result.get('success'):
                adapted_morph = self._adapt_morphology_result(morphology_result)
                if adapted_morph.get('success'):
                    morphology_regions = adapted_morph['regions']
                    all_regions.extend(morphology_regions)

            # 如果没有任何结果
            if not all_regions:
                logger.warning("⚠️ 没有可融合的区域")
                return {'success': False, 'error': '没有有效的分析结果'}

            # 去重和合并重叠区域
            logger.info(f"🔀 开始区域融合 - XY-Cut: {len(xy_cut_regions)}个, 形态学: {len(morphology_regions)}个")
            merged_regions = self._merge_overlapping_regions(all_regions)

            # 计算融合统计信息
            fusion_stats = self._calculate_fusion_statistics(
                xy_cut_regions, morphology_regions, merged_regions
            )

            return {
                'success': True,
                'algorithm': 'hybrid_fusion',
                'total_regions': len(merged_regions),
                'regions': merged_regions,
                'fusion_statistics': fusion_stats
            }

        except Exception as e:
            logger.error(f"❌ 混合融合失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _merge_overlapping_regions(self, regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并重叠的区域

        Args:
            regions: 区域列表

        Returns:
            合并后的区域列表
        """
        try:
            if len(regions) <= 1:
                return regions

            overlap_threshold = self.config['fusion_config']['overlap_threshold']

            # 按置信度和面积排序，优先保留高质量区域
            sorted_regions = sorted(
                regions,
                key=lambda x: (x.get('confidence', 0.5) * x.get('area', 0)),
                reverse=True
            )

            merged_regions = []
            used_indices = set()

            for i, region in enumerate(sorted_regions):
                if i in used_indices:
                    continue

                # 寻找与当前区域重叠的其他区域
                overlapping_regions = [region]
                overlapping_indices = {i}

                for j, other_region in enumerate(sorted_regions[i+1:], i+1):
                    if j in used_indices:
                        continue

                    overlap_ratio = self._calculate_overlap_ratio(region['bbox'], other_region['bbox'])

                    if overlap_ratio > overlap_threshold:
                        overlapping_regions.append(other_region)
                        overlapping_indices.add(j)

                # 如果有重叠区域，进行合并
                if len(overlapping_regions) > 1:
                    merged_region = self._merge_regions(overlapping_regions)
                else:
                    merged_region = region

                merged_regions.append(merged_region)
                used_indices.update(overlapping_indices)

            logger.info(f"🔀 区域合并完成 - 原始: {len(regions)}个 → 合并后: {len(merged_regions)}个")
            return merged_regions

        except Exception as e:
            logger.error(f"❌ 区域合并失败: {str(e)}")
            return regions

    def _calculate_overlap_ratio(self, bbox1: Dict[str, int], bbox2: Dict[str, int]) -> float:
        """
        计算两个边界框的重叠比例

        Args:
            bbox1: 第一个边界框
            bbox2: 第二个边界框

        Returns:
            重叠比例 (0-1)
        """
        try:
            # 计算交集
            x1 = max(bbox1['x'], bbox2['x'])
            y1 = max(bbox1['y'], bbox2['y'])
            x2 = min(bbox1['x'] + bbox1['width'], bbox2['x'] + bbox2['width'])
            y2 = min(bbox1['y'] + bbox1['height'], bbox2['y'] + bbox2['height'])

            if x2 <= x1 or y2 <= y1:
                return 0.0

            intersection_area = (x2 - x1) * (y2 - y1)

            # 计算并集
            area1 = bbox1['width'] * bbox1['height']
            area2 = bbox2['width'] * bbox2['height']
            union_area = area1 + area2 - intersection_area

            if union_area == 0:
                return 0.0

            return intersection_area / union_area

        except Exception as e:
            logger.error(f"❌ 重叠比例计算失败: {str(e)}")
            return 0.0

    def _merge_regions(self, regions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个区域为一个区域

        Args:
            regions: 要合并的区域列表

        Returns:
            合并后的区域
        """
        try:
            # 计算合并后的边界框
            min_x = min(region['bbox']['x'] for region in regions)
            min_y = min(region['bbox']['y'] for region in regions)
            max_x = max(region['bbox']['x'] + region['bbox']['width'] for region in regions)
            max_y = max(region['bbox']['y'] + region['bbox']['height'] for region in regions)

            merged_bbox = {
                'x': min_x,
                'y': min_y,
                'width': max_x - min_x,
                'height': max_y - min_y
            }

            # 选择最高置信度的区域作为主区域
            primary_region = max(regions, key=lambda x: x.get('confidence', 0.5))

            # 收集所有元素
            all_elements = []
            for region in regions:
                if 'elements' in region:
                    all_elements.extend(region['elements'])

            # 去重元素（基于索引）
            unique_elements = []
            seen_indices = set()
            for element in all_elements:
                element_index = element.get('index', id(element))
                if element_index not in seen_indices:
                    unique_elements.append(element)
                    seen_indices.add(element_index)

            # 创建合并后的区域
            merged_region = {
                'region_id': f"merged_{primary_region['region_id']}",
                'bbox': merged_bbox,
                'area': merged_bbox['width'] * merged_bbox['height'],
                'algorithm': 'fusion',
                'confidence': sum(region.get('confidence', 0.5) for region in regions) / len(regions),
                'elements': unique_elements,
                'merged_from': [region['region_id'] for region in regions],
                'merge_count': len(regions),
                'visual_features': {
                    'merged_algorithms': list(set(region['algorithm'] for region in regions)),
                    'element_density': len(unique_elements) / (merged_bbox['width'] * merged_bbox['height']) if merged_bbox['width'] * merged_bbox['height'] > 0 else 0
                }
            }

            return merged_region

        except Exception as e:
            logger.error(f"❌ 区域合并失败: {str(e)}")
            return regions[0] if regions else {}

    def _get_elements_in_region(self, region_bbox: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        获取指定区域内的元素

        Args:
            region_bbox: 区域边界框

        Returns:
            区域内的元素列表
        """
        try:
            elements = []

            if not self.bbox_data.get('success') or not self.bbox_data.get('bbox_data'):
                return elements

            bbox_elements = self.bbox_data['bbox_data']['elements']

            for i, element in enumerate(bbox_elements):
                element_bbox = element['bbox']

                # 检查元素是否在区域内（中心点判断）
                elem_center_x = element_bbox['x'] + element_bbox['width'] // 2
                elem_center_y = element_bbox['y'] + element_bbox['height'] // 2

                if (region_bbox['x'] <= elem_center_x <= region_bbox['x'] + region_bbox['width'] and
                    region_bbox['y'] <= elem_center_y <= region_bbox['y'] + region_bbox['height']):

                    element_info = {
                        'index': i,
                        'bbox': element_bbox,
                        'center': (elem_center_x, elem_center_y),
                        'area': element_bbox['width'] * element_bbox['height'],
                        'element_data': element
                    }
                    elements.append(element_info)

            return elements

        except Exception as e:
            logger.error(f"❌ 获取区域内元素失败: {str(e)}")
            return []

    def _calculate_fusion_statistics(self,
                                   xy_cut_regions: List[Dict],
                                   morphology_regions: List[Dict],
                                   merged_regions: List[Dict]) -> Dict[str, Any]:
        """
        计算融合统计信息

        Args:
            xy_cut_regions: XY-Cut区域
            morphology_regions: 形态学区域
            merged_regions: 合并后区域

        Returns:
            融合统计信息
        """
        try:
            # 计算各算法贡献度
            xy_cut_contribution = 0
            morphology_contribution = 0
            fusion_contribution = 0

            for region in merged_regions:
                if region['algorithm'] == 'xy_cut':
                    xy_cut_contribution += 1
                elif region['algorithm'] == 'morphology':
                    morphology_contribution += 1
                elif region['algorithm'] == 'fusion':
                    fusion_contribution += 1

            return {
                'input_regions': {
                    'xy_cut': len(xy_cut_regions),
                    'morphology': len(morphology_regions),
                    'total': len(xy_cut_regions) + len(morphology_regions)
                },
                'output_regions': len(merged_regions),
                'compression_ratio': round(
                    (len(xy_cut_regions) + len(morphology_regions)) / len(merged_regions)
                    if merged_regions else 1, 2
                ),
                'algorithm_contribution': {
                    'xy_cut': xy_cut_contribution,
                    'morphology': morphology_contribution,
                    'fusion': fusion_contribution
                },
                'fusion_efficiency': {
                    'regions_merged': len(xy_cut_regions) + len(morphology_regions) - len(merged_regions),
                    'merge_rate': round(
                        (len(xy_cut_regions) + len(morphology_regions) - len(merged_regions)) /
                        (len(xy_cut_regions) + len(morphology_regions)) * 100
                        if (len(xy_cut_regions) + len(morphology_regions)) > 0 else 0, 2
                    )
                }
            }

        except Exception as e:
            logger.error(f"❌ 融合统计计算失败: {str(e)}")
            return {}

    def _optimize_results(self, fusion_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化最终结果

        Args:
            fusion_result: 融合结果

        Returns:
            优化后的结果
        """
        try:
            if not fusion_result.get('success'):
                return fusion_result

            regions = fusion_result.get('regions', [])

            # 过滤过小的区域
            min_area = self.config['fusion_config']['min_final_region_area']
            filtered_regions = [
                region for region in regions
                if region.get('area', 0) >= min_area
            ]

            # 按置信度和面积重新排序
            optimized_regions = sorted(
                filtered_regions,
                key=lambda x: (x.get('confidence', 0.5), x.get('area', 0)),
                reverse=True
            )

            # 重新分配ID
            for i, region in enumerate(optimized_regions):
                region['region_id'] = f"visual_region_{i}"
                region['rank'] = i + 1

            # 更新结果
            fusion_result.update({
                'total_regions': len(optimized_regions),
                'regions': optimized_regions,
                'optimization': {
                    'original_count': len(regions),
                    'filtered_count': len(optimized_regions),
                    'filter_rate': round(
                        (len(regions) - len(optimized_regions)) / len(regions) * 100
                        if regions else 0, 2
                    )
                }
            })

            logger.info(f"✨ 结果优化完成 - 最终区域: {len(optimized_regions)}个")

            return fusion_result

        except Exception as e:
            logger.error(f"❌ 结果优化失败: {str(e)}")
            return fusion_result
