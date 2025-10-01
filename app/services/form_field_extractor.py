"""
表单字段提取服务 - 新方案Phase 2
复用现有字段提取优秀逻辑，移除复杂的视觉分析算法

负责从HTML页面中提取表单字段的完整信息：
- selector: CSS选择器
- type: 字段类型
- label: 显示标签
- required: 是否必填
- options: 选择类型的选项（仅select有值）
"""

import logging
from typing import Dict, List, Any, Optional
import json
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class FormFieldExtractor:
    """表单字段提取器 - 简化高效版本"""

    def __init__(self):
        """初始化字段提取器"""
        self._browser: Optional[Browser] = None

        # 表单元素选择器配置
        self.form_element_selectors = [
            'input:not([type="hidden"])',
            'textarea',
            'select',
            'button[type="submit"]',
            'input[type="submit"]',
            '[contenteditable="true"]'
        ]

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
            logger.info("🚀 字段提取器浏览器启动成功")
        return self._browser

    async def extract_form_fields(
        self,
        html_content: str,
        viewport_width: int = 1200,
        viewport_height: int = 1400
    ) -> Dict[str, Any]:
        """
        提取表单字段信息

        Args:
            html_content: HTML页面内容
            viewport_width: 视口宽度
            viewport_height: 视口高度

        Returns:
            包含字段信息的字典
        """
        try:
            # 静态HTML分析
            html_analysis = self._analyze_html_structure(html_content)
            logger.info(f"📄 HTML静态分析完成: {html_analysis.get('total_form_elements', 0)}个表单元素")

            # 动态字段提取
            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={'width': viewport_width, 'height': viewport_height}
            )

            # 设置页面内容
            await page.set_content(html_content, wait_until='networkidle')
            await page.wait_for_timeout(2000)  # 等待页面加载

            # 注入字段提取脚本
            field_extraction_script = """
            () => {
                const results = {
                    fields: [],
                    metadata: {
                        viewport: {
                            width: window.innerWidth,
                            height: window.innerHeight
                        },
                        timestamp: new Date().toISOString(),
                        total_processed: 0
                    }
                };

                // 表单元素选择器
                const formSelectors = [
                    'input:not([type="hidden"])',
                    'textarea',
                    'select',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    '[contenteditable="true"]'
                ];

                // 生成唯一CSS选择器
                function generateUniqueSelector(element) {
                    // 优先级：id > name > class
                    if (element.id) {
                        return `#${element.id}`;
                    }

                    if (element.name) {
                        return `${element.tagName.toLowerCase()}[name="${element.name}"]`;
                    }

                    if (element.className) {
                        const classes = element.className.trim().split(/\\s+/).slice(0, 2);
                        if (classes.length > 0) {
                            return `${element.tagName.toLowerCase()}.${classes.join('.')}`;
                        }
                    }

                    // 使用nth-child作为fallback
                    const siblings = Array.from(element.parentElement?.children || []);
                    const index = siblings.indexOf(element) + 1;
                    return `${element.tagName.toLowerCase()}:nth-child(${index})`;
                }

                // 智能标签关联算法
                function findAssociatedLabels(element) {
                    const labels = [];

                    // 辅助函数：清理标签文本
                    function cleanLabelText(text) {
                        if (!text) return '';
                        return text
                            .replace(/[\\r\\n\\t]+/g, ' ')     // 替换换行符和制表符
                            .replace(/[*:：\\s]+$/g, '')       // 移除末尾的星号、冒号、空格
                            .replace(/^\\s*[*]\\s*/, '')       // 移除开头的星号
                            .replace(/\\s+/g, ' ')             // 合并多个空格
                            .replace(/必填|选填|可选/g, '')     // 移除必填提示
                            .trim();
                    }

                    // 辅助函数：验证标签文本有效性
                    function isValidLabelText(text) {
                        if (!text || text.length < 2 || text.length > 30) return false;

                        // 过滤无效模式
                        const invalidPatterns = [
                            /^请选择$/, /^--请选择--$/, /^请输入.*[！!]$/,
                            /^选择文件$/, /^未选择文件$/, /^浏览$/,
                            /^提交$/, /^保存$/, /^取消$/, /^确定$/, /^重置$/,
                            /^\\d+$/, /^[a-zA-Z]+$/
                        ];

                        return !invalidPatterns.some(pattern => pattern.test(text));
                    }

                    // 1. 通过for属性关联（最可靠）
                    if (element.id) {
                        const forLabels = document.querySelectorAll(`label[for="${element.id}"]`);
                        forLabels.forEach(label => {
                            const text = cleanLabelText(label.textContent);
                            if (isValidLabelText(text)) {
                                labels.push({
                                    text: text,
                                    association_type: 'for_attribute',
                                    priority: 1
                                });
                            }
                        });
                    }

                    // 2. 父级label元素
                    let parent = element.parentElement;
                    let depth = 0;
                    while (parent && parent !== document.body && depth < 3) {
                        if (parent.tagName.toLowerCase() === 'label') {
                            const labelText = parent.textContent;
                            const inputText = element.value || element.placeholder || '';
                            const cleanText = cleanLabelText(labelText.replace(inputText, ''));
                            if (isValidLabelText(cleanText)) {
                                labels.push({
                                    text: cleanText,
                                    association_type: 'parent_label',
                                    priority: 2
                                });
                            }
                            break;
                        }
                        parent = parent.parentElement;
                        depth++;
                    }

                    // 3. UI框架模式识别

                    // Ant Design
                    const antFormItem = element.closest('.ant-form-item');
                    if (antFormItem) {
                        const antLabel = antFormItem.querySelector('.ant-form-item-label label');
                        if (antLabel) {
                            const text = cleanLabelText(antLabel.textContent);
                            if (isValidLabelText(text)) {
                                labels.push({
                                    text: text,
                                    association_type: 'antd_framework',
                                    priority: 3
                                });
                            }
                        }
                    }

                    // Element UI
                    const elFormItem = element.closest('.el-form-item');
                    if (elFormItem) {
                        const elLabel = elFormItem.querySelector('.el-form-item__label');
                        if (elLabel) {
                            const text = cleanLabelText(elLabel.textContent);
                            if (isValidLabelText(text)) {
                                labels.push({
                                    text: text,
                                    association_type: 'element_ui_framework',
                                    priority: 3
                                });
                            }
                        }
                    }

                    // 通用form-item模式
                    const formItem = element.closest('[class*="form-item"], [class*="field"], [class*="input-group"]');
                    if (formItem) {
                        const possibleLabels = formItem.querySelectorAll('label, [class*="label"]');
                        possibleLabels.forEach(label => {
                            if (label !== element && !label.contains(element)) {
                                const text = cleanLabelText(label.textContent);
                                if (isValidLabelText(text)) {
                                    labels.push({
                                        text: text,
                                        association_type: 'form_item_pattern',
                                        priority: 4
                                    });
                                }
                            }
                        });
                    }

                    // 4. 兄弟元素标签
                    let sibling = element.previousElementSibling;
                    let siblingCount = 0;
                    while (sibling && siblingCount < 2) {
                        const text = cleanLabelText(sibling.textContent);
                        if (isValidLabelText(text)) {
                            labels.push({
                                text: text,
                                association_type: 'sibling_text',
                                priority: 5 + siblingCount
                            });
                        }
                        sibling = sibling.previousElementSibling;
                        siblingCount++;
                    }

                    // 5. 元素属性作为fallback
                    ['placeholder', 'title', 'aria-label', 'name'].forEach((attr, index) => {
                        const value = element.getAttribute(attr);
                        if (value && value.trim()) {
                            const text = cleanLabelText(value);
                            if (isValidLabelText(text)) {
                                labels.push({
                                    text: text,
                                    association_type: 'element_attribute',
                                    priority: 10 + index
                                });
                            }
                        }
                    });

                    // 排序并去重，保留最佳标签
                    const uniqueLabels = [];
                    const seenTexts = new Set();

                    labels
                        .sort((a, b) => a.priority - b.priority)
                        .forEach(label => {
                            if (!seenTexts.has(label.text)) {
                                seenTexts.add(label.text);
                                uniqueLabels.push({
                                    text: label.text,
                                    association_type: label.association_type
                                });
                            }
                        });

                    return uniqueLabels.slice(0, 3); // 最多保留3个最佳标签
                }

                // 提取表单元素
                formSelectors.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach((element, index) => {
                            // 跳过不可见元素
                            const rect = element.getBoundingClientRect();
                            const style = window.getComputedStyle(element);

                            if (rect.width === 0 || rect.height === 0 ||
                                style.display === 'none' || style.visibility === 'hidden') {
                                return;
                            }

                            const fieldData = {
                                selector: generateUniqueSelector(element),
                                type: element.type || element.tagName.toLowerCase(),
                                label: '', // 将在后面设置
                                required: element.required || false,
                                name: element.name || '',
                                id: element.id || '',
                                placeholder: element.placeholder || '',
                                value: element.value || '',
                                disabled: element.disabled || false,
                                readonly: element.readOnly || false,
                                associated_labels: findAssociatedLabels(element)
                            };

                            // 设置主标签（选择最佳标签）
                            if (fieldData.associated_labels.length > 0) {
                                fieldData.label = fieldData.associated_labels[0].text;
                            } else if (fieldData.placeholder) {
                                fieldData.label = fieldData.placeholder;
                            } else if (fieldData.name) {
                                fieldData.label = fieldData.name;
                            } else {
                                fieldData.label = `${fieldData.type}_${index + 1}`;
                            }

                            // 针对select元素，提取选项信息
                            if (element.tagName.toLowerCase() === 'select') {
                                fieldData.options = Array.from(element.options).map(option => ({
                                    value: option.value,
                                    text: option.text.trim(),
                                    selected: option.selected
                                }));
                            } else {
                                fieldData.options = [];
                            }

                            // 针对radio/checkbox，识别分组
                            if (['radio', 'checkbox'].includes(fieldData.type) && fieldData.name) {
                                const groupElements = document.querySelectorAll(`input[name="${fieldData.name}"]`);
                                if (groupElements.length > 1) {
                                    fieldData.group_options = Array.from(groupElements).map(elem => {
                                        const label = elem.nextElementSibling;
                                        return {
                                            value: elem.value,
                                            text: label ? label.textContent.trim() : elem.value,
                                            checked: elem.checked
                                        };
                                    });
                                }
                            }

                            results.fields.push(fieldData);
                            results.metadata.total_processed++;
                        });
                    } catch (error) {
                        console.warn('提取元素时出错:', selector, error);
                    }
                });

                return results;
            }
            """

            # 执行脚本获取字段数据
            field_data = await page.evaluate(field_extraction_script)
            await page.close()

            logger.info(f"✅ 字段提取完成: 成功提取 {len(field_data['fields'])} 个表单字段")

            return {
                'success': True,
                'fields': field_data['fields'],
                'metadata': field_data['metadata'],
                'html_analysis': html_analysis,
                'total_fields': len(field_data['fields'])
            }

        except Exception as e:
            logger.error(f"❌ 字段提取失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fields': [],
                'total_fields': 0
            }

    def _analyze_html_structure(self, html_content: str) -> Dict[str, Any]:
        """
        静态分析HTML结构，提取基本信息

        Args:
            html_content: HTML页面内容

        Returns:
            包含HTML结构分析结果的字典
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 统计表单元素
            form_elements = []
            for selector in ['input', 'textarea', 'select', 'button']:
                elements = soup.find_all(selector)
                for elem in elements:
                    if elem.get('type') not in ['hidden', 'script']:
                        element_info = {
                            'tag': elem.name,
                            'type': elem.get('type', 'text'),
                            'name': elem.get('name', ''),
                            'id': elem.get('id', ''),
                            'class': ' '.join(elem.get('class', [])),
                            'placeholder': elem.get('placeholder', ''),
                            'required': elem.has_attr('required')
                        }
                        form_elements.append(element_info)

            return {
                'total_form_elements': len(form_elements),
                'has_forms': len(soup.find_all('form')) > 0,
                'page_title': soup.title.string if soup.title else '',
                'form_elements_preview': form_elements[:10]
            }

        except Exception as e:
            logger.warning(f"⚠️ HTML结构分析出错: {str(e)}")
            return {'error': str(e)}

    async def close_browser(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("🔒 字段提取器浏览器已关闭")


# 全局实例
form_field_extractor = FormFieldExtractor()
