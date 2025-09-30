#!/usr/bin/env python3
"""
截图服务调试脚本
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.visual.screenshot_service import screenshot_service


async def debug_screenshot():
    """调试截图服务"""
    print("🔍 调试截图服务")

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
        # 直接测试截图服务
        print("📸 调用截图服务...")

        screenshot_result = await screenshot_service.take_screenshot_from_html(
            html_content=test_html,
            viewport_width=800,
            viewport_height=600,
            full_page=True,
            wait_timeout=3000
        )

        print(f"📋 截图结果:")
        print(json.dumps(screenshot_result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 截图服务异常: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await screenshot_service.close()


if __name__ == "__main__":
    asyncio.run(debug_screenshot())
