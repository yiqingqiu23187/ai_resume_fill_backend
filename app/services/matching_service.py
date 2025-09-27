"""
智能字段匹配服务模块
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog
from app.services.ai_service import AIService
from app.services.resume_service import ResumeService
from app.services.activation_service import ActivationService
from app.core.config import settings
from app.schemas.matching import (
    FormFieldSchema,
    FieldMatchResult
)

logger = logging.getLogger(__name__)


class MatchingService:
    """智能字段匹配服务类"""

    @staticmethod
    async def match_resume_fields(
        db: AsyncSession,
        user_id: UUID,
        resume_id: UUID,
        form_fields: List[FormFieldSchema],
        website_url: Optional[str] = None
    ) -> Tuple[bool, List[FieldMatchResult], str]:
        """
        匹配简历字段

        Args:
            db: 数据库会话
            user_id: 用户ID
            resume_id: 简历ID
            form_fields: 表单字段列表
            website_url: 网站URL

        Returns:
            Tuple[success, matches, error_message]
        """
        try:
            # 获取简历
            resume = await ResumeService.get_resume_by_id(db, resume_id, user_id)
            if not resume:
                return False, [], "简历未找到"

            # 提取简历文本
            resume_text = ResumeService.extract_resume_text(resume)
            if not resume_text.strip():
                return False, [], "简历内容为空"

            # 转换表单字段为字典格式
            form_fields_dict = [field.model_dump() for field in form_fields]

            logger.info(f"开始匹配简历字段，用户: {user_id}, 简历: {resume_id}, 字段数: {len(form_fields)}")

            # 调用AI服务进行匹配
            ai_success, ai_matches, ai_error = await AIService.match_form_fields(
                resume_text, form_fields_dict
            )

            if not ai_success:
                logger.error(f"AI匹配失败: {ai_error}")
                return False, [], ai_error

            # 转换AI匹配结果为Pydantic模型
            matches = []
            for match_data in ai_matches:
                try:
                    match_result = FieldMatchResult(**match_data)
                    matches.append(match_result)
                except Exception as e:
                    logger.warning(f"字段匹配结果格式错误: {e}, 数据: {match_data}")
                    continue

            # 记录使用日志
            await MatchingService._log_usage(
                db, user_id, website_url or "unknown",
                len(form_fields), len(matches)
            )

            # 🔧 扣减激活次数（开发环境跳过）
            if not settings.DEBUG:
                use_success, use_message = await ActivationService.use_activation(db, user_id)
                if not use_success:
                    logger.warning(f"激活次数扣减失败: {use_message}")
            else:
                logger.info("DEBUG模式：跳过激活次数检查")

            logger.info(f"字段匹配完成，匹配数量: {len(matches)}")
            return True, matches, ""

        except Exception as e:
            error_msg = f"字段匹配过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg


    @staticmethod
    async def _log_usage(
        db: AsyncSession,
        user_id: UUID,
        website_url: str,
        fields_count: int,
        success_count: int
    ):
        """记录使用日志"""
        try:
            usage_log = UsageLog(
                user_id=user_id,
                website_url=website_url,
                fields_count=fields_count,
                success_count=success_count
            )

            db.add(usage_log)
            await db.commit()

        except Exception as e:
            logger.error(f"记录使用日志失败: {str(e)}")
            # 不影响主流程，继续执行

    @staticmethod
    def validate_form_fields(form_fields: List[FormFieldSchema]) -> Tuple[bool, str]:
        """
        验证表单字段格式

        Args:
            form_fields: 表单字段列表

        Returns:
            Tuple[is_valid, error_message]
        """
        if not form_fields:
            return False, "表单字段不能为空"

        if len(form_fields) > 50:  # 限制字段数量
            return False, "表单字段数量不能超过50个"

        valid_field_types = {
            'text', 'select', 'date', 'email', 'tel', 'number',
            'textarea', 'radio', 'checkbox', 'url', 'password',
            'time', 'datetime-local', 'month', 'week', 'file'
        }

        for i, field in enumerate(form_fields):
            if not field.name.strip():
                return False, f"第{i+1}个字段名称不能为空"

            if field.type not in valid_field_types:
                return False, f"第{i+1}个字段类型'{field.type}'不支持"

            if field.type == 'select' and not field.options:
                return False, f"选择器字段'{field.name}'必须提供选项"

        return True, ""

    @staticmethod
    def format_match_results(
        matches: List[FieldMatchResult],
        total_fields: int
    ) -> Dict[str, Any]:
        """
        格式化匹配结果

        Args:
            matches: 匹配结果列表
            total_fields: 总字段数

        Returns:
            格式化的结果字典
        """
        matched_fields = len([m for m in matches if m.matched_value])
        match_rate = matched_fields / total_fields if total_fields > 0 else 0

        return {
            "total_fields": total_fields,
            "matched_fields": matched_fields,
            "match_rate": round(match_rate, 2),
            "matches": matches
        }

    @staticmethod
    async def analyze_html_with_llm(
        db: AsyncSession,
        user_id: UUID,
        resume_id: UUID,
        html_content: str,
        website_url: Optional[str] = None
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[Dict[str, Any]], str]:
        """
        🎯 使用大模型分析HTML表单结构并匹配简历数据

        Args:
            db: 数据库会话
            user_id: 用户ID
            resume_id: 简历ID
            html_content: 页面HTML内容
            website_url: 网站URL

        Returns:
            Tuple[success, analyzed_fields, form_structure, error_message]
        """
        try:
            logger.info(f"🔥 HTML分析请求开始 - 用户:{user_id}, 简历:{resume_id}, 网站:{website_url}, HTML长度:{len(html_content)}")

            # 获取简历数据
            logger.debug(f"📄 正在获取简历数据 - 用户:{user_id}, 简历:{resume_id}")
            resume = await ResumeService.get_resume_by_id(db, resume_id, user_id)
            if not resume:
                logger.warning(f"❌ 简历不存在 - 用户:{user_id}, 简历:{resume_id}")
                return False, [], None, "简历不存在"

            logger.info(f"✅ 成功获取简历数据 - 简历标题:{getattr(resume, 'title', '未知')}")

            # 🔧 检查并使用激活次数（开发环境跳过）
            if not settings.DEBUG:
                logger.debug(f"🔒 检查激活次数 - 用户:{user_id}")
                use_success, use_message = await ActivationService.use_activation(db, user_id)
                if not use_success:
                    logger.warning(f"❌ 激活次数不足 - 用户:{user_id}, 消息:{use_message}")
                    return False, [], None, f"使用次数不足: {use_message}"
                logger.info(f"✅ 激活次数检查通过 - 用户:{user_id}")
            else:
                logger.info("🔧 DEBUG模式：跳过激活次数检查")

            # 🎯 调用AI服务进行HTML分析
            logger.info(f"🤖 开始调用AI服务分析HTML - 用户:{user_id}")
            logger.debug(f"📊 简历内容类型:{type(resume.fields)}, 简历内容长度:{len(str(resume.fields)) if resume.fields else 0}")

            ai_result = await AIService.analyze_html_form_structure(
                html_content=html_content,
                resume_data=resume.fields,
                website_url=website_url
            )

            logger.info(f"🔄 AI服务调用完成 - 用户:{user_id}, 结果类型:{type(ai_result)}")
            logger.debug(f"📋 AI返回结果键:{list(ai_result.keys()) if isinstance(ai_result, dict) else 'Not a dict'}")

            if not ai_result.get("success", False):
                error_msg = ai_result.get("error", "AI分析失败")
                logger.error(f"❌ AI HTML分析失败 - 用户:{user_id}, 错误:{error_msg}")
                return False, [], None, error_msg

            analyzed_fields = ai_result.get("analyzed_fields", [])
            form_structure = ai_result.get("form_structure", {})

            logger.info(f"📊 AI分析成功 - 用户:{user_id}, 识别字段:{len(analyzed_fields)}个, 结构分组:{len(form_structure)}个")

            # 记录使用日志
            logger.debug(f"📝 开始记录使用日志 - 用户:{user_id}")
            try:
                matched_count = len([f for f in analyzed_fields if f.get('matched_value')])
                await MatchingService._log_usage(
                    db=db,
                    user_id=user_id,
                    website_url=website_url or "unknown",
                    fields_count=len(analyzed_fields),
                    success_count=matched_count
                )
                logger.debug(f"✅ 使用日志记录成功 - 用户:{user_id}")
            except Exception as log_error:
                logger.warning(f"⚠️ 使用日志记录失败 - 用户:{user_id}, 错误:{str(log_error)}")

            matched_count = len([f for f in analyzed_fields if f.get('matched_value')])
            logger.info(f"🎉 HTML分析完成 - 用户:{user_id}, 识别字段:{len(analyzed_fields)}个, 匹配字段:{matched_count}个")

            return True, analyzed_fields, form_structure, None

        except Exception as e:
            logger.error(f"❌ HTML分析异常 - 用户:{user_id}, 简历:{resume_id}, 异常类型:{type(e).__name__}, 异常信息:{str(e)}", exc_info=True)
            return False, [], None, f"系统错误: {str(e)}"
