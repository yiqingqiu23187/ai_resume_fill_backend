"""
Phase 5: 智能提示词生成服务

基于结构化表单数据生成优化的大模型提示词
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class StructuredPromptBuilder:
    """结构化提示词构建器"""

    def __init__(self):
        """初始化提示词构建器"""
        logger.info("💬 初始化结构化提示词构建器")

    def build_matching_prompt(self,
                            form_data: Dict[str, Any],
                            resume_data: Dict[str, Any],
                            structure_summary: str) -> str:
        """
        构建字段匹配提示词

        Args:
            form_data: 格式化后的表单结构数据
            resume_data: 用户简历数据
            structure_summary: 表单结构摘要

        Returns:
            优化的提示词
        """
        try:
            logger.info("📝 开始构建结构化匹配提示词")

            # 提取关键信息
            groups = form_data.get('form_structure', {}).get('groups', [])
            total_fields = sum(len(group.get('fields', [])) for group in groups)
            repeatable_groups = [g for g in groups if g.get('is_repeatable', False)]

            # 构建提示词
            prompt = f"""你是一个专业的简历表单自动填写助手。我已经通过计算机视觉分析了表单结构，现在需要你基于结构化信息进行字段匹配。

## 📋 表单结构分析结果

{structure_summary}
总计 {total_fields} 个字段，分为 {len(groups)} 个逻辑分组。

{self._build_structure_details(groups)}

## 👤 用户简历信息

```json
{json.dumps(resume_data, ensure_ascii=False, indent=2)}
```

## 🎯 任务要求

1. **理解表单结构**: 认真分析每个分组的逻辑关系
2. **精确字段匹配**: 根据字段标签和简历信息进行匹配
3. **保持数据一致性**: {self._build_consistency_rules(repeatable_groups)}
4. **处理重复结构**: {self._build_array_handling_rules(repeatable_groups)}

## 📤 输出格式

请返回JSON格式的匹配结果，格式如下：

```json
[
  {{
    "selector": "CSS选择器",
    "value": "填写值"
  }}
]
```

## ⚠️ 重要注意事项

- 如果某个字段在简历中找不到对应信息，请不要返回该字段
- 对于可重复分组，请确保数据的逻辑一致性
- 日期格式请根据字段要求进行调整
- 数值字段请确保格式正确

请开始分析和匹配："""

            logger.info("✅ 结构化提示词构建完成")
            return prompt

        except Exception as e:
            logger.error(f"❌ 提示词构建失败: {str(e)}")
            return self._build_fallback_prompt(resume_data)

    def _build_structure_details(self, groups: List[Dict[str, Any]]) -> str:
        """构建结构详情说明"""
        if not groups:
            return "⚠️ 没有识别到表单分组"

        details = ["### 📊 详细分组结构\n"]

        for i, group in enumerate(groups, 1):
            title = group.get('title', f'分组{i}')
            fields = group.get('fields', [])
            is_repeatable = group.get('is_repeatable', False)

            if is_repeatable:
                details.append(f"**{i}. {title}** (可重复结构)")
            else:
                details.append(f"**{i}. {title}**")

            # 添加字段列表
            for field in fields[:5]:  # 只显示前5个字段
                label = field.get('label', '未知字段')
                selector = field.get('selector', '')
                array_index = field.get('array_index')

                if array_index is not None:
                    details.append(f"   - {label} [索引{array_index}] (`{selector}`)")
                else:
                    details.append(f"   - {label} (`{selector}`)")

            if len(fields) > 5:
                details.append(f"   - ... 还有{len(fields) - 5}个字段")

            details.append("")  # 空行分隔

        return "\n".join(details)

    def _build_consistency_rules(self, repeatable_groups: List[Dict[str, Any]]) -> str:
        """构建一致性规则说明"""
        if not repeatable_groups:
            return "确保各分组内字段的语义匹配正确"

        rules = []
        for group in repeatable_groups:
            title = group.get('title', '重复分组')
            rules.append(f"在{title}中，相同array_index的字段必须属于同一条记录")

        return "；".join(rules)

    def _build_array_handling_rules(self, repeatable_groups: List[Dict[str, Any]]) -> str:
        """构建数组处理规则"""
        if not repeatable_groups:
            return "无重复结构需要处理"

        rules = [
            "重复分组按array_index分组处理",
            "相同索引的字段对应简历中的同一条记录",
            "按时间顺序或重要性排序填写"
        ]

        return "；".join(rules)

    def _build_fallback_prompt(self, resume_data: Dict[str, Any]) -> str:
        """构建备用提示词"""
        return f"""你是一个表单填写助手。请根据以下简历信息填写表单：

简历信息：
{json.dumps(resume_data, ensure_ascii=False, indent=2)}

请返回JSON格式的填写结果：
[{{"selector": "CSS选择器", "value": "填写值"}}]
"""

    def estimate_complexity(self, form_data: Dict[str, Any]) -> str:
        """评估表单复杂度"""
        groups = form_data.get('form_structure', {}).get('groups', [])
        total_fields = sum(len(group.get('fields', [])) for group in groups)
        repeatable_count = len([g for g in groups if g.get('is_repeatable', False)])

        if total_fields > 20 or repeatable_count > 2:
            return "high"
        elif total_fields > 10 or repeatable_count > 0:
            return "medium"
        else:
            return "low"

    def build_validation_prompt(self,
                               matching_results: List[Dict[str, Any]],
                               form_data: Dict[str, Any]) -> str:
        """
        构建结果验证提示词

        Args:
            matching_results: 匹配结果
            form_data: 表单数据

        Returns:
            验证提示词
        """
        return f"""请验证以下表单填写结果的合理性：

表单结构：
{json.dumps(form_data, ensure_ascii=False, indent=2)}

填写结果：
{json.dumps(matching_results, ensure_ascii=False, indent=2)}

请检查：
1. 字段匹配是否合理
2. 数据类型是否正确
3. 重复结构的一致性
4. 是否有明显错误

请返回验证结果：
{{"is_valid": true/false, "issues": ["问题列表"], "suggestions": ["改进建议"]}}
"""
