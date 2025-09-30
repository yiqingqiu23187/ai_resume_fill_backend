"""
形态学聚类算法实现模块

基于元素空间邻近性的聚类算法，通过膨胀操作和连通域检测识别自然的元素分组
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
from scipy import ndimage
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)


class MorphologyCluster:
    """形态学聚类分析器"""

    def __init__(self, bbox_data: Dict[str, Any], image_size: Tuple[int, int], config: Optional[Dict] = None):
        """
        初始化形态学聚类分析器

        Args:
            bbox_data: BBOX数据
            image_size: 图像尺寸 (height, width)
            config: 配置参数
        """
        self.bbox_data = bbox_data
        self.image_height, self.image_width = image_size
        self.config = config or self._get_default_config()

        # 创建空白画布
        self.canvas = np.zeros((self.image_height, self.image_width), dtype=np.uint8)

        # 元素中心点列表（用于DBSCAN聚类）
        self.element_centers = []
        self.element_info = []

        logger.info(f"🔍 形态学聚类分析器初始化完成 - 画布尺寸: {self.image_width}x{self.image_height}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'morphology_kernel_size': 20,  # 膨胀核大小
            'min_cluster_size': 2,         # 最小聚类大小
            'max_cluster_distance': 100,   # 最大聚类距离
            'erosion_iterations': 1,       # 腐蚀迭代次数
            'dilation_iterations': 2,      # 膨胀迭代次数
            'use_dbscan': True,           # 是否使用DBSCAN辅助聚类
            'dbscan_eps': 80,             # DBSCAN的邻域半径
            'dbscan_min_samples': 2,      # DBSCAN的最小样本数
            'filter_small_components': True, # 是否过滤小连通域
            'min_component_area': 500     # 最小连通域面积
        }

    def create_element_mask(self) -> np.ndarray:
        """
        根据BBOX创建元素掩码

        Returns:
            二值掩码图像
        """
        try:
            mask = np.zeros((self.image_height, self.image_width), dtype=np.uint8)

            if not self.bbox_data.get('success') or not self.bbox_data.get('bbox_data'):
                logger.warning("⚠️ BBOX数据无效，返回空掩码")
                return mask

            elements = self.bbox_data['bbox_data']['elements']

            for i, element in enumerate(elements):
                bbox = element['bbox']
                x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']

                # 确保坐标在图像范围内
                x = max(0, min(x, self.image_width - 1))
                y = max(0, min(y, self.image_height - 1))
                w = max(1, min(w, self.image_width - x))
                h = max(1, min(h, self.image_height - y))

                # 在掩码中标记元素区域
                mask[y:y+h, x:x+w] = 255  # 使用255便于可视化

                # 记录元素中心点和信息
                center_x = x + w // 2
                center_y = y + h // 2
                self.element_centers.append([center_x, center_y])
                self.element_info.append({
                    'index': i,
                    'bbox': bbox,
                    'center': (center_x, center_y),
                    'area': w * h,
                    'element_data': element
                })

            logger.info(f"📊 元素掩码创建完成 - 元素数: {len(elements)}, 覆盖像素: {np.sum(mask > 0)}")
            return mask

        except Exception as e:
            logger.error(f"❌ 创建元素掩码失败: {str(e)}")
            return np.zeros((self.image_height, self.image_width), dtype=np.uint8)

    def apply_morphological_operations(self, mask: np.ndarray) -> np.ndarray:
        """
        应用形态学操作（腐蚀+膨胀）

        Args:
            mask: 输入掩码

        Returns:
            处理后的掩码
        """
        try:
            kernel_size = self.config['morphology_kernel_size']
            erosion_iter = self.config['erosion_iterations']
            dilation_iter = self.config['dilation_iterations']

            # 创建椭圆形核（更自然的形状）
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (kernel_size, kernel_size)
            )

            processed_mask = mask.copy()

            # 先腐蚀（减少噪点）
            if erosion_iter > 0:
                processed_mask = cv2.erode(processed_mask, kernel, iterations=erosion_iter)
                logger.debug(f"🔹 腐蚀操作完成 - 迭代次数: {erosion_iter}")

            # 再膨胀（连接相近元素）
            if dilation_iter > 0:
                processed_mask = cv2.dilate(processed_mask, kernel, iterations=dilation_iter)
                logger.debug(f"🔹 膨胀操作完成 - 迭代次数: {dilation_iter}")

            return processed_mask

        except Exception as e:
            logger.error(f"❌ 形态学操作失败: {str(e)}")
            return mask

    def find_connected_components(self, mask: np.ndarray) -> List[Dict[str, Any]]:
        """
        寻找连通区域

        Args:
            mask: 二值掩码图像

        Returns:
            连通域信息列表
        """
        try:
            # 使用OpenCV寻找连通域
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                mask, connectivity=8
            )

            components = []
            min_area = self.config['min_component_area']

            # 跳过背景（标签0）
            for label in range(1, num_labels):
                # 获取连通域统计信息
                x, y, w, h, area = stats[label]
                centroid_x, centroid_y = centroids[label]

                # 过滤小区域
                if self.config['filter_small_components'] and area < min_area:
                    continue

                # 创建连通域掩码
                component_mask = (labels == label).astype(np.uint8)

                # 计算更精确的边界框
                contours, _ = cv2.findContours(
                    component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                if contours:
                    # 使用最大轮廓
                    largest_contour = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)

                component_info = {
                    'label': label,
                    'bbox': {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)},
                    'area': int(area),
                    'centroid': (float(centroid_x), float(centroid_y)),
                    'mask': component_mask,
                    'algorithm': 'morphology'
                }

                components.append(component_info)

            logger.info(f"🔗 连通域检测完成 - 发现: {len(components)}个连通域")
            return components

        except Exception as e:
            logger.error(f"❌ 连通域检测失败: {str(e)}")
            return []

    def dbscan_clustering(self) -> List[List[int]]:
        """
        使用DBSCAN对元素中心点进行聚类

        Returns:
            聚类结果，每个聚类包含元素索引列表
        """
        try:
            if not self.element_centers or not self.config['use_dbscan']:
                return []

            centers_array = np.array(self.element_centers)

            # DBSCAN聚类
            dbscan = DBSCAN(
                eps=self.config['dbscan_eps'],
                min_samples=self.config['dbscan_min_samples']
            )

            cluster_labels = dbscan.fit_predict(centers_array)

            # 组织聚类结果
            clusters = {}
            for i, label in enumerate(cluster_labels):
                if label != -1:  # 忽略噪点（标签-1）
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(i)

            # 过滤小聚类
            min_cluster_size = self.config['min_cluster_size']
            filtered_clusters = [
                cluster for cluster in clusters.values()
                if len(cluster) >= min_cluster_size
            ]

            logger.info(f"🎯 DBSCAN聚类完成 - 发现: {len(filtered_clusters)}个聚类")
            return filtered_clusters

        except Exception as e:
            logger.error(f"❌ DBSCAN聚类失败: {str(e)}")
            return []

    def merge_clustering_results(self,
                               morphology_components: List[Dict[str, Any]],
                               dbscan_clusters: List[List[int]]) -> List[Dict[str, Any]]:
        """
        合并形态学聚类和DBSCAN聚类的结果

        Args:
            morphology_components: 形态学连通域结果
            dbscan_clusters: DBSCAN聚类结果

        Returns:
            合并后的聚类结果
        """
        try:
            final_clusters = []

            # 首先处理形态学连通域
            for comp in morphology_components:
                # 找到该连通域包含的元素
                contained_elements = []
                comp_bbox = comp['bbox']

                for elem_info in self.element_info:
                    elem_center = elem_info['center']
                    # 检查元素中心是否在连通域内
                    if (comp_bbox['x'] <= elem_center[0] <= comp_bbox['x'] + comp_bbox['width'] and
                        comp_bbox['y'] <= elem_center[1] <= comp_bbox['y'] + comp_bbox['height']):
                        contained_elements.append(elem_info)

                if contained_elements:
                    cluster_info = {
                        'cluster_id': f"morph_{comp['label']}",
                        'bbox': comp_bbox,
                        'area': comp['area'],
                        'centroid': comp['centroid'],
                        'elements': contained_elements,
                        'element_count': len(contained_elements),
                        'algorithm': 'morphology',
                        'source': 'connected_components'
                    }
                    final_clusters.append(cluster_info)

            # 然后处理DBSCAN聚类（作为补充）
            for i, cluster in enumerate(dbscan_clusters):
                cluster_elements = [self.element_info[idx] for idx in cluster]

                # 计算聚类边界框
                min_x = min(elem['bbox']['x'] for elem in cluster_elements)
                min_y = min(elem['bbox']['y'] for elem in cluster_elements)
                max_x = max(elem['bbox']['x'] + elem['bbox']['width'] for elem in cluster_elements)
                max_y = max(elem['bbox']['y'] + elem['bbox']['height'] for elem in cluster_elements)

                cluster_bbox = {
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y
                }

                # 计算聚类中心
                center_x = sum(elem['center'][0] for elem in cluster_elements) / len(cluster_elements)
                center_y = sum(elem['center'][1] for elem in cluster_elements) / len(cluster_elements)

                cluster_info = {
                    'cluster_id': f"dbscan_{i}",
                    'bbox': cluster_bbox,
                    'area': cluster_bbox['width'] * cluster_bbox['height'],
                    'centroid': (center_x, center_y),
                    'elements': cluster_elements,
                    'element_count': len(cluster_elements),
                    'algorithm': 'dbscan',
                    'source': 'distance_clustering'
                }
                final_clusters.append(cluster_info)

            # 去重和合并重叠的聚类
            final_clusters = self._remove_overlapping_clusters(final_clusters)

            logger.info(f"🔀 聚类结果合并完成 - 最终聚类: {len(final_clusters)}个")
            return final_clusters

        except Exception as e:
            logger.error(f"❌ 聚类结果合并失败: {str(e)}")
            return []

    def _remove_overlapping_clusters(self, clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        移除重叠的聚类，保留更好的那个

        Args:
            clusters: 聚类列表

        Returns:
            去重后的聚类列表
        """
        try:
            if len(clusters) <= 1:
                return clusters

            # 按元素数量排序，优先保留元素更多的聚类
            sorted_clusters = sorted(clusters, key=lambda x: x['element_count'], reverse=True)

            final_clusters = []
            used_elements = set()

            for cluster in sorted_clusters:
                cluster_elements = {elem['index'] for elem in cluster['elements']}

                # 检查是否与已有聚类重叠（重叠度超过50%）
                overlap_ratio = len(cluster_elements & used_elements) / len(cluster_elements)

                if overlap_ratio < 0.5:  # 重叠度小于50%才保留
                    final_clusters.append(cluster)
                    used_elements.update(cluster_elements)

            return final_clusters

        except Exception as e:
            logger.error(f"❌ 去重聚类失败: {str(e)}")
            return clusters

    def dilate_and_cluster(self) -> List[Dict[str, Any]]:
        """
        执行完整的膨胀+聚类流程

        Returns:
            聚类结果列表
        """
        try:
            logger.info(f"🚀 开始形态学聚类分析...")

            # 1. 创建元素掩码
            element_mask = self.create_element_mask()

            if np.sum(element_mask) == 0:
                logger.warning("⚠️ 没有元素，返回空聚类结果")
                return []

            # 2. 应用形态学操作
            processed_mask = self.apply_morphological_operations(element_mask)

            # 3. 寻找连通域
            morphology_components = self.find_connected_components(processed_mask)

            # 4. DBSCAN辅助聚类
            dbscan_clusters = self.dbscan_clustering()

            # 5. 合并聚类结果
            final_clusters = self.merge_clustering_results(morphology_components, dbscan_clusters)

            return final_clusters

        except Exception as e:
            logger.error(f"❌ 形态学聚类失败: {str(e)}")
            return []

    def analyze_clusters(self, clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析聚类结果，生成统计信息

        Args:
            clusters: 聚类结果

        Returns:
            分析结果
        """
        try:
            if not clusters:
                return {
                    'success': True,
                    'algorithm': 'morphology',
                    'total_clusters': 0,
                    'clusters': [],
                    'statistics': {
                        'total_elements': len(self.element_info),
                        'clustered_elements': 0,
                        'cluster_coverage': 0.0,
                        'avg_cluster_size': 0.0,
                        'max_cluster_size': 0,
                        'min_cluster_size': 0
                    }
                }

            # 统计信息
            total_clustered = sum(cluster['element_count'] for cluster in clusters)
            cluster_sizes = [cluster['element_count'] for cluster in clusters]

            statistics = {
                'total_elements': len(self.element_info),
                'clustered_elements': total_clustered,
                'cluster_coverage': round(total_clustered / len(self.element_info) * 100, 2) if self.element_info else 0,
                'avg_cluster_size': round(sum(cluster_sizes) / len(cluster_sizes), 2),
                'max_cluster_size': max(cluster_sizes),
                'min_cluster_size': min(cluster_sizes),
                'morphology_clusters': len([c for c in clusters if c['algorithm'] == 'morphology']),
                'dbscan_clusters': len([c for c in clusters if c['algorithm'] == 'dbscan'])
            }

            result = {
                'success': True,
                'algorithm': 'morphology',
                'total_clusters': len(clusters),
                'clusters': clusters,
                'statistics': statistics,
                'config_used': self.config
            }

            logger.info(f"✅ 形态学聚类分析完成 - 聚类数: {len(clusters)}, 覆盖率: {statistics['cluster_coverage']}%")

            return result

        except Exception as e:
            logger.error(f"❌ 聚类分析失败: {str(e)}")
            return {
                'success': False,
                'algorithm': 'morphology',
                'error': str(e)
            }
