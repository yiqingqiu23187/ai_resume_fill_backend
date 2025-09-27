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
    def _build_nested_field_matching_prompt(
        resume_text: str,
        resume_data: Dict[str, Any],
        form_structure: Dict[str, Any]
    ) -> str:
        """构建嵌套字段匹配的提示词"""

        prompt = f"""你是一个智能简历填写助手，需要将用户的简历信息与网站表单进行智能匹配。

## 任务说明
1. 分析网站表单的结构（包括嵌套的对象和数组）
2. 从用户简历中找到对应的信息
3. 按照表单结构返回匹配结果
4. 对于数组类型，需要智能判断应该创建多少项

## 用户简历信息
### 文本信息：
{resume_text}

### 结构化数据：
```json
{json.dumps(resume_data, ensure_ascii=False, indent=2)}
```

## 网站表单结构
```json
{json.dumps(form_structure, ensure_ascii=False, indent=2)}
```

## 匹配规则
1. **对象字段**: 直接匹配对应的键值
2. **数组字段**:
   - 根据用户简历判断应该有几项
   - 每项按照item_structure进行递归匹配
3. **选择器字段**:
   - 从options中选择最匹配的选项
   - 如果没有完全匹配的，选择最相近的
4. **日期字段**: 统一转换为YYYY-MM-DD格式
5. **找不到匹配数据时**: 返回null或空数组

## 特殊处理说明
- 对于教育经历、工作经历等列表，请根据简历实际情况创建对应数量的项目
- 对于嵌套的奖项、技能等子列表，也要智能匹配数量和内容
- 字段名不完全匹配时，请智能推断（如"学校"匹配到"毕业院校"）

## 返回格式
严格按照表单结构返回JSON，不要添加任何解释文字。

示例返回：
```json
{{
  "基本信息": {{
    "姓名": "具体的姓名值",
    "年龄": 25
  }},
  "教育经历": [
    {{
      "学校名称": "具体学校",
      "学历": "本科",
      "所获奖项": ["奖项1", "奖项2"]
    }}
  ]
}}
```

现在开始匹配：
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

    @staticmethod
    async def match_nested_form_fields(
        resume_text: str,
        resume_data: Dict[str, Any],
        form_structure: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        使用AI匹配嵌套表单字段

        Args:
            resume_text: 简历文本内容
            resume_data: 简历结构化数据
            form_structure: 嵌套表单结构

        Returns:
            Tuple[success, matched_data, error_message]
        """
        try:
            # 构建嵌套匹配提示词
            prompt = AIService._build_nested_field_matching_prompt(
                resume_text, resume_data, form_structure
            )

            logger.info(f"AI嵌套字段匹配开始，简历长度: {len(resume_text)}")

            # 调用阿里千问API
            response = Generation.call(
                model=settings.AI_MODEL,
                prompt=prompt,
                api_key=settings.DASHSCOPE_API_KEY,
                max_tokens=4000,  # 增加token限制以支持复杂结构
                temperature=0.1,
                top_p=0.8
            )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"AI API调用失败，状态码: {response.status_code}"
                logger.error(error_msg)
                return False, {}, error_msg

            # 解析响应内容
            ai_output = response.output.text.strip()
            logger.debug(f"AI嵌套匹配原始输出: {ai_output}")

            # 尝试解析JSON
            try:
                # 提取JSON部分
                json_start = ai_output.find('{')
                json_end = ai_output.rfind('}') + 1

                if json_start == -1 or json_end == 0:
                    raise ValueError("AI输出中未找到有效的JSON格式")

                json_content = ai_output[json_start:json_end]
                matched_data = json.loads(json_content)

                logger.info(f"AI嵌套字段匹配成功")
                return True, matched_data, ""

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                error_msg = f"AI输出解析失败: {str(e)}"
                logger.error(f"{error_msg}, 原始输出: {ai_output}")
                return False, {}, error_msg

        except Exception as e:
            error_msg = f"AI嵌套字段匹配过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
