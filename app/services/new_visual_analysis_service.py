"""
新视觉分析服务 - 视觉大模型+标签匹配方案主协调器

集成完整的新方案流程：
Phase 1: 网页截图
Phase 2: 完整字段信息提取 (form_field_extractor)
Phase 3: 视觉大模型语义理解 (visual_llm_service)
Phase 4: 智能标签匹配 (label_matching_service)
Phase 5: 精确填写执行 (form_filler_service)
"""

import logging
import json
from typing import Dict, List, Any, Optional
import os
from datetime import datetime

from .form_field_extractor import form_field_extractor
from .visual_llm_service import visual_llm_service
from .label_matching_service import label_matching_service
from .form_filler_service import form_filler_service

logger = logging.getLogger(__name__)


class NewVisualAnalysisService:
    """新视觉分析服务 - 主协调器"""

    def __init__(self):
        """初始化新视觉分析服务"""
        # 从环境变量获取DashScope API密钥
        dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
        if dashscope_api_key:
            visual_llm_service.api_key = dashscope_api_key
            import dashscope
            dashscope.api_key = dashscope_api_key
        else:
            logger.warning("⚠️ 未配置DASHSCOPE_API_KEY，视觉大模型功能将无法使用")

    async def analyze_and_fill_form(
        self,
        html_content: str,
        resume_data: Dict[str, Any],
        website_url: str = "",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的表单分析和填写流程

        Args:
            html_content: HTML页面内容
            resume_data: 简历数据
            website_url: 网站URL
            config: 配置参数

        Returns:
            完整的分析和填写结果
        """
        start_time = datetime.now()
        logger.info(f"🚀 开始新方案视觉分析流程: {website_url}")

        # 默认配置
        default_config = {
            'viewport_width': 1200,
            'viewport_height': 1400,
            'enable_form_filling': True,
            'save_screenshot': True,
            'save_analysis_result': True
        }
        final_config = {**default_config, **(config or {})}

        try:
            # Phase 1 & 2: 字段提取和截图
            logger.info("📋 Phase 2: 开始字段提取...")
            field_extraction_result = await form_field_extractor.extract_form_fields(
                html_content=html_content,
                viewport_width=final_config['viewport_width'],
                viewport_height=final_config['viewport_height']
            )

            if not field_extraction_result['success']:
                return {
                    'success': False,
                    'error': f"字段提取失败: {field_extraction_result.get('error', '未知错误')}",
                    'phase': 'field_extraction'
                }

            fields = field_extraction_result['fields']
            logger.info(f"✅ Phase 2完成: 提取到 {len(fields)} 个表单字段")

            # Phase 1: 网页截图（用于视觉分析）
            logger.info("📸 Phase 1: 开始网页截图...")
            screenshot_base64 = await visual_llm_service.take_screenshot(
                html_content=html_content,
                viewport_width=final_config['viewport_width'],
                viewport_height=final_config['viewport_height']
            )

            if not screenshot_base64:
                return {
                    'success': False,
                    'error': "网页截图失败",
                    'phase': 'screenshot'
                }

            logger.info("✅ Phase 1完成: 网页截图生成成功")

            # Phase 3: 视觉大模型语义理解
            logger.info("🧠 Phase 3: 开始视觉大模型分析...")
            field_labels = [field['label'] for field in fields if field.get('label')]

            llm_analysis_result = await visual_llm_service.analyze_with_visual_llm(
                screenshot_base64=screenshot_base64,
                resume_data=resume_data,
                field_labels=field_labels
            )

            if not llm_analysis_result['success']:
                return {
                    'success': False,
                    'error': f"视觉大模型分析失败: {llm_analysis_result.get('error', '未知错误')}",
                    'phase': 'visual_llm_analysis'
                }

            llm_field_mappings = llm_analysis_result['field_mappings']
            logger.info(f"✅ Phase 3完成: 大模型识别 {len(llm_field_mappings)} 个字段映射")

            # Phase 4: 智能标签匹配
            logger.info("🔍 Phase 4: 开始智能标签匹配...")
            matching_result = label_matching_service.match_fields(
                llm_field_mappings=llm_field_mappings,
                form_fields=fields
            )

            if not matching_result['success']:
                return {
                    'success': False,
                    'error': f"标签匹配失败: {matching_result.get('error', '未知错误')}",
                    'phase': 'label_matching'
                }

            matching_results = matching_result['matching_results']
            logger.info(f"✅ Phase 4完成: 成功匹配 {len(matching_results)} 个字段")

            # Phase 5: 表单填写执行（可选）
            fill_result = None
            if final_config['enable_form_filling'] and matching_results:
                logger.info("🖊️ Phase 5: 开始表单填写...")
                fill_result = await form_filler_service.fill_form(
                    html_content=html_content,
                    matching_results=matching_results,
                    viewport_width=final_config['viewport_width'],
                    viewport_height=final_config['viewport_height']
                )

                if fill_result['success']:
                    logger.info(f"✅ Phase 5完成: 成功填写 {fill_result['successful_fills']}/{fill_result['total_fields']} 个字段")
                else:
                    logger.warning(f"⚠️ Phase 5部分失败: {fill_result.get('error', '未知错误')}")

            # 统计最终结果
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()

            final_result = {
                'success': True,
                'website_url': website_url,
                'analysis_time': total_time,

                # Phase结果
                'phase_results': {
                    'phase1_screenshot': {
                        'success': True,
                        'screenshot_size': len(screenshot_base64) if screenshot_base64 else 0
                    },
                    'phase2_field_extraction': {
                        'success': field_extraction_result['success'],
                        'total_fields': len(fields),
                        'fields_preview': fields[:5]  # 前5个字段预览
                    },
                    'phase3_visual_llm': {
                        'success': llm_analysis_result['success'],
                        'recognized_fields': len(llm_field_mappings),
                        'confidence': llm_analysis_result.get('analysis_confidence', 0),
                        'field_mappings': llm_field_mappings
                    },
                    'phase4_label_matching': {
                        'success': matching_result['success'],
                        'matched_fields': len(matching_results),
                        'match_rate': matching_result['statistics']['match_rate'],
                        'matching_results': matching_results
                    },
                    'phase5_form_filling': fill_result if fill_result else {'skipped': True}
                },

                # 关键统计
                'statistics': {
                    'total_form_fields': len(fields),
                    'llm_recognized_fields': len(llm_field_mappings),
                    'successfully_matched_fields': len(matching_results),
                    'fill_success_rate': fill_result['fill_rate'] if fill_result else 0,
                    'overall_success_rate': len(matching_results) / len(fields) if fields else 0,
                    'analysis_time_seconds': total_time
                },

                # 可供扩展使用的脚本
                'fill_script': fill_result['fill_script'] if fill_result and fill_result.get('fill_script') else None,

                # 原始数据（调试用）
                'debug_info': {
                    'extracted_fields': fields,
                    'llm_raw_response': llm_analysis_result.get('raw_response', ''),
                    'unmatched_llm_fields': matching_result.get('unmatched_llm_fields', []),
                    'unmatched_form_fields': matching_result.get('unmatched_form_fields', [])
                }
            }

            # 生成总结报告
            success_rate = final_result['statistics']['overall_success_rate']
            if success_rate >= 0.8:
                status = "🎉 优秀"
            elif success_rate >= 0.6:
                status = "✅ 良好"
            elif success_rate >= 0.4:
                status = "⚠️ 一般"
            else:
                status = "❌ 较差"

            logger.info(f"""
🎯 新方案分析完成报告:
   📊 总体成功率: {success_rate:.1%} {status}
   ⏱️ 分析耗时: {total_time:.2f}秒
   📋 字段提取: {len(fields)}个
   🧠 大模型识别: {len(llm_field_mappings)}个
   🔍 成功匹配: {len(matching_results)}个
   🖊️ 填写成功: {fill_result['successful_fills'] if fill_result else 0}个
            """)

            return final_result

        except Exception as e:
            logger.error(f"❌ 新方案分析流程异常: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phase': 'unknown',
                'analysis_time': (datetime.now() - start_time).total_seconds()
            }

    async def analyze_form_structure_only(
        self,
        html_content: str,
        website_url: str = ""
    ) -> Dict[str, Any]:
        """
        仅分析表单结构，不进行填写（用于预览和调试）

        Args:
            html_content: HTML页面内容
            website_url: 网站URL

        Returns:
            表单结构分析结果
        """
        try:
            logger.info(f"🔍 开始表单结构分析: {website_url}")

            # 只执行Phase 2
            field_extraction_result = await form_field_extractor.extract_form_fields(html_content)

            if field_extraction_result['success']:
                fields = field_extraction_result['fields']

                # 按类型分组统计
                field_types = {}
                for field in fields:
                    field_type = field.get('type', 'unknown')
                    field_types[field_type] = field_types.get(field_type, 0) + 1

                return {
                    'success': True,
                    'website_url': website_url,
                    'total_fields': len(fields),
                    'field_types': field_types,
                    'fields': fields,
                    'html_analysis': field_extraction_result.get('html_analysis', {})
                }
            else:
                return {
                    'success': False,
                    'error': field_extraction_result.get('error', '字段提取失败')
                }

        except Exception as e:
            logger.error(f"❌ 表单结构分析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def close_all_browsers(self):
        """关闭所有浏览器实例"""
        try:
            await form_field_extractor.close_browser()
            await visual_llm_service.close_browser()
            await form_filler_service.close_browser()
            logger.info("🔒 所有浏览器实例已关闭")
        except Exception as e:
            logger.warning(f"⚠️ 关闭浏览器时出现异常: {str(e)}")


# 全局实例
new_visual_analysis_service = NewVisualAnalysisService()
