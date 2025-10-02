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

from ..schemas.new_visual_analysis import VisualLLMResult

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

            # 获取页面实际尺寸
            page_size = await page.evaluate("""
                () => {
                    return {
                        scrollWidth: document.documentElement.scrollWidth,
                        scrollHeight: document.documentElement.scrollHeight,
                        clientWidth: document.documentElement.clientWidth,
                        clientHeight: document.documentElement.clientHeight
                    };
                }
            """)

            # 截图（全页面）
            screenshot_bytes = await page.screenshot(
                full_page=True,
                type='png'
            )
            await page.close()

            # 转换为base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            logger.info(f"📸 页面截图完成 - 实际尺寸: {page_size['scrollWidth']}x{page_size['scrollHeight']}px")
            return screenshot_base64

        except Exception as e:
            logger.error(f"❌ 截图失败: {str(e)}")
            return None

    async def analyze_with_visual_llm(
        self,
        screenshot_base64: str,
        resume_data: Dict[str, Any]
    ) -> VisualLLMResult:
        """
        使用视觉大模型分析截图和简历数据

        Args:
            screenshot_base64: base64编码的截图
            resume_data: 简历数据

        Returns:
            分析结果
        """
        try:
            # 构建提示词
            prompt = self._build_visual_analysis_prompt(resume_data)

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
                return VisualLLMResult(
                    success=True,
                    field_mappings=parsed_result.get('field_mappings', {}),
                    analysis_confidence=parsed_result.get('confidence', 0.8),
                    raw_response=result_content
                )
            else:
                logger.error(f"❌ 大模型API调用失败: {response.message}")
                return VisualLLMResult(
                    success=False,
                    error=f"API调用失败: {response.message}"
                )

        except Exception as e:
            logger.error(f"❌ 视觉大模型分析失败: {str(e)}")
            return VisualLLMResult(
                success=False,
                error=str(e)
            )

    def _build_visual_analysis_prompt(
        self,
        resume_data: Dict[str, Any]
    ) -> str:
        """构建视觉分析提示词"""

        # 将简历数据转为格式化的JSON字符串
        import json
        resume_json = json.dumps(resume_data, ensure_ascii=False, indent=2)

        prompt = f"""
你是一个专业的简历自动填写助手。请分析这个招聘网站的表单截图，结合提供的简历信息，智能识别表单字段并填写对应的值。

## 简历信息（JSON格式）：
```json
{resume_json}
```

## 任务要求：
1. **仔细观察截图**：识别表单中的所有输入字段、标签文本、下拉选择、单选框等
2. **理解字段含义**：根据标签文本理解每个字段需要填写什么内容
3. **智能匹配数据**：从简历JSON数据中找到对应的值进行匹配
4. **处理选择字段**：对于下拉框、单选框等，选择最匹配的选项值
5. **生成合理默认值**：对于简历中没有的信息，根据常见情况给出合理默认值

## 常见字段类型和处理：
- **基本信息**：姓名、性别、年龄、手机号、邮箱、地址等
- **教育信息**：毕业院校、专业、学历、毕业时间等
- **工作信息**：工作经验、期望职位、期望薪资等
- **其他信息**：自我介绍、技能特长、证书等

## 输出格式：
请严格按照以下JSON格式输出，只输出JSON，不要添加任何其他文字：

```json
{{
    "field_mappings": {{
        "姓名": "张小明",
        "学历": "本科",
        "专业": "计算机科学与技术",
        "手机号": "13812345678",
        "邮箱地址": "zhangxiaoming@example.com"
    }},
    "confidence": 0.95
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
