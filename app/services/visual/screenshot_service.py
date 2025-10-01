"""
截图服务模块

负责使用Playwright获取网页的高保真截图
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class ScreenshotService:
    """网页截图服务类"""

    def __init__(self, screenshot_dir: str = "screenshots"):
        """
        初始化截图服务

        Args:
            screenshot_dir: 截图保存目录
        """
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(exist_ok=True)
        self._browser: Optional[Browser] = None

    async def _get_browser(self) -> Browser:
        """
        获取或创建浏览器实例（复用连接）
        """
        if self._browser is None or not self._browser.is_connected():
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                ]
            )
            logger.info("🚀 Playwright浏览器启动成功")
        return self._browser

    async def take_screenshot_from_html(
        self,
        html_content: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        full_page: bool = True,
        wait_timeout: int = 5000
    ) -> Dict[str, Any]:
        """
        从HTML内容生成截图

        Args:
            html_content: HTML页面内容
            viewport_width: 视窗宽度
            viewport_height: 视窗高度
            full_page: 是否截取完整页面
            wait_timeout: 页面加载等待时间(ms)

        Returns:
            包含截图路径和元信息的字典
        """
        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={'width': viewport_width, 'height': viewport_height}
            )

            # 设置内容并等待加载
            await page.set_content(html_content, wait_until='networkidle')
            await page.wait_for_timeout(wait_timeout)  # 额外等待时间确保内容渲染完成

            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"screenshot_{timestamp}_{unique_id}.png"
            screenshot_path = self.screenshot_dir / filename

            # 获取页面实际尺寸
            actual_size = await page.evaluate("""
                () => {
                    return {
                        width: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
                        height: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
                        viewportWidth: window.innerWidth,
                        viewportHeight: window.innerHeight
                    }
                }
            """)

            # 截图
            await page.screenshot(
                path=str(screenshot_path),
                full_page=full_page,
                type='png'
            )

            await page.close()

            result = {
                "success": True,
                "screenshot_path": str(screenshot_path),
                "filename": filename,
                "viewport": {
                    "width": viewport_width,
                    "height": viewport_height
                },
                "actual_size": actual_size,
                "full_page": full_page,
                "timestamp": timestamp,
                "file_size": os.path.getsize(screenshot_path)
            }

            logger.info(f"📸 截图成功生成: {filename}, 尺寸: {actual_size}")
            return result

        except Exception as e:
            logger.error(f"❌ 截图生成失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def take_screenshot_from_url(
        self,
        url: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        full_page: bool = True,
        wait_timeout: int = 10000
    ) -> Dict[str, Any]:
        """
        从URL直接生成截图

        Args:
            url: 目标网页URL
            viewport_width: 视窗宽度
            viewport_height: 视窗高度
            full_page: 是否截取完整页面
            wait_timeout: 页面加载等待时间(ms)

        Returns:
            包含截图路径和元信息的字典
        """
        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={'width': viewport_width, 'height': viewport_height}
            )

            # 访问页面并等待加载
            await page.goto(url, wait_until='networkidle', timeout=wait_timeout)
            await page.wait_for_timeout(2000)  # 额外等待确保动态内容加载

            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"url_screenshot_{timestamp}_{unique_id}.png"
            screenshot_path = self.screenshot_dir / filename

            # 获取页面实际尺寸
            actual_size = await page.evaluate("""
                () => {
                    return {
                        width: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
                        height: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
                        viewportWidth: window.innerWidth,
                        viewportHeight: window.innerHeight
                    }
                }
            """)

            # 截图
            await page.screenshot(
                path=str(screenshot_path),
                full_page=full_page,
                type='png'
            )

            await page.close()

            result = {
                "success": True,
                "screenshot_path": str(screenshot_path),
                "filename": filename,
                "url": url,
                "viewport": {
                    "width": viewport_width,
                    "height": viewport_height
                },
                "actual_size": actual_size,
                "full_page": full_page,
                "timestamp": timestamp,
                "file_size": os.path.getsize(screenshot_path)
            }

            logger.info(f"📸 URL截图成功生成: {filename}, URL: {url}")
            return result

        except Exception as e:
            logger.error(f"❌ URL截图生成失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def cleanup_old_screenshots(self, max_age_hours: int = 24):
        """
        清理过期的截图文件

        Args:
            max_age_hours: 文件最大保留时间（小时）
        """
        try:
            import time
            current_time = time.time()
            deleted_count = 0

            for file_path in self.screenshot_dir.glob("*.png"):
                file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
                if file_age_hours > max_age_hours:
                    file_path.unlink()
                    deleted_count += 1

            logger.info(f"🧹 清理完成，删除了 {deleted_count} 个过期截图文件")

        except Exception as e:
            logger.warning(f"⚠️ 清理截图文件时出错: {str(e)}")

    async def close(self):
        """
        关闭浏览器连接
        """
        if self._browser and self._browser.is_connected():
            await self._browser.close()
            logger.info("🔒 Playwright浏览器已关闭")


# 全局截图服务实例
screenshot_service = ScreenshotService()
