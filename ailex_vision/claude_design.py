"""
AILEX Vision — claude_design.py
Integração com Claude Design (Anthropic Labs, lançado 17 Abr 2026).

Claude Design usa Claude Opus 4.7 para gerar designs como código:
SVG · HTML/CSS · React/Tailwind · Design Systems · Wireframes · Slides · Pitch Decks

Pipeline completo:
  WebCapture → VisualAnalyzer → ClaudeDesign → ImageCraft/VideoCraft

Quando a API oficial do Claude Design for disponibilizada (anunciada como "coming weeks"),
este módulo será actualizado para usar os endpoints nativos.
"""
from __future__ import annotations

import base64
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

OutputType = Literal["html", "react", "svg", "css", "design_system", "wireframe", "slide", "pitch_deck"]


@dataclass
class DesignOutput:
    type:        OutputType
    title:       str
    code:        str              # generated code (HTML/SVG/CSS/JSX)
    description: str              # what was generated
    model:       str              # claude-opus-4-7
    tokens_in:   int   = 0
    tokens_out:  int   = 0
    time_s:      float = 0.0
    saved_path:  Optional[str] = None
    critique:    Optional[str] = None
    suggestions: List[str]  = field(default_factory=list)
    error:       Optional[str] = None


# ── System prompts per output type ────────────────────────────────────────────

_SYSTEM_PROMPTS: Dict[str, str] = {
    "html": (
        "You are Claude Design, Anthropic's expert UI/UX code generation system.\n"
        "Generate a COMPLETE, production-ready HTML + CSS + JS website.\n\n"
        "=== MANDATORY RULES (apply to ALL website generation) ===\n\n"
        "1. CONTEXT FIRST: Always read the website's purpose, audience and tone.\n"
        "   Diplomatic/institutional → elegant authority. Tech → bold futuristic. Health → clean trust.\n"
        "   NEVER impose a theme that contradicts the site's purpose.\n\n"
        "2. PREMIUM TECH — always use contextually appropriate technologies:\n"
        "   - Canvas particles (ALWAYS — adapt density/speed to tone: 30 slow for institutional, 150 fast for tech)\n"
        "   - Three.js for 3D (tech/innovation/ambitious sites)\n"
        "   - GSAP / CSS animations with IntersectionObserver (ALWAYS for scroll reveals)\n"
        "   - Glassmorphism cards (backdrop-filter: blur — ALWAYS)\n"
        "   - Parallax on hero images (ALWAYS when hero has background image)\n"
        "   - CSS 3D hover transforms (scale + shadow + glow on all cards)\n"
        "   - Smooth scroll (ALWAYS)\n"
        "   - Sticky blurred header (ALWAYS)\n"
        "   - Gradient text on main headings (ALWAYS)\n\n"
        "3. REAL IMAGES: Use ALL provided image URLs in the correct sections.\n"
        "   Never use placeholder images when real ones are provided.\n"
        "   Logo always in header. Photos in correct person/section.\n\n"
        "4. MINIMAL TEXT — maximum visual impact:\n"
        "   - Cards: 2-3 sentences max visible. Use SVG icons.\n"
        "   - Hero: impactful H1 + short subtitle + 2 CTAs only.\n"
        "   - Long texts: truncated with CSS, expand on click if needed.\n\n"
        "5. DESIGN STANDARDS:\n"
        "   - Glassmorphism cards: rgba(255,255,255,0.08) + backdrop-filter:blur(20px)\n"
        "   - Rounded corners: 16-24px on cards\n"
        "   - Generous spacing (section padding 100-140px)\n"
        "   - Premium typography: Cinzel/Cormorant for institutional, Inter for body\n"
        "   - Hover: transform:scale(1.03) + box-shadow upgrade\n"
        "   - Mobile: hamburger menu, all sections responsive\n\n"
        "6. PRESERVE ORIGINAL COLOR PALETTE when recreating existing sites.\n\n"
        "- Return ONLY the complete HTML document, no explanation."
    ),
    "react": (
        "You are Claude Design, Anthropic's expert UI/UX code generation system.\n"
        "Generate a production-ready React component with Tailwind CSS for the request.\n"
        "Requirements:\n"
        "- Functional component with hooks where needed\n"
        "- TypeScript props interface\n"
        "- Tailwind CSS for styling (assume v3)\n"
        "- Beautiful, modern design\n"
        "- Fully responsive\n"
        "- Include sample usage as a comment at the bottom\n"
        "- Return ONLY the component code, no explanation."
    ),
    "svg": (
        "You are Claude Design, Anthropic's expert SVG illustration system.\n"
        "Generate clean, scalable SVG code for the request.\n"
        "Requirements:\n"
        "- Clean, minimal SVG with viewBox\n"
        "- Use paths, not raster images\n"
        "- Semantic IDs for main elements\n"
        "- CSS animations where appropriate (keyframes in <style>)\n"
        "- Accessible (title + desc tags)\n"
        "- Return ONLY the SVG code, no explanation."
    ),
    "css": (
        "You are Claude Design, Anthropic's expert CSS design system generator.\n"
        "Generate comprehensive CSS for the request.\n"
        "Requirements:\n"
        "- CSS custom properties at :root level\n"
        "- Complete typography scale\n"
        "- Color palette with semantic names\n"
        "- Spacing and sizing scale\n"
        "- Component-level styles\n"
        "- Dark mode via prefers-color-scheme\n"
        "- Return ONLY the CSS, no explanation."
    ),
    "design_system": (
        "You are Claude Design, Anthropic's design system architect.\n"
        "Generate a complete design system specification as a JSON object + CSS variables.\n"
        "Include:\n"
        "- Brand colors (primary, secondary, accent, neutral scale)\n"
        "- Typography (fonts, scale, weights, line-heights)\n"
        "- Spacing scale (4px base grid)\n"
        "- Border radius, shadows, transitions\n"
        "- Component tokens (button, input, card, etc.)\n"
        "- Dark mode variants\n"
        "Return as: 1) JSON object with all tokens, 2) CSS custom properties.\n"
        "Format: ```json ... ``` then ```css ... ```"
    ),
    "wireframe": (
        "You are Claude Design, Anthropic's wireframing specialist.\n"
        "Generate a clean HTML wireframe using only grey tones and simple shapes.\n"
        "Requirements:\n"
        "- Use only: #f0f0f0, #d0d0d0, #a0a0a0, #707070, #404040\n"
        "- Boxes for images (with X pattern or img label)\n"
        "- Lorem ipsum for text placeholders\n"
        "- Clear layout hierarchy\n"
        "- Labels for interactive elements\n"
        "- Annotate with HTML comments explaining sections\n"
        "- Return ONLY the HTML wireframe."
    ),
    "slide": (
        "You are Claude Design, Anthropic's presentation design specialist.\n"
        "Generate a beautiful HTML presentation slide for the content provided.\n"
        "Requirements:\n"
        "- 16:9 aspect ratio (1280×720px)\n"
        "- Bold, clear typography (large font sizes)\n"
        "- Strong visual hierarchy\n"
        "- Minimal text — key points only\n"
        "- Beautiful background (gradient, pattern, or solid)\n"
        "- Optional: subtle CSS animation entrance\n"
        "- Return ONLY the HTML slide."
    ),
    "pitch_deck": (
        "You are Claude Design, Anthropic's pitch deck specialist.\n"
        "Generate a complete 8-10 slide HTML pitch deck.\n"
        "Slides: Title · Problem · Solution · How it works · Market size · "
        "Business model · Traction · Team · Ask/CTA\n"
        "Requirements:\n"
        "- Each slide as a <section> with id\n"
        "- JavaScript navigation (arrow keys + buttons)\n"
        "- Consistent design system across all slides\n"
        "- Professional investor-grade aesthetic\n"
        "- Return ONLY the complete HTML pitch deck."
    ),
}

_CRITIQUE_SYSTEM = (
    "You are Claude Design, Anthropic's expert UI/UX critic.\n"
    "Analyze the design and provide:\n"
    "1. OVERALL: Overall assessment (1-2 sentences)\n"
    "2. ISSUES: 3-5 specific problems (with CSS/HTML fix for each)\n"
    "3. STRENGTHS: 2-3 things that work well\n"
    "4. IMPROVED_CSS: Specific CSS improvements to apply immediately\n"
    "5. ACCESSIBILITY: Accessibility issues and ARIA fixes\n"
    "6. MOBILE: Mobile-specific issues\n"
    "Be specific. Include actual code fixes, not just descriptions."
)


class ClaudeDesign:
    """
    Claude Design integration — generates UI/UX code using Claude Opus 4.7.
    Powered by Anthropic Labs' Claude Design capabilities.
    """

    MODEL = "claude-opus-4-7"

    def __init__(self, api_key: Optional[str] = None,
                 save_dir: str = "/data/data/com.termux/files/home/ailex_vision/designs"):
        self.save_dir = save_dir
        self.client   = None
        self.available = False
        os.makedirs(save_dir, exist_ok=True)
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if key:
            try:
                import anthropic
                self.client    = anthropic.Anthropic(api_key=key)
                self.available = True
            except ImportError:
                pass

    # ── Core generation ───────────────────────────────────────────────────────

    def generate(
        self,
        description: str,
        output_type: OutputType = "html",
        context:     str = "",
        image_path:  Optional[str] = None,
        image_paths: List[str] = [],   # FIX: support multiple images
        image_urls:  List[str] = [],   # FIX: support image URLs directly
    ) -> DesignOutput:
        """Generate design code from a description."""
        start = time.time()
        if not self.available:
            return self._demo(description, output_type)

        system  = _SYSTEM_PROMPTS.get(output_type, _SYSTEM_PROMPTS["html"])
        # FIX: pass all images (single path + list + URLs)
        all_paths = ([image_path] if image_path else []) + list(image_paths)
        content = self._build_content(description, context, all_paths, image_urls)

        try:
            resp = self.client.messages.create(
                model=self.MODEL,
                max_tokens=16000,   # FIX: was 8192, cut off mid-CSS
                system=system,
                messages=[{"role": "user", "content": content}],
            )
            code  = self._extract_code(resp.content[0].text, output_type)
            title = self._extract_title(code, description, output_type)
            path  = self._save(code, output_type, title)

            return DesignOutput(
                type=output_type, title=title, code=code,
                description=description, model=self.MODEL,
                tokens_in=resp.usage.input_tokens,
                tokens_out=resp.usage.output_tokens,
                time_s=round(time.time()-start, 2),
                saved_path=path,
            )
        except Exception as e:
            return DesignOutput(type=output_type, title="", code="", description=description,
                                model=self.MODEL, error=str(e), time_s=round(time.time()-start, 2))

    def critique(
        self,
        html:        str = "",
        image_path:  Optional[str] = None,
        description: str = "",
    ) -> DesignOutput:
        """Critique an existing design (HTML or image)."""
        start = time.time()
        if not self.available:
            return self._demo_critique(description or "design")

        user_text = f"Critique this design:\n\n{html[:3000]}" if html else (description or "Critique this design.")
        content = self._build_content(user_text, "", [image_path] if (image_path and os.path.exists(image_path)) else [])

        try:
            resp = self.client.messages.create(
                model=self.MODEL,
                max_tokens=3000,
                system=_CRITIQUE_SYSTEM,
                messages=[{"role": "user", "content": content}],
            )
            text = resp.content[0].text
            suggestions = self._parse_issues(text)
            return DesignOutput(
                type="html", title="Design Critique",
                code=self._extract_code(text, "css"),
                description=description, model=self.MODEL,
                tokens_in=resp.usage.input_tokens,
                tokens_out=resp.usage.output_tokens,
                time_s=round(time.time()-start, 2),
                critique=text,
                suggestions=suggestions,
            )
        except Exception as e:
            return DesignOutput(type="html", title="Critique", code="", description=description,
                                model=self.MODEL, error=str(e), time_s=round(time.time()-start, 2))

    def improve(self, html: str, focus: str = "") -> DesignOutput:
        """Take existing HTML and return an improved version."""
        prompt = (
            f"Improve this HTML/CSS design. "
            + (f"Focus on: {focus}. " if focus else "")
            + "Fix all design issues, improve typography, spacing, color, and accessibility. "
            + "Return the complete improved HTML.\n\n"
            + f"```html\n{html[:6000]}\n```"
        )
        return self.generate(prompt, "html")

    def from_website(self, snapshot: Any) -> DesignOutput:
        """Generate improved design from a WebSnapshot — FIX: now passes logo + images."""
        # Find logo (first small image or image with 'logo' in URL)
        logo_path = None
        key_images = []
        for img in snapshot.images:
            if not img.local:
                continue
            url_low = img.url.lower()
            if any(k in url_low for k in ("logo", "brand", "icon", "emblem", "seal")):
                logo_path = img.local
            elif img.width > 200 and img.height > 200:
                key_images.append(img.local)

        # If no explicit logo found, use first image
        if not logo_path and snapshot.images and snapshot.images[0].local:
            logo_path = snapshot.images[0].local

        all_images = ([logo_path] if logo_path else []) + key_images[:3]

        ctx = (
            f"Website: {snapshot.title}\n"
            f"Description: {snapshot.description}\n"
            f"Colors: {', '.join(snapshot.colors[:6])}\n"
            f"Fonts: {', '.join(snapshot.fonts[:3])}\n"
            f"Tech: {', '.join(snapshot.tech_stack)}\n"
            f"Layout: {', '.join(snapshot.layout_hints)}\n"
            f"Text content: {snapshot.text_content[:1000]}\n"
        )
        prompt = (
            f"Redesign the '{snapshot.title}' website into a much more professional, "
            f"premium and visually superior version. "
            f"CRITICAL: Preserve the organization's identity, branding, color palette, "
            f"and professional/diplomatic tone. Keep the same logo and real photos. "
            f"Only improve the design quality, layout, and visual hierarchy. "
            f"Do NOT change the organization's character or style."
        )
        return self.generate(prompt, "html", context=ctx, image_paths=all_images)

    def recreate_website_faithful(
        self,
        snapshot: Any,
        style_direction: str = "premium and professional",
        use_original_images: bool = True,
    ) -> DesignOutput:
        """
        Faithfully recreate a website — same content, same identity, much better execution.
        FIX for the main failure: preserves original style instead of imposing new theme.
        """
        # Collect logo + all images
        logo = None
        photos = []
        for img in snapshot.images:
            if not img.local:
                continue
            url_low = img.url.lower()
            if any(k in url_low for k in ("logo","brand","icon","removebg")):
                logo = img.local
            elif img.width > 100 and img.height > 100:
                photos.append(img.local)
        if not logo and photos:
            logo = photos[0]

        all_images = ([logo] if logo else []) + photos[:4]

        # Build faithful context with ALL text content
        ctx = (
            f"ORIGINAL SITE: {snapshot.url}\n"
            f"Title: {snapshot.title}\n"
            f"Colors from original CSS: {', '.join(snapshot.colors[:8])}\n"
            f"Fonts from original CSS: {', '.join(snapshot.fonts[:4])}\n"
            f"Tech stack: {', '.join(snapshot.tech_stack)}\n"
            f"Layout: {', '.join(snapshot.layout_hints)}\n"
            f"\nFULL TEXT CONTENT:\n{snapshot.text_content[:3000]}\n"
        )

        # Build list of image URLs for use in the generated site
        img_urls = [img.url for img in snapshot.images if img.url][:10]
        img_urls_str = "\n".join(f"- {u}" for u in img_urls)

        prompt = f"""
Recreate this website — same content and identity, MUCH better premium execution.

STYLE DIRECTION: {style_direction}

MANDATORY RULES:
1. CONTEXT: Read the website purpose and audience. Choose ALL tech choices to match that context.
2. REAL IMAGES: Use every provided image URL in the CORRECT section. Logo in header always.
3. PREMIUM TECH (all required, adapted to context):
   - Canvas particles in hero (density/speed matches site tone)
   - IntersectionObserver scroll animations on every section
   - Glassmorphism cards (backdrop-filter: blur)
   - CSS 3D hover (scale + glow)
   - Parallax on hero background
   - Smooth scroll + sticky blurred header
   - Gradient text on main headings
4. LESS TEXT: Cards max 2-3 sentences. Hero: impactful title + short subtitle only.
5. PRESERVE original color palette and institutional identity exactly.
6. NEVER invent a visual theme that contradicts the organization's purpose.

Generate a complete, single-file HTML website that is drastically better than the original
while being 100% faithful to its identity, content, and purpose.
"""
        return self.generate(prompt, "html", context=ctx, image_paths=all_images)

    def from_analysis(self, analysis: Any, output_type: OutputType = "html") -> DesignOutput:
        """Generate design from VisualAnalysis."""
        prompt = (
            f"Create a {output_type} design inspired by:\n"
            f"Style: {analysis.style}\n"
            f"Mood: {analysis.dominant_mood}\n"
            f"Colors: {', '.join(analysis.colors[:5])}\n"
            f"Description: {analysis.description[:200]}\n\n"
            f"Make it even better than the original. "
            f"{analysis.improvement_prompt}"
        )
        return self.generate(prompt, output_type)

    # ── Convenience methods ───────────────────────────────────────────────────

    def generate_html(self, description: str, **kw) -> DesignOutput:
        return self.generate(description, "html", **kw)

    def generate_react(self, description: str, **kw) -> DesignOutput:
        return self.generate(description, "react", **kw)

    def generate_svg(self, description: str, **kw) -> DesignOutput:
        return self.generate(description, "svg", **kw)

    def generate_design_system(self, brand: str, **kw) -> DesignOutput:
        return self.generate(f"Design system for: {brand}", "design_system", **kw)

    def generate_wireframe(self, description: str, **kw) -> DesignOutput:
        return self.generate(description, "wireframe", **kw)

    def generate_slide(self, content: str, **kw) -> DesignOutput:
        return self.generate(content, "slide", **kw)

    def generate_pitch_deck(self, startup: str, **kw) -> DesignOutput:
        return self.generate(f"Pitch deck for: {startup}", "pitch_deck", **kw)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _build_content(self, description: str, context: str,
                        image_paths: List[str] = [],
                        image_urls:  List[str] = []) -> list:
        """Build multimodal content: text + local images + URL images. FIX: was single image only."""
        content = []

        # Local image files (up to 5, base64 encoded)
        for path in image_paths[:5]:
            if path and os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    b64  = base64.standard_b64encode(data).decode()
                    ext  = path.split(".")[-1].lower()
                    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                            "png": "image/png", "webp": "image/webp",
                            "gif": "image/gif"}.get(ext, "image/jpeg")
                    content.append({"type": "image",
                                    "source": {"type": "base64", "media_type": mime, "data": b64}})
                except Exception:
                    pass

        # URL images (up to 5, referenced directly)
        for url in image_urls[:5]:
            if url:
                content.append({"type": "image",
                                 "source": {"type": "url", "url": url}})

        text = description
        if context:
            text = f"Context:\n{context}\n\nRequest: {description}"
        content.append({"type": "text", "text": text})
        return content

    def _extract_code(self, text: str, output_type: str) -> str:
        """
        Extract code from Claude response.
        ALWAYS strips markdown fences — they must never appear in final output.
        """
        # Try fenced code blocks first
        patterns = [
            r"```(?:html|jsx|tsx|react|svg|css|json)?\s*\n([\s\S]+?)\n```",
            r"```\s*\n([\s\S]+?)\n```",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.I)
            if matches:
                code = max(matches, key=len).strip()
                return self._strip_fences(code)
        # No code block — strip any remaining fences from raw text
        return self._strip_fences(text.strip())

    def _strip_fences(self, code: str) -> str:
        """Remove any remaining markdown fence artifacts. MANDATORY."""
        code = re.sub(r'(<style[^>]*>)\s*```\w*\s*', r'\1\n', code)
        code = re.sub(r'```\s*(</style>)', r'\1', code)
        code = re.sub(r'(</head>\s*<body>)\s*```\w*\s*', r'\1\n', code)
        code = re.sub(r'```\s*(</body>)', r'\1', code)
        code = re.sub(r'^\s*```\w*\s*$', '', code, flags=re.MULTILINE)
        return code.strip()

    def _extract_title(self, code: str, description: str, output_type: str) -> str:
        if output_type in ("html", "wireframe", "slide", "pitch_deck"):
            m = re.search(r"<title[^>]*>([^<]+)</title>", code, re.I)
            if m: return m.group(1).strip()
            m = re.search(r"<h1[^>]*>([^<]+)</h1>", code, re.I)
            if m: return m.group(1).strip()[:50]
        return description[:50]

    def _save(self, code: str, output_type: str, title: str) -> str:
        ext_map = {"html": "html", "react": "tsx", "svg": "svg",
                   "css": "css", "design_system": "css", "wireframe": "html",
                   "slide": "html", "pitch_deck": "html"}
        ext   = ext_map.get(output_type, "html")
        slug  = re.sub(r"[^a-z0-9]+", "_", title.lower())[:30] or "design"
        fname = f"{slug}_{int(time.time())}.{ext}"
        path  = os.path.join(self.save_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return path

    def _parse_issues(self, text: str) -> List[str]:
        lines = text.split("\n")
        issues = [l.strip() for l in lines
                  if l.strip() and any(c in l for c in ["-", "•", "1.", "2.", "3."])]
        return [re.sub(r"^[\-•\d\.]+\s*", "", i) for i in issues[:8]]

    def _demo(self, description: str, output_type: str) -> DesignOutput:
        templates = {
            "html": f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{description[:40]}</title>
<style>
  :root {{
    --primary: #6366f1;
    --bg: #0f0f1a;
    --surface: #1a1a2e;
    --text: #e2e8f0;
    --accent: #f472b6;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; }}
  .hero {{ min-height: 100vh; display: flex; align-items: center; justify-content: center;
           background: radial-gradient(ellipse at center, var(--surface) 0%, var(--bg) 70%); }}
  .content {{ text-align: center; padding: 2rem; max-width: 600px; }}
  h1 {{ font-size: clamp(2rem, 5vw, 4rem); font-weight: 800;
        background: linear-gradient(135deg, var(--primary), var(--accent));
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  p {{ margin-top: 1rem; font-size: 1.2rem; opacity: 0.8; line-height: 1.6; }}
  .cta {{ margin-top: 2rem; padding: 0.875rem 2rem; background: var(--primary);
          color: white; border: none; border-radius: 9999px; font-size: 1rem;
          cursor: pointer; transition: transform 0.2s, opacity 0.2s; }}
  .cta:hover {{ transform: scale(1.05); opacity: 0.9; }}
</style>
</head>
<body>
  <section class="hero">
    <div class="content">
      <h1>{description[:60]}</h1>
      <p>[DEMO MODE — set ANTHROPIC_API_KEY for real Claude Design generation]</p>
      <button class="cta">Get Started</button>
    </div>
  </section>
</body>
</html>""",
            "svg": f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><title>{description[:40]}</title><circle cx="50" cy="50" r="40" fill="#6366f1" opacity="0.8"/><text x="50" y="55" text-anchor="middle" fill="white" font-size="8">DEMO</text></svg>',
            "react": f'// DEMO MODE — {description[:60]}\nexport default function Component() {{\n  return <div className="p-8 text-center">Claude Design Demo</div>;\n}}',
        }
        code = templates.get(output_type, templates["html"])
        path = self._save(code, output_type, description[:30])
        return DesignOutput(
            type=output_type, title=description[:50], code=code,
            description=description, model="demo",
            saved_path=path,
            suggestions=["Set ANTHROPIC_API_KEY to use real Claude Design (Opus 4.7)"],
        )

    def _demo_critique(self, description: str) -> DesignOutput:
        return DesignOutput(
            type="html", title="Demo Critique", code="",
            description=description, model="demo",
            critique="[DEMO MODE] Set ANTHROPIC_API_KEY for real Claude Design critique.",
            suggestions=["Set ANTHROPIC_API_KEY to enable Claude Design analysis"],
        )

    def format_output(self, d: DesignOutput) -> str:
        if d.error:
            return f"CLAUDE DESIGN FAILED: {d.error}"
        lines = [
            f"Claude Design  [{d.model}]  type={d.type}",
            f"Title:    {d.title}",
            f"Time:     {d.time_s}s | tokens_in={d.tokens_in} out={d.tokens_out}",
        ]
        if d.saved_path: lines.append(f"Saved:    {d.saved_path}")
        if d.critique:
            lines += ["", "CRITIQUE:", d.critique[:500]]
        if d.suggestions:
            lines += ["", "Suggestions:"] + [f"  • {s}" for s in d.suggestions[:5]]
        if d.model == "demo":
            lines.append("\nNOTE: Demo mode — set ANTHROPIC_API_KEY for real Claude Design")
        return "\n".join(lines)
