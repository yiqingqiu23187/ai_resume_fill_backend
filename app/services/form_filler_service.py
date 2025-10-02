"""
表单填写执行服务 - 新方案Phase 5
负责将匹配的字段值精确填写到表单中

支持的字段类型：
- text/password/email/tel: 文本输入
- select: 下拉选择
- radio: 单选按钮
- checkbox: 复选框
- textarea: 文本域
"""

import logging
import json
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Browser, Page

from ..schemas.new_visual_analysis import FormFillingResult, FillResult, FieldMatchResult

logger = logging.getLogger(__name__)


class FormFillerService:
    """表单填写执行服务"""

    def __init__(self):
        """初始化表单填写服务"""
        self._browser: Optional[Browser] = None

    async def _get_browser(self) -> Browser:
        """获取或创建浏览器实例"""
        if self._browser is None or not self._browser.is_connected():
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=False,  # 非无头模式，便于观察填写过程
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            logger.info("🚀 表单填写服务浏览器启动成功")
        return self._browser

    async def fill_form(
        self,
        html_content: str,
        matching_results: List[FieldMatchResult],
        viewport_width: int = 1200,
        viewport_height: int = 1400
    ) -> FormFillingResult:
        """
        执行表单填写

        Args:
            html_content: HTML页面内容
            matching_results: 匹配结果列表
            viewport_width: 视口宽度
            viewport_height: 视口高度

        Returns:
            填写结果
        """
        try:
            logger.info(f"🖊️ 开始表单填写: {len(matching_results)}个字段")

            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={'width': viewport_width, 'height': viewport_height}
            )

            # 设置页面内容
            await page.set_content(html_content, wait_until='networkidle')
            await page.wait_for_timeout(2000)

            # 执行填写
            fill_results = []
            for match_result in matching_results:
                result = await self._fill_single_field(page, match_result)
                fill_results.append(result)

            # 统计填写结果
            successful_fills = [r for r in fill_results if r.success]
            failed_fills = [r for r in fill_results if not r.success]

            logger.info(f"✅ 表单填写完成: {len(successful_fills)}/{len(matching_results)} 成功")

            # 生成填写脚本供扩展使用（转换为字典供脚本生成使用）
            successful_fills_dict = []
            for fill_result in successful_fills:
                successful_fills_dict.append({
                    'selector': fill_result.selector,
                    'value': fill_result.value,
                    'type': fill_result.type,
                    'label': fill_result.label
                })
            fill_script = self._generate_fill_script(successful_fills_dict)

            return FormFillingResult(
                success=True,
                total_fields=len(matching_results),
                successful_fills=len(successful_fills),
                failed_fills=len(failed_fills),
                fill_results=fill_results,
                fill_script=fill_script,
                fill_rate=len(successful_fills) / len(matching_results) if matching_results else 0
            )

        except Exception as e:
            logger.error(f"❌ 表单填写失败: {str(e)}")
            return FormFillingResult(
                success=False,
                error=str(e),
                total_fields=0,
                successful_fills=0,
                failed_fills=0,
                fill_results=[],
                fill_rate=0.0
            )

    async def _fill_single_field(
        self,
        page: Page,
        match_result: FieldMatchResult
    ) -> FillResult:
        """
        填写单个字段

        Args:
            page: 页面对象
            match_result: 匹配结果

        Returns:
            填写结果
        """
        selector = match_result.selector
        value = match_result.value
        field_type = match_result.type
        form_label = match_result.form_label

        try:
            # 等待元素出现
            await page.wait_for_selector(selector, timeout=5000)

            # 根据字段类型执行不同的填写策略
            if field_type in ['text', 'email', 'tel', 'password', 'url', 'number']:
                success = await self._fill_text_field(page, selector, value)
            elif field_type == 'select':
                success = await self._fill_select_field(page, selector, value)
            elif field_type == 'radio':
                success = await self._fill_radio_field(page, selector, value)
            elif field_type == 'checkbox':
                success = await self._fill_checkbox_field(page, selector, value)
            elif field_type == 'textarea':
                success = await self._fill_textarea_field(page, selector, value)
            else:
                # 默认按文本字段处理
                success = await self._fill_text_field(page, selector, value)

            if success:
                logger.info(f"✅ 字段填写成功: {form_label} = {value}")
                return FillResult(
                    success=True,
                    selector=selector,
                    value=value,
                    type=field_type,
                    label=form_label
                )
            else:
                logger.warning(f"⚠️ 字段填写失败: {form_label}")
                return FillResult(
                    success=False,
                    selector=selector,
                    value=value,
                    type=field_type,
                    label=form_label,
                    error='填写操作失败'
                )

        except Exception as e:
            logger.error(f"❌ 字段填写异常: {form_label} - {str(e)}")
            return FillResult(
                success=False,
                selector=selector,
                value=value,
                type=field_type,
                label=form_label,
                error=str(e)
            )

    async def _fill_text_field(self, page: Page, selector: str, value: str) -> bool:
        """填写文本字段"""
        try:
            # 清空并填写
            await page.fill(selector, str(value))
            await page.wait_for_timeout(100)  # 短暂等待
            return True
        except Exception as e:
            logger.warning(f"文本字段填写失败 {selector}: {str(e)}")
            return False

    async def _fill_select_field(self, page: Page, selector: str, value: str) -> bool:
        """填写下拉选择字段"""
        try:
            # 尝试按值选择
            try:
                await page.select_option(selector, value=str(value))
                return True
            except:
                pass

            # 尝试按文本选择
            try:
                await page.select_option(selector, label=str(value))
                return True
            except:
                pass

            # 尝试模糊匹配选项
            options = await page.eval_on_selector_all(
                f"{selector} option",
                "elements => elements.map(el => ({value: el.value, text: el.textContent.trim()}))"
            )

            for option in options:
                if str(value).lower() in option['text'].lower() or option['text'].lower() in str(value).lower():
                    await page.select_option(selector, value=option['value'])
                    return True

            logger.warning(f"未找到匹配的选项: {value}")
            return False

        except Exception as e:
            logger.warning(f"下拉选择填写失败 {selector}: {str(e)}")
            return False

    async def _fill_radio_field(self, page: Page, selector: str, value: str) -> bool:
        """填写单选按钮字段"""
        try:
            # 如果selector指向单个radio，直接选中
            element_count = await page.locator(selector).count()
            if element_count == 1:
                await page.check(selector)
                return True

            # 如果有多个radio，查找匹配的选项
            radios = await page.query_selector_all(selector)
            for radio in radios:
                radio_value = await radio.get_attribute('value')
                if radio_value and str(value).lower() in radio_value.lower():
                    await radio.check()
                    return True

            # 尝试根据关联标签匹配
            for radio in radios:
                # 查找关联的label
                radio_id = await radio.get_attribute('id')
                if radio_id:
                    label = await page.query_selector(f'label[for="{radio_id}"]')
                    if label:
                        label_text = await label.text_content()
                        if label_text and str(value).lower() in label_text.lower():
                            await radio.check()
                            return True

            return False

        except Exception as e:
            logger.warning(f"单选按钮填写失败 {selector}: {str(e)}")
            return False

    async def _fill_checkbox_field(self, page: Page, selector: str, value: str) -> bool:
        """填写复选框字段"""
        try:
            # 将值转换为布尔值
            should_check = str(value).lower() in ['true', '是', '1', 'yes', 'on', '选中']

            if should_check:
                await page.check(selector)
            else:
                await page.uncheck(selector)

            return True

        except Exception as e:
            logger.warning(f"复选框填写失败 {selector}: {str(e)}")
            return False

    async def _fill_textarea_field(self, page: Page, selector: str, value: str) -> bool:
        """填写文本域字段"""
        try:
            await page.fill(selector, str(value))
            return True
        except Exception as e:
            logger.warning(f"文本域填写失败 {selector}: {str(e)}")
            return False

    def _generate_fill_script(self, successful_fills: List[Dict[str, Any]]) -> str:
        """
        生成JavaScript填写脚本，供浏览器扩展使用

        Args:
            successful_fills: 成功填写的字段列表

        Returns:
            JavaScript代码字符串
        """
        script_parts = [
            "// AI简历自动填写脚本",
            "console.log('🤖 开始执行AI简历自动填写...');",
            "",
            "function autoFillForm() {"
        ]

        for fill_result in successful_fills:
            selector = fill_result['selector']
            value = fill_result['value']
            field_type = fill_result['type']

            # 转义特殊字符
            escaped_value = str(value).replace('"', '\\"').replace('\n', '\\n')

            script_parts.append(f"    // 填写字段: {fill_result['label']}")

            if field_type in ['text', 'email', 'tel', 'password', 'url', 'number', 'textarea']:
                script_parts.append(f'    try {{')
                script_parts.append(f'        const elem_{len(script_parts)} = document.querySelector("{selector}");')
                script_parts.append(f'        if (elem_{len(script_parts)}) {{')
                script_parts.append(f'            elem_{len(script_parts)}.value = "{escaped_value}";')
                script_parts.append(f'            elem_{len(script_parts)}.dispatchEvent(new Event("input", {{bubbles: true}}));')
                script_parts.append(f'            elem_{len(script_parts)}.dispatchEvent(new Event("change", {{bubbles: true}}));')
                script_parts.append(f'        }}')
                script_parts.append(f'    }} catch(e) {{ console.warn("填写失败:", e); }}')

            elif field_type == 'select':
                script_parts.append(f'    try {{')
                script_parts.append(f'        const select_{len(script_parts)} = document.querySelector("{selector}");')
                script_parts.append(f'        if (select_{len(script_parts)}) {{')
                script_parts.append(f'            select_{len(script_parts)}.value = "{escaped_value}";')
                script_parts.append(f'            select_{len(script_parts)}.dispatchEvent(new Event("change", {{bubbles: true}}));')
                script_parts.append(f'        }}')
                script_parts.append(f'    }} catch(e) {{ console.warn("选择失败:", e); }}')

            elif field_type == 'checkbox':
                should_check = str(value).lower() in ['true', '是', '1', 'yes', 'on', '选中']
                script_parts.append(f'    try {{')
                script_parts.append(f'        const checkbox_{len(script_parts)} = document.querySelector("{selector}");')
                script_parts.append(f'        if (checkbox_{len(script_parts)}) {{')
                script_parts.append(f'            checkbox_{len(script_parts)}.checked = {str(should_check).lower()};')
                script_parts.append(f'            checkbox_{len(script_parts)}.dispatchEvent(new Event("change", {{bubbles: true}}));')
                script_parts.append(f'        }}')
                script_parts.append(f'    }} catch(e) {{ console.warn("复选框操作失败:", e); }}')

            script_parts.append("")

        script_parts.extend([
            "    console.log('✅ AI简历自动填写完成!');",
            "}",
            "",
            "// 执行填写",
            "autoFillForm();"
        ])

        return "\n".join(script_parts)

    async def close_browser(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("🔒 表单填写服务浏览器已关闭")


# 全局实例
form_filler_service = FormFillerService()
