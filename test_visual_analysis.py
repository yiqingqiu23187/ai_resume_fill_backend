#!/usr/bin/env python3
"""
Phase 1 视觉分析功能测试脚本

用于验证截图服务、BBOX提取服务和视觉分析服务的基本功能
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.visual.screenshot_service import screenshot_service
from app.services.visual.bbox_service import bbox_service
from app.services.visual.visual_analysis_service import visual_analysis_service


async def test_screenshot_service():
    """测试截图服务"""
    print("\n🔧 测试1: 截图服务")

    # 创建一个简单的测试HTML
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试表单</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, textarea {
                width: 300px;
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            .submit-btn {
                background: #007bff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <h2>个人信息表单</h2>
        <form id="testForm">
            <div class="form-group">
                <label for="name">姓名:</label>
                <input type="text" id="name" name="name" placeholder="请输入姓名">
            </div>

            <div class="form-group">
                <label for="email">邮箱:</label>
                <input type="email" id="email" name="email" placeholder="请输入邮箱">
            </div>

            <div class="form-group">
                <label for="phone">电话:</label>
                <input type="tel" id="phone" name="phone" placeholder="请输入电话号码">
            </div>

            <div class="form-group">
                <label for="gender">性别:</label>
                <select id="gender" name="gender">
                    <option value="">请选择</option>
                    <option value="male">男</option>
                    <option value="female">女</option>
                </select>
            </div>

            <div class="form-group">
                <label for="bio">个人简介:</label>
                <textarea id="bio" name="bio" rows="4" placeholder="请输入个人简介"></textarea>
            </div>

            <button type="submit" class="submit-btn">提交</button>
        </form>
    </body>
    </html>
    """

    try:
        # 测试截图功能
        screenshot_result = await screenshot_service.take_screenshot_from_html(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=800
        )

        print(f"✅ 截图生成成功:")
        print(f"   📄 文件路径: {screenshot_result['screenshot_path']}")
        print(f"   📏 文件大小: {screenshot_result['file_size']} 字节")
        print(f"   🖼️ 页面尺寸: {screenshot_result['actual_size']}")

        return screenshot_result, test_html

    except Exception as e:
        print(f"❌ 截图服务测试失败: {str(e)}")
        return None, test_html


async def test_bbox_service(test_html):
    """测试BBOX提取服务"""
    print("\n🔧 测试2: BBOX提取服务")

    try:
        # 测试BBOX提取功能
        bbox_result = await bbox_service.extract_element_bboxes(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=800
        )

        if bbox_result.get('success'):
            elements = bbox_result['bbox_data']['elements']
            print(f"✅ BBOX提取成功:")
            print(f"   🎯 发现元素: {len(elements)} 个")
            print(f"   📊 HTML分析: {bbox_result['html_analysis']['total_form_elements']} 个表单元素")

            # 显示前几个元素的详细信息
            for i, element in enumerate(elements[:3]):
                print(f"   元素 {i+1}: {element['tag']}[{element['type']}]")
                print(f"      选择器: {element['selector']}")
                print(f"      坐标: ({element['bbox']['x']}, {element['bbox']['y']}) 尺寸: {element['bbox']['width']}x{element['bbox']['height']}")
                if element['associated_labels']:
                    labels = [label['text'] for label in element['associated_labels']]
                    print(f"      关联标签: {', '.join(labels)}")

            if len(elements) > 3:
                print(f"   ... 还有 {len(elements) - 3} 个元素")
        else:
            print(f"❌ BBOX提取失败: {bbox_result.get('error')}")
            return None

        return bbox_result

    except Exception as e:
        print(f"❌ BBOX服务测试失败: {str(e)}")
        return None


async def test_visual_analysis_service(test_html):
    """测试完整的视觉分析服务"""
    print("\n🔧 测试3: 完整视觉分析流程")

    try:
        # 测试完整的视觉分析流程
        analysis_config = {
            'viewport_width': 1200,
            'viewport_height': 800,
            'full_page': True,
            'screenshot_timeout': 3000
        }

        analysis_result = await visual_analysis_service.analyze_html_visual(
            html_content=test_html,
            website_url="test://localhost/form",
            analysis_config=analysis_config
        )

        if analysis_result.get('success'):
            print(f"✅ 视觉分析成功:")
            print(f"   🎯 识别元素: {analysis_result['elements']['total_count']} 个")
            print(f"   🔗 空间关系: {analysis_result['relationships']['total_relationships']} 对")
            print(f"   📊 分析摘要: {analysis_result['summary']}")
            print(f"   📸 截图文件: {analysis_result['screenshot']['filename']}")

            # 显示质量指标
            metrics = analysis_result['summary']['quality_metrics']
            print(f"   📈 质量指标:")
            print(f"      标签覆盖率: {metrics['labeling_rate']}%")
            print(f"      填写率: {metrics['fill_rate']}%")
            print(f"      结构复杂度: {metrics['structure_complexity']}")
        else:
            print(f"❌ 视觉分析失败: {analysis_result.get('error')}")
            return None

        return analysis_result

    except Exception as e:
        print(f"❌ 视觉分析服务测试失败: {str(e)}")
        return None


async def cleanup_test_resources():
    """清理测试资源"""
    print("\n🧹 清理测试资源")

    try:
        await screenshot_service.close()
        await bbox_service.close()
        await visual_analysis_service.cleanup_resources()
        print("✅ 资源清理完成")
    except Exception as e:
        print(f"⚠️ 资源清理时出现错误: {str(e)}")


async def main():
    """主测试流程"""
    print("🚀 Phase 1 视觉分析功能测试开始")
    print("=" * 60)

    try:
        # 测试1: 截图服务
        screenshot_result, test_html = await test_screenshot_service()
        if not screenshot_result:
            print("❌ 截图服务测试失败，停止后续测试")
            return

        # 测试2: BBOX提取服务
        bbox_result = await test_bbox_service(test_html)
        if not bbox_result:
            print("❌ BBOX提取服务测试失败，停止后续测试")
            return

        # 测试3: 完整视觉分析服务
        analysis_result = await test_visual_analysis_service(test_html)
        if not analysis_result:
            print("❌ 视觉分析服务测试失败")
            return

        print("\n" + "=" * 60)
        print("🎉 Phase 1 所有功能测试通过！")
        print("\n📋 测试总结:")
        print(f"   ✅ 截图服务: 正常工作")
        print(f"   ✅ BBOX提取: 识别了 {bbox_result['total_elements']} 个元素")
        print(f"   ✅ 视觉分析: 完整流程正常")
        print(f"   ✅ 空间关系: 分析了 {analysis_result['relationships']['total_relationships']} 对关系")

        print("\n🔄 Phase 1 完成状态:")
        print("   ✅ 环境搭建与依赖引入")
        print("   ✅ 截图服务开发")
        print("   ✅ BBOX提取服务")
        print("   ✅ 视觉分析API接口")
        print("   ✅ 功能测试验证")

        print("\n🎯 下一步: Phase 2 - 计算机视觉核心算法")
        print("   🔄 XY-Cut算法实现")
        print("   🔄 形态学聚类算法")
        print("   🔄 算法融合与优化")

    except Exception as e:
        print(f"❌ 测试过程中出现异常: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        await cleanup_test_resources()


if __name__ == "__main__":
    # 创建screenshots目录
    os.makedirs("screenshots", exist_ok=True)

    # 运行测试
    asyncio.run(main())
