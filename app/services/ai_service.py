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

    @staticmethod
    async def analyze_html_form_structure(
        html_content: str,
        resume_data: Dict[str, Any],
        website_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        🎯 使用大模型分析HTML表单结构并匹配简历数据

        Args:
            html_content: 页面HTML内容
            resume_data: 简历数据
            website_url: 网站URL

        Returns:
            分析结果字典
        """
        try:
            logger.info(f"🔥 AIService开始HTML分析 - HTML长度:{len(html_content)}, 简历数据类型:{type(resume_data)}")

            # 🎯 简化HTML - 只保留表单相关内容
            logger.debug(f"📄 开始HTML简化处理...")
            simplified_html = AIService._simplify_html_for_analysis(html_content)
            logger.info(f"✅ HTML简化完成 - 原长度:{len(html_content)}, 简化后:{len(simplified_html)}")

            # 构建分析提示词
            logger.debug(f"🔧 开始构建分析提示词...")
            try:
                prompt = AIService._build_html_analysis_prompt(simplified_html, resume_data, website_url)
                logger.info(f"✅ 提示词构建完成 - 长度:{len(prompt)}")
            except Exception as prompt_error:
                logger.error(f"❌ 提示词构建失败 - 错误:{str(prompt_error)}")
                raise prompt_error

            # 调用千问API
            logger.info(f"🤖 开始调用千问API - 模型:{settings.AI_MODEL}")
            logger.debug(f"🔑 API配置 - 有API密钥:{bool(settings.DASHSCOPE_API_KEY)}")

            try:
                logger.info("🌊 使用流式调用，避免超时问题...")

                # 使用流式调用
                responses = Generation.call(
                    model=settings.AI_MODEL,
                    prompt=prompt,
                    api_key=settings.DASHSCOPE_API_KEY,
                    stream=True  # 启用流式调用
                )

                # 收集流式响应
                ai_output = ""
                chunk_count = 0
                logger.debug("📡 开始接收流式数据...")

                for response in responses:
                    if response.status_code == 200:
                        # 流式输出：使用最新的完整内容，不是增量拼接
                        ai_output = response.output.text  # 直接赋值，不是累加
                        chunk_count += 1
                        # 只显示接收进度，不输出具体内容
                        if chunk_count % 5 == 0:  # 每5个chunk显示一次进度
                            logger.debug(f"📦 已接收 {chunk_count} 个数据块，当前总长度: {len(ai_output)}")
                    else:
                        error_msg = f"流式响应错误 - 状态码:{response.status_code}, 错误码:{getattr(response, 'code', 'unknown')}"
                        logger.error(f"❌ {error_msg}")
                        raise Exception(error_msg)

                logger.info(f"✅ 流式接收完成 - 共接收 {chunk_count} 个数据块，总输出长度:{len(ai_output)}")
                # 只在最后输出完整内容
                logger.info(f"📝 AI最终输出:\n{ai_output}")

                # 解析AI输出
                logger.debug(f"🔍 开始解析AI输出...")
                try:
                    result = AIService._parse_html_analysis_output(ai_output)
                    logger.info(f"🎉 AI输出解析完成 - 成功:{result.get('success', False)}")
                    return result
                except Exception as parse_error:
                    logger.error(f"❌ AI输出解析失败 - 错误:{str(parse_error)}")
                    return {"success": False, "error": f"输出解析失败: {str(parse_error)}"}

            except Exception as api_error:
                logger.error(f"❌ 流式API调用异常 - 错误类型:{type(api_error).__name__}, 错误信息:{str(api_error)}")
                raise api_error

        except Exception as e:
            error_msg = f"HTML分析过程异常 - 类型:{type(e).__name__}, 信息:{str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {"success": False, "error": error_msg}

    @staticmethod
    def _simplify_html_for_analysis(html_content: str) -> str:
        """
        🎯 智能表单提取：只保留表单相关的HTML片段
        """
        import time
        start_time = time.time()

        try:
            from bs4 import BeautifulSoup, Comment

            logger.info(f"🔄 开始智能表单提取 - HTML原始大小:{len(html_content)} 字符")

            # 🚨 超大HTML预检查
            if len(html_content) > 500000:  # 500KB
                logger.warning(f"⚠️ HTML过大({len(html_content)} 字符)，可能影响性能")
                # 可以考虑先做基础压缩
                html_content = AIService._basic_html_cleanup(html_content)
                logger.info(f"📉 预压缩后大小:{len(html_content)} 字符")

            # Step 1: 解析HTML
            parse_start = time.time()
            logger.debug("🔧 Step 1: 开始解析HTML...")
            soup = BeautifulSoup(html_content, 'html.parser')
            parse_time = time.time() - parse_start
            logger.info(f"✅ Step 1 完成: HTML解析耗时 {parse_time:.2f}秒")

            # Step 2: 清理无用元素
            cleanup_start = time.time()
            logger.debug("🔧 Step 2: 开始清理无用元素...")

            # 统计要删除的元素数量
            scripts = soup(['script', 'style', 'link', 'meta', 'noscript'])
            logger.debug(f"📋 发现无用元素: {len(scripts)} 个")

            for i, element in enumerate(scripts):
                if i % 50 == 0:  # 每50个元素输出进度
                    logger.debug(f"🗑️ 清理进度: {i}/{len(scripts)}")
                element.decompose()

            # 移除注释
            comments = soup(text=lambda text: isinstance(text, Comment))
            logger.debug(f"📋 发现注释: {len(comments)} 个")
            for comment in comments:
                comment.extract()

            cleanup_time = time.time() - cleanup_start
            logger.info(f"✅ Step 2 完成: 元素清理耗时 {cleanup_time:.2f}秒")

            # Step 3: 提取表单元素
            extract_start = time.time()
            logger.debug("🔧 Step 3: 开始提取表单元素...")
            form_elements = AIService._extract_form_elements_with_context(soup)
            extract_time = time.time() - extract_start
            logger.info(f"✅ Step 3 完成: 表单提取耗时 {extract_time:.2f}秒, 发现 {len(form_elements)} 个表单元素")

            if not form_elements:
                logger.warning("⚠️ 未发现表单元素，降级使用基础清理")
                return AIService._basic_html_cleanup(html_content)

            # 🚨 元素数量限制
            if len(form_elements) > 200:
                logger.warning(f"⚠️ 表单元素过多({len(form_elements)}个)，限制为前200个")
                form_elements = form_elements[:200]

            # Step 4: 重构HTML
            rebuild_start = time.time()
            logger.debug("🔧 Step 4: 开始重构HTML...")
            simplified_html = AIService._reconstruct_form_html(form_elements)
            rebuild_time = time.time() - rebuild_start
            logger.info(f"✅ Step 4 完成: HTML重构耗时 {rebuild_time:.2f}秒")

            # 总结
            total_time = time.time() - start_time
            compression_ratio = (1 - len(simplified_html) / len(html_content)) * 100
            logger.info(f"🎉 智能表单提取完成!")
            logger.info(f"📊 统计信息: 原长度:{len(html_content)}, 精简后:{len(simplified_html)}, 压缩率:{compression_ratio:.1f}%")
            logger.info(f"⏱️ 总耗时: {total_time:.2f}秒 (解析:{parse_time:.2f}s + 清理:{cleanup_time:.2f}s + 提取:{extract_time:.2f}s + 重构:{rebuild_time:.2f}s)")

            return simplified_html

        except ImportError as e:
            logger.warning(f"⚠️ BeautifulSoup未安装: {str(e)}，降级使用基础清理")
            return AIService._basic_html_cleanup(html_content)
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ 智能表单提取异常 (耗时:{total_time:.2f}秒): {type(e).__name__}: {str(e)}", exc_info=True)
            logger.warning("🔄 降级使用基础清理")
            return AIService._basic_html_cleanup(html_content)

    @staticmethod
    def _extract_form_elements_with_context(soup):
        """
        🔍 提取表单元素及其必要上下文
        """
        import time
        extract_start = time.time()
        form_data = []

        # Step 3.1: 查找所有表单相关元素
        find_start = time.time()
        logger.debug("🔍 Step 3.1: 查找表单元素...")
        form_elements = soup.find_all(['input', 'textarea', 'select', 'button'])
        find_time = time.time() - find_start

        logger.info(f"📋 Step 3.1 完成: 发现 {len(form_elements)} 个表单元素 (耗时:{find_time:.2f}秒)")

        # 🚨 元素数量预警
        if len(form_elements) > 500:
            logger.warning(f"⚠️ 表单元素数量较多({len(form_elements)}个)，处理可能较慢")

        valid_count = 0
        for i, element in enumerate(form_elements):
            # 进度日志
            if i % 20 == 0 and i > 0:
                elapsed = time.time() - extract_start
                logger.debug(f"🔄 处理进度: {i}/{len(form_elements)} ({(i/len(form_elements)*100):.1f}%) - 已耗时:{elapsed:.2f}秒")

            # 跳过不相关的按钮和隐藏元素
            if (element.name == 'input' and
                element.get('type') in ['button', 'submit', 'reset', 'hidden']):
                continue

            element_start = time.time()
            valid_count += 1

            element_data = {
                'element': element,
                'labels': [],
                'containers': [],
                'context_text': []
            }

            # Step 3.2: 查找关联的标签
            try:
                labels_start = time.time()
                element_data['labels'] = AIService._find_associated_labels(element, soup)
                labels_time = time.time() - labels_start

                if labels_time > 0.5:  # 如果单个标签查找超过0.5秒
                    logger.debug(f"⚠️ 标签查找较慢: 元素{valid_count} 耗时{labels_time:.2f}秒")

            except Exception as e:
                logger.warning(f"⚠️ 标签查找异常 - 元素{valid_count}: {str(e)}")
                element_data['labels'] = []

            # Step 3.3: 查找父级容器
            try:
                containers_start = time.time()
                element_data['containers'] = AIService._find_form_containers(element)
                containers_time = time.time() - containers_start

                if containers_time > 0.5:
                    logger.debug(f"⚠️ 容器查找较慢: 元素{valid_count} 耗时{containers_time:.2f}秒")

            except Exception as e:
                logger.warning(f"⚠️ 容器查找异常 - 元素{valid_count}: {str(e)}")
                element_data['containers'] = []

            # Step 3.4: 查找上下文文字
            try:
                context_start = time.time()
                element_data['context_text'] = AIService._find_context_text(element)
                context_time = time.time() - context_start

                if context_time > 0.5:
                    logger.debug(f"⚠️ 上下文查找较慢: 元素{valid_count} 耗时{context_time:.2f}秒")

            except Exception as e:
                logger.warning(f"⚠️ 上下文查找异常 - 元素{valid_count}: {str(e)}")
                element_data['context_text'] = []

            element_time = time.time() - element_start
            if element_time > 1.0:  # 单个元素处理超过1秒
                logger.debug(f"🐌 元素{valid_count}处理较慢: {element_time:.2f}秒 - {element.name}.{element.get('type', 'unknown')}")

            form_data.append(element_data)

            # 🚨 超时保护：如果处理时间过长，提前退出
            total_elapsed = time.time() - extract_start
            if total_elapsed > 30.0:  # 30秒超时
                logger.warning(f"⏰ 表单提取超时({total_elapsed:.2f}秒)，已处理{len(form_data)}/{len(form_elements)}个元素")
                break

        total_time = time.time() - extract_start
        logger.info(f"✅ 表单元素处理完成: {len(form_data)}/{len(form_elements)} 个有效元素 (总耗时:{total_time:.2f}秒)")

        return form_data

    @staticmethod
    def _find_associated_labels(element, soup):
        """查找与表单元素关联的标签"""
        labels = []

        try:
            # 方法1: 通过for属性查找 (最快速的方法)
            element_id = element.get('id')
            if element_id:
                label = soup.find('label', {'for': element_id})
                if label:
                    labels.append(label)

            # 方法2: 查找包裹的label (添加深度限制)
            parent = element.parent
            depth = 0
            max_depth = 10  # 最多向上查找10层

            while parent and parent.name != 'html' and depth < max_depth:
                if parent.name == 'label':
                    labels.append(parent)
                    break
                parent = parent.parent
                depth += 1

            # 如果达到最大深度，记录警告
            if depth >= max_depth:
                logger.debug(f"⚠️ 标签查找达到最大深度({max_depth})，可能存在复杂嵌套")

            # 方法3: 查找相邻的label (只在没找到时执行)
            if not labels:
                # 向前查找 (限制范围)
                prev_sibling = element.find_previous_sibling('label')
                if prev_sibling:
                    labels.append(prev_sibling)

                # 向后查找 (限制范围)
                next_sibling = element.find_next_sibling('label')
                if next_sibling:
                    labels.append(next_sibling)

        except Exception as e:
            logger.debug(f"标签查找异常: {str(e)}")

        return labels

    @staticmethod
    def _find_form_containers(element):
        """查找表单元素的容器层次"""
        containers = []

        try:
            # 向上查找重要的容器元素 (添加深度限制)
            parent = element.parent
            important_tags = {'form', 'fieldset', 'div', 'section', 'article', 'td', 'th', 'li'}
            depth = 0
            max_depth = 15  # 最多向上查找15层
            max_containers = 3  # 最多保留3个容器

            while (parent and parent.name != 'html' and
                   len(containers) < max_containers and depth < max_depth):

                if parent.name in important_tags:
                    # 只保留有意义的容器
                    if (parent.get('class') or parent.get('id') or
                        parent.name in {'form', 'fieldset', 'td', 'th'}):
                        containers.insert(0, parent)

                parent = parent.parent
                depth += 1

            # 如果达到最大深度，记录调试信息
            if depth >= max_depth:
                logger.debug(f"⚠️ 容器查找达到最大深度({max_depth})，可能存在深度嵌套")

        except Exception as e:
            logger.debug(f"容器查找异常: {str(e)}")

        return containers

    @staticmethod
    def _find_context_text(element):
        """查找元素周围的上下文文字"""
        context_texts = []

        try:
            # 查找相邻的文本节点 (添加数量限制)
            sibling_count = 0
            max_siblings = 5  # 最多检查5个兄弟元素

            # 向前查找
            for sibling in element.previous_siblings:
                if sibling_count >= max_siblings:
                    break

                if hasattr(sibling, 'get_text'):
                    text = sibling.get_text(strip=True)
                    if text and len(text) < 100:  # 避免过长的文本
                        context_texts.insert(0, text)
                        break
                sibling_count += 1

            # 向后查找
            sibling_count = 0
            for sibling in element.next_siblings:
                if sibling_count >= max_siblings:
                    break

                if hasattr(sibling, 'get_text'):
                    text = sibling.get_text(strip=True)
                    if text and len(text) < 100:
                        context_texts.append(text)
                        break
                sibling_count += 1

        except Exception as e:
            logger.debug(f"上下文文字查找异常: {str(e)}")

        return context_texts

    @staticmethod
    def _reconstruct_form_html(form_data):
        """
        🏗️ 重新构造精简的HTML结构
        """
        html_parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>']

        for data in form_data:
            element = data['element']

            # 构建容器结构
            container_html = AIService._build_container_html(data['containers'])
            html_parts.append(container_html['open'])

            # 添加标签
            for label in data['labels']:
                # 简化标签，只保留文本内容
                label_text = label.get_text(strip=True)
                if label_text:
                    html_parts.append(f'<label>{label_text}</label>')

            # 添加上下文文字
            for text in data['context_text']:
                html_parts.append(f'<span>{text}</span>')

            # 🎯 核心优化：简化表单元素
            simplified_element = AIService._simplify_form_element(element)
            html_parts.append(simplified_element)

            html_parts.append(container_html['close'])

        html_parts.append('</body></html>')

        return '\n'.join(html_parts)

    @staticmethod
    def _simplify_form_element(element):
        """
        🎯 极度简化表单元素，移除冗余信息
        """
        tag_name = element.name

        # 保留的重要属性
        important_attrs = ['id', 'name', 'type', 'placeholder', 'value', 'required']

        # 构建简化的属性
        attrs = []
        for attr in important_attrs:
            value = element.get(attr)
            if value and str(value).strip():
                # 截断过长的值
                if len(str(value)) > 50:
                    value = str(value)[:47] + "..."
                attrs.append(f'{attr}="{value}"')

        # 处理select元素的选项
        if tag_name == 'select':
            attr_str = ' ' + ' '.join(attrs) if attrs else ''
            options_html = AIService._simplify_select_options(element)
            return f'<{tag_name}{attr_str}>{options_html}</{tag_name}>'
        else:
            attr_str = ' ' + ' '.join(attrs) if attrs else ''
            return f'<{tag_name}{attr_str}/>'

    @staticmethod
    def _simplify_select_options(select_element):
        """
        🎯 极度简化select选项 - 只保留前3个和"其他"类选项
        """
        options = select_element.find_all('option')

        if len(options) <= 5:
            # 选项较少，全部保留但简化
            simplified_options = []
            for opt in options:
                value = opt.get('value', '')
                text = opt.get_text(strip=True)
                if text:
                    # 截断过长的值和文本
                    if len(value) > 30:
                        value = value[:27] + "..."
                    if len(text) > 20:
                        text = text[:17] + "..."
                    simplified_options.append(f'<option value="{value}">{text}</option>')
            return ''.join(simplified_options)
        else:
            # 选项很多，只保留代表性的
            simplified_options = []

            # 保留前3个选项
            for i, opt in enumerate(options[:3]):
                value = opt.get('value', '')[:20]  # 限制长度
                text = opt.get_text(strip=True)[:15]  # 限制长度
                if text:
                    simplified_options.append(f'<option value="{value}">{text}</option>')

            # 如果有很多选项，添加省略提示
            if len(options) > 3:
                simplified_options.append(f'<!-- ...还有{len(options)-3}个选项 -->')

                # 查找并保留"其他"、"请选择"等重要选项
                for opt in options[3:]:
                    text = opt.get_text(strip=True).lower()
                    if any(keyword in text for keyword in ['其他', '其它', '请选择', 'other', 'select']):
                        value = opt.get('value', '')[:20]
                        text = opt.get_text(strip=True)[:15]
                        simplified_options.append(f'<option value="{value}">{text}</option>')
                        break  # 只保留第一个匹配的

            return ''.join(simplified_options)

    @staticmethod
    def _build_container_html(containers):
        """构建容器的开启和关闭标签"""
        open_tags = []
        close_tags = []

        for container in containers:
            # 简化容器属性，只保留重要的class和id
            attrs = []
            if container.get('class'):
                class_str = ' '.join(container.get('class'))
                attrs.append(f'class="{class_str}"')
            if container.get('id'):
                attrs.append(f'id="{container.get("id")}"')

            attr_str = ' ' + ' '.join(attrs) if attrs else ''
            open_tags.append(f'<{container.name}{attr_str}>')
            close_tags.insert(0, f'</{container.name}>')

        return {
            'open': '\n'.join(open_tags),
            'close': '\n'.join(close_tags)
        }

    @staticmethod
    def _basic_html_cleanup(html_content: str) -> str:
        """基础HTML清理（降级方案）"""
        import re

        # 移除script和style标签
        html_content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html_content, flags=re.IGNORECASE)

        # 移除注释
        html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)

        # 压缩空白
        html_content = re.sub(r'\s+', ' ', html_content)

        # 限制长度
        if len(html_content) > 50000:
            html_content = html_content[:50000] + "..."
            logger.warning("HTML内容过长，已截断处理")

        return html_content.strip()

    @staticmethod
    def _build_html_analysis_prompt(
        html_content: str,
        resume_data: Dict[str, Any],
        website_url: Optional[str] = None
    ) -> str:
        """
        构建HTML分析的提示词
        """
        resume_text = json.dumps(resume_data, ensure_ascii=False, indent=2)

        prompt = f"""
你是一个专业的表单自动填写助手。你的任务是分析HTML表单，识别所有可填写的字段，并根据简历信息为每个字段提供合适的填写值，确保表单填写的完整性。

HTML表单内容：
```html
{html_content}
```

简历信息：
```json
{resume_text}
```

任务要求：
1. 识别所有需要用户填写的表单字段（input、select、textarea等）
2. 跳过以下类型的字段：
   - 隐藏字段(type="hidden")
   - 按钮(type="button/submit/reset")
   - 只读字段(readonly="true")
   - 文件上传(type="file")
3. 尽力为每个可填写字段匹配简历中的对应信息
4. 重要：只输出能够从简历中匹配到具体值的字段，如果简历中匹配不到相关信息，跳过该字段

输出JSON格式（直接输出数组，不要其他说明文字）：
[
  {{
    "name": "字段的name属性",
    "type": "字段类型(input/select/textarea)",
    "selector": "CSS选择器(使用属性选择器格式：[id='字段id'] 或 [name='字段name'])",
    "value": "匹配的填写值"
  }}
]

"""
        return prompt

    @staticmethod
    def _parse_html_analysis_output(ai_output: str) -> Dict[str, Any]:
        """
        解析AI HTML分析输出 - 简化版本
        """
        try:
            # 提取JSON部分
            import re
            json_start = ai_output.find('[')
            json_end = ai_output.rfind(']') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("AI输出中未找到有效的JSON数组")

            json_str = ai_output[json_start:json_end]
            fields_array = json.loads(json_str)

            # 验证和转换字段格式
            validated_fields = []
            for field in fields_array:
                if isinstance(field, dict) and field.get("name"):
                    validated_field = {
                        'name': field.get('name', ''),
                        'type': field.get('type', 'input'),  # 使用AI识别的类型
                        'label': field.get('name', ''),  # 使用name作为label
                        'selector': field.get('selector', f"[name='{field.get('name', '')}']"),  # 使用AI提供的选择器
                        'required': False,
                        'category': '其他',  # 简化分类
                        'matched_value': field.get('value', '')
                    }
                    validated_fields.append(validated_field)

            logger.info(f"HTML分析成功，识别字段数量: {len(validated_fields)}")

            return {
                "success": True,
                "analyzed_fields": validated_fields,
                "form_structure": {}  # 空的结构信息
            }

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            error_msg = f"AI HTML分析输出解析失败: {str(e)}"
            logger.error(f"{error_msg}, 原始输出前500字符: {ai_output[:500]}...")
            return {"success": False, "error": error_msg}
