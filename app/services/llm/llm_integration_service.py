"""
Phase 5: LLM集成主服务

整合数据格式转换、智能提示词生成、结果验证等功能
提供从Phase 4结构化数据到最终匹配结果的完整流程
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional

from .data_formatter import LLMDataFormatter
from .prompt_builder import StructuredPromptBuilder
from ..validation.result_validator import ResultValidator
from ..ai_service import AIService

logger = logging.getLogger(__name__)


class LLMIntegrationService:
    """LLM集成服务 - Phase 5主服务"""

    def __init__(self, ai_service=None):
        """
        初始化LLM集成服务

        Args:
            ai_service: AI服务实例（用于调用大模型）
        """
        self.data_formatter = LLMDataFormatter()
        self.prompt_builder = StructuredPromptBuilder()
        self.result_validator = ResultValidator()
        self.ai_service = ai_service

        logger.info("🤖 Phase 5 LLM集成服务初始化完成")

    async def process_structured_matching(self,
                                        phase4_result: Dict[str, Any],
                                        resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理结构化匹配 - Phase 5主入口

        Args:
            phase4_result: Phase 4的结构化分析结果
            resume_data: 用户简历数据

        Returns:
            完整的匹配结果，包含验证信息
        """
        start_time = time.time()

        try:
            logger.info("🚀 Phase 5开始处理结构化匹配...")

            # Step 1: 数据格式转换
            logger.info("📊 Step 1: 转换数据格式...")
            llm_data = self.data_formatter.format_for_llm(phase4_result)

            if not llm_data.get('form_structure', {}).get('groups'):
                logger.warning("⚠️ 没有有效的表单分组数据")
                return self._create_empty_result("没有有效的表单分组数据")

            # Step 2: 生成智能提示词
            logger.info("💬 Step 2: 生成智能提示词...")
            structure_summary = self.data_formatter.extract_structure_summary(llm_data)
            prompt = self.prompt_builder.build_matching_prompt(
                form_data=llm_data,
                resume_data=resume_data,
                structure_summary=structure_summary
            )

            # Step 3: 调用大模型进行匹配
            logger.info("🧠 Step 3: 调用大模型进行字段匹配...")
            if not self.ai_service:
                logger.warning("⚠️ AI服务未配置，使用模拟结果")
                llm_response = self._simulate_llm_response(llm_data, resume_data)
            else:
                llm_response = await self.ai_service.analyze_with_prompt(prompt)

            # Step 4: 解析大模型响应
            logger.info("🔄 Step 4: 解析大模型响应...")
            matching_results = self._parse_llm_response(llm_response)

            # Step 5: 验证匹配结果
            logger.info("🔍 Step 5: 验证匹配结果...")
            validation_result = self.result_validator.validate_matching_results(
                matching_results=matching_results,
                form_data=llm_data
            )

            # Step 6: 构建最终结果
            processing_time = time.time() - start_time
            final_result = self._build_final_result(
                phase4_result=phase4_result,
                llm_data=llm_data,
                matching_results=matching_results,
                validation_result=validation_result,
                processing_time=processing_time,
                structure_summary=structure_summary
            )

            logger.info(f"✅ Phase 5处理完成: {len(matching_results)}个字段匹配, 用时{processing_time:.2f}秒")
            return final_result

        except Exception as e:
            logger.error(f"❌ Phase 5处理失败: {str(e)}", exc_info=True)
            return self._create_error_result(str(e))

    def _simulate_llm_response(self, llm_data: Dict[str, Any], resume_data: Dict[str, Any]) -> str:
        """
        模拟大模型响应（用于测试）

        Args:
            llm_data: 格式化后的表单数据
            resume_data: 简历数据

        Returns:
            模拟的LLM响应
        """
        logger.info("🎭 使用模拟LLM响应进行测试")

        mock_results = []

        # 简单的模拟匹配逻辑
        resume_name = resume_data.get('basic_info', {}).get('name', '张三')
        resume_phone = resume_data.get('basic_info', {}).get('phone', '13800138000')
        resume_email = resume_data.get('basic_info', {}).get('email', 'test@example.com')

        for group in llm_data.get('form_structure', {}).get('groups', []):
            for field in group.get('fields', []):
                label = field.get('label', '').lower()
                selector = field.get('selector', '')

                value = None
                confidence = 0.8
                reasoning = "模拟匹配"

                # 基本信息匹配
                if '姓名' in label or 'name' in label:
                    value = resume_name
                    confidence = 0.95
                    reasoning = "匹配简历姓名字段"
                elif '手机' in label or 'phone' in label or '电话' in label:
                    value = resume_phone
                    confidence = 0.9
                    reasoning = "匹配简历手机号字段"
                elif '邮箱' in label or 'email' in label:
                    value = resume_email
                    confidence = 0.9
                    reasoning = "匹配简历邮箱字段"
                elif '学校' in label or '院校' in label:
                    value = "清华大学"
                    confidence = 0.85
                    reasoning = "匹配教育经历学校"
                elif '专业' in label:
                    value = "计算机科学与技术"
                    confidence = 0.85
                    reasoning = "匹配教育经历专业"

                if value:
                    mock_results.append({
                        "selector": selector,
                        "value": value,
                        "confidence": confidence,
                        "reasoning": reasoning
                    })

        return json.dumps(mock_results, ensure_ascii=False, indent=2)

    def _parse_llm_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        解析大模型响应

        Args:
            llm_response: 大模型的响应文本

        Returns:
            解析后的匹配结果列表
        """
        try:
            # 尝试直接解析JSON
            if llm_response.strip().startswith('['):
                return json.loads(llm_response)

            # 尝试从文本中提取JSON
            import re
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # 如果无法解析，返回空列表
            logger.warning("⚠️ 无法解析大模型响应，返回空结果")
            return []

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {str(e)}")
            return []

    def _build_final_result(self,
                          phase4_result: Dict[str, Any],
                          llm_data: Dict[str, Any],
                          matching_results: List[Dict[str, Any]],
                          validation_result: Dict[str, Any],
                          processing_time: float,
                          structure_summary: str) -> Dict[str, Any]:
        """
        构建最终结果

        Args:
            phase4_result: Phase 4结果
            llm_data: 格式化后的数据
            matching_results: 匹配结果
            validation_result: 验证结果
            processing_time: 处理时间
            structure_summary: 结构摘要

        Returns:
            最终结果
        """
        return {
            'success': True,
            'phase': 'phase5_llm_integration',
            'processing_time': processing_time,

            # 核心结果
            'matching_results': matching_results,
            'validation_result': validation_result,

            # 数据统计
            'statistics': {
                'input_groups': len(llm_data.get('form_structure', {}).get('groups', [])),
                'input_fields': self.data_formatter.get_total_field_count(llm_data),
                'matched_fields': len(matching_results),
                'valid_matches': validation_result.get('statistics', {}).get('valid_fields', 0),
                'match_rate': len(matching_results) / max(self.data_formatter.get_total_field_count(llm_data), 1),
                'validation_score': validation_result.get('overall_score', 0)
            },

            # 质量评估
            'quality_assessment': {
                'overall_quality': self._assess_overall_quality(validation_result, len(matching_results)),
                'structure_quality': phase4_result.get('phase4_quality', {}),
                'matching_quality': validation_result.get('overall_score', 0),
                'recommendations': validation_result.get('suggestions', [])
            },

            # 元数据
            'metadata': {
                'structure_summary': structure_summary,
                'complexity': self.prompt_builder.estimate_complexity(llm_data),
                'repeatable_groups': len(self.data_formatter.get_repeatable_groups(llm_data)),
                'phase4_source': {
                    'total_logical_groups': len(phase4_result.get('logical_groups', [])),
                    'phase4_quality_level': phase4_result.get('phase4_quality', {}).get('level', 'unknown')
                }
            },

            # 调试信息（可选）
            'debug_info': {
                'llm_input_groups': len(llm_data.get('form_structure', {}).get('groups', [])),
                'validation_issues': len(validation_result.get('issues', [])),
                'has_array_fields': any(
                    field.get('array_index') is not None
                    for group in llm_data.get('form_structure', {}).get('groups', [])
                    for field in group.get('fields', [])
                )
            }
        }

    def _assess_overall_quality(self, validation_result: Dict[str, Any], match_count: int) -> str:
        """评估总体质量"""
        validation_score = validation_result.get('overall_score', 0)
        error_count = len(validation_result.get('issues', []))

        if validation_score >= 0.9 and error_count == 0:
            return 'excellent'
        elif validation_score >= 0.8 and error_count <= 1:
            return 'good'
        elif validation_score >= 0.6 and error_count <= 3:
            return 'fair'
        else:
            return 'poor'

    def _create_empty_result(self, message: str) -> Dict[str, Any]:
        """创建空结果"""
        return {
            'success': True,
            'phase': 'phase5_llm_integration',
            'processing_time': 0,
            'matching_results': [],
            'validation_result': {
                'is_valid': True,
                'overall_score': 0,
                'issues': [message],
                'suggestions': []
            },
            'statistics': {
                'input_groups': 0,
                'input_fields': 0,
                'matched_fields': 0,
                'valid_matches': 0,
                'match_rate': 0,
                'validation_score': 0
            },
            'quality_assessment': {
                'overall_quality': 'poor',
                'recommendations': [message]
            }
        }

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'success': False,
            'error': error_message,
            'phase': 'phase5_llm_integration_error',
            'processing_time': 0,
            'matching_results': [],
            'validation_result': {
                'is_valid': False,
                'overall_score': 0,
                'issues': [f"处理错误: {error_message}"],
                'suggestions': ['建议重新分析表单结构']
            }
        }

    async def validate_and_optimize_results(self,
                                          matching_results: List[Dict[str, Any]],
                                          form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        单独的结果验证和优化接口

        Args:
            matching_results: 匹配结果
            form_data: 表单数据

        Returns:
            验证和优化结果
        """
        try:
            logger.info("🔍 开始独立的结果验证...")

            # 验证结果
            validation_result = self.result_validator.validate_matching_results(
                matching_results=matching_results,
                form_data=form_data
            )

            # 检测不一致性
            inconsistencies = self.result_validator.detect_inconsistencies(matching_results)

            # 生成修正建议
            corrections = self.result_validator.suggest_corrections(inconsistencies)

            return {
                'validation': validation_result,
                'inconsistencies': inconsistencies,
                'corrections': corrections,
                'optimization_suggestions': self._generate_optimization_suggestions(validation_result)
            }

        except Exception as e:
            logger.error(f"❌ 独立验证失败: {str(e)}")
            return {
                'validation': {'is_valid': False, 'error': str(e)},
                'inconsistencies': [],
                'corrections': [],
                'optimization_suggestions': []
            }

    def _generate_optimization_suggestions(self, validation_result: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        suggestions = []

        score = validation_result.get('overall_score', 0)
        issues_count = len(validation_result.get('issues', []))

        if score < 0.7:
            suggestions.append("考虑优化Phase 4的结构识别精度")

        if issues_count > 5:
            suggestions.append("建议检查字段标签的语义清晰度")

        return suggestions


# 全局服务实例 - 注入AI服务
llm_integration_service = LLMIntegrationService(ai_service=AIService)
