#!/usr/bin/env python3
"""
Phase 2 详细集成测试脚本
专门用于展示CV算法的详细识别结果
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.visual.visual_analysis_service import visual_analysis_service
from test_phase2_cv_algorithms import create_complex_test_html, print_detailed_analysis_results


async def main():
    """运行详细的Phase 2集成测试"""
    print("🔍 Phase 2 详细识别结果展示")
    print("=" * 80)

    # 创建截图目录
    os.makedirs("screenshots", exist_ok=True)

    try:
        # 创建测试HTML
        test_html = create_complex_test_html()

        # 测试完整的视觉分析服务
        print(f"🚀 开始Phase 2视觉分析...")
        start_time = time.time()

        # 使用优化的配置
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
            website_url="test://phase2/detailed-analysis",
            analysis_config=analysis_config
        )

        analysis_time = time.time() - start_time

        if result.get('success'):
            print(f"✅ Phase 2分析成功:")
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
            print(f"   📋 质量指标:")
            print(f"      🏷️ 标签覆盖率: {summary.get('quality_metrics', {}).get('labeling_rate', 0)}%")
            print(f"      🏗️ 结构复杂度: {summary.get('quality_metrics', {}).get('structure_complexity', 'unknown')}")

            visual_layout_summary = summary.get('visual_layout', {})
            if visual_layout_summary.get('available'):
                print(f"      🎯 布局质量: {visual_layout_summary.get('layout_quality', 'unknown')}")
                print(f"      🤖 算法贡献: {visual_layout_summary.get('algorithm_contributions', {})}")

            # 打印详细识别结果
            print_detailed_analysis_results(result)

            print("\n🎉 详细测试完成！")

        else:
            print(f"❌ Phase 2分析失败: {result.get('error')}")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        try:
            await visual_analysis_service.cleanup_resources()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
