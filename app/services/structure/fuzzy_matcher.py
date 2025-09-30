"""
智能模糊匹配引擎

支持多种匹配策略，避免硬编码，提供灵活的语义匹配能力
"""

import re
import json
from typing import List, Dict, Any, Tuple, Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """智能模糊匹配引擎"""

    def __init__(self, config_path: str = None):
        """
        初始化模糊匹配引擎

        Args:
            config_path: 语义配置文件路径
        """
        self.config = {}
        self.semantic_groups = {}
        self.matching_config = {}

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str):
        """加载语义配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self.semantic_groups = config_data.get('semantic_groups', {})
                self.matching_config = config_data.get('matching_config', {})
                logger.info(f"✅ 加载语义配置成功: {len(self.semantic_groups)}个分组")
        except Exception as e:
            logger.error(f"❌ 加载语义配置失败: {str(e)}")
            # 使用默认配置
            self._load_default_config()

    def _load_default_config(self):
        """加载默认配置"""
        self.matching_config = {
            'similarity_threshold': 0.6,
            'fuzzy_match_enabled': True,
            'case_sensitive': False,
            'partial_match_enabled': True,
            'pattern_match_weight': 0.7,
            'keyword_match_weight': 0.8,
            'spatial_proximity_weight': 0.5
        }

    def find_best_match(self, field_label: str, field_name: str = None, context: str = None) -> Optional[Dict[str, Any]]:
        """
        为字段找到最佳的语义匹配

        Args:
            field_label: 字段标签文本
            field_name: 字段name属性 (可选)
            context: 上下文信息 (可选)

        Returns:
            最佳匹配结果
        """
        if not field_label and not field_name:
            return None

        best_match = None
        best_score = 0

        # 预处理输入文本
        search_texts = []
        if field_label:
            search_texts.append(self._normalize_text(field_label))
        if field_name:
            search_texts.append(self._normalize_text(field_name))
        if context:
            search_texts.append(self._normalize_text(context))

        # 对每个语义分组进行匹配
        for group_id, group_config in self.semantic_groups.items():
            match_result = self._match_group(search_texts, group_id, group_config)
            if match_result and match_result['score'] > best_score:
                best_score = match_result['score']
                best_match = match_result

        # 只返回超过阈值的匹配
        threshold = self.matching_config.get('similarity_threshold', 0.6)
        if best_score >= threshold:
            return best_match

        return None

    def _match_group(self, search_texts: List[str], group_id: str, group_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        匹配特定语义分组

        Args:
            search_texts: 搜索文本列表
            group_id: 分组ID
            group_config: 分组配置

        Returns:
            匹配结果和得分
        """
        max_score = 0
        best_field_type = None
        match_details = []

        # 1. 关键词匹配
        keywords = group_config.get('keywords', {})
        for field_type, keyword_list in keywords.items():
            keyword_score = self._match_keywords(search_texts, keyword_list)
            if keyword_score > max_score:
                max_score = keyword_score
                best_field_type = field_type
                match_details.append({
                    'type': 'keyword',
                    'field_type': field_type,
                    'score': keyword_score
                })

        # 2. 模式匹配
        patterns = group_config.get('patterns', [])
        if patterns:
            pattern_score = self._match_patterns(search_texts, patterns)
            weighted_pattern_score = pattern_score * self.matching_config.get('pattern_match_weight', 0.7)
            if weighted_pattern_score > max_score * 0.8:  # 模式匹配权重稍低
                max_score = max(max_score, weighted_pattern_score)
                match_details.append({
                    'type': 'pattern',
                    'score': pattern_score,
                    'weighted_score': weighted_pattern_score
                })

        if max_score > 0:
            return {
                'group_id': group_id,
                'group_title': group_config.get('title', group_id),
                'field_type': best_field_type,
                'score': max_score,
                'is_repeatable': group_config.get('is_repeatable', False),
                'priority': group_config.get('priority', 999),
                'match_details': match_details
            }

        return None

    def _match_keywords(self, search_texts: List[str], keywords: List[str]) -> float:
        """
        关键词匹配

        Args:
            search_texts: 搜索文本列表
            keywords: 关键词列表

        Returns:
            匹配得分 (0-1)
        """
        max_score = 0

        for search_text in search_texts:
            if not search_text:
                continue

            for keyword in keywords:
                keyword_norm = self._normalize_text(keyword)

                # 完全匹配
                if search_text == keyword_norm:
                    return 1.0

                # 包含匹配
                if self.matching_config.get('partial_match_enabled', True):
                    if keyword_norm in search_text or search_text in keyword_norm:
                        partial_score = min(len(keyword_norm), len(search_text)) / max(len(keyword_norm), len(search_text))
                        max_score = max(max_score, partial_score * 0.9)

                # 模糊相似度匹配
                if self.matching_config.get('fuzzy_match_enabled', True):
                    similarity = SequenceMatcher(None, search_text, keyword_norm).ratio()
                    if similarity > 0.7:  # 相似度阈值
                        max_score = max(max_score, similarity * 0.8)

        return max_score

    def _match_patterns(self, search_texts: List[str], patterns: List[str]) -> float:
        """
        模式匹配

        Args:
            search_texts: 搜索文本列表
            patterns: 正则表达式模式列表

        Returns:
            匹配得分 (0-1)
        """
        for search_text in search_texts:
            if not search_text:
                continue

            for pattern in patterns:
                try:
                    if re.search(pattern, search_text, re.IGNORECASE):
                        return 0.9  # 模式匹配给较高分数
                except re.error:
                    logger.warning(f"⚠️ 无效的正则表达式模式: {pattern}")
                    continue

        return 0

    def detect_array_pattern(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        检测数组模式字段

        Args:
            field_name: 字段名称

        Returns:
            数组模式信息
        """
        if not field_name:
            return None

        array_indicators = [
            r'\[\d+\]',  # education[0]
            r'_\d+$',    # school_1
            r'\d+$',     # name1, name2
            r'第.{0,2}个',  # 第一个, 第1个
            r'第.{0,2}条'   # 第一条
        ]

        for pattern in array_indicators:
            match = re.search(pattern, field_name)
            if match:
                # 提取基础名称和索引
                base_name = re.sub(pattern, '', field_name)
                index_match = re.search(r'\d+', match.group())
                index = int(index_match.group()) if index_match else 0

                return {
                    'is_array': True,
                    'base_name': base_name,
                    'index': index,
                    'pattern_matched': pattern,
                    'original_name': field_name
                }

        return {'is_array': False}

    def group_array_fields(self, fields: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        将数组字段进行分组

        Args:
            fields: 字段列表

        Returns:
            分组后的数组字段
        """
        array_groups = {}
        single_fields = []

        for field in fields:
            field_name = field.get('name', '') or field.get('selector', '')
            array_info = self.detect_array_pattern(field_name)

            if array_info and array_info.get('is_array'):
                base_name = array_info['base_name']
                if base_name not in array_groups:
                    array_groups[base_name] = []

                field['array_info'] = array_info
                array_groups[base_name].append(field)
            else:
                single_fields.append(field)

        # 排序数组字段
        for base_name, group_fields in array_groups.items():
            group_fields.sort(key=lambda x: x.get('array_info', {}).get('index', 0))

        return {
            'array_groups': array_groups,
            'single_fields': single_fields
        }

    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        if not text:
            return ""

        # 移除特殊字符和多余空白
        normalized = re.sub(r'[^\w\s]', '', text)
        normalized = re.sub(r'\s+', '', normalized)

        # 大小写处理
        if not self.matching_config.get('case_sensitive', False):
            normalized = normalized.lower()

        return normalized

    def calculate_spatial_proximity_score(self, field1: Dict[str, Any], field2: Dict[str, Any]) -> float:
        """
        计算两个字段的空间邻近度得分

        Args:
            field1: 字段1
            field2: 字段2

        Returns:
            邻近度得分 (0-1)
        """
        bbox1 = field1.get('bbox', {})
        bbox2 = field2.get('bbox', {})

        if not bbox1 or not bbox2:
            return 0

        # 计算中心点距离
        center1 = (bbox1.get('x', 0) + bbox1.get('width', 0) / 2,
                  bbox1.get('y', 0) + bbox1.get('height', 0) / 2)
        center2 = (bbox2.get('x', 0) + bbox2.get('width', 0) / 2,
                  bbox2.get('y', 0) + bbox2.get('height', 0) / 2)

        distance = ((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2) ** 0.5

        # 转换为得分 (距离越近得分越高)
        max_distance = 500  # 最大有效距离
        if distance > max_distance:
            return 0

        return 1 - (distance / max_distance)
