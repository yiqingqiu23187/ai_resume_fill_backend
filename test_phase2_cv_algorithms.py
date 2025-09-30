#!/usr/bin/env python3
"""
Phase 2 计算机视觉算法测试脚本

测试XY-Cut算法、形态学聚类算法和算法融合功能
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.visual.screenshot_service import screenshot_service
from app.services.visual.bbox_service import bbox_service
from app.services.visual.visual_analysis_service import visual_analysis_service
from app.services.cv.xy_cut import XYCutAnalyzer
from app.services.cv.morphology_cluster import MorphologyCluster
from app.services.cv.visual_analyzer import VisualLayoutAnalyzer


def print_detailed_analysis_results(result):
    """打印详细的分析结果，包括识别的字段和区域信息"""
    print("\n" + "="*80)
    print("📋 **详细识别结果分析**")
    print("="*80)

    # 1. 打印识别的所有字段
    print("\n🔍 **1. 识别字段详情**")
    elements = result.get('elements', {}).get('elements_data', [])

    if elements:
        print(f"\n📊 总计识别字段: {len(elements)} 个")
        print("-" * 60)

        # 按字段类型分组显示
        field_types = {}
        for element in elements:
            field_type = element.get('type', 'unknown')
            if field_type not in field_types:
                field_types[field_type] = []
            field_types[field_type].append(element)

        for field_type, fields in field_types.items():
            print(f"\n🔹 {field_type.upper()} 字段 ({len(fields)}个):")
            for i, field in enumerate(fields, 1):
                name_attr = field.get('name', '')
                id_attr = field.get('id', '')
                placeholder = field.get('placeholder', '')

                # 获取关联的标签
                labels = field.get('associated_labels', [])
                label_texts = [label.get('text', '').strip() for label in labels if label.get('text', '').strip()]

                print(f"   {i:2d}. 选择器: {field.get('selector', 'N/A')}")
                if name_attr:
                    print(f"       name=\"{name_attr}\"")
                if id_attr:
                    print(f"       id=\"{id_attr}\"")
                if placeholder:
                    print(f"       placeholder=\"{placeholder}\"")
                if label_texts:
                    print(f"       🏷️ 关联标签: {', '.join(label_texts)}")
                else:
                    print(f"       ⚠️ 无关联标签")

                # 显示位置信息
                bbox = field.get('bbox', {})
                if bbox:
                    print(f"       📍 位置: ({bbox.get('x', 0)}, {bbox.get('y', 0)}) 尺寸: {bbox.get('width', 0)}x{bbox.get('height', 0)}")
                print()

    # 2. 打印视觉区域分组
    print("\n🎯 **2. 视觉区域分组**")
    visual_layout = result.get('visual_layout', {})

    if visual_layout.get('success'):
        regions = visual_layout.get('regions', [])
        print(f"\n📊 总计视觉区域: {len(regions)} 个")
        print("-" * 60)

        for i, region in enumerate(regions, 1):
            print(f"\n🔸 区域 {i} ({region.get('algorithm', 'unknown')}算法)")

            # 区域基本信息
            bbox = region.get('bbox', {})
            if bbox:
                print(f"   📍 区域范围: ({bbox.get('x', 0)}, {bbox.get('y', 0)}) 尺寸: {bbox.get('width', 0)}x{bbox.get('height', 0)}")

            # 区域内的元素
            region_elements = region.get('elements', [])
            if region_elements:
                print(f"   📋 包含元素 ({len(region_elements)}个):")
                for j, elem in enumerate(region_elements, 1):
                    elem_type = elem.get('type', 'unknown')
                    elem_name = elem.get('name', elem.get('id', ''))

                    # 找到对应的完整元素信息
                    full_element = None
                    for element in elements:
                        if element.get('selector') == elem.get('selector'):
                            full_element = element
                            break

                    if full_element:
                        labels = full_element.get('associated_labels', [])
                        label_texts = [label.get('text', '').strip() for label in labels if label.get('text', '').strip()]
                        label_display = f" 🏷️[{', '.join(label_texts)}]" if label_texts else " ⚠️[无标签]"
                    else:
                        label_display = ""

                    print(f"      {j:2d}. {elem_type}: {elem_name}{label_display}")
            else:
                print(f"   ⚠️ 区域内无元素")

            # 区域特征
            if region.get('confidence'):
                print(f"   🎯 置信度: {region.get('confidence', 0):.2f}")

    # 3. 打印标签关联统计
    print("\n🏷️ **3. 标签关联分析**")
    print("-" * 60)

    labeled_count = 0
    unlabeled_count = 0
    label_examples = []
    unlabeled_examples = []

    for element in elements:
        labels = element.get('associated_labels', [])
        label_texts = [label.get('text', '').strip() for label in labels if label.get('text', '').strip()]

        if label_texts:
            labeled_count += 1
            if len(label_examples) < 5:  # 只收集前5个例子
                elem_name = element.get('name', element.get('id', element.get('selector', ''))).replace('name="', '').replace('"', '')
                label_examples.append(f"{elem_name} ← {', '.join(label_texts)}")
        else:
            unlabeled_count += 1
            if len(unlabeled_examples) < 5:  # 只收集前5个例子
                elem_name = element.get('name', element.get('id', element.get('selector', ''))).replace('name="', '').replace('"', '')
                unlabeled_examples.append(elem_name)

    print(f"✅ 已关联标签: {labeled_count} 个字段")
    if label_examples:
        print(f"   示例:")
        for example in label_examples:
            print(f"      • {example}")

    print(f"\n⚠️ 未关联标签: {unlabeled_count} 个字段")
    if unlabeled_examples:
        print(f"   示例:")
        for example in unlabeled_examples:
            print(f"      • {example}")

    coverage_rate = (labeled_count / len(elements) * 100) if elements else 0
    print(f"\n📈 标签覆盖率: {coverage_rate:.1f}% ({labeled_count}/{len(elements)})")

    # 4. 算法性能分析
    print("\n⚡ **4. 算法性能分析**")
    print("-" * 60)

    if visual_layout.get('success'):
        fusion_stats = visual_layout.get('fusion_statistics', {})
        if fusion_stats:
            input_regions = fusion_stats.get('input_regions', {})
            output_regions = fusion_stats.get('output_regions', 0)

            print(f"🔀 算法融合过程:")
            if 'xy_cut' in input_regions:
                print(f"   • XY-Cut算法: {input_regions['xy_cut']} 个区域")
            if 'morphology' in input_regions:
                print(f"   • 形态学聚类: {input_regions['morphology']} 个区域")

            total_input = input_regions.get('total', 0)
            if total_input > 0:
                compression_ratio = (total_input - output_regions) / total_input * 100
                print(f"   • 总输入区域: {total_input} 个")
                print(f"   • 最终输出区域: {output_regions} 个")
                print(f"   • 优化压缩率: {compression_ratio:.1f}%")

    print("\n" + "="*80)


def create_complex_test_html():
    """创建复杂的测试HTML表单"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>复杂表单测试</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; padding: 20px; background: #f5f5f5; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
            .section { margin: 30px 0; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }
            .section-title { font-size: 18px; font-weight: bold; margin-bottom: 20px; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            .form-row { display: flex; gap: 20px; margin: 15px 0; }
            .form-group { flex: 1; }
            .form-group-half { flex: 0.5; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
            input, select, textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                box-sizing: border-box;
            }
            .submit-section { text-align: center; margin-top: 30px; padding: 20px; }
            .submit-btn {
                background: #007bff;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin: 0 10px;
            }
            .education-item, .experience-item {
                border: 1px dashed #ccc;
                padding: 15px;
                margin: 10px 0;
                background: #f9f9f9;
            }
            .checkbox-group { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; }
            .checkbox-item { display: flex; align-items: center; gap: 5px; margin-right: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>求职申请表</h1>

            <!-- 基本信息 -->
            <div class="section">
                <div class="section-title">基本信息</div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="fullName">姓名 *</label>
                        <input type="text" id="fullName" name="fullName" required>
                    </div>
                    <div class="form-group">
                        <label for="gender">性别</label>
                        <select id="gender" name="gender">
                            <option value="">请选择</option>
                            <option value="male">男</option>
                            <option value="female">女</option>
                        </select>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="phone">手机号 *</label>
                        <input type="tel" id="phone" name="phone" required>
                    </div>
                    <div class="form-group">
                        <label for="email">邮箱 *</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="birthDate">出生日期</label>
                        <input type="date" id="birthDate" name="birthDate">
                    </div>
                    <div class="form-group">
                        <label for="idCard">身份证号</label>
                        <input type="text" id="idCard" name="idCard">
                    </div>
                </div>

                <div class="form-group">
                    <label for="address">详细地址</label>
                    <textarea id="address" name="address" rows="3"></textarea>
                </div>
            </div>

            <!-- 教育背景 -->
            <div class="section">
                <div class="section-title">教育背景</div>
                <div class="education-item">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="edu1_school">学校名称</label>
                            <input type="text" id="edu1_school" name="education[0][school]">
                        </div>
                        <div class="form-group">
                            <label for="edu1_degree">学历</label>
                            <select id="edu1_degree" name="education[0][degree]">
                                <option value="">请选择</option>
                                <option value="bachelor">本科</option>
                                <option value="master">硕士</option>
                                <option value="doctor">博士</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="edu1_major">专业</label>
                            <input type="text" id="edu1_major" name="education[0][major]">
                        </div>
                        <div class="form-group-half">
                            <label for="edu1_start">开始时间</label>
                            <input type="date" id="edu1_start" name="education[0][startDate]">
                        </div>
                        <div class="form-group-half">
                            <label for="edu1_end">结束时间</label>
                            <input type="date" id="edu1_end" name="education[0][endDate]">
                        </div>
                    </div>
                </div>

                <div class="education-item">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="edu2_school">学校名称</label>
                            <input type="text" id="edu2_school" name="education[1][school]">
                        </div>
                        <div class="form-group">
                            <label for="edu2_degree">学历</label>
                            <select id="edu2_degree" name="education[1][degree]">
                                <option value="">请选择</option>
                                <option value="bachelor">本科</option>
                                <option value="master">硕士</option>
                                <option value="doctor">博士</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="edu2_major">专业</label>
                            <input type="text" id="edu2_major" name="education[1][major]">
                        </div>
                        <div class="form-group-half">
                            <label for="edu2_start">开始时间</label>
                            <input type="date" id="edu2_start" name="education[1][startDate]">
                        </div>
                        <div class="form-group-half">
                            <label for="edu2_end">结束时间</label>
                            <input type="date" id="edu2_end" name="education[1][endDate]">
                        </div>
                    </div>
                </div>
            </div>

            <!-- 工作经历 -->
            <div class="section">
                <div class="section-title">工作经历</div>
                <div class="experience-item">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="exp1_company">公司名称</label>
                            <input type="text" id="exp1_company" name="experience[0][company]">
                        </div>
                        <div class="form-group">
                            <label for="exp1_position">职位</label>
                            <input type="text" id="exp1_position" name="experience[0][position]">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group-half">
                            <label for="exp1_start">开始时间</label>
                            <input type="date" id="exp1_start" name="experience[0][startDate]">
                        </div>
                        <div class="form-group-half">
                            <label for="exp1_end">结束时间</label>
                            <input type="date" id="exp1_end" name="experience[0][endDate]">
                        </div>
                        <div class="form-group">
                            <label for="exp1_salary">薪资</label>
                            <input type="text" id="exp1_salary" name="experience[0][salary]">
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="exp1_desc">工作描述</label>
                        <textarea id="exp1_desc" name="experience[0][description]" rows="3"></textarea>
                    </div>
                </div>
            </div>

            <!-- 技能特长 -->
            <div class="section">
                <div class="section-title">技能特长</div>
                <div class="form-group">
                    <label>编程语言</label>
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" id="skill_python" name="skills[]" value="python">
                            <label for="skill_python">Python</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="skill_java" name="skills[]" value="java">
                            <label for="skill_java">Java</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="skill_js" name="skills[]" value="javascript">
                            <label for="skill_js">JavaScript</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="skill_cpp" name="skills[]" value="cpp">
                            <label for="skill_cpp">C++</label>
                        </div>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="englishLevel">英语水平</label>
                        <select id="englishLevel" name="englishLevel">
                            <option value="">请选择</option>
                            <option value="cet4">CET-4</option>
                            <option value="cet6">CET-6</option>
                            <option value="toefl">TOEFL</option>
                            <option value="ielts">IELTS</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="drivingLicense">驾驶证</label>
                        <select id="drivingLicense" name="drivingLicense">
                            <option value="">请选择</option>
                            <option value="c1">C1</option>
                            <option value="c2">C2</option>
                            <option value="none">无</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label for="selfIntro">自我介绍</label>
                    <textarea id="selfIntro" name="selfIntro" rows="4" placeholder="请简要介绍您的优势和特长..."></textarea>
                </div>
            </div>

            <!-- 提交按钮 -->
            <div class="submit-section">
                <button type="submit" class="submit-btn">提交申请</button>
                <button type="button" class="submit-btn" style="background: #6c757d;">保存草稿</button>
                <button type="reset" class="submit-btn" style="background: #dc3545;">重置表单</button>
            </div>
        </div>
    </body>
    </html>
    """


async def test_xy_cut_algorithm():
    """测试XY-Cut算法"""
    print("\n🔧 测试1: XY-Cut算法")

    try:
        # 创建测试HTML
        test_html = create_complex_test_html()

        # 生成截图和BBOX
        screenshot_result = await screenshot_service.take_screenshot_from_html(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=1400
        )

        bbox_result = await bbox_service.extract_element_bboxes(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=1400
        )

        if not screenshot_result.get('success') or not bbox_result.get('success'):
            print("❌ 准备数据失败")
            return None

        # 测试XY-Cut算法
        print(f"📐 开始XY-Cut分析...")
        start_time = time.time()

        xy_cut_analyzer = XYCutAnalyzer(
            screenshot_result['screenshot_path'],
            bbox_result,
            config={
                'xy_cut_threshold': 15,  # 适应复杂表单
                'min_region_width': 100,
                'min_region_height': 50,
                'max_recursion_depth': 4
            }
        )

        xy_result = xy_cut_analyzer.analyze_layout()

        analysis_time = time.time() - start_time

        if xy_result.get('success'):
            print(f"✅ XY-Cut分析完成:")
            print(f"   ⏱️ 分析用时: {analysis_time:.2f}秒")
            print(f"   📊 识别区域: {xy_result['total_regions']}个")
            print(f"   📈 覆盖率: {xy_result['statistics']['coverage_rate']}%")
            print(f"   🏗️ 深度分布: {xy_result['statistics']['depth_distribution']}")

            # 显示前几个区域
            for i, region in enumerate(xy_result['regions'][:3]):
                print(f"   区域 {i+1}: {region['bbox']['width']}x{region['bbox']['height']} (深度: {region['depth']}, 原因: {region['stop_reason']})")
        else:
            print(f"❌ XY-Cut分析失败: {xy_result.get('error')}")
            return None

        return xy_result

    except Exception as e:
        print(f"❌ XY-Cut测试失败: {str(e)}")
        return None


async def test_morphology_cluster():
    """测试形态学聚类算法"""
    print("\n🔧 测试2: 形态学聚类算法")

    try:
        # 创建测试HTML
        test_html = create_complex_test_html()

        # 生成截图和BBOX
        screenshot_result = await screenshot_service.take_screenshot_from_html(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=1400
        )

        bbox_result = await bbox_service.extract_element_bboxes(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=1400
        )

        if not screenshot_result.get('success') or not bbox_result.get('success'):
            print("❌ 准备数据失败")
            return None

        # 测试形态学聚类算法
        print(f"🔗 开始形态学聚类分析...")
        start_time = time.time()

        image_size = (screenshot_result['actual_size']['height'], screenshot_result['actual_size']['width'])
        morph_analyzer = MorphologyCluster(
            bbox_result,
            image_size,
            config={
                'morphology_kernel_size': 25,  # 适应复杂表单
                'min_cluster_size': 2,
                'dilation_iterations': 3,
                'dbscan_eps': 100,
                'min_component_area': 800
            }
        )

        clusters = morph_analyzer.dilate_and_cluster()
        morph_result = morph_analyzer.analyze_clusters(clusters)

        analysis_time = time.time() - start_time

        if morph_result.get('success'):
            print(f"✅ 形态学聚类完成:")
            print(f"   ⏱️ 分析用时: {analysis_time:.2f}秒")
            print(f"   🎯 发现聚类: {morph_result['total_clusters']}个")
            print(f"   📊 元素覆盖率: {morph_result['statistics']['cluster_coverage']}%")
            print(f"   🔄 形态学聚类: {morph_result['statistics']['morphology_clusters']}个")
            print(f"   🎯 DBSCAN聚类: {morph_result['statistics']['dbscan_clusters']}个")

            # 显示前几个聚类
            for i, cluster in enumerate(morph_result['clusters'][:3]):
                print(f"   聚类 {i+1}: {cluster['element_count']}个元素 ({cluster['algorithm']}) - {cluster['bbox']['width']}x{cluster['bbox']['height']}")
        else:
            print(f"❌ 形态学聚类失败: {morph_result.get('error')}")
            return None

        return morph_result

    except Exception as e:
        print(f"❌ 形态学聚类测试失败: {str(e)}")
        return None


async def test_visual_analyzer_fusion():
    """测试视觉分析器融合功能"""
    print("\n🔧 测试3: 视觉分析器融合")

    try:
        # 创建测试HTML
        test_html = create_complex_test_html()

        # 生成截图和BBOX
        screenshot_result = await screenshot_service.take_screenshot_from_html(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=1400
        )

        bbox_result = await bbox_service.extract_element_bboxes(
            html_content=test_html,
            viewport_width=1200,
            viewport_height=1400
        )

        if not screenshot_result.get('success') or not bbox_result.get('success'):
            print("❌ 准备数据失败")
            return None

        # 测试不同融合模式
        fusion_modes = ['xy_cut', 'morphology', 'hybrid']
        results = {}

        for mode in fusion_modes:
            print(f"🔀 测试融合模式: {mode}")
            start_time = time.time()

            visual_analyzer = VisualLayoutAnalyzer(
                screenshot_result['screenshot_path'],
                bbox_result,
                config={
                    'fusion_mode': mode,
                    'xy_cut_config': {
                        'xy_cut_threshold': 12,
                        'min_region_width': 80,
                        'min_region_height': 40,
                        'max_recursion_depth': 4
                    },
                    'morphology_config': {
                        'morphology_kernel_size': 22,
                        'min_cluster_size': 2,
                        'dilation_iterations': 2,
                        'dbscan_eps': 90
                    },
                    'fusion_config': {
                        'overlap_threshold': 0.25,
                        'min_final_region_area': 1200
                    }
                }
            )

            result = visual_analyzer.analyze_layout()
            analysis_time = time.time() - start_time

            if result.get('success'):
                regions_count = result.get('total_regions', 0)
                fusion_stats = result.get('fusion_statistics', {})

                print(f"   ✅ {mode}模式: {regions_count}个区域, 用时: {analysis_time:.2f}秒")

                if fusion_stats:
                    input_regions = fusion_stats.get('input_regions', {}).get('total', 0)
                    compression_ratio = fusion_stats.get('compression_ratio', 1)
                    print(f"      📊 输入区域: {input_regions} → 输出区域: {regions_count} (压缩率: {compression_ratio})")

                results[mode] = {
                    'success': True,
                    'regions_count': regions_count,
                    'analysis_time': analysis_time,
                    'fusion_stats': fusion_stats
                }
            else:
                print(f"   ❌ {mode}模式失败: {result.get('error')}")
                results[mode] = {'success': False, 'error': result.get('error')}

        return results

    except Exception as e:
        print(f"❌ 视觉分析器融合测试失败: {str(e)}")
        return None


async def test_complete_phase2_integration():
    """测试Phase 2完整集成"""
    print("\n🔧 测试4: Phase 2完整集成")

    try:
        # 创建测试HTML
        test_html = create_complex_test_html()

        # 测试完整的视觉分析服务
        print(f"🚀 开始Phase 2完整视觉分析...")
        start_time = time.time()

        # 使用增强的配置
        analysis_config = {
            'viewport_width': 1200,
            'viewport_height': 1400,
            'full_page': True,
            'screenshot_timeout': 8000,

            # CV算法配置
            'fusion_mode': 'hybrid',
            'xy_cut_threshold': 12,
            'min_region_width': 80,
            'min_region_height': 40,
            'morphology_kernel_size': 25,
            'min_cluster_size': 2,
            'overlap_threshold': 0.3,
            'min_final_region_area': 1000
        }

        result = await visual_analysis_service.analyze_html_visual(
            html_content=test_html,
            website_url="test://phase2/complex-form",
            analysis_config=analysis_config
        )

        analysis_time = time.time() - start_time

        if result.get('success'):
            print(f"✅ Phase 2完整集成成功:")
            print(f"   ⏱️ 总分析用时: {analysis_time:.2f}秒")
            print(f"   📋 阶段: {result['phase']}")
            print(f"   📊 识别元素: {result['elements']['total_count']}个")

            # 视觉布局分析结果
            visual_layout = result.get('visual_layout', {})
            if visual_layout.get('success'):
                print(f"   🎯 视觉区域: {visual_layout.get('total_regions', 0)}个")
                print(f"   🔀 融合算法: {visual_layout.get('algorithm', 'unknown')}")

                fusion_stats = visual_layout.get('fusion_statistics', {})
                if fusion_stats:
                    input_total = fusion_stats.get('input_regions', {}).get('total', 0)
                    output_total = fusion_stats.get('output_regions', 0)
                    merge_rate = fusion_stats.get('fusion_efficiency', {}).get('merge_rate', 0)
                    print(f"   📈 融合效率: {input_total} → {output_total} (合并率: {merge_rate}%)")

            # 分析摘要
            summary = result.get('summary', {})
            print(f"   📋 分析摘要:")
            print(f"      🏷️ 标签覆盖率: {summary.get('quality_metrics', {}).get('labeling_rate', 0)}%")
            print(f"      🏗️ 结构复杂度: {summary.get('quality_metrics', {}).get('structure_complexity', 'unknown')}")

            visual_layout_summary = summary.get('visual_layout', {})
            if visual_layout_summary.get('available'):
                print(f"      🎯 布局质量: {visual_layout_summary.get('layout_quality', 'unknown')}")
                print(f"      🤖 算法贡献: {visual_layout_summary.get('algorithm_contributions', {})}")

            # 新增：打印详细识别结果
            print_detailed_analysis_results(result)

            return result
        else:
            print(f"❌ Phase 2完整集成失败: {result.get('error')}")
            return None

    except Exception as e:
        print(f"❌ Phase 2完整集成测试失败: {str(e)}")
        return None


async def benchmark_performance():
    """性能基准测试"""
    print("\n🔧 测试5: 性能基准测试")

    try:
        # 创建不同复杂度的测试HTML
        simple_html = """<html><body><form><input name="name"><input name="email"><button>Submit</button></form></body></html>"""
        test_htmls = [
            ("简单表单", simple_html),
            ("复杂表单", create_complex_test_html())
        ]

        fusion_modes = ['xy_cut', 'morphology', 'hybrid']

        performance_results = {}

        for html_name, html_content in test_htmls:
            print(f"\n📊 测试 {html_name}:")
            performance_results[html_name] = {}

            for mode in fusion_modes:
                print(f"   🔄 模式: {mode}")

                # 执行多次测试取平均值
                times = []
                for i in range(3):
                    start_time = time.time()

                    result = await visual_analysis_service.analyze_html_visual(
                        html_content=html_content,
                        website_url=f"test://benchmark/{html_name}",
                        analysis_config={
                            'viewport_width': 1000,
                            'viewport_height': 800,
                            'fusion_mode': mode,
                            'xy_cut_threshold': 10,
                            'morphology_kernel_size': 20
                        }
                    )

                    analysis_time = time.time() - start_time
                    times.append(analysis_time)

                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)

                performance_results[html_name][mode] = {
                    'avg_time': avg_time,
                    'min_time': min_time,
                    'max_time': max_time,
                    'success': result.get('success', False) if 'result' in locals() else False
                }

                print(f"      ⏱️ 平均用时: {avg_time:.2f}s (范围: {min_time:.2f}s - {max_time:.2f}s)")

        # 显示性能总结
        print(f"\n📈 性能基准测试总结:")
        for html_name, modes in performance_results.items():
            print(f"   {html_name}:")
            for mode, metrics in modes.items():
                if metrics['success']:
                    print(f"      {mode}: {metrics['avg_time']:.2f}s (±{(metrics['max_time'] - metrics['min_time'])/2:.2f}s)")
                else:
                    print(f"      {mode}: 测试失败")

        return performance_results

    except Exception as e:
        print(f"❌ 性能基准测试失败: {str(e)}")
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
    print("🚀 Phase 2 计算机视觉算法测试开始")
    print("=" * 80)

    # 创建截图目录
    os.makedirs("screenshots", exist_ok=True)

    try:
        # 测试1: XY-Cut算法
        xy_result = await test_xy_cut_algorithm()

        # 测试2: 形态学聚类算法
        morph_result = await test_morphology_cluster()

        # 测试3: 视觉分析器融合
        fusion_results = await test_visual_analyzer_fusion()

        # 测试4: Phase 2完整集成
        integration_result = await test_complete_phase2_integration()

        # 测试5: 性能基准测试
        performance_results = await benchmark_performance()

        # 测试总结
        print("\n" + "=" * 80)
        print("🎉 Phase 2 计算机视觉算法测试完成！")

        print("\n📋 测试结果总结:")
        print(f"   ✅ XY-Cut算法: {'通过' if xy_result else '失败'}")
        print(f"   ✅ 形态学聚类: {'通过' if morph_result else '失败'}")
        print(f"   ✅ 算法融合: {'通过' if fusion_results else '失败'}")
        print(f"   ✅ 完整集成: {'通过' if integration_result else '失败'}")
        print(f"   ✅ 性能测试: {'通过' if performance_results else '失败'}")

        if all([xy_result, morph_result, fusion_results, integration_result, performance_results]):
            print("\n🎯 Phase 2 实施状态:")
            print("   ✅ XY-Cut算法实现")
            print("   ✅ 形态学聚类算法实现")
            print("   ✅ 算法融合与优化")
            print("   ✅ 视觉分析服务集成")
            print("   ✅ 性能验证通过")

            print("\n🔄 下一步: Phase 3 - DOM语义回填系统")
            print("   🔄 元素-区块映射")
            print("   🔄 局部LCA算法优化")
            print("   🔄 语义增强引擎")
        else:
            failed_tests = []
            if not xy_result: failed_tests.append("XY-Cut算法")
            if not morph_result: failed_tests.append("形态学聚类")
            if not fusion_results: failed_tests.append("算法融合")
            if not integration_result: failed_tests.append("完整集成")
            if not performance_results: failed_tests.append("性能测试")

            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            print("   请检查日志并修复问题后重新测试")

    except Exception as e:
        print(f"❌ 测试过程中出现异常: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        await cleanup_test_resources()


if __name__ == "__main__":
    asyncio.run(main())
