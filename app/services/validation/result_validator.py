"""
Phase 5: 结果验证与优化服务

验证大模型匹配结果的合理性，检测不一致性并提供改进建议
"""

import logging
import re
from typing import Dict, List, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ResultValidator:
    """大模型结果验证器"""

    def __init__(self):
        """初始化验证器"""
        logger.info("🔍 初始化结果验证器")

        # 常见字段类型的验证规则
        self.field_patterns = {
            'phone': r'^1[3-9]\d{9}$',  # 手机号
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',  # 邮箱
            'id_card': r'^\d{17}[\dxX]$',  # 身份证
            'date': r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$',  # 日期
            'number': r'^\d+(\.\d+)?$'  # 数字
        }

    def validate_matching_results(self,
                                matching_results: List[Dict[str, Any]],
                                form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证匹配结果的合理性

        Args:
            matching_results: 大模型的匹配结果
            form_data: 表单结构数据

        Returns:
            验证结果和改进建议
        """
        try:
            logger.info(f"🔍 开始验证 {len(matching_results)} 个匹配结果")

            validation_result = {
                'is_valid': True,
                'overall_score': 0.0,
                'issues': [],
                'suggestions': [],
                'field_validations': [],
                'statistics': {
                    'total_fields': len(matching_results),
                    'valid_fields': 0,
                    'warning_fields': 0,
                    'error_fields': 0
                }
            }

            # 获取表单字段映射
            form_field_map = self._build_form_field_map(form_data)

            # 验证每个字段
            total_score = 0
            for result in matching_results:
                field_validation = self._validate_single_field(result, form_field_map)
                validation_result['field_validations'].append(field_validation)

                # 更新统计
                if field_validation['status'] == 'valid':
                    validation_result['statistics']['valid_fields'] += 1
                elif field_validation['status'] == 'warning':
                    validation_result['statistics']['warning_fields'] += 1
                    validation_result['issues'].append(field_validation['message'])
                else:  # error
                    validation_result['statistics']['error_fields'] += 1
                    validation_result['issues'].append(field_validation['message'])
                    validation_result['is_valid'] = False

                total_score += field_validation['score']

            # 计算总体得分
            if matching_results:
                validation_result['overall_score'] = total_score / len(matching_results)

            # 验证数组一致性
            array_issues = self._validate_array_consistency(matching_results, form_data)
            validation_result['issues'].extend(array_issues)

            # 生成改进建议
            suggestions = self._generate_suggestions(validation_result)
            validation_result['suggestions'] = suggestions

            logger.info(f"✅ 验证完成: 总体得分 {validation_result['overall_score']:.2f}")
            return validation_result

        except Exception as e:
            logger.error(f"❌ 结果验证失败: {str(e)}")
            return self._create_error_validation()

    def _validate_single_field(self,
                              field_result: Dict[str, Any],
                              form_field_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证单个字段

        Args:
            field_result: 单个字段的匹配结果
            form_field_map: 表单字段映射

        Returns:
            字段验证结果
        """
        selector = field_result.get('selector', '')
        value = field_result.get('value', '')

        validation = {
            'selector': selector,
            'value': value,
            'status': 'valid',
            'score': 1.0,
            'message': '',
            'suggestions': []
        }

        # 检查选择器是否存在
        if selector not in form_field_map:
            validation.update({
                'status': 'error',
                'score': 0.0,
                'message': f"选择器不存在: {selector}"
            })
            return validation

        form_field = form_field_map[selector]
        field_label = form_field.get('label', '')

        # 检查值是否为空
        if not value or not str(value).strip():
            validation.update({
                'status': 'warning',
                'score': 0.3,
                'message': f"字段'{field_label}'值为空"
            })
            return validation

        # 根据字段标签推断类型并验证
        field_type = self._infer_field_type(field_label)
        type_validation = self._validate_field_type(value, field_type)

        if not type_validation['valid']:
            validation.update({
                'status': 'warning',
                'score': 0.6,
                'message': f"字段'{field_label}'格式可能不正确: {type_validation['reason']}",
                'suggestions': [type_validation['suggestion']]
            })

        # 检查置信度
        confidence = field_result.get('confidence', 0.5)
        if confidence < 0.7:
            validation['score'] *= 0.8
            validation['suggestions'].append(f"匹配置信度较低 ({confidence:.2f})")

        return validation

    def _validate_field_type(self, value: str, field_type: str) -> Dict[str, Any]:
        """验证字段类型"""
        if field_type not in self.field_patterns:
            return {'valid': True, 'reason': '', 'suggestion': ''}

        pattern = self.field_patterns[field_type]
        if re.match(pattern, str(value)):
            return {'valid': True, 'reason': '', 'suggestion': ''}

        suggestions = {
            'phone': '请检查手机号格式，应为11位数字',
            'email': '请检查邮箱格式',
            'id_card': '请检查身份证号格式',
            'date': '请检查日期格式，应为YYYY-MM-DD或YYYY/MM/DD',
            'number': '请检查数字格式'
        }

        return {
            'valid': False,
            'reason': f'{field_type}格式不匹配',
            'suggestion': suggestions.get(field_type, '请检查字段格式')
        }

    def _infer_field_type(self, field_label: str) -> str:
        """根据字段标签推断字段类型"""
        label_lower = field_label.lower()

        if any(keyword in label_lower for keyword in ['手机', '电话', 'phone', 'mobile']):
            return 'phone'
        elif any(keyword in label_lower for keyword in ['邮箱', '邮件', 'email']):
            return 'email'
        elif any(keyword in label_lower for keyword in ['身份证', 'id']):
            return 'id_card'
        elif any(keyword in label_lower for keyword in ['日期', '时间', 'date', '年月']):
            return 'date'
        elif any(keyword in label_lower for keyword in ['年龄', '薪资', '工资', '分数', '数量']):
            return 'number'
        else:
            return 'text'

    def _validate_array_consistency(self,
                                  matching_results: List[Dict[str, Any]],
                                  form_data: Dict[str, Any]) -> List[str]:
        """验证数组一致性"""
        issues = []

        # 获取可重复分组
        repeatable_groups = []
        for group in form_data.get('form_structure', {}).get('groups', []):
            if group.get('is_repeatable', False):
                repeatable_groups.append(group)

        if not repeatable_groups:
            return issues

        # 验证每个可重复分组
        for group in repeatable_groups:
            group_title = group.get('title', '未知分组')
            group_fields = group.get('fields', [])

            # 按array_index分组字段
            index_map = {}
            for field in group_fields:
                array_index = field.get('array_index')
                if array_index is not None:
                    if array_index not in index_map:
                        index_map[array_index] = []
                    index_map[array_index].append(field.get('selector'))

            # 检查每个索引的完整性
            for index, selectors in index_map.items():
                matched_selectors = [r['selector'] for r in matching_results if r['selector'] in selectors]

                if len(matched_selectors) > 0 and len(matched_selectors) < len(selectors):
                    issues.append(f"{group_title}的第{index}组数据不完整: 只匹配了{len(matched_selectors)}/{len(selectors)}个字段")

        return issues

    def _build_form_field_map(self, form_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """构建表单字段映射"""
        field_map = {}

        for group in form_data.get('form_structure', {}).get('groups', []):
            for field in group.get('fields', []):
                selector = field.get('selector', '')
                if selector:
                    field_map[selector] = field

        return field_map

    def _generate_suggestions(self, validation_result: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        stats = validation_result['statistics']

        # 基于错误率的建议
        total_fields = stats['total_fields']
        error_rate = stats['error_fields'] / total_fields if total_fields > 0 else 0
        warning_rate = stats['warning_fields'] / total_fields if total_fields > 0 else 0

        if error_rate > 0.2:
            suggestions.append("错误率较高，建议检查字段识别准确性")

        if warning_rate > 0.3:
            suggestions.append("警告字段较多，建议优化字段匹配逻辑")

        # 基于得分的建议
        overall_score = validation_result['overall_score']
        if overall_score < 0.7:
            suggestions.append("总体质量较低，建议重新分析表单结构")
        elif overall_score < 0.85:
            suggestions.append("部分字段匹配质量有待提升")

        # 收集字段级别的建议
        field_suggestions = []
        for field_val in validation_result['field_validations']:
            field_suggestions.extend(field_val.get('suggestions', []))

        # 去重并添加
        unique_field_suggestions = list(set(field_suggestions))
        suggestions.extend(unique_field_suggestions[:3])  # 最多3个字段建议

        return suggestions

    def _create_error_validation(self) -> Dict[str, Any]:
        """创建错误验证结果"""
        return {
            'is_valid': False,
            'overall_score': 0.0,
            'issues': ['验证过程发生错误'],
            'suggestions': ['建议重新进行表单分析'],
            'field_validations': [],
            'statistics': {
                'total_fields': 0,
                'valid_fields': 0,
                'warning_fields': 0,
                'error_fields': 0
            }
        }

    def detect_inconsistencies(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测不一致性

        Args:
            results: 匹配结果列表

        Returns:
            不一致性列表
        """
        inconsistencies = []

        # 检测重复选择器
        selectors = [r.get('selector', '') for r in results]
        duplicates = [s for s in set(selectors) if selectors.count(s) > 1]

        for dup in duplicates:
            inconsistencies.append({
                'type': 'duplicate_selector',
                'selector': dup,
                'message': f"选择器重复: {dup}",
                'severity': 'error'
            })

        return inconsistencies

    def suggest_corrections(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        建议修正方案

        Args:
            issues: 问题列表

        Returns:
            修正建议列表
        """
        corrections = []

        for issue in issues:
            if issue.get('type') == 'duplicate_selector':
                corrections.append({
                    'issue': issue['message'],
                    'correction': '移除重复的选择器，保留置信度最高的匹配',
                    'priority': 'high'
                })

        return corrections
