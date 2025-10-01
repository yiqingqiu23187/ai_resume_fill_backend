#!/usr/bin/env python3
"""
统一视觉分析API接口测试脚本

测试 analyze_visual_form 接口的功能
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import httpx
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 测试配置
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/v1/visual-unified/analyze"
STATUS_ENDPOINT = f"{BASE_URL}/api/v1/visual-unified/status"

# 从数据库查询得到的测试数据
TEST_USER_EMAIL = "huangzihao1218@gmail.com"
TEST_USER_ID = "26fc711c-0146-49b6-bbf4-a1dc65a6012e"
TEST_RESUME_ID = "479cca5a-307e-4e84-b945-a02762f17e73"

# 测试网站URL
TEST_WEBSITE_URL = "https://example-recruitment.com/apply"


async def get_access_token(email: str = TEST_USER_EMAIL) -> str:
    """获取访问令牌"""
    print(f"🔑 获取用户 {email} 的访问令牌...")

    # 登录接口
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_data = {
        "email": email,
        "password": "qwer1234"  # 真实的测试密码
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(login_url, json=login_data)
            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token")
                print(f"✅ 成功获取令牌: {token[:20]}...")
                return token
            else:
                print(f"❌ 登录失败: {response.status_code}")
                print(f"响应内容: {response.text}")

                # 如果登录失败，尝试注册用户
                print("🔧 尝试注册新用户...")
                return await register_user(email)

        except Exception as e:
            print(f"❌ 登录请求失败: {e}")
            return await register_user(email)


async def register_user(email: str) -> str:
    """注册新用户"""
    print(f"📝 注册新用户: {email}")

    register_url = f"{BASE_URL}/api/v1/auth/register"
    register_data = {
        "email": email,
        "password": "qwer1234"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(register_url, json=register_data)
            if response.status_code == 201:
                result = response.json()
                token = result.get("access_token")
                print(f"✅ 用户注册成功，获取令牌: {token[:20]}...")
                return token
            else:
                print(f"❌ 注册失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                raise Exception("无法注册用户")

        except Exception as e:
            print(f"❌ 注册请求失败: {e}")
            raise


def load_test_html() -> str:
    """加载测试HTML内容"""
    print("📄 加载测试HTML文件...")

    # 从项目根目录读取 test_html.txt
    html_file_path = project_root.parent / "test_html.txt"

    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 去除外层的引号
        if html_content.startswith('"') and html_content.endswith('"'):
            html_content = html_content[1:-1]

        # 处理转义字符
        html_content = html_content.replace('\\"', '"').replace('\\n', '\n')

        print(f"✅ 成功加载HTML文件，内容长度: {len(html_content)} 字符")
        return html_content

    except FileNotFoundError:
        print(f"❌ 找不到测试HTML文件: {html_file_path}")
        raise
    except Exception as e:
        print(f"❌ 读取HTML文件失败: {e}")
        raise


async def test_analyze_visual_form():
    """测试视觉分析接口"""
    print("🚀 开始测试统一视觉分析API接口\n")

    try:
        # 1. 获取访问令牌
        access_token = await get_access_token()

        # 2. 加载测试HTML
        html_content = load_test_html()

        # 3. 准备请求数据
        request_data = {
            "resume_id": TEST_RESUME_ID,
            "html_content": html_content,
            "website_url": TEST_WEBSITE_URL
        }

        # 4. 设置请求头
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        print(f"📊 准备发送请求到: {API_ENDPOINT}")
        print(f"简历ID: {TEST_RESUME_ID}")
        print(f"网站URL: {TEST_WEBSITE_URL}")
        print(f"HTML内容长度: {len(html_content)} 字符")
        print()

        # 5. 发送分析请求
        async with httpx.AsyncClient(timeout=300.0) as client:  # 设置5分钟超时
            print("⏳ 发送视觉分析请求...")

            response = await client.post(
                API_ENDPOINT,
                json=request_data,
                headers=headers
            )

            print(f"📈 响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✅ 视觉分析请求成功!")
                print(f"📊 响应数据:")
                print(json.dumps(result, indent=2, ensure_ascii=False))

                # 检查返回的匹配结果
                if result.get("success"):
                    matching_results = result.get("matching_results", [])
                    print(f"\n🎯 匹配结果统计:")
                    print(f"总共匹配字段数: {len(matching_results)}")

                    # 显示前5个匹配结果作为示例
                    if matching_results:
                        print("\n📋 匹配结果示例 (前5个):")
                        for i, match in enumerate(matching_results[:5]):
                            print(f"  {i+1}. 选择器: {match.get('selector', 'N/A')}")
                            print(f"     值: {match.get('value', 'N/A')}")
                            print()

                return result

            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"错误响应: {response.text}")
                return None

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_status_endpoint(request_id: str):
    """测试状态查询接口"""
    print(f"\n📊 测试状态查询接口 - 请求ID: {request_id}")

    try:
        # 获取访问令牌
        access_token = await get_access_token()

        # 设置请求头
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        # 发送状态查询请求
        status_url = f"{STATUS_ENDPOINT}/{request_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(status_url, headers=headers)

            print(f"📈 状态查询响应码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✅ 状态查询成功!")
                print(f"📊 状态信息:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            else:
                print(f"❌ 状态查询失败: {response.status_code}")
                print(f"错误响应: {response.text}")
                return None

    except Exception as e:
        print(f"❌ 状态查询错误: {e}")
        return None


def print_test_summary():
    """打印测试总结"""
    print("\n" + "="*60)
    print("🧪 测试总结")
    print("="*60)
    print(f"测试用户: {TEST_USER_EMAIL}")
    print(f"用户ID: {TEST_USER_ID}")
    print(f"简历ID: {TEST_RESUME_ID}")
    print(f"测试网站: {TEST_WEBSITE_URL}")
    print(f"API端点: {API_ENDPOINT}")
    print("="*60)


async def main():
    """主函数"""
    print("🎯 统一视觉分析API测试脚本")
    print("="*60)

    # 打印测试配置
    print_test_summary()

    try:
        # 测试主要的分析接口
        result = await test_analyze_visual_form()

        # 如果有返回request_id，测试状态查询接口
        if result and "request_id" in result:
            await test_status_endpoint(result["request_id"])

        print("\n✅ 测试完成!")

    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
