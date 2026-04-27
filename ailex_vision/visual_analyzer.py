"""
AILEX Vision — visual_analyzer.py
Analyze any image or website screenshot using Claude Vision API.
Extracts design intent, identifies issues, generates improvement prompts.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from PIL import Image
    import io
    PIL_OK = True
except ImportError:
    PIL_OK = False


@dataclass
class VisualAnalysis:
    description:       str
    style:             str        # "minimalist", "corporate", "playful", etc.
    dominant_mood:     str        # "professional", "energetic", "calm", etc.
    colors:            List[str]
    composition:       str        # layout description
    issues:            List[str]  # quality/design problems
    strengths:         List[str]  # what works well
    improvement_prompt: str       # prompt to generate improved version
    recreation_prompt:  str       # prompt to recreate from scratch
    style_tags:        List[str]  # for image generation
    aspect_ratio:      str        # "16:9", "1:1", "4:3", etc.
    estimated_type:    str        # "website screenshot", "product photo", "illustration", etc.


class VisualAnalyzer:
    """Analyzes images using Claude Vision (multimodal)."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        self.available = False
        try:
            import anthropic
            key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            if key:
                self.client    = anthropic.Anthropic(api_key=key)
                self.available = True
        except ImportError:
            pass

    def analyze_image_file(self, path: str) -> VisualAnalysis:
        """Analyze a local image file."""
        if not os.path.exists(path):
            return self._fallback(f"File not found: {path}")

        with open(path, "rb") as f:
            data = f.read()
        ext = path.split(".")[-1].lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "gif": "image/gif",
                "webp": "image/webp"}.get(ext, "image/jpeg")
        return self._analyze_bytes(data, mime)

    def analyze_image_url(self, url: str) -> VisualAnalysis:
        """Analyze an image from a URL."""
        import requests
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "image/jpeg")
            return self._analyze_bytes(resp.content, ct.split(";")[0].strip())
        except Exception as e:
            return self._fallback(str(e))

    def analyze_website(self, snapshot: Any) -> VisualAnalysis:
        """Analyze a WebSnapshot — uses largest downloaded image or HTML structure."""
        # Try to analyze the OG image first
        if snapshot.og_image:
            try:
                analysis = self.analyze_image_url(snapshot.og_image)
                analysis.description = (
                    f"Website: {snapshot.title}\n"
                    f"Tech: {', '.join(snapshot.tech_stack)}\n"
                    f"Layout: {', '.join(snapshot.layout_hints)}\n"
                    f"OG Image analysis: {analysis.description}"
                )
                return analysis
            except Exception:
                pass

        # Fall back to largest downloaded image
        downloaded = sorted(
            [img for img in snapshot.images if img.local],
            key=lambda x: x.width * x.height, reverse=True
        )
        if downloaded:
            analysis = self.analyze_image_file(downloaded[0].local)
        else:
            analysis = self._analyze_html_structure(snapshot)

        # Enrich with web-specific data
        analysis.colors    = (snapshot.colors[:6] or analysis.colors)
        analysis.style_tags.extend(snapshot.tech_stack)
        return analysis

    def _analyze_bytes(self, data: bytes, mime: str) -> VisualAnalysis:
        if not self.available:
            return self._demo_analysis(data, mime)

        b64  = base64.standard_b64encode(data).decode()
        prompt = (
            "Analyze this image in detail as a visual designer and AI art director. Provide:\n"
            "1. DESCRIPTION: What is shown (2-3 sentences)\n"
            "2. STYLE: Visual style (e.g., minimalist, corporate, photorealistic, illustrated)\n"
            "3. MOOD: Dominant emotional tone\n"
            "4. COLORS: 5 dominant hex colors as #rrggbb\n"
            "5. COMPOSITION: Layout and visual hierarchy\n"
            "6. ISSUES: 2-3 specific design/quality problems\n"
            "7. STRENGTHS: 2-3 things that work well\n"
            "8. IMPROVEMENT_PROMPT: A detailed Flux/SDXL prompt to generate an improved version\n"
            "9. RECREATION_PROMPT: A detailed prompt to recreate this from scratch\n"
            "10. STYLE_TAGS: 5-8 tags for image generation (comma-separated)\n"
            "11. ASPECT_RATIO: Best ratio (16:9, 1:1, 4:3, 9:16, 21:9)\n"
            "12. TYPE: What kind of image (website screenshot, product photo, illustration, etc.)\n\n"
            "Format as:\n"
            "DESCRIPTION: ...\nSTYLE: ...\nMOOD: ...\nCOLORS: #hex1,#hex2,...\n"
            "COMPOSITION: ...\nISSUES: issue1; issue2\nSTRENGTHS: str1; str2\n"
            "IMPROVEMENT_PROMPT: ...\nRECREATION_PROMPT: ...\n"
            "STYLE_TAGS: tag1, tag2, ...\nASPECT_RATIO: ...\nTYPE: ..."
        )

        try:
            resp = self.client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                        {"type": "text",  "text": prompt},
                    ],
                }],
            )
            return self._parse_analysis(resp.content[0].text)
        except Exception as e:
            return self._fallback(str(e))

    def _parse_analysis(self, text: str) -> VisualAnalysis:
        import re

        def get(key: str) -> str:
            m = re.search(rf"{key}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.I | re.S)
            return m.group(1).strip() if m else ""

        colors_raw = get("COLORS")
        colors     = re.findall(r"#[0-9a-fA-F]{6}", colors_raw)

        issues_raw = get("ISSUES")
        issues     = [i.strip() for i in re.split(r"[;,\n]", issues_raw) if i.strip()][:5]

        strengths_raw = get("STRENGTHS")
        strengths     = [s.strip() for s in re.split(r"[;,\n]", strengths_raw) if s.strip()][:5]

        tags_raw  = get("STYLE_TAGS")
        tags      = [t.strip() for t in tags_raw.split(",") if t.strip()][:10]

        return VisualAnalysis(
            description       = get("DESCRIPTION"),
            style             = get("STYLE"),
            dominant_mood     = get("MOOD"),
            colors            = colors if colors else ["#000000"],
            composition       = get("COMPOSITION"),
            issues            = issues if issues else ["Unable to detect issues"],
            strengths         = strengths if strengths else ["Unable to detect strengths"],
            improvement_prompt = get("IMPROVEMENT_PROMPT"),
            recreation_prompt  = get("RECREATION_PROMPT"),
            style_tags         = tags,
            aspect_ratio       = get("ASPECT_RATIO") or "16:9",
            estimated_type     = get("TYPE") or "image",
        )

    def _demo_analysis(self, data: bytes, mime: str) -> VisualAnalysis:
        size = len(data)
        return VisualAnalysis(
            description       = f"[DEMO] Image ({size//1024}KB, {mime})",
            style             = "modern web design",
            dominant_mood     = "professional",
            colors            = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#ffffff"],
            composition       = "centered layout with hero section",
            issues            = ["contrast could be improved", "mobile spacing needs review"],
            strengths         = ["clean layout", "consistent color palette"],
            improvement_prompt = "A stunning modern website design, dark theme, vibrant accent colors, "
                                 "clean typography, professional layout, 4k quality, ultra detailed",
            recreation_prompt  = "Modern web design, dark background, clean minimal layout, "
                                 "professional aesthetic, high quality render",
            style_tags         = ["modern", "clean", "dark", "professional", "web design"],
            aspect_ratio       = "16:9",
            estimated_type     = "website screenshot",
        )

    def _analyze_html_structure(self, snapshot: Any) -> VisualAnalysis:
        style_guess = "unknown"
        if "bootstrap" in snapshot.tech_stack:   style_guess = "Bootstrap grid layout"
        if "tailwind"  in snapshot.tech_stack:   style_guess = "Tailwind utility-first"
        if "wordpress" in snapshot.tech_stack:   style_guess = "WordPress CMS style"
        colors = snapshot.colors[:5] or ["#000000"]
        return VisualAnalysis(
            description       = f"{snapshot.title} — {snapshot.description[:100]}",
            style             = style_guess,
            dominant_mood     = "professional",
            colors            = colors,
            composition       = ", ".join(snapshot.layout_hints) or "standard layout",
            issues            = ["no screenshot available for deep visual analysis"],
            strengths         = [f"detected {len(snapshot.images)} images"],
            improvement_prompt = (
                f"A beautiful modern website, inspired by {snapshot.title}, "
                f"color palette: {', '.join(colors[:3])}, "
                f"clean professional design, high quality, 4k"
            ),
            recreation_prompt  = (
                f"Website redesign of '{snapshot.title}', {style_guess}, "
                f"modern UI, clean layout, professional typography"
            ),
            style_tags        = snapshot.tech_stack + ["website", "UI design"],
            aspect_ratio      = "16:9",
            estimated_type    = "website",
        )

    def _fallback(self, error: str) -> VisualAnalysis:
        return VisualAnalysis(
            description       = f"Analysis failed: {error}",
            style             = "unknown",
            dominant_mood     = "unknown",
            colors            = ["#000000"],
            composition       = "unknown",
            issues            = [error],
            strengths         = [],
            improvement_prompt = "A beautiful, high quality image",
            recreation_prompt  = "A beautiful, high quality image",
            style_tags        = ["high quality"],
            aspect_ratio      = "1:1",
            estimated_type    = "unknown",
        )
