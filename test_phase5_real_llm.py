#!/usr/bin/env python3
"""
Phase 5: 真实大模型调用测试

测试使用真实的阿里千问API进行字段匹配
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.llm.llm_integration_service import llm_integration_service
from app.core.config import settings


def create_simple_phase4_result():
    """创建简化的Phase 4结果用于测试"""
    return {
        'success': True,
        'phase': 'phase4_structure_recognition',
        'logical_groups': [
            {
                'id': 'basic_info',
                'title': '基本信息',
                'is_repeatable': False,
                'fields': [
                    {'selector': 'input[name="name"]', 'label': '姓名', 'type': 'text'},
                    {'selector': 'input[name="phone"]', 'label': '手机号', 'type': 'text'},
                    {'selector': 'input[name="email"]', 'label': '邮箱', 'type': 'email'}
                ]
            },
            {
                'id': 'education',
                'title': '教育背景',
                'is_repeatable': True,
                'fields': [
                    {'selector': 'input[name="school1"]', 'label': '毕业院校', 'type': 'text', 'array_index': 0},
                    {'selector': 'input[name="major1"]', 'label': '专业', 'type': 'text', 'array_index': 0},
                    {'selector': 'input[name="school2"]', 'label': '毕业院校', 'type': 'text', 'array_index': 1},
                    {'selector': 'input[name="major2"]', 'label': '专业', 'type': 'text', 'array_index': 1}
                ]
            }
        ],
        'input_fields': 7,
        'phase4_quality': {
            'level': 'good',
            'score': 0.85
        }
    }


def create_simple_resume_data():
    """创建简化的简历数据"""
    return {
        "basic_info": {
            "name": "李明",
            "phone": "13912345678",
            "email": "liming@example.com",
            "gender": "男"
        },
        "education": [
            {
                "school": "北京大学",
                "degree": "本科",
                "major": "计算机科学与技术",
                "start_date": "2016-09",
                "end_date": "2020-07"
            },
            {
                "school": "清华大学",
                "degree": "硕士",
                "major": "人工智能",
                "start_date": "2020-09",
                "end_date": "2023-07"
            }
        ]
    }


async def test_real_llm_integration():
    """测试真实的大模型集成"""
    print("🤖 Phase 5真实大模型调用测试")
    print("🎯 目标: 验证阿里千问API是否正确配置和调用")
    print("=" * 60)

    # 检查配置
    print(f"\n🔧 配置检查:")
    print(f"   AI模型: {settings.AI_MODEL}")
    print(f"   API密钥: {'已配置' if settings.DASHSCOPE_API_KEY else '未配置'}")
    print(f"   密钥长度: {len(settings.DASHSCOPE_API_KEY) if settings.DASHSCOPE_API_KEY else 0}")

    if not settings.DASHSCOPE_API_KEY:
        print("❌ DASHSCOPE_API_KEY未配置，请检查.env文件")
        return

    try:
        # 准备测试数据
        print(f"\n📊 准备测试数据...")
        phase4_result = create_simple_phase4_result()
        resume_data = create_simple_resume_data()

        print(f"   Phase 4分组: {len(phase4_result['logical_groups'])}个")
        print(f"   简历信息: {len(resume_data)}个部分")

        # 调用Phase 5服务
        print(f"\n🚀 开始调用Phase 5服务...")
        result = await llm_integration_service.process_structured_matching(
            phase4_result=phase4_result,
            resume_data=resume_data
        )

        # 分析结果
        print(f"\n📈 处理结果:")
        print(f"   成功: {'✅' if result.get('success') else '❌'}")

        if result.get('success'):
            stats = result.get('statistics', {})
            print(f"   匹配字段: {stats.get('matched_fields', 0)}个")
            print(f"   匹配率: {stats.get('match_rate', 0):.1%}")
            print(f"   验证得分: {stats.get('validation_score', 0):.2f}")
            print(f"   处理时间: {result.get('processing_time', 0):.2f}秒")

            # 显示实际匹配结果
            matching_results = result.get('matching_results', [])
            if matching_results:
                print(f"\n🎯 匹配结果详情:")
                for i, match in enumerate(matching_results[:5], 1):
                    selector = match.get('selector', '')
                    value = match.get('value', '')
                    confidence = match.get('confidence', 0)
                    print(f"   {i}. {selector}: {value} (置信度: {confidence:.2f})")

                if len(matching_results) > 5:
                    print(f"   ... 还有{len(matching_results) - 5}个结果")

            # 显示质量评估
            quality = result.get('quality_assessment', {})
            print(f"\n🏆 质量评估:")
            print(f"   总体质量: {quality.get('overall_quality', 'unknown')}")
            print(f"   匹配质量: {quality.get('matching_quality', 0):.2f}")

            recommendations = quality.get('recommendations', [])
            if recommendations:
                print(f"   建议: {', '.join(recommendations[:2])}")

        else:
            error_msg = result.get('error', '未知错误')
            print(f"   错误: {error_msg}")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*60}")
    if result.get('success'):
        print("🎉 真实大模型调用测试成功!")
        print("✅ AI服务配置正确，可以正常调用阿里千问API")
    else:
        print("❌ 真实大模型调用测试失败")
        print("🔧 请检查DASHSCOPE_API_KEY配置或网络连接")


async def test_ai_service_directly():
    """直接测试AI服务"""
    print(f"\n🧪 直接测试AI服务")
    print("-" * 40)

    try:
        from app.services.ai_service import AIService

        # 简单的测试提示词
        test_prompt = """
你是一个表单填写助手。现在有一个表单包含以下字段：
- 姓名 (input[name="name"])
- 手机号 (input[name="phone"])

用户简历信息：
- 姓名: 张三
- 手机号: 13800138000

请返回JSON格式的匹配结果：
[{"selector": "input[name=\"name\"]", "value": "张三", "confidence": 0.95}]
"""

        print("📝 发送测试提示词...")
        response = await AIService.analyze_with_prompt(test_prompt)

        print(f"✅ 收到AI响应，长度: {len(response)}字符")
        print(f"📄 响应内容预览: {response[:200]}...")

        # 尝试解析响应
        try:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                print(f"✅ JSON解析成功，包含{len(parsed)}个匹配结果")
            else:
                print("⚠️ 响应中未找到JSON格式数据")
        except:
            print("⚠️ JSON解析失败")

    except Exception as e:
        print(f"❌ 直接AI服务测试失败: {str(e)}")


if __name__ == "__main__":
    # 运行真实大模型测试
    asyncio.run(test_real_llm_integration())

    # 运行直接AI服务测试
    asyncio.run(test_ai_service_directly())
