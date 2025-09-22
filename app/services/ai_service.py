"""
AI服务模块 - 集成阿里千问大模型
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dashscope import Generation
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """AI服务类"""

    @staticmethod
    def _build_field_matching_prompt(
        resume_text: str,
        form_fields: List[Dict[str, Any]]
    ) -> str:
        """构建字段匹配的提示词"""

        # 格式化表单字段信息
        fields_info = []
        for field in form_fields:
            field_type = field.get('type', 'text')
            field_name = field.get('name', '')
            field_label = field.get('label', '')
            field_placeholder = field.get('placeholder', '')
            field_options = field.get('options', [])

            field_desc = f"字段名: {field_name}"
            if field_label:
                field_desc += f", 标签: {field_label}"
            if field_placeholder:
                field_desc += f", 占位符: {field_placeholder}"
            field_desc += f", 类型: {field_type}"

            if field_options:
                field_desc += f", 选项: {field_options}"

            fields_info.append(field_desc)

        prompt = f"""
你是一个专业的简历信息提取和表单填写助手。

请根据以下简历信息，为给定的表单字段提供合适的填写内容。

【简历信息】：
{resume_text}

【表单字段】：
{chr(10).join(f'{i+1}. {info}' for i, info in enumerate(fields_info))}

【任务要求】：
1. 仔细分析简历信息，理解候选人的背景
2. 为每个表单字段匹配最合适的内容
3. 如果简历中没有相关信息，返回空字符串
4. 对于选择类型的字段，请从给定选项中选择最匹配的
5. 日期格式请统一为 YYYY-MM-DD 或 YYYY-MM 格式
6. 电话号码保持原格式
7. 地址信息要具体到城市

【输出格式】：
请直接返回一个JSON数组，包含所有匹配结果，不要包含任何其他内容：

[
    {{
        "field_name": "字段名",
        "field_type": "字段类型",
        "matched_value": "匹配的值"
    }}
]
"""
        return prompt

    @staticmethod
    async def match_form_fields(
        resume_text: str,
        form_fields: List[Dict[str, Any]]
    ) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        使用AI匹配表单字段

        Args:
            resume_text: 简历文本内容
            form_fields: 表单字段列表

        Returns:
            Tuple[success, matches, error_message]
        """
        try:
            # 构建提示词
            prompt = AIService._build_field_matching_prompt(resume_text, form_fields)

            logger.info(f"AI字段匹配开始，简历长度: {len(resume_text)}, 字段数量: {len(form_fields)}")

            # 调用阿里千问API
            response = Generation.call(
                model=settings.AI_MODEL,
                prompt=prompt,
                api_key=settings.DASHSCOPE_API_KEY,
                max_tokens=2000,
                temperature=0.1,  # 较低的温度以获得更稳定的输出
                top_p=0.8
            )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"AI API调用失败，状态码: {response.status_code}"
                logger.error(error_msg)
                return False, [], error_msg

            # 解析响应内容
            ai_output = response.output.text.strip()
            logger.debug(f"AI原始输出: {ai_output}")

            # 尝试解析JSON
            try:
                # 提取JSON部分（去除可能的额外文本）
                json_start = ai_output.find('[')
                json_end = ai_output.rfind(']') + 1

                if json_start == -1 or json_end == 0:
                    raise ValueError("AI输出中未找到有效的JSON数组格式")

                json_content = ai_output[json_start:json_end]
                matches = json.loads(json_content)

                # 验证匹配结果格式
                validated_matches = []
                for match in matches:
                    if not isinstance(match, dict):
                        continue

                    validated_match = {
                        'field_name': match.get('field_name', ''),
                        'field_type': match.get('field_type', 'text'),
                        'matched_value': match.get('matched_value', '')
                    }
                    validated_matches.append(validated_match)

                logger.info(f"AI字段匹配成功，匹配结果数量: {len(validated_matches)}")
                return True, validated_matches, ""

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                error_msg = f"AI输出解析失败: {str(e)}"
                logger.error(f"{error_msg}, 原始输出: {ai_output}")
                return False, [], error_msg

        except Exception as e:
            error_msg = f"AI字段匹配过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
