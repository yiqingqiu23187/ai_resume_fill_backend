"""
XY-Cut算法实现模块

基于水平和垂直投影的递归页面分割算法，用于识别表单的自然布局结构
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
from pathlib import Path

logger = logging.getLogger(__name__)


class XYCutAnalyzer:
    """XY-Cut算法分析器"""

    def __init__(self, screenshot_path: str, bbox_data: Dict[str, Any], config: Optional[Dict] = None):
        """
        初始化XY-Cut分析器

        Args:
            screenshot_path: 截图文件路径
            bbox_data: BBOX数据
            config: 配置参数
        """
        self.screenshot_path = screenshot_path
        self.bbox_data = bbox_data
        self.config = config or self._get_default_config()

        # 加载图像
        self.image = cv2.imread(screenshot_path)
        if self.image is None:
            raise ValueError(f"无法加载截图: {screenshot_path}")

        self.image_height, self.image_width = self.image.shape[:2]

        # 创建元素掩码
        self.element_mask = self._create_element_mask()

        logger.info(f"🔍 XY-Cut分析器初始化完成 - 图像尺寸: {self.image_width}x{self.image_height}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'xy_cut_threshold': 10,  # 空白区域阈值(像素)
            'min_region_width': 50,  # 最小区域宽度
            'min_region_height': 30, # 最小区域高度
            'max_recursion_depth': 5, # 最大递归深度
            'merge_close_cuts': True, # 是否合并相近的切割线
            'cut_merge_threshold': 20 # 切割线合并阈值
        }

    def _create_element_mask(self) -> np.ndarray:
        """
        根据BBOX数据创建元素掩码图像

        Returns:
            二值掩码图像，元素区域为1，空白区域为0
        """
        try:
            mask = np.zeros((self.image_height, self.image_width), dtype=np.uint8)

            if not self.bbox_data.get('success') or not self.bbox_data.get('bbox_data'):
                logger.warning("⚠️ BBOX数据无效，返回空掩码")
                return mask

            elements = self.bbox_data['bbox_data']['elements']

            for element in elements:
                bbox = element['bbox']
                x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']

                # 确保坐标在图像范围内
                x = max(0, min(x, self.image_width - 1))
                y = max(0, min(y, self.image_height - 1))
                w = max(1, min(w, self.image_width - x))
                h = max(1, min(h, self.image_height - y))

                # 在掩码中标记元素区域
                mask[y:y+h, x:x+w] = 1

            return mask

        except Exception as e:
            logger.error(f"❌ 创建元素掩码失败: {str(e)}")
            return np.zeros((self.image_height, self.image_width), dtype=np.uint8)

    def horizontal_projection(self, region_mask: np.ndarray, region_bbox: Dict[str, int]) -> List[int]:
        """
        计算水平投影，检测空白行

        Args:
            region_mask: 区域掩码
            region_bbox: 区域边界框 {'x': x, 'y': y, 'width': w, 'height': h}

        Returns:
            每行的元素像素数量列表
        """
        try:
            y_start = region_bbox['y']
            y_end = y_start + region_bbox['height']
            x_start = region_bbox['x']
            x_end = x_start + region_bbox['width']

            # 提取区域掩码
            region = region_mask[y_start:y_end, x_start:x_end]

            # 计算每行的元素像素数量
            horizontal_proj = np.sum(region, axis=1)

            return horizontal_proj.tolist()

        except Exception as e:
            logger.error(f"❌ 水平投影计算失败: {str(e)}")
            return []

    def vertical_projection(self, region_mask: np.ndarray, region_bbox: Dict[str, int]) -> List[int]:
        """
        计算垂直投影，检测空白列

        Args:
            region_mask: 区域掩码
            region_bbox: 区域边界框

        Returns:
            每列的元素像素数量列表
        """
        try:
            y_start = region_bbox['y']
            y_end = y_start + region_bbox['height']
            x_start = region_bbox['x']
            x_end = x_start + region_bbox['width']

            # 提取区域掩码
            region = region_mask[y_start:y_end, x_start:x_end]

            # 计算每列的元素像素数量
            vertical_proj = np.sum(region, axis=0)

            return vertical_proj.tolist()

        except Exception as e:
            logger.error(f"❌ 垂直投影计算失败: {str(e)}")
            return []

    def find_cut_lines(self, projection: List[int], is_horizontal: bool = True) -> List[int]:
        """
        在投影中寻找切割线（连续的空白区域）

        Args:
            projection: 投影数据
            is_horizontal: 是否为水平投影

        Returns:
            切割线位置列表
        """
        try:
            if not projection:
                return []

            threshold = self.config['xy_cut_threshold']
            cut_lines = []
            in_empty_region = False
            empty_start = 0

            for i, count in enumerate(projection):
                if count <= threshold:  # 空白区域
                    if not in_empty_region:
                        in_empty_region = True
                        empty_start = i
                else:  # 有内容区域
                    if in_empty_region:
                        # 空白区域结束，检查是否足够宽以成为切割线
                        empty_width = i - empty_start
                        if empty_width >= threshold:
                            # 在空白区域中间位置放置切割线
                            cut_pos = empty_start + empty_width // 2
                            cut_lines.append(cut_pos)
                        in_empty_region = False

            # 处理最后的空白区域
            if in_empty_region:
                empty_width = len(projection) - empty_start
                if empty_width >= threshold:
                    cut_pos = empty_start + empty_width // 2
                    cut_lines.append(cut_pos)

            # 合并相近的切割线
            if self.config['merge_close_cuts'] and len(cut_lines) > 1:
                cut_lines = self._merge_close_cuts(cut_lines)

            return cut_lines

        except Exception as e:
            logger.error(f"❌ 寻找切割线失败: {str(e)}")
            return []

    def _merge_close_cuts(self, cut_lines: List[int]) -> List[int]:
        """
        合并距离过近的切割线

        Args:
            cut_lines: 原始切割线列表

        Returns:
            合并后的切割线列表
        """
        if len(cut_lines) <= 1:
            return cut_lines

        merged = [cut_lines[0]]
        merge_threshold = self.config['cut_merge_threshold']

        for cut in cut_lines[1:]:
            if cut - merged[-1] > merge_threshold:
                merged.append(cut)
            # 否则忽略这个太近的切割线

        return merged

    def recursive_cut(self, region_bbox: Dict[str, int], depth: int = 0) -> List[Dict[str, Any]]:
        """
        递归执行XY-Cut切割

        Args:
            region_bbox: 当前区域的边界框
            depth: 当前递归深度

        Returns:
            切割后的子区域列表
        """
        try:
            max_depth = self.config['max_recursion_depth']
            min_width = self.config['min_region_width']
            min_height = self.config['min_region_height']

            # 递归深度检查
            if depth >= max_depth:
                return [self._create_region_info(region_bbox, depth, "max_depth")]

            # 区域大小检查
            if (region_bbox['width'] < min_width or
                region_bbox['height'] < min_height):
                return [self._create_region_info(region_bbox, depth, "min_size")]

            # 计算水平投影和垂直投影
            h_proj = self.horizontal_projection(self.element_mask, region_bbox)
            v_proj = self.vertical_projection(self.element_mask, region_bbox)

            # 寻找切割线
            h_cuts = self.find_cut_lines(h_proj, is_horizontal=True)
            v_cuts = self.find_cut_lines(v_proj, is_horizontal=False)

            # 如果没有切割线，返回当前区域
            if not h_cuts and not v_cuts:
                return [self._create_region_info(region_bbox, depth, "no_cuts")]

            # 选择切割方向：优先选择有更多切割线的方向
            if len(h_cuts) >= len(v_cuts):
                # 水平切割（按行分割）
                sub_regions = self._horizontal_cut(region_bbox, h_cuts, depth)
            else:
                # 垂直切割（按列分割）
                sub_regions = self._vertical_cut(region_bbox, v_cuts, depth)

            # 递归处理子区域
            final_regions = []
            for sub_region in sub_regions:
                final_regions.extend(self.recursive_cut(sub_region, depth + 1))

            return final_regions

        except Exception as e:
            logger.error(f"❌ 递归切割失败: {str(e)}")
            return [self._create_region_info(region_bbox, depth, "error")]

    def _horizontal_cut(self, region_bbox: Dict[str, int], h_cuts: List[int], depth: int) -> List[Dict[str, int]]:
        """
        执行水平切割

        Args:
            region_bbox: 原区域
            h_cuts: 水平切割线位置
            depth: 当前深度

        Returns:
            切割后的子区域列表
        """
        sub_regions = []
        y_start = region_bbox['y']
        prev_cut = 0

        for cut_pos in h_cuts + [region_bbox['height']]:
            if cut_pos > prev_cut:
                sub_height = cut_pos - prev_cut
                if sub_height >= self.config['min_region_height']:
                    sub_region = {
                        'x': region_bbox['x'],
                        'y': y_start + prev_cut,
                        'width': region_bbox['width'],
                        'height': sub_height
                    }
                    sub_regions.append(sub_region)
            prev_cut = cut_pos

        return sub_regions

    def _vertical_cut(self, region_bbox: Dict[str, int], v_cuts: List[int], depth: int) -> List[Dict[str, int]]:
        """
        执行垂直切割

        Args:
            region_bbox: 原区域
            v_cuts: 垂直切割线位置
            depth: 当前深度

        Returns:
            切割后的子区域列表
        """
        sub_regions = []
        x_start = region_bbox['x']
        prev_cut = 0

        for cut_pos in v_cuts + [region_bbox['width']]:
            if cut_pos > prev_cut:
                sub_width = cut_pos - prev_cut
                if sub_width >= self.config['min_region_width']:
                    sub_region = {
                        'x': x_start + prev_cut,
                        'y': region_bbox['y'],
                        'width': sub_width,
                        'height': region_bbox['height']
                    }
                    sub_regions.append(sub_region)
            prev_cut = cut_pos

        return sub_regions

    def _create_region_info(self, bbox: Dict[str, int], depth: int, stop_reason: str) -> Dict[str, Any]:
        """
        创建区域信息

        Args:
            bbox: 区域边界框
            depth: 递归深度
            stop_reason: 停止切割的原因

        Returns:
            区域信息字典
        """
        return {
            'bbox': bbox,
            'depth': depth,
            'stop_reason': stop_reason,
            'area': bbox['width'] * bbox['height'],
            'algorithm': 'xy_cut'
        }

    def analyze_layout(self) -> Dict[str, Any]:
        """
        执行完整的XY-Cut布局分析

        Returns:
            分析结果
        """
        try:
            logger.info(f"🚀 开始XY-Cut布局分析...")

            # 从整个图像开始递归切割
            full_image_bbox = {
                'x': 0,
                'y': 0,
                'width': self.image_width,
                'height': self.image_height
            }

            regions = self.recursive_cut(full_image_bbox, depth=0)

            # 统计分析结果
            total_area = self.image_width * self.image_height
            regions_area = sum(region['area'] for region in regions)
            coverage_rate = regions_area / total_area * 100

            # 按深度分组统计
            depth_stats = {}
            for region in regions:
                depth = region['depth']
                if depth not in depth_stats:
                    depth_stats[depth] = 0
                depth_stats[depth] += 1

            result = {
                'success': True,
                'algorithm': 'xy_cut',
                'total_regions': len(regions),
                'regions': regions,
                'statistics': {
                    'total_area': total_area,
                    'regions_area': regions_area,
                    'coverage_rate': round(coverage_rate, 2),
                    'depth_distribution': depth_stats,
                    'avg_region_area': round(regions_area / len(regions) if regions else 0, 2)
                },
                'config_used': self.config
            }

            logger.info(f"✅ XY-Cut分析完成 - 识别区域: {len(regions)}个, 覆盖率: {coverage_rate:.1f}%")

            return result

        except Exception as e:
            logger.error(f"❌ XY-Cut布局分析失败: {str(e)}")
            return {
                'success': False,
                'algorithm': 'xy_cut',
                'error': str(e)
            }
