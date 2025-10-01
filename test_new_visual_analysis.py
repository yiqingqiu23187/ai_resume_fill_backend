#!/usr/bin/env python3
"""
新视觉分析方案测试脚本

测试完整的视觉大模型+标签匹配方案，包括：
- Phase 2: 字段提取
- Phase 3: 视觉大模型分析
- Phase 4: 智能标签匹配
- Phase 5: 表单填写

使用方法:
python test_new_visual_analysis.py [--test-phase PHASE] [--enable-llm]
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.services.new_visual_analysis_service import new_visual_analysis_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 测试HTML内容 - 模拟招聘网站表单
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>招聘申请表</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .form-group { margin: 15px 0; }
        label { display: inline-block; width: 120px; font-weight: bold; }
        input, select, textarea { width: 250px; padding: 8px; margin-left: 10px; }
        .required { color: red; }
    </style>
</head>
<body>
    <h2>🏢 XX科技有限公司 - 简历申请表</h2>

    <form id="application-form">
        <div class="form-group">
            <label for="name">姓名 <span class="required">*</span></label>
            <input type="text" id="name" name="name" placeholder="请输入真实姓名" required>
        </div>

        <div class="form-group">
            <label for="gender">性别</label>
            <select id="gender" name="gender">
                <option value="">请选择</option>
                <option value="male">男</option>
                <option value="female">女</option>
            </select>
        </div>

        <div class="form-group">
            <label for="phone">手机号 <span class="required">*</span></label>
            <input type="tel" id="phone" name="phone" placeholder="请输入11位手机号" required>
        </div>

        <div class="form-group">
            <label for="email">邮箱地址</label>
            <input type="email" id="email" name="email" placeholder="example@email.com">
        </div>

        <div class="form-group">
            <label for="school">毕业院校 <span class="required">*</span></label>
            <input type="text" id="school" name="school" placeholder="请输入毕业院校" required>
        </div>

        <div class="form-group">
            <label for="major">专业</label>
            <input type="text" id="major" name="major" placeholder="请输入专业名称">
        </div>

        <div class="form-group">
            <label for="degree">学历</label>
            <select id="degree" name="degree">
                <option value="">请选择学历</option>
                <option value="high_school">高中</option>
                <option value="associate">大专</option>
                <option value="bachelor">本科</option>
                <option value="master">硕士</option>
                <option value="phd">博士</option>
            </select>
        </div>

        <div class="form-group">
            <label for="work_experience">工作年限</label>
            <select id="work_experience" name="work_experience">
                <option value="">请选择</option>
                <option value="0">应届毕业生</option>
                <option value="1">1年</option>
                <option value="2">2年</option>
                <option value="3-5">3-5年</option>
                <option value="5+">5年以上</option>
            </select>
        </div>

        <div class="form-group">
            <label for="expected_salary">期望薪资</label>
            <select id="expected_salary" name="expected_salary">
                <option value="">请选择</option>
                <option value="5k-8k">5K-8K</option>
                <option value="8k-12k">8K-12K</option>
                <option value="12k-20k">12K-20K</option>
                <option value="20k+">20K以上</option>
            </select>
        </div>

        <div class="form-group">
            <label for="self_intro">自我介绍</label>
            <textarea id="self_intro" name="self_intro" rows="4" placeholder="请简单介绍一下自己"></textarea>
        </div>

        <div class="form-group">
            <button type="submit" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px;">
                提交申请
            </button>
        </div>
    </form>
</body>
</html>
"""

# 测试简历数据
TEST_RESUME_DATA = {
    "basic_info": {
        "姓名": "张小明",
        "性别": "男",
        "年龄": "25",
        "手机号": "13812345678",
        "邮箱": "zhangxiaoming@example.com",
        "地址": "北京市朝阳区",
        "身份证号": "110101199901010001"
    },
    "education": [
        {
            "school": "北京大学",
            "major": "计算机科学与技术",
            "degree": "本科",
            "period": "2018-2022",
            "gpa": "3.8"
        }
    ],
    "experience": [
        {
            "company": "腾讯科技有限公司",
            "position": "前端开发工程师",
            "period": "2022-2024",
            "description": "负责微信小程序开发"
        }
    ],
    "skills": [
        "JavaScript", "Python", "React", "Vue.js", "Node.js", "MySQL"
    ]
}


async def test_phase2_field_extraction():
    """测试Phase 2: 字段提取"""
    print("\n" + "="*60)
    print("🧪 测试Phase 2: 字段提取")
    print("="*60)

    try:
        from app.services.form_field_extractor import form_field_extractor

        result = await form_field_extractor.extract_form_fields(TEST_HTML)

        if result['success']:
            fields = result['fields']
            print(f"✅ 字段提取成功: {len(fields)}个字段")

            print("\n📋 提取的字段列表:")
            for i, field in enumerate(fields, 1):
                print(f"  {i:2d}. {field['label']:<15} | {field['type']:<10} | {field['selector']}")

            print(f"\n📊 字段类型统计:")
            field_types = {}
            for field in fields:
                field_type = field.get('type', 'unknown')
                field_types[field_type] = field_types.get(field_type, 0) + 1

            for field_type, count in field_types.items():
                print(f"  - {field_type}: {count}个")

        else:
            print(f"❌ 字段提取失败: {result.get('error', '未知错误')}")

        return result

    except Exception as e:
        print(f"❌ Phase 2测试异常: {str(e)}")
        return {'success': False, 'error': str(e)}


async def test_phase4_label_matching():
    """测试Phase 4: 标签匹配"""
    print("\n" + "="*60)
    print("🧪 测试Phase 4: 标签匹配")
    print("="*60)

    try:
        from app.services.form_field_extractor import form_field_extractor
        from app.services.label_matching_service import label_matching_service

        # 先提取字段
        field_result = await form_field_extractor.extract_form_fields(TEST_HTML)
        if not field_result['success']:
            print("❌ 字段提取失败，无法进行匹配测试")
            return {'success': False}

        fields = field_result['fields']

        # 模拟大模型识别结果
        mock_llm_mappings = {
            "姓名": "张小明",
            "性别": "男",
            "手机号": "13812345678",
            "邮箱地址": "zhangxiaoming@example.com",
            "毕业院校": "北京大学",
            "专业": "计算机科学与技术",
            "学历": "本科",
            "工作年限": "2年",
            "期望薪资": "12k-20k"
        }

        print(f"🧠 模拟大模型识别: {len(mock_llm_mappings)}个字段")
        for label, value in mock_llm_mappings.items():
            print(f"  - {label}: {value}")

        # 执行匹配
        matching_result = label_matching_service.match_fields(mock_llm_mappings, fields)

        if matching_result['success']:
            matched = matching_result['matching_results']
            stats = matching_result['statistics']

            print(f"\n✅ 标签匹配完成:")
            print(f"  📊 匹配率: {stats['match_rate']:.1%} ({stats['matched_count']}/{stats['total_llm_fields']})")

            print(f"\n🔍 匹配结果:")
            for i, match in enumerate(matched, 1):
                print(f"  {i:2d}. {match['llm_label']:<10} → {match['form_label']:<15} | {match['match_type']:<8} | {match['confidence']:.2f}")

            unmatched_llm = matching_result.get('unmatched_llm_fields', [])
            if unmatched_llm:
                print(f"\n⚠️ 未匹配的大模型字段:")
                for field in unmatched_llm:
                    print(f"  - {field['label']}: {field['value']}")

        else:
            print(f"❌ 标签匹配失败: {matching_result.get('error', '未知错误')}")

        return matching_result

    except Exception as e:
        print(f"❌ Phase 4测试异常: {str(e)}")
        return {'success': False, 'error': str(e)}


async def test_full_analysis(enable_llm=False):
    """测试完整分析流程"""
    print("\n" + "="*60)
    print("🧪 测试完整分析流程")
    print("="*60)

    try:
        config = {
            'enable_form_filling': False,  # 测试时不实际填写
            'viewport_width': 1200,
            'viewport_height': 1000
        }

        if enable_llm:
            print("🧠 启用大模型分析...")
            result = await new_visual_analysis_service.analyze_and_fill_form(
                html_content=TEST_HTML,
                resume_data=TEST_RESUME_DATA,
                website_url="https://test.example.com/apply",
                config=config
            )
        else:
            print("🔍 仅进行表单结构分析...")
            result = await new_visual_analysis_service.analyze_form_structure_only(
                html_content=TEST_HTML,
                website_url="https://test.example.com/apply"
            )

        if result['success']:
            if 'statistics' in result:
                stats = result['statistics']
                print(f"\n📊 分析统计:")
                print(f"  - 总字段数: {stats.get('total_form_fields', 0)}")
                print(f"  - 大模型识别: {stats.get('llm_recognized_fields', 0)}")
                print(f"  - 成功匹配: {stats.get('successfully_matched_fields', 0)}")
                print(f"  - 总体成功率: {stats.get('overall_success_rate', 0):.1%}")
                print(f"  - 分析耗时: {stats.get('analysis_time_seconds', 0):.2f}秒")

                if enable_llm and 'phase_results' in result:
                    phase_results = result['phase_results']

                    print(f"\n🔄 各Phase执行情况:")
                    print(f"  Phase 1 (截图): {'✅' if phase_results['phase1_screenshot']['success'] else '❌'}")
                    print(f"  Phase 2 (字段提取): {'✅' if phase_results['phase2_field_extraction']['success'] else '❌'}")
                    print(f"  Phase 3 (视觉分析): {'✅' if phase_results['phase3_visual_llm']['success'] else '❌'}")
                    print(f"  Phase 4 (标签匹配): {'✅' if phase_results['phase4_label_matching']['success'] else '❌'}")

                    # 显示匹配的字段
                    matching_results = phase_results['phase4_label_matching'].get('matching_results', [])
                    if matching_results:
                        print(f"\n🎯 成功匹配的字段:")
                        for match in matching_results[:10]:  # 显示前10个
                            print(f"  - {match['form_label']}: {match['value']} ({match['match_type']})")
            else:
                print(f"\n✅ 表单结构分析成功:")
                print(f"  - 总字段数: {result.get('total_fields', 0)}")
                print(f"  - 字段类型: {result.get('field_types', {})}")

        else:
            print(f"❌ 分析失败: {result.get('error', '未知错误')}")

        return result

    except Exception as e:
        print(f"❌ 完整分析测试异常: {str(e)}")
        return {'success': False, 'error': str(e)}


async def main():
    """主测试函数"""
    parser = argparse.ArgumentParser(description='新视觉分析方案测试')
    parser.add_argument('--test-phase', choices=['2', '4', 'full'], default='full',
                      help='测试特定阶段 (2=字段提取, 4=标签匹配, full=完整流程)')
    parser.add_argument('--enable-llm', action='store_true',
                      help='启用大模型分析 (需要配置DASHSCOPE_API_KEY)')

    args = parser.parse_args()

    print("🚀 新视觉分析方案测试开始")
    print(f"⚙️ 测试配置: Phase={args.test_phase}, LLM={'开启' if args.enable_llm else '关闭'}")

    try:
        if args.test_phase == '2':
            await test_phase2_field_extraction()

        elif args.test_phase == '4':
            await test_phase4_label_matching()

        elif args.test_phase == 'full':
            await test_full_analysis(enable_llm=args.enable_llm)

        print(f"\n🎉 测试完成!")

    except KeyboardInterrupt:
        print(f"\n⏹️ 测试被用户中断")

    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {str(e)}")

    finally:
        # 清理资源
        try:
            await new_visual_analysis_service.close_all_browsers()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
