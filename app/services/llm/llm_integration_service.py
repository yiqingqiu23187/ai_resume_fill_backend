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
            llm_response = await self.ai_service.analyze_with_prompt(prompt)

            # Step 4: 解析大模型响应
            logger.info("🔄 Step 4: 解析大模型响应...")
            matching_results = self._parse_llm_response(llm_response)

            # Step 5: 构建简化结果
            processing_time = time.time() - start_time
            final_result = self._build_simple_result(
                matching_results=matching_results,
                processing_time=processing_time
            )

            logger.info(f"✅ Phase 5处理完成: {len(matching_results)}个字段匹配, 用时{processing_time:.2f}秒")
            return final_result

        except Exception as e:
            logger.error(f"❌ Phase 5处理失败: {str(e)}", exc_info=True)
            return self._create_error_result(str(e))


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

    def _build_simple_result(self,
                           matching_results: List[Dict[str, Any]],
                           processing_time: float) -> Dict[str, Any]:
        """
        构建简化结果

        Args:
            matching_results: 匹配结果
            processing_time: 处理时间

        Returns:
            简化的结果
        """
        return {
            'success': True,
            'phase': 'phase5_llm_integration',
            'processing_time': processing_time,
            'matching_results': matching_results,
            'statistics': {
                'matched_fields': len(matching_results)
            }
        }

    def _create_empty_result(self, message: str) -> Dict[str, Any]:
        """创建空结果"""
        return {
            'success': True,
            'phase': 'phase5_llm_integration',
            'processing_time': 0,
            'matching_results': []
        }

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'success': False,
            'error': error_message,
            'phase': 'phase5_llm_integration_error',
            'processing_time': 0,
            'matching_results': []
        }


# 全局服务实例 - 注入AI服务
llm_integration_service = LLMIntegrationService(ai_service=AIService)
