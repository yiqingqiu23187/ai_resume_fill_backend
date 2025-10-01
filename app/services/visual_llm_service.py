"""
视觉大模型服务 - 新方案Phase 3
使用Qwen3-VL-Plus进行视觉语义理解

负责：
1. 网页截图
2. 结合简历信息进行视觉理解
3. 输出结构化的字段-值映射
"""

import logging
import json
import base64
from typing import Dict, List, Any, Optional
from io import BytesIO
from PIL import Image
import dashscope
from dashscope import MultiModalConversation
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class VisualLLMService:
    """视觉大模型服务"""

    def __init__(self, api_key: str = None):
        """初始化视觉大模型服务"""
        self._browser: Optional[Browser] = None
        self.api_key = api_key

        # 设置DashScope API密钥
        if api_key:
            dashscope.api_key = api_key

    async def _get_browser(self) -> Browser:
        """获取或创建浏览器实例"""
        if self._browser is None or not self._browser.is_connected():
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            logger.info("🚀 视觉大模型服务浏览器启动成功")
        return self._browser

    async def take_screenshot(
        self,
        html_content: str,
        viewport_width: int = 1200,
        viewport_height: int = 1400
    ) -> Optional[str]:
        """
        对HTML页面进行截图

        Args:
            html_content: HTML页面内容
            viewport_width: 视口宽度
            viewport_height: 视口高度

        Returns:
            base64编码的截图数据，失败返回None
        """
        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={'width': viewport_width, 'height': viewport_height}
            )

            # 设置页面内容
            await page.set_content(html_content, wait_until='networkidle')
            await page.wait_for_timeout(2000)  # 等待页面完全渲染

            # 截图
            screenshot_bytes = await page.screenshot(
                full_page=True,
                type='png'
            )
            await page.close()

            # 转换为base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            logger.info("📸 页面截图完成")
            return screenshot_base64

        except Exception as e:
            logger.error(f"❌ 截图失败: {str(e)}")
            return None

    async def analyze_with_visual_llm(
        self,
        screenshot_base64: str,
        resume_data: Dict[str, Any],
        field_labels: List[str]
    ) -> Dict[str, Any]:
        """
        使用视觉大模型分析截图和简历数据

        Args:
            screenshot_base64: base64编码的截图
            resume_data: 简历数据
            field_labels: 表单字段标签列表

        Returns:
            分析结果
        """
        try:
            # 构建提示词
            prompt = self._build_visual_analysis_prompt(resume_data, field_labels)

            # 调用Qwen3-VL-Plus
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": f"data:image/png;base64,{screenshot_base64}"
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]

            response = MultiModalConversation.call(
                model="qwen-vl-plus",
                messages=messages,
                temperature=0.1,  # 降低随机性，提高一致性
                max_tokens=2000
            )

            if response.status_code == 200:
                result_content = response.output.choices[0].message.content

                # 处理不同的响应格式
                if isinstance(result_content, dict) and 'text' in result_content:
                    result_content = result_content['text']
                elif isinstance(result_content, list):
                    result_content = '\n'.join(str(item) for item in result_content)
                elif not isinstance(result_content, str):
                    result_content = str(result_content)

                parsed_result = self._parse_llm_response(result_content)

                logger.info(f"🧠 视觉大模型分析完成，识别字段: {len(parsed_result.get('field_mappings', {}))}")
                return {
                    'success': True,
                    'field_mappings': parsed_result.get('field_mappings', {}),
                    'analysis_confidence': parsed_result.get('confidence', 0.8),
                    'raw_response': result_content
                }
            else:
                logger.error(f"❌ 大模型API调用失败: {response.message}")
                return {
                    'success': False,
                    'error': f"API调用失败: {response.message}"
                }

        except Exception as e:
            logger.error(f"❌ 视觉大模型分析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _build_visual_analysis_prompt(
        self,
        resume_data: Dict[str, Any],
        field_labels: List[str]
    ) -> str:
        """构建视觉分析提示词"""

        # 构建简历信息摘要
        resume_summary = self._build_resume_summary(resume_data)

        # 构建字段列表
        fields_text = "、".join(field_labels[:20])  # 限制长度避免过长
        if len(field_labels) > 20:
            fields_text += f"等共{len(field_labels)}个字段"

        prompt = f"""
你是一个专业的简历自动填写助手。请分析这个招聘网站的表单截图，结合提供的简历信息，智能匹配表单字段并填写对应的值。

## 简历信息：
{resume_summary}

## 表单字段列表：
{fields_text}

## 任务要求：
1. 仔细观察截图中的表单字段和标签
2. 理解每个字段的含义和要求
3. 从简历信息中找到对应的值进行匹配
4. 对于选择类字段（下拉框、单选框等），选择最匹配的选项
5. 对于特殊字段（如期望薪资、到岗时间等），给出合理的默认值

## 输出格式：
请严格按照以下JSON格式输出，不要添加任何其他内容：

```json
{{
    "field_mappings": {{
        "字段标签1": "对应的值",
        "字段标签2": "对应的值",
        "毕业院校": "北京大学",
        "学历": "本科",
        "专业": "计算机科学与技术",
        "姓名": "张三",
        "手机号": "13800138000"
    }},
    "confidence": 0.9
}}
```

## 注意事项：
- 只输出能确定映射的字段，不确定的不要包含
- 所有的键都必须是表单中实际存在的字段标签
- 值必须符合字段的格式要求
- confidence表示整体匹配的置信度（0-1之间）
- 务必使用中文字段标签作为键名
- 对于日期字段，使用YYYY-MM-DD格式
- 对于布尔字段，使用"是"或"否"

现在请开始分析：
"""
        return prompt

    def _build_resume_summary(self, resume_data: Dict[str, Any]) -> str:
        """构建简历信息摘要"""
        summary_parts = []

        # 基本信息
        basic_info = resume_data.get('basic_info', {})
        if basic_info:
            summary_parts.append("### 基本信息：")
            for key, value in basic_info.items():
                if value:
                    summary_parts.append(f"- {key}: {value}")

        # 教育经历
        education = resume_data.get('education', [])
        if education:
            summary_parts.append("\n### 教育经历：")
            for edu in education[:3]:  # 最多显示3个
                school = edu.get('school', '')
                major = edu.get('major', '')
                degree = edu.get('degree', '')
                period = edu.get('period', '')
                if school:
                    summary_parts.append(f"- {school} {major} {degree} ({period})")

        # 工作经验
        experience = resume_data.get('experience', [])
        if experience:
            summary_parts.append("\n### 工作经验：")
            for exp in experience[:3]:  # 最多显示3个
                company = exp.get('company', '')
                position = exp.get('position', '')
                period = exp.get('period', '')
                if company:
                    summary_parts.append(f"- {company} {position} ({period})")

        # 技能特长
        skills = resume_data.get('skills', [])
        if skills:
            summary_parts.append(f"\n### 技能特长：")
            summary_parts.append(f"- {', '.join(skills[:10])}")  # 最多显示10个技能

        # 如果没有任何信息，返回默认提示
        if not summary_parts:
            return "（未提供简历信息）"

        return "\n".join(summary_parts)

    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """解析大模型响应"""
        try:
            # 首先尝试移除markdown代码块
            if '```json' in response_content:
                # 提取markdown代码块中的JSON
                start_marker = '```json'
                end_marker = '```'
                start_idx = response_content.find(start_marker)
                if start_idx != -1:
                    start_idx += len(start_marker)
                    end_idx = response_content.find(end_marker, start_idx)
                    if end_idx != -1:
                        response_content = response_content[start_idx:end_idx].strip()

            # 先处理转义字符
            response_content = response_content.replace('\\n', '\n').replace('\\t', '\t')

            # 提取JSON部分
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                logger.warning("⚠️ LLM响应中未找到有效JSON")
                return {'field_mappings': {}, 'confidence': 0.0}

            json_str = response_content[json_start:json_end].strip()
            parsed_data = json.loads(json_str)

            # 验证和清理数据
            field_mappings = parsed_data.get('field_mappings', {})
            confidence = parsed_data.get('confidence', 0.8)

            # 过滤掉空值
            cleaned_mappings = {k: v for k, v in field_mappings.items() if v and str(v).strip()}

            return {
                'field_mappings': cleaned_mappings,
                'confidence': confidence
            }

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {str(e)}")
            logger.error(f"响应内容: {response_content[:500]}...")
            return {'field_mappings': {}, 'confidence': 0.0}
        except Exception as e:
            logger.error(f"❌ 响应解析失败: {str(e)}")
            return {'field_mappings': {}, 'confidence': 0.0}

    async def close_browser(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("🔒 视觉大模型服务浏览器已关闭")


# 全局实例
visual_llm_service = VisualLLMService()
