"""
AILEX Vision — web_capture.py
Fetch any website: HTML structure, images, colors, fonts, layout analysis.
No headless browser required — pure requests + BeautifulSoup + Pillow.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


@dataclass
class WebAsset:
    url:      str
    type:     str        # "image" | "video" | "css" | "font"
    local:    Optional[str] = None   # local file path if downloaded
    size:     int = 0
    width:    int = 0
    height:   int = 0
    format:   str = ""
    dominant_colors: List[str] = field(default_factory=list)


@dataclass
class WebSnapshot:
    url:           str
    title:         str
    description:   str
    html:          str
    text_content:  str
    images:        List[WebAsset]
    videos:        List[WebAsset]
    fonts:         List[str]
    colors:        List[str]           # dominant CSS colors
    typography:    Dict[str, str]      # heading/body font analysis
    layout_hints:  List[str]           # flex/grid/columns detected
    tech_stack:    List[str]           # frameworks detected
    og_image:      Optional[str]       # Open Graph image URL
    favicon:       Optional[str]
    word_count:    int
    fetch_time_s:  float
    error:         Optional[str] = None


class WebCapture:
    def __init__(self, timeout: int = 15, max_images: int = 20,
                 download_images: bool = True, save_dir: str = "/data/data/com.termux/files/home/ailex_vision"):
        self.timeout        = timeout
        self.max_images     = max_images
        self.download_images = download_images
        self.save_dir       = save_dir
        os.makedirs(save_dir, exist_ok=True)

    def capture(self, url: str) -> WebSnapshot:
        start = time.time()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            resp = requests.get(url, headers=HEADERS, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            return WebSnapshot(url=url, title="", description="", html="",
                               text_content="", images=[], videos=[], fonts=[],
                               colors=[], typography={}, layout_hints=[],
                               tech_stack=[], og_image=None, favicon=None,
                               word_count=0, fetch_time_s=0, error=str(e))

        soup = BeautifulSoup(resp.text, "html.parser")
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        title       = self._title(soup)
        description = self._description(soup)
        text        = self._text(soup)
        images      = self._images(soup, base, url)
        videos      = self._videos(soup, base)
        fonts       = self._fonts(soup, resp.text)
        colors      = self._colors(resp.text)
        typography  = self._typography(resp.text, fonts)
        layout      = self._layout_hints(resp.text)
        tech        = self._tech_stack(resp.text, str(soup))
        og_image    = self._og_image(soup, base)
        favicon     = self._favicon(soup, base)

        return WebSnapshot(
            url=url, title=title, description=description,
            html=resp.text[:50_000],
            text_content=text[:5_000],
            images=images, videos=videos, fonts=fonts,
            colors=colors, typography=typography,
            layout_hints=layout, tech_stack=tech,
            og_image=og_image, favicon=favicon,
            word_count=len(text.split()),
            fetch_time_s=round(time.time() - start, 2),
        )

    def _title(self, soup: BeautifulSoup) -> str:
        tag = soup.find("title")
        if tag: return tag.get_text(strip=True)
        h1 = soup.find("h1")
        return h1.get_text(strip=True) if h1 else ""

    def _description(self, soup: BeautifulSoup) -> str:
        for attrs in [{"name": "description"}, {"property": "og:description"},
                      {"name": "twitter:description"}]:
            m = soup.find("meta", attrs=attrs)
            if m and m.get("content"): return m["content"][:200]
        return ""

    def _text(self, soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return re.sub(r"\s+", " ", soup.get_text(" ")).strip()

    def _images(self, soup: BeautifulSoup, base: str, page_url: str) -> List[WebAsset]:
        assets: List[WebAsset] = []
        seen: set = set()
        for tag in soup.find_all(["img", "source", "picture"])[:self.max_images * 2]:
            src = tag.get("src") or tag.get("srcset", "").split(",")[0].split()[0] or ""
            if not src or src.startswith("data:"): continue
            full = urljoin(page_url, src)
            if full in seen: continue
            seen.add(full)
            asset = WebAsset(url=full, type="image")
            if self.download_images:
                asset = self._download_asset(asset)
            assets.append(asset)
            if len(assets) >= self.max_images: break
        return assets

    def _videos(self, soup: BeautifulSoup, base: str) -> List[WebAsset]:
        assets: List[WebAsset] = []
        for tag in soup.find_all(["video", "source"])[:5]:
            src = tag.get("src") or ""
            if src and not src.startswith("data:"):
                assets.append(WebAsset(url=urljoin(base, src), type="video"))
        # YouTube/Vimeo embeds
        for iframe in soup.find_all("iframe", src=True)[:5]:
            src = iframe["src"]
            if "youtube" in src or "vimeo" in src:
                assets.append(WebAsset(url=src, type="video", format="embed"))
        return assets

    def _download_asset(self, asset: WebAsset) -> WebAsset:
        try:
            r = requests.get(asset.url, headers=HEADERS, timeout=10, stream=True)
            r.raise_for_status()
            data = r.content
            asset.size = len(data)
            ext  = asset.url.split(".")[-1].split("?")[0].lower()[:5]
            name = hashlib.md5(asset.url.encode()).hexdigest()[:12] + f".{ext}"
            path = os.path.join(self.save_dir, name)
            with open(path, "wb") as f:
                f.write(data)
            asset.local = path
            if PIL_OK:
                try:
                    img = Image.open(io.BytesIO(data))
                    asset.width, asset.height = img.size
                    asset.format = img.format or ext
                    asset.dominant_colors = self._dominant_colors(img)
                except Exception:
                    pass
        except Exception:
            pass
        return asset

    def _dominant_colors(self, img: "Image.Image", n: int = 5) -> List[str]:
        try:
            small = img.convert("RGB").resize((50, 50))
            pixels = list(small.getdata())
            buckets: Dict[Tuple, int] = {}
            for r, g, b in pixels:
                key = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
                buckets[key] = buckets.get(key, 0) + 1
            top = sorted(buckets.items(), key=lambda x: -x[1])[:n]
            return [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in top]
        except Exception:
            return []

    def _fonts(self, soup: BeautifulSoup, css: str) -> List[str]:
        fonts: List[str] = []
        # Google Fonts links
        for link in soup.find_all("link", href=True):
            if "fonts.googleapis.com" in link["href"]:
                m = re.findall(r"family=([^&:]+)", link["href"])
                fonts.extend(m.replace("+", " ") for m in m)
        # CSS font-family
        m = re.findall(r"font-family:\s*['\"]?([^;,'\"\n]+)", css)
        for f in m:
            clean = f.strip().strip("'\"").split(",")[0].strip()
            if clean and clean not in fonts:
                fonts.append(clean)
        return list(dict.fromkeys(fonts))[:10]

    def _colors(self, css: str) -> List[str]:
        hex_colors  = re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css)
        rgb_colors  = re.findall(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", css)
        colors: List[str] = []
        for h in hex_colors[:20]:
            if len(h) == 3: h = h[0]*2 + h[1]*2 + h[2]*2
            colors.append(f"#{h.lower()}")
        for r, g, b in rgb_colors[:10]:
            colors.append(f"#{int(r):02x}{int(g):02x}{int(b):02x}")
        # Deduplicate preserving order
        return list(dict.fromkeys(colors))[:15]

    def _typography(self, css: str, fonts: List[str]) -> Dict[str, str]:
        sizes = re.findall(r"font-size:\s*([\d.]+(?:px|rem|em))", css)
        weights = re.findall(r"font-weight:\s*(\d+|bold|normal)", css)
        return {
            "detected_fonts": ", ".join(fonts[:3]) if fonts else "system default",
            "font_sizes":     ", ".join(dict.fromkeys(sizes[:5])),
            "font_weights":   ", ".join(dict.fromkeys(weights[:4])),
        }

    def _layout_hints(self, css: str) -> List[str]:
        hints: List[str] = []
        if "display:flex" in css.replace(" ", "") or "display: flex" in css:
            hints.append("flexbox layout")
        if "display:grid" in css.replace(" ", "") or "display: grid" in css:
            hints.append("CSS grid layout")
        if "@media" in css:
            hints.append("responsive design (media queries)")
        if "max-width" in css:
            hints.append("max-width constrained container")
        if "position:fixed" in css.replace(" ", "") or "position: fixed" in css:
            hints.append("fixed positioned elements")
        return hints

    def _tech_stack(self, html: str, text: str) -> List[str]:
        tech: List[str] = []
        indicators = {
            "React":      ["react", "__NEXT_DATA__", "_reactrootcontainer"],
            "Next.js":    ["__NEXT_DATA__", "_next/static"],
            "Vue.js":     ["vue.js", "__vue_store__", "v-app"],
            "Angular":    ["ng-app", "angular.js", "__ng_app"],
            "Tailwind":   ["tailwind", "tw-", "text-xl", "flex-col"],
            "Bootstrap":  ["bootstrap", "btn-primary", "container-fluid"],
            "WordPress":  ["wp-content", "wp-includes", "wordpress"],
            "Shopify":    ["shopify", "cdn.shopify.com"],
            "Webflow":    ["webflow", "wf-form"],
        }
        low = html.lower()
        for name, signals in indicators.items():
            if any(s in low for s in signals):
                tech.append(name)
        return tech

    def _og_image(self, soup: BeautifulSoup, base: str) -> Optional[str]:
        m = soup.find("meta", property="og:image")
        if m and m.get("content"): return urljoin(base, m["content"])
        m = soup.find("meta", attrs={"name": "twitter:image"})
        if m and m.get("content"): return urljoin(base, m["content"])
        return None

    def _favicon(self, soup: BeautifulSoup, base: str) -> Optional[str]:
        for rel in ["icon", "shortcut icon", "apple-touch-icon"]:
            link = soup.find("link", rel=rel)
            if link and link.get("href"): return urljoin(base, link["href"])
        return base + "/favicon.ico"

    def summary(self, snap: WebSnapshot) -> str:
        if snap.error:
            return f"CAPTURE FAILED: {snap.error}"
        lines = [
            f"URL:         {snap.url}",
            f"Title:       {snap.title}",
            f"Description: {snap.description[:100]}",
            f"Tech stack:  {', '.join(snap.tech_stack) or 'unknown'}",
            f"Images:      {len(snap.images)} found ({sum(1 for i in snap.images if i.local)} downloaded)",
            f"Videos:      {len(snap.videos)} found",
            f"Fonts:       {', '.join(snap.fonts[:4]) or 'none detected'}",
            f"Colors:      {', '.join(snap.colors[:6]) or 'none detected'}",
            f"Layout:      {', '.join(snap.layout_hints) or 'unknown'}",
            f"Words:       {snap.word_count}",
            f"Fetch time:  {snap.fetch_time_s}s",
        ]
        return "\n".join(lines)
