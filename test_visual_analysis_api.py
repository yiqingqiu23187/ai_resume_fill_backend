"""
新视觉分析API测试脚本
测试完整的智能表单分析和填写API接口
"""

import asyncio
import json
import sys
from datetime import datetime

import httpx

# 测试配置
API_BASE_URL = "http://localhost:8000/api/v1"
ANALYZE_ENDPOINT = f"{API_BASE_URL}/v2/visual-analysis/analyze"

# 测试HTML内容
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>测试招聘表单</title>
    <style>
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>简历信息填写</h1>
    <form id="resumeForm">
        <div class="form-group">
            <label for="name">姓名 *</label>
            <input type="text" id="name" name="name" required>
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
            <label for="phone">手机号</label>
            <input type="tel" id="phone" name="phone">
        </div>

        <div class="form-group">
            <label for="email">邮箱地址</label>
            <input type="email" id="email" name="email">
        </div>

        <div class="form-group">
            <label for="school">毕业院校</label>
            <input type="text" id="school" name="school">
        </div>

        <div class="form-group">
            <label for="major">专业</label>
            <input type="text" id="major" name="major">
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
            <label for="experience">工作经验</label>
            <select id="experience" name="experience">
                <option value="">请选择</option>
                <option value="0-1">0-1年</option>
                <option value="1-3">1-3年</option>
                <option value="3-5">3-5年</option>
                <option value="5+">5年以上</option>
            </select>
        </div>

        <div class="form-group">
            <label for="self_intro">自我介绍</label>
            <textarea id="self_intro" name="self_intro" rows="4" placeholder="请简单介绍一下自己"></textarea>
        </div>

        <div class="form-group">
            <button type="submit">提交申请</button>
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
        "地址": "北京市朝阳区"
    },
    "education": [
        {
            "school": "北京大学",
            "major": "计算机科学与技术",
            "degree": "本科",
            "start_date": "2018-09",
            "end_date": "2022-06",
            "gpa": "3.8"
        }
    ],
    "experience": [
        {
            "company": "字节跳动",
            "position": "前端工程师",
            "start_date": "2022-07",
            "end_date": "2024-01",
            "description": "负责抖音Web端开发"
        }
    ],
    "skills": ["JavaScript", "Vue.js", "React", "Python", "Node.js"],
    "projects": [
        {
            "name": "电商管理系统",
            "description": "基于Vue.js开发的后台管理系统",
            "start_date": "2023-01",
            "end_date": "2023-06"
        }
    ]
}




async def test_complete_analysis():
    """测试完整分析API"""
    print("\n🧠 测试完整分析API...")

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "html_content": TEST_HTML,
                "resume_data": TEST_RESUME_DATA,
                "website_url": "test://recruitment.example.com",
                "config": {
                    "viewport_width": 1200,
                    "viewport_height": 1400,
                    "enable_form_filling": False,  # 测试时不执行填写
                    "save_screenshot": True,
                    "save_analysis_result": True
                }
            }

            print("⏳ 发送分析请求...")
            response = await client.post(
                ANALYZE_ENDPOINT,
                json=payload,
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    print("✅ 完整分析成功!")
                    print(f"   网站: {result.get('website_url', 'N/A')}")
                    print(f"   分析耗时: {result.get('analysis_time', 0):.2f}秒")

                    # 显示各阶段状态
                    phase_status = result.get('phase_status', {})
                    print("\n📊 各阶段执行情况:")
                    for phase_name, status in phase_status.items():
                        status_icon = "✅" if status.get('success') else "❌"
                        print(f"   {status_icon} {phase_name}: {status.get('message', '')}")

                    # 显示统计信息
                    stats = result.get('statistics', {})
                    print(f"\n📈 分析统计:")
                    print(f"   表单字段总数: {stats.get('total_form_fields', 0)}")
                    print(f"   大模型识别: {stats.get('llm_recognized_fields', 0)}")
                    print(f"   成功匹配: {stats.get('successfully_matched_fields', 0)}")
                    print(f"   总体成功率: {stats.get('overall_success_rate', 0):.1%}")

                    # 显示匹配的字段
                    matched_fields = result.get('matched_fields', [])
                    if matched_fields:
                        print(f"\n🎯 匹配字段 ({len(matched_fields)}个):")
                        for i, field in enumerate(matched_fields, 1):
                            print(f"   {i}. {field.get('form_label', '')}: {field.get('value', '')} ({field.get('match_type', '')})")

                    # 显示填写脚本
                    fill_script = result.get('fill_script')
                    if fill_script:
                        print(f"\n📝 生成填写脚本: {len(fill_script)}字符")

                    return True
                else:
                    print(f"❌ 分析失败: {result.get('error', '未知错误')}")
                    print(f"   失败阶段: {result.get('failed_phase', 'unknown')}")
                    return False
            else:
                print(f"❌ API请求失败: {response.status_code}")
                print(f"   错误详情: {response.text}")
                return False

    except Exception as e:
        print(f"❌ 完整分析测试异常: {str(e)}")
        return False


async def test_error_handling():
    """测试错误处理"""
    print("\n🚨 测试错误处理...")

    try:
        async with httpx.AsyncClient() as client:
            # 测试无效HTML
            payload = {
                "html_content": "",  # 空HTML
                "resume_data": TEST_RESUME_DATA,
                "website_url": "test://invalid.com"
            }

            response = await client.post(
                ANALYZE_ENDPOINT,
                json=payload,
                timeout=30.0
            )

            if response.status_code == 422:
                print("✅ 输入验证错误处理正确 (422)")
                return True
            elif response.status_code == 200:
                result = response.json()
                if not result.get('success'):
                    print("✅ 业务逻辑错误处理正确")
                    return True

            print(f"⚠️ 错误处理结果: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 错误处理测试异常: {str(e)}")
        return False


async def check_api_availability():
    """检查API可用性"""
    print("🔗 检查API服务可用性...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/status", timeout=10.0)

            if response.status_code == 200:
                print("✅ API服务正常运行")
                return True
            else:
                print(f"❌ API服务异常: {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ 无法连接API服务: {str(e)}")
        print("💡 请确保后端服务正在运行 (python -m uvicorn app.main:app --reload)")
        return False


async def main():
    """主测试函数"""
    print("🚀 新视觉分析API测试开始")
    print("=" * 50)

    # 检查API可用性
    if not await check_api_availability():
        print("\n❌ API服务不可用，测试终止")
        return

    results = []

    # 测试完整分析
    results.append(await test_complete_analysis())

    # 测试错误处理
    results.append(await test_error_handling())

    # 总结
    print("\n" + "=" * 50)
    success_count = sum(results)
    total_count = len(results)

    print(f"🎯 测试完成: {success_count}/{total_count} 通过")

    if success_count == total_count:
        print("🎉 所有测试通过! API准备就绪!")
    else:
        print("⚠️ 部分测试失败，请检查日志")

    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    # 设置环境变量提示
    print("💡 测试前请确保:")
    print("   1. 后端服务正在运行: python -m uvicorn app.main:app --reload")
    print("   2. 已配置DASHSCOPE_API_KEY环境变量")
    print("   3. 数据库连接正常")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试运行异常: {str(e)}")
