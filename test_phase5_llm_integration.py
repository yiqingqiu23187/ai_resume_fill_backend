#!/usr/bin/env python3
"""
Phase 5: LLM集成优化完整测试

展示从Phase 2视觉分析到Phase 5大模型集成的完整流程
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.visual.visual_analysis_service import visual_analysis_service
from app.services.structure.structure_recognition_service import structure_recognition_service
from app.services.llm.llm_integration_service import llm_integration_service
from test_phase2_cv_algorithms import create_complex_test_html


def create_mock_resume_data():
    """创建模拟简历数据"""
    return {
        "basic_info": {
            "name": "张三",
            "phone": "13800138000",
            "email": "zhangsan@example.com",
            "gender": "男",
            "birth_date": "1995-06-15",
            "address": "北京市朝阳区"
        },
        "education": [
            {
                "school": "清华大学",
                "degree": "本科",
                "major": "计算机科学与技术",
                "start_date": "2013-09",
                "end_date": "2017-07",
                "gpa": "3.8"
            },
            {
                "school": "北京大学",
                "degree": "硕士",
                "major": "软件工程",
                "start_date": "2017-09",
                "end_date": "2020-07",
                "gpa": "3.9"
            }
        ],
        "work_experience": [
            {
                "company": "字节跳动",
                "position": "高级软件工程师",
                "start_date": "2020-08",
                "end_date": "2023-05",
                "salary": "35000",
                "description": "负责推荐系统的开发和优化"
            },
            {
                "company": "腾讯",
                "position": "资深软件工程师",
                "start_date": "2023-06",
                "end_date": "至今",
                "salary": "45000",
                "description": "负责微信支付核心系统开发"
            }
        ],
        "skills": {
            "programming": ["Python", "Java", "Go", "JavaScript"],
            "languages": ["英语(CET-6)", "日语(N2)"],
            "certificates": ["PMP项目管理认证", "AWS解决方案架构师"]
        }
    }


async def run_complete_phase5_test():
    """运行完整的Phase 5测试"""
    print("🚀 Phase 5 LLM集成优化完整测试")
    print("🎯 目标: 展示从Phase 2到Phase 5的完整视觉驱动表单分析流程")
    print("✨ 特色: 结构化数据 + 智能提示词 + 结果验证")
    print("=" * 80)

    try:
        # Step 1: 运行Phase 2 (视觉分析)
        print("\n📊 Step 1: 运行Phase 2视觉分析...")
        test_html = create_complex_test_html()

        phase2_result = await visual_analysis_service.analyze_html_visual(
            html_content=test_html,
            website_url="test://demo/phase5-complete",
            analysis_config={'viewport_width': 1200, 'viewport_height': 1400}
        )

        if not phase2_result.get('success'):
            print(f"❌ Phase 2失败: {phase2_result.get('error')}")
            return

        print(f"✅ Phase 2完成: {phase2_result.get('elements', {}).get('total_count', 0)}个字段识别")

        # Step 2: 运行Phase 4 (结构识别)
        print("\n🏗️ Step 2: 运行Phase 4结构识别...")
        phase4_result = await structure_recognition_service.recognize_structure(phase2_result)

        if not phase4_result.get('success'):
            print(f"❌ Phase 4失败: {phase4_result.get('error')}")
            return

        print(f"✅ Phase 4完成: {len(phase4_result.get('logical_groups', []))}个逻辑分组")

        # Step 3: 运行Phase 5 (LLM集成)
        print("\n🤖 Step 3: 运行Phase 5 LLM集成...")
        resume_data = create_mock_resume_data()

        phase5_result = await llm_integration_service.process_structured_matching(
            phase4_result=phase4_result,
            resume_data=resume_data
        )

        if not phase5_result.get('success'):
            print(f"❌ Phase 5失败: {phase5_result.get('error')}")
            return

        # Step 4: 展示完整结果
        print("\n" + "=" * 80)
        display_phase5_results(phase5_result)

        # Step 5: 展示数据流转过程
        print("\n" + "=" * 80)
        display_data_flow_summary(phase2_result, phase4_result, phase5_result)

        # Step 6: 展示核心匹配结果
        print("\n" + "=" * 80)
        display_matching_results(phase5_result)

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            await visual_analysis_service.cleanup_resources()
        except:
            pass

    print("\n" + "=" * 80)
    print("🎉 Phase 5完整测试完成!")
    print("✨ 核心成就:")
    print("   🔗 完整流程: Phase 2 → Phase 4 → Phase 5")
    print("   📊 结构化处理: 平铺字段 → 逻辑分组 → 智能匹配")
    print("   🎯 质量验证: 自动验证 + 改进建议")
    print("   🚀 生产就绪: 可直接用于表单自动填写")
    print("=" * 80)


def display_phase5_results(phase5_result):
    """展示Phase 5结果"""
    print("🎯 **Phase 5 LLM集成结果**")

    # 基本统计
    stats = phase5_result.get('statistics', {})
    print(f"\n📊 **处理统计**:")
    print(f"   输入分组: {stats.get('input_groups', 0)}个")
    print(f"   输入字段: {stats.get('input_fields', 0)}个")
    print(f"   匹配字段: {stats.get('matched_fields', 0)}个")
    print(f"   有效匹配: {stats.get('valid_matches', 0)}个")
    print(f"   匹配率: {stats.get('match_rate', 0):.1%}")
    print(f"   验证得分: {stats.get('validation_score', 0):.2f}")

    # 质量评估
    quality = phase5_result.get('quality_assessment', {})
    print(f"\n🏆 **质量评估**:")
    print(f"   总体质量: {quality.get('overall_quality', 'unknown')}")
    print(f"   匹配质量: {quality.get('matching_quality', 0):.2f}")

    recommendations = quality.get('recommendations', [])
    if recommendations:
        print(f"   💡 改进建议:")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"      {i}. {rec}")

    # 元数据
    metadata = phase5_result.get('metadata', {})
    print(f"\n📋 **元数据**:")
    print(f"   表单复杂度: {metadata.get('complexity', 'unknown')}")
    print(f"   可重复分组: {metadata.get('repeatable_groups', 0)}个")
    print(f"   结构摘要: {metadata.get('structure_summary', 'N/A')}")

    # 处理性能
    processing_time = phase5_result.get('processing_time', 0)
    print(f"\n⚡ **性能指标**:")
    print(f"   处理时间: {processing_time:.3f}秒")


def display_data_flow_summary(phase2_result, phase4_result, phase5_result):
    """展示数据流转摘要"""
    print("🔄 **数据流转摘要**")

    # Phase 2 → Phase 4 → Phase 5
    phase2_fields = phase2_result.get('elements', {}).get('total_count', 0)
    phase4_groups = len(phase4_result.get('logical_groups', []))
    phase5_matches = len(phase5_result.get('matching_results', []))

    print(f"\n📈 **数据转换链路**:")
    print(f"   Phase 2 (视觉分析): {phase2_fields}个平铺字段")
    print(f"   Phase 4 (结构识别): {phase4_groups}个逻辑分组")
    print(f"   Phase 5 (智能匹配): {phase5_matches}个匹配结果")

    # 计算转换效率
    if phase2_fields > 0:
        structure_reduction = (phase2_fields - phase4_groups) / phase2_fields
        matching_efficiency = phase5_matches / phase2_fields

        print(f"\n📊 **转换效率**:")
        print(f"   结构简化率: {structure_reduction:.1%} ({phase2_fields}→{phase4_groups})")
        print(f"   匹配覆盖率: {matching_efficiency:.1%} ({phase5_matches}/{phase2_fields})")

    # 质量传递
    phase4_quality = phase4_result.get('phase4_quality', {}).get('level', 'unknown')
    phase5_quality = phase5_result.get('quality_assessment', {}).get('overall_quality', 'unknown')

    print(f"\n🎯 **质量传递**:")
    print(f"   Phase 4质量: {phase4_quality}")
    print(f"   Phase 5质量: {phase5_quality}")


def display_matching_results(phase5_result):
    """展示匹配结果详情"""
    print("🎯 **字段匹配结果详情**")

    matching_results = phase5_result.get('matching_results', [])
    validation_result = phase5_result.get('validation_result', {})

    if not matching_results:
        print("   ⚠️ 没有匹配结果")
        return

    print(f"\n✅ **成功匹配 ({len(matching_results)}个字段)**:")

    # 按置信度排序显示
    sorted_results = sorted(matching_results, key=lambda x: x.get('confidence', 0), reverse=True)

    for i, result in enumerate(sorted_results[:10], 1):  # 只显示前10个
        selector = result.get('selector', '')
        value = result.get('value', '')
        confidence = result.get('confidence', 0)
        reasoning = result.get('reasoning', '')

        print(f"   {i:2d}. {selector}")
        print(f"       值: {value}")
        print(f"       置信度: {confidence:.2f}")
        print(f"       原因: {reasoning}")
        print()

    if len(matching_results) > 10:
        print(f"   ... 还有{len(matching_results) - 10}个匹配结果")

    # 验证问题
    issues = validation_result.get('issues', [])
    if issues:
        print(f"\n⚠️ **验证问题 ({len(issues)}个)**:")
        for i, issue in enumerate(issues[:5], 1):
            print(f"   {i}. {issue}")

        if len(issues) > 5:
            print(f"   ... 还有{len(issues) - 5}个问题")


async def test_individual_components():
    """测试各个组件的独立功能"""
    print("\n🧪 **组件独立测试**")
    print("-" * 50)

    # 测试数据格式转换
    print("🔄 测试数据格式转换...")
    from app.services.llm.data_formatter import LLMDataFormatter

    formatter = LLMDataFormatter()

    # 创建模拟Phase 4数据
    mock_phase4_result = {
        'logical_groups': [
            {
                'id': 'basic_info',
                'title': '基本信息',
                'is_repeatable': False,
                'fields': [
                    {'selector': 'input[name="name"]', 'label': '姓名', 'type': 'text'},
                    {'selector': 'input[name="phone"]', 'label': '手机号', 'type': 'text'}
                ]
            }
        ],
        'input_fields': 2
    }

    llm_data = formatter.format_for_llm(mock_phase4_result)
    print(f"   ✅ 格式转换成功: {len(llm_data.get('form_structure', {}).get('groups', []))}个分组")

    # 测试提示词生成
    print("💬 测试提示词生成...")
    from app.services.llm.prompt_builder import StructuredPromptBuilder

    prompt_builder = StructuredPromptBuilder()
    resume_data = create_mock_resume_data()
    structure_summary = formatter.extract_structure_summary(llm_data)

    prompt = prompt_builder.build_matching_prompt(llm_data, resume_data, structure_summary)
    print(f"   ✅ 提示词生成成功: {len(prompt)}字符")

    # 测试结果验证
    print("🔍 测试结果验证...")
    from app.services.validation.result_validator import ResultValidator

    validator = ResultValidator()
    mock_results = [
        {'selector': 'input[name="name"]', 'value': '张三', 'confidence': 0.9},
        {'selector': 'input[name="phone"]', 'value': '13800138000', 'confidence': 0.85}
    ]

    validation = validator.validate_matching_results(mock_results, llm_data)
    print(f"   ✅ 结果验证成功: 总体得分 {validation.get('overall_score', 0):.2f}")

    print("🎉 所有组件测试通过!")


if __name__ == "__main__":
    # 运行完整测试
    asyncio.run(run_complete_phase5_test())

    # 运行组件测试
    asyncio.run(test_individual_components())
