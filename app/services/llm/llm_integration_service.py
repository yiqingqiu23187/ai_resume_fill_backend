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

            # 记录完整提示词
            logger.info("📝 完整提示词内容:")
            logger.info("=" * 80)
            logger.info(prompt)
            logger.info("=" * 80)

            # Step 3: 调用大模型进行匹配
            logger.info("🧠 Step 3: 调用大模型进行字段匹配...")
            llm_response = await self.ai_service.analyze_with_prompt(prompt)

            # 记录完整响应
            logger.info("🤖 大模型完整响应内容:")
            logger.info("=" * 80)
            logger.info(f"响应长度: {len(llm_response)} 字符")
            logger.info(llm_response)
            logger.info("=" * 80)

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
        解析大模型响应 - 增强版

        Args:
            llm_response: 大模型的响应文本

        Returns:
            解析后的匹配结果列表
        """
        try:
            logger.info(f"🔍 开始解析响应，原始长度: {len(llm_response)} 字符")

            # Step 1: 清理响应文本
            cleaned_response = self._clean_llm_response(llm_response)
            logger.info(f"🧹 清理后长度: {len(cleaned_response)} 字符")

            # Step 2: 尝试多种解析策略
            strategies = [
                ("直接解析", lambda x: json.loads(x) if x.strip().startswith('[') else None),
                ("提取JSON数组", self._extract_json_array),
                ("提取代码块", self._extract_code_block),
                ("修复常见错误", self._fix_and_parse_json),
            ]

            for strategy_name, strategy_func in strategies:
                try:
                    logger.info(f"🔧 尝试策略: {strategy_name}")
                    result = strategy_func(cleaned_response)
                    if result is not None and isinstance(result, list):
                        logger.info(f"✅ 策略 '{strategy_name}' 成功解析出 {len(result)} 个结果")
                        return result
                    logger.info(f"⚠️ 策略 '{strategy_name}' 未成功")
                except Exception as e:
                    logger.warning(f"⚠️ 策略 '{strategy_name}' 失败: {str(e)}")
                    continue

            # Step 3: 如果所有策略都失败，返回空列表
            logger.warning("⚠️ 所有解析策略都失败，返回空结果")
            return []

        except Exception as e:
            logger.error(f"❌ 响应解析过程中发生严重错误: {str(e)}", exc_info=True)
            return []

    def _clean_llm_response(self, response: str) -> str:
        """清理大模型响应文本"""
        if not response:
            return ""

        # 移除可能的前后空白
        cleaned = response.strip()

        # 移除可能的BOM标记
        if cleaned.startswith('\ufeff'):
            cleaned = cleaned[1:]

        # 移除可能的markdown标记
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]

        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]

        return cleaned.strip()

    def _extract_json_array(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取JSON数组"""
        import re

        # 查找JSON数组模式
        patterns = [
            r'\[\s*\{.*?\}\s*\]',  # 标准数组格式
            r'\[[\s\S]*\]',       # 多行数组格式
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
        return None

    def _extract_code_block(self, text: str) -> List[Dict[str, Any]]:
        """从代码块中提取JSON"""
        import re

        # 查找代码块中的JSON
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(code_block_pattern, text)

        for match in matches:
            try:
                cleaned = match.strip()
                if cleaned.startswith('['):
                    return json.loads(cleaned)
            except:
                continue
        return None

    def _fix_and_parse_json(self, text: str) -> List[Dict[str, Any]]:
        """尝试修复常见的JSON错误并解析"""
        try:
            # 查找看起来像JSON的部分
            start_idx = text.find('[')
            end_idx = text.rfind(']')

            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                return None

            json_text = text[start_idx:end_idx + 1]

            # 尝试修复常见错误
            fixes = [
                # 修复缺失的逗号
                (r'}\s*{', '},\n{'),
                # 修复多余的逗号
                (r',\s*}', '}'),
                (r',\s*]', ']'),
                # 修复单引号
                (r"'([^']*)':", r'"\1":'),
                (r":\s*'([^']*)'", r': "\1"'),
            ]

            fixed_text = json_text
            for pattern, replacement in fixes:
                import re
                fixed_text = re.sub(pattern, replacement, fixed_text)

            return json.loads(fixed_text)

        except Exception as e:
            logger.debug(f"JSON修复失败: {str(e)}")
            return None

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
