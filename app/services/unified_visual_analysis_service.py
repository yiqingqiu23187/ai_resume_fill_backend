"""
统一视觉驱动表单分析服务

整合Phase 1-5的完整处理流程，提供统一的前端API接口
"""

import asyncio
import uuid
import time
import logging
from typing import Dict, List, Any, Optional

from ..schemas.visual_analysis_schemas import (
    UnifiedAnalysisResult, ProcessingPhase,
    MatchingResult, QualityAssessment, QualityLevel
)
from .visual.visual_analysis_service import visual_analysis_service
from .structure.structure_recognition_service import structure_recognition_service
from .llm.llm_integration_service import llm_integration_service

logger = logging.getLogger(__name__)


class UnifiedVisualAnalysisService:
    """统一视觉驱动分析服务"""

    def __init__(self):
        """初始化服务"""
        logger.info("🔧 统一视觉驱动分析服务初始化完成")

    async def analyze_complete_pipeline(self,
                                      html_content: str,
                                      website_url: str,
                                      resume_data: dict) -> UnifiedAnalysisResult:
        """
        完整的分析流水线 - 主入口方法

        Args:
            html_content: HTML内容
            website_url: 网站URL
            resume_data: 简历数据(原始JSON)

        Returns:
            统一的分析结果
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"🚀 开始完整分析流水线 - 请求ID: {request_id}")
        logger.info(f"📊 请求信息: 网站={website_url}, HTML长度={len(html_content)}")

        result = UnifiedAnalysisResult(
            success=False,
            request_id=request_id,
            total_processing_time=0,
            final_matching_results=[],
            final_quality_assessment=QualityAssessment(
                overall_quality=QualityLevel.POOR,
                matching_quality=0.0,
                recommendations=[]
            ),
            final_recommendations=[]
        )

        try:
            # 执行完整流水线
            return await self._execute_complete_pipeline(html_content, website_url, resume_data, result)

        except Exception as e:
            logger.error(f"❌ 分析流水线失败: {str(e)}", exc_info=True)
            result.success = False
            result.error = f"分析流水线失败: {str(e)}"
            result.total_processing_time = time.time() - start_time
            return result

    async def _execute_complete_pipeline(self,
                                       html_content: str,
                                       website_url: str,
                                       resume_data: dict,
                                       result: UnifiedAnalysisResult) -> UnifiedAnalysisResult:
        """执行完整的分析流水线"""
        start_time = time.time()

        try:
            # Phase 1: 视觉信息采集
            logger.info("📊 Phase 1: 视觉信息采集...")
            phase1_result = await self._execute_phase1(html_content, website_url)
            result.phase1_result = phase1_result

            if not phase1_result or not phase1_result.get('success'):
                result.failed_phase = ProcessingPhase.PHASE1_SCREENSHOT
                result.error = "Phase 1失败: 视觉信息采集失败"
                return result

            # Phase 2: 计算机视觉分析 (输入: Phase1结果)
            logger.info("🔍 Phase 2: 计算机视觉分析...")
            phase2_result = await visual_analysis_service.analyze_html_visual(
                html_content=html_content,
                website_url=website_url,
                analysis_config={}
            )
            result.phase2_result = self._convert_to_schema_format(phase2_result, ProcessingPhase.PHASE2_CV_ANALYSIS)

            if not phase2_result.get('success'):
                result.failed_phase = ProcessingPhase.PHASE2_CV_ANALYSIS
                result.error = "Phase 2失败: 计算机视觉分析失败"
                return result

            # Phase 4: 结构识别 (输入: Phase2结果)
            logger.info("🏗️ Phase 4: 结构识别...")
            phase4_result = await structure_recognition_service.recognize_structure(phase2_result)
            result.phase4_result = self._convert_to_schema_format(phase4_result, ProcessingPhase.PHASE4_STRUCTURE_RECOGNITION)

            if not phase4_result.get('success'):
                result.failed_phase = ProcessingPhase.PHASE4_STRUCTURE_RECOGNITION
                result.error = "Phase 4失败: 结构识别失败"
                return result

            # Phase 5: LLM集成 (输入: Phase4结果 + 简历数据)
            logger.info("🤖 Phase 5: LLM集成...")
            phase5_result = await llm_integration_service.process_structured_matching(
                phase4_result=phase4_result,
                resume_data=resume_data  # 直接使用原始JSON数据
            )
            result.phase5_result = self._convert_to_schema_format(phase5_result, ProcessingPhase.PHASE5_LLM_INTEGRATION)

            if not phase5_result.get('success'):
                result.failed_phase = ProcessingPhase.PHASE5_LLM_INTEGRATION
                result.error = "Phase 5失败: LLM集成失败"
                return result

            # 直接提取匹配结果
            matching_results = phase5_result.get('matching_results', [])
            result.final_matching_results = [
                MatchingResult(selector=mr['selector'], value=mr['value'])
                for mr in matching_results
            ]

            result.success = True
            result.total_processing_time = time.time() - start_time

            logger.info(f"✅ 完整分析流水线成功完成，用时: {result.total_processing_time:.2f}秒")
            logger.info(f"📊 最终结果: {len(matching_results)}个匹配字段")

            return result

        except Exception as e:
            logger.error(f"❌ 流水线执行失败: {str(e)}", exc_info=True)
            result.success = False
            result.error = f"流水线执行失败: {str(e)}"
            result.total_processing_time = time.time() - start_time
            return result


    async def _execute_phase1(self, html_content: str, website_url: str) -> Dict[str, Any]:
        """执行Phase 1: 视觉信息采集"""
        # 这里应该调用独立的Phase 1服务来生成截图和BBOX
        # 但目前由于Playwright异步问题，暂时返回简化结果
        # Phase 2会自己处理截图生成
        return {
            'success': True,
            'phase': ProcessingPhase.PHASE1_SCREENSHOT,
            'screenshot_url': None,
            'viewport': {'width': 1920, 'height': 1080},
            'elements': {},
            'processing_time': 0.1,
            'html_content': html_content,  # 传递给下一阶段
            'website_url': website_url     # 传递给下一阶段
        }

    def _convert_to_schema_format(self, raw_result: Dict[str, Any], phase: ProcessingPhase) -> Dict[str, Any]:
        """将原始结果转换为Schema格式"""
        if not raw_result:
            return {
                'success': False,
                'phase': phase,
                'error': '阶段结果为空',
                'processing_time': 0
            }

        # 基本转换，保持原有格式
        converted = raw_result.copy()
        converted['phase'] = phase

        return converted


    async def get_analysis_status(self, request_id: str) -> Dict[str, Any]:
        """获取分析状态 (用于长时间处理的异步查询)"""
        return {
            'status': 'not_found',
            'message': f'请求ID {request_id} 不存在'
        }

    def get_supported_phases(self) -> List[ProcessingPhase]:
        """获取支持的处理阶段"""
        return [
            ProcessingPhase.PHASE2_CV_ANALYSIS,
            ProcessingPhase.PHASE4_STRUCTURE_RECOGNITION,
            ProcessingPhase.PHASE5_LLM_INTEGRATION
        ]


    def get_processing_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            'total_requests_processed': 42,  # 临时数据
            'supported_phases': [phase.value for phase in self.get_supported_phases()],
            'service_status': 'running'
        }


# 全局服务实例
unified_visual_analysis_service = UnifiedVisualAnalysisService()
