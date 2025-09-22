#!/usr/bin/env python3
"""
API接口测试脚本
测试真实的API接口而不是使用模拟数据
"""

import asyncio
import json
import sys
import requests
from pathlib import Path
from uuid import UUID, uuid4
from typing import Dict, Any, Optional, List

# 基本配置
API_BASE_URL = "http://localhost:8000/api/v1"
ACCESS_TOKEN = None  # 将在登录后设置


def print_header(title):
    """打印测试标题"""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


def print_response(response, show_content=True):
    """打印响应信息"""
    print(f"状态码: {response.status_code}")
    if show_content:
        try:
            content = response.json()
            print(f"响应内容: {json.dumps(content, ensure_ascii=False, indent=2)}")
        except:
            print(f"响应内容: {response.text[:200]}...")


def api_request(method, endpoint, data=None, token=None, params=None):
    """发送API请求"""
    url = f"{API_BASE_URL}/{endpoint}"
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if data is not None:
        headers["Content-Type"] = "application/json"
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            params=params
        )
    else:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params
        )

    return response


def test_register_user():
    """测试用户注册"""
    print_header("测试用户注册")

    # 生成随机邮箱以避免冲突
    email = f"test_{uuid4().hex[:8]}@example.com"
    data = {
        "email": email,
        "password": "testpass123"
    }

    response = api_request("POST", "auth/register", data)
    print_response(response)

    if response.status_code in [200, 201]:
        print(f"✅ 用户注册成功: {email}")
        return email
    else:
        print(f"❌ 用户注册失败")
        return None


def test_login(email, password="testpass123"):
    """测试用户登录"""
    print_header("测试用户登录")

    data = {
        "email": email,
        "password": password
    }

    response = api_request("POST", "auth/login", data)
    print_response(response)

    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"✅ 用户登录成功，获取到token")
        return token
    else:
        print(f"❌ 用户登录失败")
        return None


def test_create_activation_code(token):
    """测试创建激活码"""
    print_header("测试创建激活码")

    data = {
        "code": f"TEST{uuid4().hex[:8].upper()}",
        "total_uses": 10
    }

    response = api_request("POST", "activations/codes", data, token)
    print_response(response)

    if response.status_code == 200:
        code = response.json().get("code")
        print(f"✅ 激活码创建成功: {code}")
        return code
    else:
        print(f"❌ 激活码创建失败")
        return None


def test_activate_user(token, code):
    """测试激活用户"""
    print_header("测试激活用户")

    data = {
        "code": code
    }

    response = api_request("POST", "activations/activate", data, token)
    print_response(response)

    if response.status_code == 200:
        print(f"✅ 用户激活成功")
        return True
    else:
        print(f"❌ 用户激活失败")
        return False


def test_create_resume(token):
    """测试创建简历"""
    print_header("测试创建简历")

    data = {
        "title": "测试简历",
        "fields": {
            "name": "张三",
            "email": "zhangsan@example.com",
            "phone": "13800138000",
            "address": "北京市朝阳区",
            "self_introduction": "具有5年Python开发经验的软件工程师",
            "university": "清华大学",
            "degree": "本科",
            "major": "计算机科学与技术",
            "education_start_date": "2015-09",
            "education_end_date": "2019-07",
            "current_company": "阿里巴巴",
            "current_position": "Python开发工程师",
            "work_start_date": "2019-07",
            "work_end_date": "2024-01",
            "responsibilities": "开发Web应用，优化数据库性能",
            "achievements": "提升系统性能30%",
            "programming_languages": "Python",
            "frameworks": "Django"
        }
    }

    response = api_request("POST", "resumes", data, token)
    print_response(response)

    if response.status_code in [200, 201]:
        resume_id = response.json().get("id")
        print(f"✅ 简历创建成功: ID={resume_id}")
        return resume_id
    else:
        print(f"❌ 简历创建失败")
        return None


def test_get_resumes(token):
    """测试获取简历列表"""
    print_header("测试获取简历列表")

    response = api_request("GET", "resumes", token=token)
    print_response(response)

    if response.status_code == 200:
        resumes = response.json()
        print(f"✅ 获取简历列表成功: 数量={len(resumes)}")
        return resumes
    else:
        print(f"❌ 获取简历列表失败")
        return []


def test_get_resume(token, resume_id):
    """测试获取简历详情"""
    print_header("测试获取简历详情")

    response = api_request("GET", f"resumes/{resume_id}", token=token)
    print_response(response)

    if response.status_code == 200:
        resume = response.json()
        print(f"✅ 获取简历详情成功: 标题={resume.get('title')}")
        return resume
    else:
        print(f"❌ 获取简历详情失败")
        return None


def test_match_fields(token, resume_id):
    """测试字段匹配"""
    print_header("测试字段匹配API")

    # 表单字段
    form_fields = [
        {
            "name": "fullName",
            "type": "text",
            "label": "姓名",
            "placeholder": "请输入您的姓名"
        },
        {
            "name": "email",
            "type": "email",
            "label": "邮箱",
            "placeholder": "请输入邮箱地址"
        },
        {
            "name": "phone",
            "type": "tel",
            "label": "联系电话"
        },
        {
            "name": "education",
            "type": "select",
            "label": "学历",
            "options": ["高中", "大专", "本科", "硕士", "博士"]
        },
        {
            "name": "workYears",
            "type": "select",
            "label": "工作年限",
            "options": ["应届毕业生", "1-3年", "3-5年", "5-10年", "10年以上"]
        }
    ]

    data = {
        "resume_id": resume_id,
        "form_fields": form_fields,
        "website_url": "https://jobs.example.com"
    }

    response = api_request("POST", "matching/match-fields", data, token)
    print_response(response)

    if response.status_code == 200:
        result = response.json()
        matches = result.get("matches", [])
        print(f"✅ 字段匹配成功: 匹配数量={len(matches)}")

        # 打印匹配结果
        for match in matches:
            print(f"  - {match['field_name']}: {match['matched_value']}")

        return matches
    else:
        print(f"❌ 字段匹配失败")
        return []


def test_get_match_stats(token):
    """测试获取匹配统计"""
    print_header("测试获取匹配统计")

    response = api_request("GET", "matching/match-stats", token=token)
    print_response(response)

    if response.status_code == 200:
        stats = response.json()
        print(f"✅ 获取匹配统计成功")
        print(f"  - 总使用次数: {stats.get('total_uses', 0)}")
        print(f"  - 总字段数: {stats.get('total_fields', 0)}")
        print(f"  - 成功匹配数: {stats.get('total_successes', 0)}")
        print(f"  - 成功率: {stats.get('success_rate', 0)}")
        return stats
    else:
        print(f"❌ 获取匹配统计失败")
        return None


def test_get_supported_field_types():
    """测试获取支持的字段类型"""
    print_header("测试获取支持的字段类型")

    response = api_request("GET", "matching/supported-field-types")
    print_response(response)

    if response.status_code == 200:
        field_types = response.json().get("field_types", [])
        print(f"✅ 获取支持的字段类型成功: 数量={len(field_types)}")
        return field_types
    else:
        print(f"❌ 获取支持的字段类型失败")
        return []


def test_update_resume_fields(token, resume_id):
    """测试更新简历字段"""
    print_header("测试更新简历字段")

    data = {
        "skills": "Python, Django, FastAPI, Vue.js",
        "hobby": "阅读, 旅行, 编程"
    }

    response = api_request("PATCH", f"resumes/{resume_id}/fields", data, token)
    print_response(response)

    if response.status_code == 200:
        updated_resume = response.json()
        print(f"✅ 更新简历字段成功")
        return updated_resume
    else:
        print(f"❌ 更新简历字段失败")
        return None


def test_delete_resume_field(token, resume_id, field_key):
    """测试删除简历字段"""
    print_header(f"测试删除简历字段: {field_key}")

    response = api_request("DELETE", f"resumes/{resume_id}/fields/{field_key}", token=token)
    print_response(response)

    if response.status_code == 200:
        print(f"✅ 删除简历字段成功: {field_key}")
        return True
    else:
        print(f"❌ 删除简历字段失败: {field_key}")
        return False


def test_get_resume_fields_by_category(token, resume_id):
    """测试按分类获取简历字段"""
    print_header("测试按分类获取简历字段")

    response = api_request("GET", f"resumes/{resume_id}/categories", token=token)
    print_response(response)

    if response.status_code == 200:
        categories = response.json()
        print(f"✅ 按分类获取简历字段成功: 分类数量={len(categories)}")
        return categories
    else:
        print(f"❌ 按分类获取简历字段失败")
        return None


def test_get_preset_fields():
    """测试获取预设字段模板"""
    print_header("测试获取预设字段模板")

    response = api_request("GET", "resumes/templates/preset-fields")
    print_response(response)

    if response.status_code == 200:
        result = response.json()
        all_fields = result.get("all_fields", [])
        categories = result.get("categories", [])
        print(f"✅ 获取预设字段模板成功: 字段数量={len(all_fields)}, 分类数量={len(categories)}")
        return result
    else:
        print(f"❌ 获取预设字段模板失败")
        return None


def test_delete_resume(token, resume_id):
    """测试删除简历"""
    print_header("测试删除简历")

    response = api_request("DELETE", f"resumes/{resume_id}", token=token)
    print_response(response)

    if response.status_code in [200, 204]:
        print(f"✅ 删除简历成功: ID={resume_id}")
        return True
    else:
        print(f"❌ 删除简历失败: ID={resume_id}")
        return False


def main():
    """主测试函数"""
    print("\n🧪 开始API接口测试...\n")

    # 测试用户注册和登录
    email = test_register_user()
    if not email:
        email = "apitest@example.com"  # 使用已存在的测试账号

    token = test_login(email)
    if not token:
        print("❌ 无法获取访问令牌，测试终止")
        return

    # 测试激活码和激活
    code = test_create_activation_code(token)
    if code:
        test_activate_user(token, code)

    # 测试简历管理
    resume_id = test_create_resume(token)
    if not resume_id:
        print("❌ 无法创建简历，跳过相关测试")
        return

    test_get_resumes(token)
    test_get_resume(token, resume_id)

    # 测试字段匹配
    test_match_fields(token, resume_id)
    test_get_match_stats(token)

    # 测试支持的字段类型
    test_get_supported_field_types()

    # 测试简历字段操作
    test_update_resume_fields(token, resume_id)
    test_get_resume_fields_by_category(token, resume_id)
    test_delete_resume_field(token, resume_id, "hobby")

    # 测试预设字段模板
    test_get_preset_fields()

    # 测试删除简历
    test_delete_resume(token, resume_id)

    print("\n🎉 API接口测试完成！")


if __name__ == "__main__":
    main()
