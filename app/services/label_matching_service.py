"""
智能标签匹配服务 - 新方案Phase 4
负责将视觉大模型识别的字段与表单字段进行智能匹配

匹配策略：
1. 精确匹配
2. 同义词匹配
3. 模糊匹配
4. 语义相似度匹配
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from difflib import SequenceMatcher
import jieba

logger = logging.getLogger(__name__)


class LabelMatchingService:
    """智能标签匹配服务"""

    def __init__(self):
        """初始化标签匹配服务"""
        # 同义词映射表
        self.synonym_mapping = {
            # 基本信息
            "姓名": ["名字", "真实姓名", "用户姓名", "申请人姓名", "full_name", "name"],
            "性别": ["gender", "sex"],
            "年龄": ["age"],
            "身份证号": ["身份证", "身份证号码", "证件号", "证件号码", "id_card", "id_number"],
            "手机号": ["电话", "手机", "移动电话", "联系电话", "phone", "mobile", "telephone"],
            "邮箱": ["电子邮箱", "电子邮件", "email", "e-mail", "邮件地址"],
            "地址": ["联系地址", "现住址", "家庭住址", "address", "location"],

            # 教育信息
            "毕业院校": ["学校", "毕业学校", "就读院校", "university", "school", "college"],
            "专业": ["所学专业", "专业名称", "major"],
            "学历": ["学历层次", "最高学历", "教育程度", "degree", "education"],
            "学位": ["学位类型", "degree"],
            "毕业时间": ["毕业年份", "毕业日期", "graduation_time"],
            "入学时间": ["入学日期", "开始时间"],
            "学号": ["student_id", "student_number"],
            "GPA": ["绩点", "平均分", "成绩"],

            # 工作信息
            "公司": ["工作单位", "就职公司", "单位名称", "company"],
            "职位": ["岗位", "职务", "工作岗位", "position", "title", "job"],
            "工作年限": ["工作经验", "从业年限", "experience_years"],
            "薪资": ["工资", "薪酬", "期望薪资", "salary", "wage"],
            "到岗时间": ["入职时间", "可到岗时间", "开始工作时间"],

            # 其他
            "简历": ["个人简历", "cv", "resume"],
            "照片": ["头像", "证件照", "个人照片", "photo", "avatar"],
            "备注": ["其他", "补充说明", "additional_info", "remark"],
            "技能": ["专业技能", "技能特长", "skills"],
            "证书": ["资格证书", "证书名称", "certificate"],
            "语言": ["外语水平", "语言能力", "language"],
            "项目经验": ["项目", "项目经历", "project"]
        }

        # 构建反向映射
        self.reverse_synonym_mapping = {}
        for standard, synonyms in self.synonym_mapping.items():
            for synonym in synonyms:
                self.reverse_synonym_mapping[synonym.lower()] = standard

    def match_fields(
        self,
        llm_field_mappings: Dict[str, Any],
        form_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        匹配字段

        Args:
            llm_field_mappings: 大模型识别的字段映射 {"毕业院校": "北京大学"}
            form_fields: 表单字段列表 [{"selector": "#school", "label": "学校"}]

        Returns:
            匹配结果
        """
        try:
            logger.info(f"🔍 开始字段匹配: LLM识别{len(llm_field_mappings)}个字段, 表单有{len(form_fields)}个字段")

            # 构建表单字段标签索引
            form_field_labels = {field['label']: field for field in form_fields}

            matching_results = []
            unmatched_llm_fields = []
            unmatched_form_fields = list(form_fields)

            # 对每个LLM识别的字段进行匹配
            for llm_label, llm_value in llm_field_mappings.items():
                best_match = self._find_best_match(llm_label, form_field_labels)

                if best_match:
                    match_info, form_field = best_match
                    matching_results.append({
                        'selector': form_field['selector'],
                        'type': form_field.get('type', 'text'),
                        'llm_label': llm_label,
                        'form_label': form_field['label'],
                        'value': llm_value,
                        'match_type': match_info['match_type'],
                        'confidence': match_info['confidence'],
                        'required': form_field.get('required', False)
                    })

                    # 从未匹配列表中移除
                    if form_field in unmatched_form_fields:
                        unmatched_form_fields.remove(form_field)
                else:
                    unmatched_llm_fields.append({
                        'label': llm_label,
                        'value': llm_value
                    })

            # 统计匹配结果
            total_llm_fields = len(llm_field_mappings)
            matched_count = len(matching_results)
            match_rate = matched_count / total_llm_fields if total_llm_fields > 0 else 0

            logger.info(f"✅ 字段匹配完成: {matched_count}/{total_llm_fields} ({match_rate:.1%}) 匹配成功")

            return {
                'success': True,
                'matching_results': matching_results,
                'unmatched_llm_fields': unmatched_llm_fields,
                'unmatched_form_fields': [
                    {'selector': f['selector'], 'label': f['label']}
                    for f in unmatched_form_fields
                ],
                'statistics': {
                    'total_llm_fields': total_llm_fields,
                    'total_form_fields': len(form_fields),
                    'matched_count': matched_count,
                    'match_rate': match_rate,
                    'unmatched_llm_count': len(unmatched_llm_fields),
                    'unmatched_form_count': len(unmatched_form_fields)
                }
            }

        except Exception as e:
            logger.error(f"❌ 字段匹配失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'matching_results': []
            }

    def _find_best_match(
        self,
        llm_label: str,
        form_field_labels: Dict[str, Dict[str, Any]]
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        为LLM标签找到最佳匹配的表单字段

        Args:
            llm_label: LLM识别的标签
            form_field_labels: 表单字段标签字典

        Returns:
            匹配信息和对应的表单字段，无匹配返回None
        """
        best_match = None
        best_confidence = 0.0

        for form_label, form_field in form_field_labels.items():
            match_info = self._calculate_match_score(llm_label, form_label)

            if match_info['confidence'] > best_confidence:
                best_confidence = match_info['confidence']
                best_match = (match_info, form_field)

        # 只返回置信度大于阈值的匹配
        if best_confidence >= 0.6:  # 调低阈值，提高匹配率
            return best_match

        return None

    def _calculate_match_score(self, llm_label: str, form_label: str) -> Dict[str, Any]:
        """
        计算两个标签的匹配分数

        Args:
            llm_label: LLM标签
            form_label: 表单标签

        Returns:
            匹配信息
        """
        # 1. 精确匹配（最高优先级）
        if llm_label == form_label:
            return {
                'match_type': 'exact',
                'confidence': 1.0
            }

        # 2. 同义词匹配
        synonym_score = self._check_synonym_match(llm_label, form_label)
        if synonym_score > 0:
            return {
                'match_type': 'synonym',
                'confidence': synonym_score
            }

        # 3. 包含匹配
        contain_score = self._check_contain_match(llm_label, form_label)
        if contain_score > 0:
            return {
                'match_type': 'contain',
                'confidence': contain_score
            }

        # 4. 模糊匹配
        fuzzy_score = self._calculate_fuzzy_score(llm_label, form_label)
        if fuzzy_score > 0.6:
            return {
                'match_type': 'fuzzy',
                'confidence': fuzzy_score
            }

        # 5. 语义匹配（基于关键词）
        semantic_score = self._calculate_semantic_score(llm_label, form_label)
        if semantic_score > 0.7:
            return {
                'match_type': 'semantic',
                'confidence': semantic_score
            }

        return {
            'match_type': 'none',
            'confidence': 0.0
        }

    def _check_synonym_match(self, llm_label: str, form_label: str) -> float:
        """检查同义词匹配"""
        # 标准化标签
        standard_llm = self._normalize_label(llm_label)
        standard_form = self._normalize_label(form_label)

        # 查找标准形式
        llm_standard = self.reverse_synonym_mapping.get(standard_llm.lower(), standard_llm)
        form_standard = self.reverse_synonym_mapping.get(standard_form.lower(), standard_form)

        if llm_standard == form_standard:
            return 0.95

        # 检查是否在同一同义词组中
        for standard, synonyms in self.synonym_mapping.items():
            all_forms = [standard] + synonyms
            if standard_llm in all_forms and standard_form in all_forms:
                return 0.9

        return 0.0

    def _check_contain_match(self, llm_label: str, form_label: str) -> float:
        """检查包含匹配"""
        llm_clean = self._clean_text(llm_label)
        form_clean = self._clean_text(form_label)

        # 较短的包含在较长的中
        shorter, longer = (llm_clean, form_clean) if len(llm_clean) < len(form_clean) else (form_clean, llm_clean)

        if len(shorter) >= 2 and shorter in longer:
            # 根据长度比例调整置信度
            ratio = len(shorter) / len(longer)
            return 0.8 + ratio * 0.1  # 0.8-0.9之间

        return 0.0

    def _calculate_fuzzy_score(self, llm_label: str, form_label: str) -> float:
        """计算模糊匹配分数"""
        llm_clean = self._clean_text(llm_label)
        form_clean = self._clean_text(form_label)

        # 使用SequenceMatcher计算相似度
        similarity = SequenceMatcher(None, llm_clean, form_clean).ratio()

        # 对短文本给予更高权重
        min_length = min(len(llm_clean), len(form_clean))
        if min_length <= 4:  # 短标签
            similarity *= 1.1

        return min(similarity, 1.0)

    def _calculate_semantic_score(self, llm_label: str, form_label: str) -> float:
        """计算语义匹配分数"""
        # 提取关键词
        llm_keywords = self._extract_keywords(llm_label)
        form_keywords = self._extract_keywords(form_label)

        if not llm_keywords or not form_keywords:
            return 0.0

        # 计算关键词重叠度
        intersection = set(llm_keywords) & set(form_keywords)
        union = set(llm_keywords) | set(form_keywords)

        if not union:
            return 0.0

        jaccard_score = len(intersection) / len(union)

        # 考虑同义词
        synonym_bonus = 0.0
        for llm_kw in llm_keywords:
            for form_kw in form_keywords:
                if self._are_synonyms(llm_kw, form_kw):
                    synonym_bonus += 0.3

        return min(jaccard_score + synonym_bonus, 1.0)

    def _normalize_label(self, label: str) -> str:
        """标准化标签"""
        # 移除标点和空格
        normalized = re.sub(r'[^\w]', '', label)
        return normalized.strip()

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除标点、空格、特殊字符
        cleaned = re.sub(r'[^\w\u4e00-\u9fa5]', '', text)
        return cleaned.lower()

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 使用jieba分词
        words = jieba.lcut(text)

        # 过滤停用词和短词
        keywords = []
        stop_words = {'的', '了', '在', '是', '和', '与', '或', '及'}

        for word in words:
            if len(word) >= 2 and word not in stop_words:
                keywords.append(word)

        return keywords

    def _are_synonyms(self, word1: str, word2: str) -> bool:
        """检查两个词是否为同义词"""
        for synonyms in self.synonym_mapping.values():
            all_forms = synonyms
            if word1 in all_forms and word2 in all_forms:
                return True
        return False


# 全局实例
label_matching_service = LabelMatchingService()
