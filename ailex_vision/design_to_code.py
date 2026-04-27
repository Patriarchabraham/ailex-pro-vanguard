"""
AILEX Vision — design_to_code.py
Screenshot / mockup → HTML/React/CSS using Claude Vision.
"""
from __future__ import annotations

import base64
import os
import re
import time
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class DesignToCodeResult:
    source:      str
    output_type: str
    code:        str
    saved_path:  Optional[str]
    tokens_in:   int = 0
    tokens_out:  int = 0
    time_s:      float = 0.0
    error:       Optional[str] = None


class DesignToCode:
    """
    Convert any visual design (screenshot, mockup, wireframe) to code.
    Uses Claude Vision to understand the design then generate implementation.
    """

    SAVE_DIR = "/data/data/com.termux/files/home/ailex_vision/design_to_code"
    MODEL    = "claude-opus-4-7"

    def __init__(self, client: Any = None):
        self.client = client
        os.makedirs(self.SAVE_DIR, exist_ok=True)

    def from_file(self, path: str, output_type: str = "html",
                  framework: str = "vanilla") -> DesignToCodeResult:
        if not os.path.exists(path):
            return DesignToCodeResult(path, output_type, "", None, error="File not found")
        with open(path, "rb") as f:
            data = f.read()
        ext  = path.split(".")[-1].lower()
        mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png",
                "webp":"image/webp","gif":"image/gif"}.get(ext,"image/png")
        return self._generate(path, base64.standard_b64encode(data).decode(),
                              mime, output_type, framework)

    def from_url(self, url: str, output_type: str = "html",
                 framework: str = "vanilla") -> DesignToCodeResult:
        import requests as req
        try:
            r    = req.get(url, timeout=15)
            mime = r.headers.get("content-type","image/jpeg").split(";")[0]
            b64  = base64.standard_b64encode(r.content).decode()
            return self._generate(url, b64, mime, output_type, framework)
        except Exception as e:
            return DesignToCodeResult(url, output_type, "", None, error=str(e))

    def _generate(self, source: str, b64: str, mime: str,
                  output_type: str, framework: str) -> DesignToCodeResult:
        if not self.client:
            return self._demo(source, output_type)
        start = time.time()
        prompts = {
            "html":  "Convert this design to complete HTML + CSS. Pixel-perfect. Mobile responsive. Return ONLY the HTML.",
            "react": f"Convert this design to a React {'+ Tailwind ' if framework=='tailwind' else ''}component in TypeScript. Return ONLY the component code.",
            "css":   "Extract the complete CSS design system from this design as CSS custom properties. Return ONLY the CSS.",
            "vue":   "Convert this design to a Vue 3 component with <script setup>. Return ONLY the component.",
        }
        prompt = prompts.get(output_type, prompts["html"])
        try:
            resp = self.client.messages.create(
                model=self.MODEL, max_tokens=8000,
                messages=[{"role":"user","content":[
                    {"type":"image","source":{"type":"base64","media_type":mime,"data":b64}},
                    {"type":"text","text":prompt},
                ]}],
            )
            text = resp.content[0].text
            code = self._extract(text, output_type)
            ext  = {"html":"html","react":"tsx","css":"css","vue":"vue"}.get(output_type,"html")
            name = f"d2c_{int(time.time())}.{ext}"
            path = os.path.join(self.SAVE_DIR, name)
            with open(path,"w",encoding="utf-8") as f:
                f.write(code)
            return DesignToCodeResult(
                source=source, output_type=output_type, code=code, saved_path=path,
                tokens_in=resp.usage.input_tokens, tokens_out=resp.usage.output_tokens,
                time_s=round(time.time()-start, 2),
            )
        except Exception as e:
            return DesignToCodeResult(source, output_type, "", None,
                                      error=str(e), time_s=round(time.time()-start,2))

    def _extract(self, text: str, output_type: str) -> str:
        for lang in (output_type, "html", "jsx", "tsx", "css", "vue", ""):
            m = re.search(rf"```{lang}\s*\n([\s\S]+?)\n```", text, re.I)
            if m: return m.group(1).strip()
        return text.strip()

    def _demo(self, source: str, output_type: str) -> DesignToCodeResult:
        code = (f'<!-- Design-to-Code: {source} -->\n'
                f'<!-- Set ANTHROPIC_API_KEY to generate real code -->\n'
                f'<div class="design-placeholder">Design conversion demo</div>')
        return DesignToCodeResult(source, output_type, code, None,
                                  error="No API key — demo mode")
