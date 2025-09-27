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
from app.schemas.matching import (
    FormFieldSchema,
    FieldMatchResult,
    NestedFormStructure
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

            # 扣减激活次数
            use_success, use_message = await ActivationService.use_activation(db, user_id)
            if not use_success:
                logger.warning(f"激活次数扣减失败: {use_message}")

            logger.info(f"字段匹配完成，匹配数量: {len(matches)}")
            return True, matches, ""

        except Exception as e:
            error_msg = f"字段匹配过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg

    @staticmethod
    async def match_nested_form_fields(
        db: AsyncSession,
        user_id: UUID,
        resume_id: UUID,
        form_structure: NestedFormStructure,
        website_url: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any], int, int, str]:
        """
        匹配嵌套表单结构

        Args:
            db: 数据库会话
            user_id: 用户ID
            resume_id: 简历ID
            form_structure: 嵌套表单结构
            website_url: 网站URL

        Returns:
            Tuple[success, matched_data, total_fields, matched_fields, error_message]
        """
        try:
            # 获取简历
            resume = await ResumeService.get_resume_by_id(db, resume_id, user_id)
            if not resume:
                return False, {}, 0, 0, "简历未找到"

            # 提取简历文本和结构化数据
            resume_text = ResumeService.extract_resume_text(resume)
            resume_data = resume.fields if hasattr(resume, 'fields') else {}

            if not resume_text.strip() and not resume_data:
                return False, {}, 0, 0, "简历内容为空"

            logger.info(f"开始匹配嵌套表单结构，用户: {user_id}, 简历: {resume_id}")

            # 调用AI服务进行嵌套匹配
            ai_success, matched_data, ai_error = await AIService.match_nested_form_fields(
                resume_text=resume_text,
                resume_data=resume_data,
                form_structure=form_structure.model_dump()
            )

            if not ai_success:
                logger.error(f"AI嵌套匹配失败: {ai_error}")
                return False, {}, 0, 0, ai_error

            # 统计字段数量
            total_fields = MatchingService._count_total_fields(form_structure.model_dump())
            matched_fields = MatchingService._count_matched_fields(matched_data)

            # 记录使用日志
            await MatchingService._log_usage(
                db, user_id, website_url or "unknown",
                total_fields, matched_fields
            )

            # 扣减激活次数
            use_success, use_message = await ActivationService.use_activation(db, user_id)
            if not use_success:
                logger.warning(f"激活次数扣减失败: {use_message}")

            logger.info(f"嵌套字段匹配完成，总字段: {total_fields}, 匹配字段: {matched_fields}")
            return True, matched_data, total_fields, matched_fields, ""

        except Exception as e:
            error_msg = f"嵌套字段匹配过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return False, {}, 0, 0, error_msg

    @staticmethod
    def _count_total_fields(structure: Dict[str, Any]) -> int:
        """递归统计表单结构中的总字段数"""
        count = 0

        def _count_recursive(struct: Dict[str, Any]) -> None:
            nonlocal count

            if isinstance(struct, dict):
                if struct.get('type') == 'object':
                    # 对象类型，递归统计fields中的字段
                    fields = struct.get('fields', {})
                    for field_config in fields.values():
                        _count_recursive(field_config)
                elif struct.get('type') == 'array':
                    # 数组类型，统计item_structure中的字段
                    item_structure = struct.get('item_structure', {})
                    _count_recursive(item_structure)
                else:
                    # 简单字段类型
                    count += 1

                # 如果是根级字段结构（有fields属性但没有type）
                if 'fields' in struct and 'type' not in struct:
                    for field_config in struct['fields'].values():
                        _count_recursive(field_config)

        _count_recursive(structure)
        return count

    @staticmethod
    def _count_matched_fields(data: Dict[str, Any]) -> int:
        """递归统计匹配数据中的字段数"""
        count = 0

        def _count_recursive(obj: Any) -> None:
            nonlocal count

            if isinstance(obj, dict):
                for value in obj.values():
                    _count_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    _count_recursive(item)
            elif obj is not None and str(obj).strip():
                # 非空字符串才算匹配成功的字段
                count += 1

        _count_recursive(data)
        return count


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
