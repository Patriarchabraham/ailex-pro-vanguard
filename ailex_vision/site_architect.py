"""
AILEX Vision — site_architect.py
Plans complete multi-page websites before generation.
Step 1: generate sitemap + design system
Step 2: generate each page separately (full token budget per page)
Step 3: assemble with shared nav/footer/CSS

This solves the #1 generation problem: Claude cutting off mid-file
because a single 10-page site exceeds 16K tokens.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PageSpec:
    slug:        str           # "index" | "about" | "contact" | ...
    title:       str
    description: str
    sections:    List[str]     # section names in order
    parent:      str = ""      # parent page slug (for sub-pages)
    nav_label:   str = ""      # label in navigation


@dataclass
class SiteSpec:
    name:        str
    tagline:     str
    pages:       List[PageSpec]
    design:      Dict           # colors, fonts, style direction
    nav:         List[Dict]     # navigation structure
    footer:      Dict
    meta:        Dict           # SEO, OG, contact info


@dataclass
class GeneratedPage:
    spec:        PageSpec
    html:        str
    saved_path:  Optional[str]
    tokens_used: int = 0
    error:       Optional[str] = None


@dataclass
class GeneratedSite:
    spec:        SiteSpec
    pages:       List[GeneratedPage]
    shared_css:  str
    shared_js:   str
    index_path:  Optional[str]
    output_dir:  str
    total_tokens: int = 0
    duration_s:  float = 0.0


class SiteArchitect:
    """
    Plans and generates complete multi-page websites.
    Each page gets its own Claude call — no token cutoff.
    """

    SAVE_DIR = "/data/data/com.termux/files/home/ailex_vision/sites"

    def __init__(self, client: Any = None):
        self.client = client
        os.makedirs(self.SAVE_DIR, exist_ok=True)

    # ── Step 1: Plan the site ─────────────────────────────────────────────────

    def plan(self, description: str, snapshot: Any = None) -> SiteSpec:
        """
        Generate a complete sitemap and design system from a description.
        Uses Claude to decide: how many pages, what sections, what design.
        """
        if not self.client:
            return self._demo_plan(description)

        context = ""
        if snapshot:
            context = (
                f"Original site: {snapshot.title}\n"
                f"Text: {snapshot.text_content[:1000]}\n"
                f"Colors: {', '.join(snapshot.colors[:6])}\n"
                f"Tech: {', '.join(snapshot.tech_stack)}\n"
            )

        prompt = f"""
Plan a complete multi-page website for: {description}

{f"Context: {context}" if context else ""}

Return a JSON object with this exact structure:
{{
  "name": "Site Name",
  "tagline": "Short tagline",
  "design": {{
    "style": "professional|minimal|bold|elegant|futuristic",
    "primary_color": "#hex",
    "secondary_color": "#hex",
    "accent_color": "#hex",
    "background": "#hex",
    "text_color": "#hex",
    "font_heading": "Font Name",
    "font_body": "Font Name",
    "border_radius": "8px",
    "mood": "professional|energetic|calm|authoritative"
  }},
  "pages": [
    {{
      "slug": "index",
      "title": "Page Title",
      "nav_label": "Home",
      "description": "What this page contains",
      "sections": ["hero", "features", "about", "cta"],
      "parent": ""
    }}
  ],
  "nav": [
    {{"label": "Home", "slug": "index", "children": []}},
    {{"label": "About", "slug": "about", "children": []}}
  ],
  "footer": {{
    "columns": ["About", "Links", "Contact"],
    "copyright": "© 2024",
    "social": ["facebook", "twitter", "linkedin"]
  }},
  "meta": {{
    "description": "SEO description",
    "keywords": ["kw1", "kw2"],
    "contact_email": "",
    "contact_phone": ""
  }}
}}

Include 3-8 pages covering all important content areas.
Return ONLY the JSON, no explanation.
"""
        try:
            resp = self.client.messages.create(
                model="claude-opus-4-7", max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
            data = self._extract_json(text)
            return self._parse_spec(data)
        except Exception as e:
            return self._demo_plan(description)

    def _parse_spec(self, data: Dict) -> SiteSpec:
        pages = [
            PageSpec(
                slug=p.get("slug", "page"),
                title=p.get("title", ""),
                description=p.get("description", ""),
                sections=p.get("sections", []),
                parent=p.get("parent", ""),
                nav_label=p.get("nav_label", p.get("title", "")),
            )
            for p in data.get("pages", [])
        ]
        return SiteSpec(
            name=data.get("name", ""),
            tagline=data.get("tagline", ""),
            pages=pages,
            design=data.get("design", {}),
            nav=data.get("nav", []),
            footer=data.get("footer", {}),
            meta=data.get("meta", {}),
        )

    # ── Step 2: Generate shared CSS ───────────────────────────────────────────

    def generate_shared_css(self, spec: SiteSpec) -> str:
        d = spec.design
        primary   = d.get("primary_color", "#0066ff")
        secondary = d.get("secondary_color", "#1e1e2e")
        accent    = d.get("accent_color", "#d4af37")
        bg        = d.get("background", "#ffffff")
        text      = d.get("text_color", "#1a1a1a")
        radius    = d.get("border_radius", "8px")
        font_h    = d.get("font_heading", "Inter")
        font_b    = d.get("font_body", "Inter")

        return f"""
/* AILEX Generated — {spec.name} — Shared Design System */
@import url('https://fonts.googleapis.com/css2?family={font_h.replace(" ", "+")}:wght@400;600;700;800;900&family={font_b.replace(" ", "+")}:wght@300;400;500;600&display=swap');

:root {{
  --primary:    {primary};
  --secondary:  {secondary};
  --accent:     {accent};
  --bg:         {bg};
  --bg-2:       {self._darken(bg, 5)};
  --text:       {text};
  --text-muted: {self._blend(text, bg, 0.5)};
  --border:     {self._blend(primary, bg, 0.15)};
  --radius:     {radius};
  --radius-lg:  calc({radius} * 2);
  --shadow:     0 4px 24px rgba(0,0,0,0.08);
  --shadow-lg:  0 8px 48px rgba(0,0,0,0.15);
  --font-h:     '{font_h}', sans-serif;
  --font-b:     '{font_b}', system-ui, sans-serif;
  --max-w:      1200px;
  --transition: 0.2s ease;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; font-size: 16px; }}
body {{ font-family: var(--font-b); background: var(--bg); color: var(--text); line-height: 1.6; }}
img {{ max-width: 100%; height: auto; display: block; }}
a {{ color: var(--primary); text-decoration: none; transition: opacity var(--transition); }}
a:hover {{ opacity: 0.8; }}

/* Typography */
h1,h2,h3,h4,h5,h6 {{ font-family: var(--font-h); font-weight: 700; line-height: 1.2; }}
h1 {{ font-size: clamp(2rem, 5vw, 4rem); }}
h2 {{ font-size: clamp(1.5rem, 3vw, 2.5rem); }}
h3 {{ font-size: clamp(1.1rem, 2vw, 1.5rem); }}
p  {{ max-width: 65ch; }}

/* Layout */
.container {{ max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }}
section {{ padding: clamp(60px, 8vw, 120px) 0; }}
.grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 32px; }}
.grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 28px; }}
.grid-4 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; }}
.flex {{ display: flex; align-items: center; gap: 16px; }}
.flex-center {{ display: flex; align-items: center; justify-content: center; }}
.text-center {{ text-align: center; }}

/* Components */
.btn {{ display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px;
        border-radius: var(--radius); font-weight: 600; font-size: 1rem;
        transition: all var(--transition); cursor: pointer; border: none; }}
.btn-primary {{ background: var(--primary); color: #fff; }}
.btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,102,255,0.3); opacity: 1; }}
.btn-outline {{ background: transparent; color: var(--primary); border: 2px solid var(--primary); }}
.btn-outline:hover {{ background: var(--primary); color: #fff; }}

.card {{ background: var(--bg-2); border: 1px solid var(--border); border-radius: var(--radius-lg);
         padding: 28px; transition: all var(--transition); }}
.card:hover {{ transform: translateY(-4px); box-shadow: var(--shadow-lg); border-color: var(--primary); }}

.badge {{ display: inline-block; padding: 4px 12px; border-radius: 99px;
          font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
          background: color-mix(in srgb, var(--primary) 15%, transparent);
          color: var(--primary); text-transform: uppercase; }}

/* Navigation (shared) */
nav {{ position: sticky; top: 0; z-index: 100; background: var(--bg);
      border-bottom: 1px solid var(--border); backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px); }}
.nav-inner {{ max-width: var(--max-w); margin: 0 auto; padding: 0 24px;
             display: flex; align-items: center; justify-content: space-between; height: 64px; }}
.nav-logo {{ font-family: var(--font-h); font-weight: 800; font-size: 1.2rem;
            color: var(--text); display: flex; align-items: center; gap: 10px; }}
.nav-links {{ display: flex; gap: 32px; list-style: none; }}
.nav-links a {{ color: var(--text-muted); font-weight: 500; font-size: 0.95rem; transition: color var(--transition); }}
.nav-links a:hover, .nav-links a.active {{ color: var(--primary); opacity: 1; }}
.nav-cta {{ margin-left: 16px; }}
.hamburger {{ display: none; flex-direction: column; gap: 5px; cursor: pointer; padding: 8px; }}
.hamburger span {{ display: block; width: 24px; height: 2px; background: var(--text); transition: all .3s; border-radius: 2px; }}

/* Footer (shared) */
footer {{ background: var(--secondary); color: rgba(255,255,255,0.7); padding: 64px 0 32px; }}
.footer-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 40px; margin-bottom: 48px; }}
.footer-col h4 {{ color: #fff; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 16px; }}
.footer-col a {{ display: block; color: rgba(255,255,255,0.6); font-size: 0.9rem; margin-bottom: 8px; transition: color .2s; }}
.footer-col a:hover {{ color: var(--accent); opacity: 1; }}
.footer-bottom {{ border-top: 1px solid rgba(255,255,255,0.1); padding-top: 24px;
                  display: flex; justify-content: space-between; align-items: center;
                  font-size: 0.85rem; flex-wrap: wrap; gap: 12px; }}
.social-links {{ display: flex; gap: 12px; }}
.social-links a {{ width: 36px; height: 36px; border-radius: 50%;
                   background: rgba(255,255,255,0.1); display: flex;
                   align-items: center; justify-content: center; transition: .2s; }}
.social-links a:hover {{ background: var(--primary); opacity: 1; }}

/* Animations */
@keyframes fadeUp {{ from {{ opacity:0; transform:translateY(24px); }} to {{ opacity:1; transform:none; }} }}
@keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
.animate {{ animation: fadeUp 0.6s ease both; }}
.animate-d1 {{ animation-delay: 0.1s; }}
.animate-d2 {{ animation-delay: 0.2s; }}
.animate-d3 {{ animation-delay: 0.3s; }}

/* Responsive */
@media (max-width: 768px) {{
  .nav-links {{ display: none; flex-direction: column; position: absolute; top: 64px;
               left: 0; right: 0; background: var(--bg); padding: 16px 24px;
               border-bottom: 1px solid var(--border); }}
  .nav-links.open {{ display: flex; }}
  .hamburger {{ display: flex; }}
  .nav-cta {{ display: none; }}
  .footer-bottom {{ flex-direction: column; text-align: center; }}
}}
"""

    # ── Step 3: Generate shared JS ────────────────────────────────────────────

    def generate_shared_js(self, spec: SiteSpec) -> str:
        return """
// AILEX Generated — Shared JS
document.addEventListener('DOMContentLoaded', () => {
  // Mobile nav toggle
  const ham = document.querySelector('.hamburger');
  const links = document.querySelector('.nav-links');
  if (ham && links) {
    ham.addEventListener('click', () => links.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (!ham.contains(e.target) && !links.contains(e.target))
        links.classList.remove('open');
    });
  }

  // Active nav link
  const current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === current) a.classList.add('active');
  });

  // Scroll animations
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.1 });
  document.querySelectorAll('[data-animate]').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
  });

  // Add visible style
  const style = document.createElement('style');
  style.textContent = '[data-animate].visible { opacity: 1 !important; transform: none !important; }';
  document.head.appendChild(style);

  // Smooth counter animation
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count);
    const duration = 2000;
    const step = target / (duration / 16);
    let current = 0;
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = Math.floor(current).toLocaleString() + (el.dataset.suffix || '');
      if (current >= target) clearInterval(timer);
    }, 16);
  });

  // Form handling
  document.querySelectorAll('form[data-ailex]').forEach(form => {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const btn = form.querySelector('[type=submit]');
      const orig = btn?.textContent;
      if (btn) { btn.textContent = 'Sending…'; btn.disabled = true; }
      await new Promise(r => setTimeout(r, 1500));
      form.innerHTML = '<div style="text-align:center;padding:40px;color:var(--primary)"><h3>✓ Message sent!</h3><p>We will get back to you soon.</p></div>';
    });
  });
});
"""

    # ── Step 4: Generate each page ────────────────────────────────────────────

    def generate_page(self, spec: SiteSpec, page: PageSpec,
                      shared_css_path: str, shared_js_path: str,
                      image_map: Dict[str, str] = {}) -> GeneratedPage:
        if not self.client:
            return self._demo_page(spec, page, shared_css_path, shared_js_path)

        # Build navigation HTML
        nav_html = self._build_nav(spec, page.slug)
        footer_html = self._build_footer(spec)

        # List all other pages for linking
        other_pages = [f"{p.slug}.html — {p.title}" for p in spec.pages if p.slug != page.slug]

        # Gather real images for this page
        img_context = "\n".join(
            f"Use <img src=\"{url}\" loading=\"lazy\"> for {label}"
            for label, url in image_map.items()
        ) if image_map else "No specific images — use descriptive alt text only, no placeholders."

        prompt = f"""
Generate the COMPLETE HTML body content for the "{page.title}" page of {spec.name}.

DESIGN SYSTEM (already defined in shared.css — reference these CSS vars):
  Primary: {spec.design.get('primary_color','#0066ff')}
  Secondary: {spec.design.get('secondary_color','#1e1e2e')}
  Accent: {spec.design.get('accent_color','#d4af37')}
  Style: {spec.design.get('style','professional')} | Mood: {spec.design.get('mood','professional')}

PAGE: {page.title}
DESCRIPTION: {page.description}
SECTIONS TO INCLUDE (in this order): {', '.join(page.sections)}

OTHER PAGES (for internal links):
{chr(10).join(other_pages)}

IMAGES:
{img_context}

NAVIGATION (already built — include exactly as provided):
{nav_html}

FOOTER (already built — include exactly as provided):
{footer_html}

RULES:
1. Generate COMPLETE HTML document with <!DOCTYPE html> through </html>
2. Link shared files: <link rel="stylesheet" href="shared.css"> and <script src="shared.js"></script>
3. Add page-specific <style> in <head> for any extra styles
4. Use data-animate on all major sections/cards for scroll animation
5. Use CSS variables (--primary, --accent, etc.) — do NOT hardcode colours
6. All internal links must use correct .html filenames
7. Include proper meta tags, title, OG tags
8. Make ALL sections COMPLETE — no placeholders, no "lorem ipsum" unless explicitly a placeholder page
9. Forms must have data-ailex attribute for JS handling
10. Mobile responsive using CSS Grid and clamp()

Return ONLY the complete HTML. No explanations.
"""
        try:
            resp = self.client.messages.create(
                model="claude-opus-4-7", max_tokens=12000,
                messages=[{"role": "user", "content": prompt}],
            )
            html = self._extract_html(resp.content[0].text)
            path = self._save_page(html, spec, page)
            return GeneratedPage(
                spec=page, html=html, saved_path=path,
                tokens_used=resp.usage.output_tokens,
            )
        except Exception as e:
            return GeneratedPage(spec=page, html="", saved_path=None, error=str(e))

    # ── Main entry point ──────────────────────────────────────────────────────

    def generate_site(
        self,
        description:   str,
        snapshot:      Any = None,
        image_map:     Dict[str, str] = {},
        output_dir:    str = "",
    ) -> GeneratedSite:
        """Plan + generate complete multi-page site."""
        start      = time.time()
        output_dir = output_dir or os.path.join(
            self.SAVE_DIR, re.sub(r"[^a-z0-9]", "_", description[:30].lower())
        )
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Plan
        spec = self.plan(description, snapshot)

        # Step 2: Shared assets
        css = self.generate_shared_css(spec)
        js  = self.generate_shared_js(spec)

        css_path = os.path.join(output_dir, "shared.css")
        js_path  = os.path.join(output_dir, "shared.js")
        with open(css_path, "w") as f: f.write(css)
        with open(js_path,  "w") as f: f.write(js)

        # Step 3: Generate each page
        pages: List[GeneratedPage] = []
        total_tokens = 0
        for page in spec.pages:
            print(f"  Generating page: {page.title} ({page.slug})…")
            gp = self.generate_page(spec, page, "shared.css", "shared.js", image_map)
            pages.append(gp)
            total_tokens += gp.tokens_used

        index_path = next(
            (p.saved_path for p in pages if p.spec.slug == "index"),
            pages[0].saved_path if pages else None
        )

        return GeneratedSite(
            spec=spec, pages=pages,
            shared_css=css, shared_js=js,
            index_path=index_path,
            output_dir=output_dir,
            total_tokens=total_tokens,
            duration_s=round(time.time() - start, 2),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_nav(self, spec: SiteSpec, current_slug: str) -> str:
        logo_img = spec.meta.get("logo_url", "")
        logo_html = (f'<img src="{logo_img}" alt="{spec.name}" height="40">'
                     if logo_img else f'<span>{spec.name}</span>')
        items = ""
        for item in spec.nav:
            slug     = item.get("slug", "")
            label    = item.get("label", "")
            active   = "active" if slug == current_slug else ""
            children = item.get("children", [])
            if children:
                sub = "".join(
                    f'<li><a href="{c["slug"]}.html">{c["label"]}</a></li>'
                    for c in children
                )
                items += f'<li class="has-dropdown"><a href="{slug}.html" class="{active}">{label}</a><ul class="dropdown">{sub}</ul></li>'
            else:
                items += f'<li><a href="{slug}.html" class="{active}">{label}</a></li>'
        cta_page = next((p for p in spec.nav if "contact" in p.get("slug","").lower()), None)
        cta_html = (f'<a href="{cta_page["slug"]}.html" class="btn btn-primary nav-cta">Contact</a>'
                    if cta_page else "")
        return f"""<nav>
  <div class="nav-inner">
    <a href="index.html" class="nav-logo">{logo_html}</a>
    <ul class="nav-links">{items}</ul>
    {cta_html}
    <button class="hamburger" aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
  </div>
</nav>"""

    def _build_footer(self, spec: SiteSpec) -> str:
        footer_data = spec.footer
        columns     = footer_data.get("columns", [])
        copyright   = footer_data.get("copyright", f"© {time.strftime('%Y')} {spec.name}")
        socials     = footer_data.get("social", [])
        cols_html   = ""
        for col in columns:
            name   = col if isinstance(col, str) else col.get("name", "")
            links  = col.get("links", []) if isinstance(col, dict) else []
            links_html = "".join(f'<a href="#">{l}</a>' for l in links[:5])
            cols_html += f'<div class="footer-col"><h4>{name}</h4>{links_html}</div>'
        if not cols_html:
            cols_html = f'<div class="footer-col"><h4>{spec.name}</h4><p>{spec.tagline}</p></div>'
        social_icons = {"facebook":"f","twitter":"t","linkedin":"in","instagram":"ig","youtube":"yt"}
        social_html  = "".join(
            f'<a href="#" aria-label="{s}">{social_icons.get(s,s[:2].upper())}</a>'
            for s in socials
        )
        return f"""<footer>
  <div class="container">
    <div class="footer-grid">{cols_html}</div>
    <div class="footer-bottom">
      <p>{copyright} All rights reserved.</p>
      <div class="social-links">{social_html}</div>
    </div>
  </div>
</footer>"""

    def _save_page(self, html: str, spec: SiteSpec, page: PageSpec) -> str:
        site_dir = os.path.join(
            self.SAVE_DIR,
            re.sub(r"[^a-z0-9]", "_", spec.name[:25].lower())
        )
        os.makedirs(site_dir, exist_ok=True)
        path = os.path.join(site_dir, f"{page.slug}.html")
        # Strip markdown fences + QA autofix before every save
        html = self._extract_html(html)
        try:
            from ailex_vision.html_qa import HTMLQualityAssurance
            html, fixes = HTMLQualityAssurance().autofix(html)
            if fixes:
                print(f"    [QA] Auto-fixed: {', '.join(fixes[:2])}")
        except Exception:
            pass
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def _extract_html(self, text: str) -> str:
        m = re.search(r"<!DOCTYPE html[\s\S]+", text, re.I)
        if m:
            html = m.group(0)
            return re.sub(r"\s*```\s*$", "", html).strip()
        return text.strip()

    def _extract_json(self, text: str) -> Dict:
        m = re.search(r"```json\s*([\s\S]+?)\s*```", text, re.I)
        if m: text = m.group(1)
        m = re.search(r"\{[\s\S]+\}", text)
        if m: text = m.group(0)
        return json.loads(text)

    def _darken(self, hex_color: str, pct: int) -> str:
        """Darken a hex color by pct%."""
        try:
            h = hex_color.lstrip("#")
            r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            factor = (100 - pct) / 100
            return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
        except Exception:
            return hex_color

    def _blend(self, c1: str, c2: str, ratio: float) -> str:
        try:
            def parse(c): h=c.lstrip("#"); return int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
            r1,g1,b1 = parse(c1); r2,g2,b2 = parse(c2)
            r = int(r1*(1-ratio)+r2*ratio)
            g = int(g1*(1-ratio)+g2*ratio)
            b = int(b1*(1-ratio)+b2*ratio)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return c1

    def _demo_plan(self, description: str) -> SiteSpec:
        return SiteSpec(
            name=description[:40],
            tagline="Professional. Modern. Complete.",
            pages=[
                PageSpec("index",   "Home",    "Landing page with hero and features", ["hero","features","about","cta"], nav_label="Home"),
                PageSpec("about",   "About",   "About us and team",                   ["hero","story","team","values"],  nav_label="About"),
                PageSpec("services","Services","Our services and offerings",           ["hero","list","pricing","faq"],   nav_label="Services"),
                PageSpec("contact", "Contact", "Contact form and information",         ["hero","form","map","info"],      nav_label="Contact"),
            ],
            design={"primary_color":"#0066ff","secondary_color":"#1e1e2e","accent_color":"#d4af37",
                    "background":"#ffffff","text_color":"#1a1a2e","style":"professional",
                    "font_heading":"Inter","font_body":"Inter","border_radius":"8px","mood":"professional"},
            nav=[{"label":"Home","slug":"index","children":[]},
                 {"label":"About","slug":"about","children":[]},
                 {"label":"Services","slug":"services","children":[]},
                 {"label":"Contact","slug":"contact","children":[]}],
            footer={"columns":["Company","Services","Contact"],"copyright":f"© {time.strftime('%Y')}","social":["linkedin","twitter"]},
            meta={"description":description[:150],"keywords":[]},
        )

    def _demo_page(self, spec: SiteSpec, page: PageSpec,
                   css_path: str, js_path: str) -> GeneratedPage:
        d = spec.design
        nav    = self._build_nav(spec, page.slug)
        footer = self._build_footer(spec)
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page.title} — {spec.name}</title>
<link rel="stylesheet" href="{css_path}">
</head>
<body>
{nav}
<main>
  <section style="padding:120px 0;background:linear-gradient(135deg,{d.get('primary_color','#0066ff')}22,{d.get('accent_color','#d4af37')}11)">
    <div class="container text-center">
      <span class="badge animate">{page.nav_label}</span>
      <h1 class="animate animate-d1" style="margin:16px 0">{page.title}</h1>
      <p class="animate animate-d2" style="margin:0 auto 32px;color:var(--text-muted)">{page.description}</p>
      <div class="flex-center gap-16 animate animate-d3">
        <a href="index.html" class="btn btn-primary">Home</a>
        <a href="contact.html" class="btn btn-outline">Contact</a>
      </div>
    </div>
  </section>
  <section><div class="container">
    <div class="grid-3">
      {"".join(f'<div class="card" data-animate><h3>{s.title()}</h3><p>Complete content for {s} section.</p></div>' for s in page.sections[:6])}
    </div>
  </div></section>
</main>
{footer}
<script src="{js_path}"></script>
</body>
</html>"""
        path = self._save_page(html, spec, page)
        return GeneratedPage(spec=page, html=html, saved_path=path)

    def format_result(self, site: GeneratedSite) -> str:
        lines = [
            f"Site: {site.spec.name}",
            f"Pages: {len(site.pages)} | Tokens: {site.total_tokens:,} | Time: {site.duration_s}s",
            f"Output: {site.output_dir}",
            "",
        ]
        for p in site.pages:
            status = "✓" if p.saved_path and not p.error else "✗"
            lines.append(f"  {status} {p.spec.slug:15s} — {p.spec.title}")
            if p.error: lines.append(f"    Error: {p.error}")
        lines += ["", f"  → shared.css + shared.js", f"  → Open: {site.index_path}"]
        return "\n".join(lines)
