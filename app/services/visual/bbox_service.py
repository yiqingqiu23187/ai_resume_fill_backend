"""
BBOX提取服务模块

负责从HTML页面中提取表单元素的精确边界框坐标信息
"""

import logging
from typing import Dict, List, Any, Optional, Set
import json
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class BBoxService:
    """表单元素边界框提取服务类"""

    def __init__(self):
        """初始化BBOX提取服务"""
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

        # 标签元素选择器配置
        self.label_selectors = [
            'label',
            '.label',
            '.field-label',
            '.form-label',
            '[for]',  # 任何具有for属性的元素
        ]

        # 需要忽略的元素类型
        self.ignore_types = {
            'hidden', 'script', 'style', 'noscript'
        }

    async def _get_browser(self) -> Browser:
        """
        获取或创建浏览器实例（复用连接）
        """
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
            logger.info("🚀 BBOX服务浏览器启动成功")
        return self._browser

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

            # 统计各类元素
            form_elements = []
            for selector in self.form_element_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    # 跳过隐藏元素
                    if elem.get('type') in self.ignore_types:
                        continue

                    element_info = {
                        'tag': elem.name,
                        'type': elem.get('type', 'text'),
                        'name': elem.get('name', ''),
                        'id': elem.get('id', ''),
                        'class': ' '.join(elem.get('class', [])),
                        'placeholder': elem.get('placeholder', ''),
                        'value': elem.get('value', ''),
                        'required': elem.has_attr('required'),
                        'text_content': elem.get_text(strip=True)[:100]  # 限制长度
                    }
                    form_elements.append(element_info)

            # 统计标签元素
            label_elements = []
            for selector in self.label_selectors:
                labels = soup.select(selector)
                for label in labels:
                    label_info = {
                        'tag': label.name,
                        'for': label.get('for', ''),
                        'text_content': label.get_text(strip=True),
                        'class': ' '.join(label.get('class', []))
                    }
                    label_elements.append(label_info)

            return {
                'total_form_elements': len(form_elements),
                'total_labels': len(label_elements),
                'form_elements_preview': form_elements[:10],  # 预览前10个
                'labels_preview': label_elements[:10],
                'has_forms': len(soup.find_all('form')) > 0,
                'page_title': soup.title.string if soup.title else ''
            }

        except Exception as e:
            logger.warning(f"⚠️ HTML结构分析出错: {str(e)}")
            return {'error': str(e)}

    async def extract_element_bboxes(
        self,
        html_content: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080
    ) -> Dict[str, Any]:
        """
        提取所有表单元素的边界框坐标

        Args:
            html_content: HTML页面内容
            viewport_width: 视窗宽度
            viewport_height: 视窗高度

        Returns:
            包含所有元素BBOX信息的字典
        """
        try:
            # 首先进行静态HTML分析
            html_analysis = self._analyze_html_structure(html_content)
            logger.info(f"📋 HTML分析完成: 发现 {html_analysis.get('total_form_elements', 0)} 个表单元素")

            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={'width': viewport_width, 'height': viewport_height}
            )

            # 设置页面内容
            await page.set_content(html_content, wait_until='networkidle')
            await page.wait_for_timeout(3000)  # 等待页面完全加载

            # 注入BBOX提取脚本
            bbox_script = """
            () => {
                const results = {
                    elements: [],
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollWidth: document.documentElement.scrollWidth,
                        scrollHeight: document.documentElement.scrollHeight
                    },
                    timestamp: new Date().toISOString()
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

                // 标签选择器
                const labelSelectors = [
                    'label',
                    '.label',
                    '.field-label',
                    '.form-label'
                ];

                // 生成唯一选择器
                function generateUniqueSelector(element) {
                    let selector = element.tagName.toLowerCase();

                    if (element.id) {
                        return `#${element.id}`;
                    }

                    if (element.name) {
                        selector += `[name="${element.name}"]`;
                    } else if (element.className) {
                        const classes = element.className.trim().split(/\s+/).slice(0, 2);
                        if (classes.length > 0) {
                            selector += '.' + classes.join('.');
                        }
                    }

                    return selector;
                }

                // 增强的标签关联查找函数
                function findAssociatedLabels(element) {
                    const labels = [];

                    // 辅助函数：清理标签文本
                    function cleanLabelText(text) {
                        if (!text) return '';
                        return text
                            .replace(/[*:：\\s]+$/g, '') // 移除末尾的星号、冒号、空格
                            .replace(/^\\s*[*]\\s*/, '') // 移除开头的星号
                            .replace(/\\s+/g, ' ')      // 合并多个空格
                            .replace(/必填|选填|可选/g, '') // 移除必填提示
                            .trim();
                    }

                    // 辅助函数：添加标签（避免重复）
                    function addLabel(text, type) {
                        const cleanText = cleanLabelText(text);
                        if (cleanText && cleanText.length >= 2 && cleanText.length <= 50) {
                            // 检查是否已存在相同文本
                            const exists = labels.some(label => label.text === cleanText);
                            if (!exists) {
                                labels.push({
                                    text: cleanText,
                                    association_type: type
                                });
                            }
                        }
                    }

                    // 1. 通过for属性关联 (最可靠)
                    if (element.id) {
                        const forLabels = document.querySelectorAll(`label[for="${element.id}"]`);
                        forLabels.forEach(label => {
                            addLabel(label.textContent, 'for_attribute');
                        });
                    }

                    // 2. 父级label元素
                    let parent = element.parentElement;
                    let depth = 0;
                    while (parent && parent !== document.body && depth < 5) {
                        if (parent.tagName.toLowerCase() === 'label') {
                            // 排除input自身的文本
                            const labelText = parent.textContent;
                            const inputText = element.value || element.placeholder || '';
                            const cleanText = labelText.replace(inputText, '');
                            addLabel(cleanText, 'parent_label');
                            break;
                        }
                        parent = parent.parentElement;
                        depth++;
                    }

                    // 3. UI框架特殊结构识别

                    // Ant Design 框架模式
                    const antFormItem = element.closest('.ant-form-item');
                    if (antFormItem) {
                        const antLabel = antFormItem.querySelector('.ant-form-item-label label');
                        if (antLabel) {
                            addLabel(antLabel.textContent, 'antd_framework');
                        }
                    }

                    // Element UI 框架模式
                    const elFormItem = element.closest('.el-form-item');
                    if (elFormItem) {
                        const elLabel = elFormItem.querySelector('.el-form-item__label');
                        if (elLabel) {
                            addLabel(elLabel.textContent, 'element_ui_framework');
                        }
                    }

                    // iView/View UI 框架模式
                    const ivuFormItem = element.closest('.ivu-form-item');
                    if (ivuFormItem) {
                        const ivuLabel = ivuFormItem.querySelector('.ivu-form-item-label');
                        if (ivuLabel) {
                            addLabel(ivuLabel.textContent, 'iview_framework');
                        }
                    }

                    // 通用form-item模式
                    const genericFormItem = element.closest('[class*="form-item"], [class*="field"], [class*="input-group"], [class*="form-group"]');
                    if (genericFormItem) {
                        const possibleLabels = genericFormItem.querySelectorAll('label, [class*="label"], .control-label');
                        possibleLabels.forEach(label => {
                            if (label !== element && !label.contains(element)) {
                                addLabel(label.textContent, 'form_item_pattern');
                            }
                        });
                    }

                    // 4. 邻近的标签文本（前面的兄弟元素）
                    let sibling = element.previousElementSibling;
                    let siblingCount = 0;
                    while (sibling && siblingCount < 3) {
                        const text = sibling.textContent.trim();
                        if (text && text.length < 50 && !text.includes('\\n')) {
                            addLabel(text, 'sibling_text');
                        }
                        sibling = sibling.previousElementSibling;
                        siblingCount++;
                    }

                    // 5. 表格结构中的标签 (td前面的th或td)
                    const cell = element.closest('td');
                    if (cell) {
                        // 检查同行的前一个单元格
                        const prevCell = cell.previousElementSibling;
                        if (prevCell) {
                            addLabel(prevCell.textContent, 'table_header');
                        }

                        // 检查对应的表头
                        const table = cell.closest('table');
                        if (table) {
                            const cellIndex = Array.from(cell.parentElement.children).indexOf(cell);
                            const headerRow = table.querySelector('thead tr, tr:first-child');
                            if (headerRow) {
                                const headerCell = headerRow.children[cellIndex];
                                if (headerCell) {
                                    addLabel(headerCell.textContent, 'table_header');
                                }
                            }
                        }
                    }

                    // 6. 查找附近的文本节点
                    function findNearbyTextNodes(element, maxDistance = 3) {
                        const textNodes = [];
                        let parent = element.parentElement;

                        for (let i = 0; i < maxDistance && parent; i++) {
                            const walker = document.createTreeWalker(
                                parent,
                                NodeFilter.SHOW_TEXT,
                                {
                                    acceptNode: (node) => {
                                        const text = node.textContent.trim();
                                        return text && text.length > 1 && text.length < 30 ?
                                            NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
                                    }
                                }
                            );

                            let node;
                            while (node = walker.nextNode()) {
                                if (!element.contains(node)) {
                                    textNodes.push(node);
                                }
                            }
                            parent = parent.parentElement;
                        }
                        return textNodes;
                    }

                    const nearbyTextNodes = findNearbyTextNodes(element);
                    nearbyTextNodes.forEach(node => {
                        addLabel(node.textContent, 'nearby_text');
                    });

                    // 7. 使用元素属性作为fallback
                    if (labels.length === 0) {
                        const attrLabel = element.placeholder || element.title || element.getAttribute('data-label') || element.getAttribute('aria-label');
                        if (attrLabel) {
                            addLabel(attrLabel, 'element_attribute');
                        }
                    }

                    return labels;
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

                            const elementData = {
                                selector: generateUniqueSelector(element),
                                tag: element.tagName.toLowerCase(),
                                type: element.type || 'text',
                                name: element.name || '',
                                id: element.id || '',
                                class: element.className || '',
                                placeholder: element.placeholder || '',
                                value: element.value || '',
                                text_content: element.textContent ? element.textContent.trim().substring(0, 100) : '',
                                required: element.required || false,
                                disabled: element.disabled || false,
                                readonly: element.readOnly || false,
                                bbox: {
                                    x: Math.round(rect.left + window.scrollX),
                                    y: Math.round(rect.top + window.scrollY),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                    left: Math.round(rect.left),
                                    top: Math.round(rect.top),
                                    right: Math.round(rect.right),
                                    bottom: Math.round(rect.bottom)
                                },
                                associated_labels: findAssociatedLabels(element),
                                element_index: index
                            };

                            // 针对select元素，提取选项信息
                            if (element.tagName.toLowerCase() === 'select') {
                                elementData.options = Array.from(element.options).map(option => ({
                                    value: option.value,
                                    text: option.text,
                                    selected: option.selected
                                }));
                            }

                            results.elements.push(elementData);
                        });
                    } catch (error) {
                        console.warn('提取元素时出错:', selector, error);
                    }
                });

                return results;
            }
            """

            # 执行脚本获取BBOX数据
            bbox_data = await page.evaluate(bbox_script)
            await page.close()

            # 合并结果
            final_result = {
                'success': True,
                'html_analysis': html_analysis,
                'bbox_data': bbox_data,
                'total_elements': len(bbox_data['elements']),
                'viewport_info': bbox_data['viewport'],
                'extraction_timestamp': bbox_data['timestamp']
            }

            logger.info(f"📊 BBOX提取完成: 成功提取 {len(bbox_data['elements'])} 个元素的坐标信息")

            return final_result

        except Exception as e:
            logger.error(f"❌ BBOX提取失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'html_analysis': html_analysis if 'html_analysis' in locals() else {}
            }

    def analyze_element_relationships(self, bbox_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析元素之间的空间关系

        Args:
            bbox_data: BBOX提取结果

        Returns:
            元素关系分析结果
        """
        try:
            if not bbox_data.get('success') or not bbox_data.get('bbox_data'):
                return {'error': 'Invalid bbox_data'}

            elements = bbox_data['bbox_data']['elements']
            relationships = []

            for i, elem1 in enumerate(elements):
                for j, elem2 in enumerate(elements):
                    if i >= j:  # 避免重复计算
                        continue

                    bbox1 = elem1['bbox']
                    bbox2 = elem2['bbox']

                    # 计算距离
                    center1_x = bbox1['x'] + bbox1['width'] / 2
                    center1_y = bbox1['y'] + bbox1['height'] / 2
                    center2_x = bbox2['x'] + bbox2['width'] / 2
                    center2_y = bbox2['y'] + bbox2['height'] / 2

                    distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5

                    # 判断空间关系
                    relationship = self._determine_spatial_relationship(bbox1, bbox2)

                    if distance < 200:  # 只记录距离较近的元素关系
                        relationships.append({
                            'element1_selector': elem1['selector'],
                            'element2_selector': elem2['selector'],
                            'distance': round(distance, 2),
                            'relationship': relationship,
                            'alignment': self._check_alignment(bbox1, bbox2)
                        })

            return {
                'total_relationships': len(relationships),
                'close_relationships': [r for r in relationships if r['distance'] < 100],
                'aligned_elements': [r for r in relationships if r['alignment'] != 'none'],
                'summary': {
                    'nearby_pairs': len([r for r in relationships if r['distance'] < 50]),
                    'aligned_pairs': len([r for r in relationships if r['alignment'] != 'none']),
                    'vertical_groups': len([r for r in relationships if r['alignment'] == 'vertical'])
                }
            }

        except Exception as e:
            logger.error(f"❌ 元素关系分析失败: {str(e)}")
            return {'error': str(e)}

    def _determine_spatial_relationship(self, bbox1: Dict, bbox2: Dict) -> str:
        """
        判断两个元素的空间关系
        """
        # 垂直关系判断
        if bbox1['bottom'] < bbox2['top']:
            return 'above'
        elif bbox1['top'] > bbox2['bottom']:
            return 'below'
        # 水平关系判断
        elif bbox1['right'] < bbox2['left']:
            return 'left_of'
        elif bbox1['left'] > bbox2['right']:
            return 'right_of'
        # 重叠关系
        else:
            return 'overlapping'

    def _check_alignment(self, bbox1: Dict, bbox2: Dict) -> str:
        """
        检查两个元素的对齐关系
        """
        # 垂直对齐（左边缘对齐）
        if abs(bbox1['left'] - bbox2['left']) < 10:
            return 'vertical'
        # 水平对齐（顶部对齐）
        elif abs(bbox1['top'] - bbox2['top']) < 10:
            return 'horizontal'
        # 中心对齐
        elif (abs((bbox1['left'] + bbox1['width']/2) - (bbox2['left'] + bbox2['width']/2)) < 10 or
              abs((bbox1['top'] + bbox1['height']/2) - (bbox2['top'] + bbox2['height']/2)) < 10):
            return 'center'
        else:
            return 'none'

    async def close(self):
        """
        关闭浏览器连接
        """
        if self._browser and self._browser.is_connected():
            await self._browser.close()
            logger.info("🔒 BBOX服务浏览器已关闭")


# 全局BBOX服务实例
bbox_service = BBoxService()
