"""
AILEX Vision — diagram.py
Generate architecture diagrams, ERDs, flowcharts from code or description.
Outputs: Mermaid.js, SVG, HTML with interactive diagram.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DiagramResult:
    title:      str
    kind:       str       # "architecture" | "erd" | "flowchart" | "sequence" | "class"
    mermaid:    str       # Mermaid.js syntax
    html:       str       # self-contained HTML with rendered diagram
    saved_path: Optional[str]
    time_s:     float = 0.0
    error:      Optional[str] = None


class DiagramGenerator:
    """
    Generate diagrams from code analysis or natural language description.
    Uses Claude + Mermaid.js for rendering.
    """

    SAVE_DIR = "/data/data/com.termux/files/home/ailex_vision/diagrams"
    MODEL    = "claude-sonnet-4-6"

    def __init__(self, client: Any = None):
        self.client = client
        os.makedirs(self.SAVE_DIR, exist_ok=True)

    def from_code(self, code: str, kind: str = "architecture",
                  title: str = "Diagram") -> DiagramResult:
        return self._generate(f"Generate from this code:\n{code[:3000]}", kind, title)

    def from_description(self, description: str, kind: str = "architecture",
                          title: str = "") -> DiagramResult:
        return self._generate(description, kind, title or description[:40])

    def from_project(self, context_summary: str, kind: str = "architecture") -> DiagramResult:
        return self._generate(
            f"Generate for this project:\n{context_summary[:2000]}",
            kind, "Project Architecture"
        )

    def _generate(self, prompt: str, kind: str, title: str) -> DiagramResult:
        if not self.client:
            return self._demo(title, kind)
        start = time.time()
        type_prompts = {
            "architecture": "component/service architecture diagram showing modules and their relationships",
            "erd":          "entity-relationship diagram showing database tables and relationships",
            "flowchart":    "flowchart showing the process flow and decision points",
            "sequence":     "sequence diagram showing interactions between components",
            "class":        "class diagram showing classes, attributes, and inheritance",
        }
        diag_type = type_prompts.get(kind, type_prompts["architecture"])
        try:
            resp = self.client.messages.create(
                model=self.MODEL, max_tokens=2000,
                messages=[{"role":"user","content":
                    f"Generate a Mermaid.js {diag_type} for: {prompt}\n\n"
                    "Return ONLY the Mermaid syntax inside ```mermaid ... ``` block. "
                    "Make it complete and detailed."}],
            )
            text    = resp.content[0].text
            mermaid = self._extract_mermaid(text)
            html    = self._wrap_html(mermaid, title)
            path    = self._save(html, title)
            return DiagramResult(title=title, kind=kind, mermaid=mermaid,
                                 html=html, saved_path=path,
                                 time_s=round(time.time()-start,2))
        except Exception as e:
            return DiagramResult(title=title, kind=kind, mermaid="", html="",
                                 saved_path=None, error=str(e),
                                 time_s=round(time.time()-start,2))

    def _extract_mermaid(self, text: str) -> str:
        m = re.search(r"```mermaid\s*\n([\s\S]+?)\n```", text, re.I)
        if m: return m.group(1).strip()
        return text.strip()

    def _wrap_html(self, mermaid: str, title: str) -> str:
        escaped = mermaid.replace("`", "\\`")
        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<style>
  body {{ font-family: Inter, sans-serif; background: #f8faff; padding: 32px; }}
  h1   {{ color: #1a1a2e; font-size: 1.5rem; margin-bottom: 24px; }}
  .mermaid {{ background: white; padding: 32px; border-radius: 16px;
              box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="mermaid">{mermaid}</div>
<script>mermaid.initialize({{startOnLoad:true,theme:'default'}});</script>
</body></html>"""

    def _save(self, html: str, title: str) -> str:
        slug  = re.sub(r"[^a-z0-9]+","_", title.lower())[:30]
        path  = os.path.join(self.SAVE_DIR, f"{slug}_{int(time.time())}.html")
        with open(path,"w",encoding="utf-8") as f:
            f.write(html)
        return path

    def _demo(self, title: str, kind: str) -> DiagramResult:
        mermaid = (
            "graph TD\n    A[AILEX Pilot] --> B[ProjectReader]\n"
            "    A --> C[CodeExecutor]\n    A --> D[GitIntegration]\n"
            "    A --> E[AILEXMythosPipeline]\n    E --> F[33 Agents]\n    E --> G[CHAOS Critic]"
        )
        return DiagramResult(title=title, kind=kind, mermaid=mermaid,
                             html=self._wrap_html(mermaid, title), saved_path=None)
