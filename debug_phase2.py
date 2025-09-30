#!/usr/bin/env python3
"""
Phase 2 调试脚本
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.visual.visual_analysis_service import visual_analysis_service


async def debug_phase2():
    """调试Phase 2问题"""
    print("🔍 调试Phase 2问题")

    # 简单的测试HTML
    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <form>
            <input name="test" type="text">
            <button>Submit</button>
        </form>
    </body>
    </html>
    """

    try:
        # 测试视觉分析服务
        result = await visual_analysis_service.analyze_html_visual(
            html_content=test_html,
            website_url="test://debug",
            analysis_config={
                'viewport_width': 800,
                'viewport_height': 600,
                'full_page': True,
                'screenshot_timeout': 3000
            }
        )

        print(f"✅ 成功: {result.get('success')}")
        if not result.get('success'):
            print(f"❌ 错误: {result.get('error')}")

    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_phase2())
