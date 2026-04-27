"""
AILEX Vision — browser.py
Real browser automation via Playwright — accurate screenshots of any page.
Fixes the image mapping problem: captures what the browser actually renders.
"""
from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BrowserSnapshot:
    url:           str
    title:         str
    screenshot:    Optional[bytes]   # PNG bytes
    screenshot_path: Optional[str]
    html:          str
    width:         int = 1440
    height:        int = 900
    mobile:        bool = False
    duration_s:    float = 0.0
    error:         Optional[str] = None


class BrowserCapture:
    """
    Playwright-based browser capture.
    Renders JavaScript, captures real screenshots, extracts rendered HTML.
    """

    SAVE_DIR = "/data/data/com.termux/files/home/ailex_vision/screenshots"

    def __init__(self, headless: bool = True, save_dir: str = SAVE_DIR):
        self.headless = headless
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self._available = False
        try:
            from playwright.sync_api import sync_playwright  # noqa
            self._available = True
        except ImportError:
            pass

    def capture(self, url: str, width: int = 1440, height: int = 900,
                mobile: bool = False, wait_s: int = 2) -> BrowserSnapshot:
        if not self._available:
            return BrowserSnapshot(url=url, title="", screenshot=None,
                                   screenshot_path=None, html="",
                                   error="Install playwright: pip install playwright && playwright install chromium")
        start = time.time()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                ctx = browser.new_context(
                    viewport={"width": width, "height": height},
                    **({"is_mobile": True, "viewport": {"width": 390, "height": 844}} if mobile else {}),
                )
                page = ctx.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(wait_s * 1000)

                title = page.title()
                html  = page.content()

                # Full page screenshot
                fname = f"screenshot_{int(time.time())}.png"
                path  = os.path.join(self.save_dir, fname)
                page.screenshot(path=path, full_page=True)

                with open(path, "rb") as f:
                    png_bytes = f.read()

                browser.close()

                return BrowserSnapshot(
                    url=url, title=title, screenshot=png_bytes,
                    screenshot_path=path, html=html[:100_000],
                    width=width, height=height, mobile=mobile,
                    duration_s=round(time.time()-start, 2),
                )
        except Exception as e:
            return BrowserSnapshot(url=url, title="", screenshot=None,
                                   screenshot_path=None, html="",
                                   error=str(e), duration_s=round(time.time()-start, 2))

    def capture_mobile(self, url: str) -> BrowserSnapshot:
        return self.capture(url, width=390, height=844, mobile=True)

    def capture_element(self, url: str, selector: str) -> Optional[bytes]:
        """Capture a specific element (logo, hero, section) as PNG."""
        if not self._available:
            return None
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page    = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(url, wait_until="networkidle", timeout=30000)
                elem    = page.query_selector(selector)
                if elem:
                    return elem.screenshot()
                browser.close()
        except Exception:
            pass
        return None

    def screenshot_to_base64(self, png_bytes: bytes) -> str:
        return base64.standard_b64encode(png_bytes).decode()

    def install(self) -> bool:
        """Install playwright and chromium."""
        import subprocess
        r1 = subprocess.run(["pip", "install", "playwright", "-q"], capture_output=True)
        r2 = subprocess.run(["playwright", "install", "chromium", "--with-deps"],
                            capture_output=True)
        self._available = (r1.returncode == 0 and r2.returncode == 0)
        return self._available
