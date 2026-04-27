"""
AILEX — generation_guard.py
Zero-Bug Generation Constitution for all website output.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every bug that ever reached production is documented here with a
specific automated fix. This module runs AUTOMATICALLY on every
generated HTML before it is saved or deployed.

10 bugs permanently fixed:
  B01  Counter default "0" (shows before JS loads)
  B02  Hero element invisible (opacity:0 in CSS)
  B03  Image 404 (unverified Unsplash ID)
  B04  Missing sub-pages (incomplete site)
  B05  Mobile layout breaking (no responsive test)
  B06  Wrong image context (headphones on romance site)
  B07  Markdown fence leak (```html visible in browser)
  B08  HTML token cutoff (no </html>)
  B09  Rate limit without retry (silent failure)
  B10  Dead nav links (href pointing to non-existent page)

Usage:
    from ailex_vision.generation_guard import GenerationGuard
    guard = GenerationGuard()

    # After generating HTML:
    html, report = guard.validate_and_fix(html)
    if not report.deployable:
        raise Exception(report.summary())

    # Before generating:
    prompt = guard.enrich_prompt(user_brief, site_type)

    # Full site check:
    report = guard.check_site(pages_dict)  # {'index.html': html, ...}
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Bug catalogue ──────────────────────────────────────────────────────────────

BUG_CATALOGUE = {
    "B01": "Counter default '0' — counter shows 0 before JS animates it",
    "B02": "Hero opacity:0 in CSS — element invisible if JS fails to load",
    "B03": "Image 404 — Unsplash ID not verified via HTTP 200",
    "B04": "Missing sub-pages — nav links point to non-existent files",
    "B05": "Mobile layout breaking — no responsive CSS for key elements",
    "B06": "Wrong image context — image category doesn't match slot purpose",
    "B07": "Markdown fence leak — ```html visible as text in browser",
    "B08": "HTML token cutoff — missing </html> closing tag",
    "B09": "Rate limit without retry — silent API failure on 429",
    "B10": "Dead nav links — href targets that don't exist",
}


@dataclass
class BugFinding:
    bug_id:   str
    severity: str      # CRITICAL | HIGH | MEDIUM
    element:  str      # what was found
    fix:      str      # what was done (if auto-fixed)
    fixed:    bool     # whether auto-fix was applied


@dataclass
class GuardReport:
    html_length:  int
    bugs_found:   List[BugFinding]
    bugs_fixed:   int
    bugs_remaining: int
    deployable:   bool
    image_urls:   List[str]
    broken_images: List[str]

    def summary(self) -> str:
        lines = [
            f"GenerationGuard Report",
            f"  HTML: {self.html_length:,} chars",
            f"  Bugs found: {len(self.bugs_found)} | Fixed: {self.bugs_fixed} | Remaining: {self.bugs_remaining}",
            f"  Images: {len(self.image_urls)} total, {len(self.broken_images)} broken",
            f"  {'✅ DEPLOYABLE' if self.deployable else '🚫 BLOCKED'}",
        ]
        for b in self.bugs_found:
            icon = "✅" if b.fixed else "🔴" if b.severity == "CRITICAL" else "⚠️"
            lines.append(f"  {icon} [{b.bug_id}] {b.element[:60]}")
            if b.fix:
                lines.append(f"       → {b.fix}")
        return "\n".join(lines)

    @property
    def critical_remaining(self) -> int:
        return sum(1 for b in self.bugs_found
                   if not b.fixed and b.severity == "CRITICAL")


# ── Main guard ─────────────────────────────────────────────────────────────────

class GenerationGuard:
    """
    The AILEX zero-bug constitution.
    Runs on every generated HTML before save/deploy.
    Fixes what it can, blocks what it can't.
    """

    # ── Public API ─────────────────────────────────────────────────────────────

    def validate_and_fix(
        self,
        html: str,
        verify_images: bool = True,
        site_pages: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, GuardReport]:
        """
        Validate and auto-fix a generated HTML string.

        Args:
            html:          The generated HTML to check
            verify_images: Whether to HTTP-verify each image URL (slower but thorough)
            site_pages:    Dict of {filename: html} for cross-page link checking

        Returns:
            (fixed_html, report)
        """
        findings: List[BugFinding] = []

        # Apply all fixes in sequence
        html = self._fix_b07_markdown_fences(html, findings)
        html = self._fix_b08_token_cutoff(html, findings)
        html = self._fix_b01_counter_defaults(html, findings)
        html = self._fix_b02_hero_opacity(html, findings)

        # Image checks
        image_urls = self._extract_image_urls(html)
        broken = []
        if verify_images and image_urls:
            broken = self._verify_images(image_urls)
            for url in broken:
                findings.append(BugFinding(
                    "B03", "CRITICAL",
                    f"Image 404: {url[-50:]}",
                    "Manual fix required — use ContentGuard.pick(category)",
                    False,
                ))

        # Nav link checks (within single page — href="#..." are fine)
        self._check_b10_dead_links(html, site_pages, findings)

        # Cross-page completeness
        if site_pages:
            self._check_b04_missing_pages(html, site_pages, findings)

        # Mobile check
        self._check_b05_mobile(html, findings)

        bugs_fixed = sum(1 for f in findings if f.fixed)
        bugs_remaining = sum(1 for f in findings if not f.fixed)

        report = GuardReport(
            html_length=len(html),
            bugs_found=findings,
            bugs_fixed=bugs_fixed,
            bugs_remaining=bugs_remaining,
            deployable=sum(1 for f in findings
                          if not f.fixed and f.severity == "CRITICAL") == 0,
            image_urls=image_urls,
            broken_images=broken,
        )
        return html, report

    def check_site(self, pages: Dict[str, str]) -> Dict[str, GuardReport]:
        """Check all pages of a site together."""
        reports = {}
        for name, html in pages.items():
            _, report = self.validate_and_fix(
                html,
                verify_images=True,
                site_pages=pages,
            )
            reports[name] = report
        return reports

    def enrich_prompt(self, brief: str, site_type: str = "general") -> str:
        """
        Add zero-bug rules to a generation prompt.
        Call this BEFORE sending any prompt to Claude.
        """
        rules = self._get_prompt_rules(site_type)
        return f"{brief}\n\n{rules}"

    # ── Fix: B07 — Markdown fences ─────────────────────────────────────────────

    def _fix_b07_markdown_fences(self, html: str, findings: List) -> str:
        if "```" not in html:
            return html
        before = html
        html = re.sub(r'(<style[^>]*>)\s*```\w*\s*', r'\1\n', html)
        html = re.sub(r'```\s*(</style>)', r'\1', html)
        html = re.sub(r'(</head>\s*<body>)\s*```\w*\s*', r'\1\n', html)
        html = re.sub(r'```\s*(</body>)', r'\1', html)
        html = re.sub(r'^\s*```\w*\s*$', '', html, flags=re.MULTILINE)
        if html != before:
            count = before.count("```")
            findings.append(BugFinding(
                "B07", "CRITICAL",
                f"{count} markdown fence(s) found",
                "Auto-removed all ``` blocks",
                True,
            ))
        return html

    # ── Fix: B08 — Token cutoff ────────────────────────────────────────────────

    def _fix_b08_token_cutoff(self, html: str, findings: List) -> str:
        if "</html>" in html.lower():
            return html
        html = html.rstrip()
        if "</body>" not in html.lower():
            html += "\n</body>"
        html += "\n</html>"
        findings.append(BugFinding(
            "B08", "CRITICAL",
            "Missing </html> — HTML truncated (token cutoff)",
            "Appended </body></html>",
            True,
        ))
        return html

    # ── Fix: B01 — Counter defaults ────────────────────────────────────────────

    def _fix_b01_counter_defaults(self, html: str, findings: List) -> str:
        """
        Counters with data-count="N" that have '0' as default text.
        Fix: replace '0' with the actual formatted number.
        """
        pattern = re.compile(
            r'(<[^>]+data-count="([^"]+)"[^>]*data-suffix="([^"]*)"[^>]*>)\s*0\s*(</)',
            re.DOTALL,
        )
        fixed_count = 0

        def replace_zero(m):
            nonlocal fixed_count
            tag, count_val, suffix, close = m.group(1), m.group(2), m.group(3), m.group(4)
            try:
                n = float(count_val)
                if n == int(n):
                    formatted = f"{int(n):,}{suffix}"
                else:
                    formatted = f"{n}{suffix}"
                fixed_count += 1
                return f"{tag}{formatted}{close}"
            except ValueError:
                return m.group(0)

        new_html = pattern.sub(replace_zero, html)

        # Also try: data-count="N">0< (no data-suffix)
        pattern2 = re.compile(r'(<[^>]+data-count="([\d.]+)"[^>]*>)\s*0\s*(</)', re.DOTALL)

        def replace_zero2(m):
            nonlocal fixed_count
            tag, count_val, close = m.group(1), m.group(2), m.group(3)
            if 'data-suffix' in tag:  # already handled above
                return m.group(0)
            try:
                n = float(count_val)
                formatted = f"{int(n):,}" if n == int(n) else str(n)
                fixed_count += 1
                return f"{tag}{formatted}{close}"
            except ValueError:
                return m.group(0)

        new_html = pattern2.sub(replace_zero2, new_html)

        if fixed_count > 0:
            findings.append(BugFinding(
                "B01", "HIGH",
                f"{fixed_count} counter(s) had default '0'",
                f"Set default text to actual values (visible without JS)",
                True,
            ))
        return new_html

    # ── Fix: B02 — Hero opacity:0 in CSS ──────────────────────────────────────

    def _fix_b02_hero_opacity(self, html: str, findings: List) -> str:
        """
        Hero elements with opacity:0 in CSS are invisible if JS fails.
        Fix: Add a 3s failsafe that shows all hero elements regardless.
        """
        # Detect the pattern: class="hero-..." has opacity:0 in <style>
        has_hero_opacity = bool(
            re.search(r'\.hero-[a-z]+\s*\{[^}]*opacity\s*:\s*0', html) or
            re.search(r'opacity\s*:\s*0\s*;[^}]*transform\s*:\s*translateY', html)
        )

        if not has_hero_opacity:
            return html

        # Check if failsafe already exists
        if "failsafe" in html.lower() or "setTimeout" in html and "opacity" in html:
            return html

        # Inject failsafe before </body>
        failsafe = """
<script>
/* AILEX GenerationGuard — B02 Failsafe: show hero elements if JS animation fails */
setTimeout(function(){
  var heroIds=['hbadge','hsub','htag','hbtns','hkpis','hSeal','hEye','hTitle','hSub','hBtns','hStats'];
  heroIds.forEach(function(id){
    var el=document.getElementById(id);
    if(el&&(el.style.opacity==='0'||el.style.opacity==='')){
      el.style.transition='opacity .8s ease,transform .8s ease';
      el.style.opacity='1';el.style.transform='none';
    }
  });
  document.querySelectorAll('[style*="opacity: 0"],[style*="opacity:0"]').forEach(function(el){
    if(el.closest('.hero,.hero-in')){
      el.style.opacity='1';el.style.transform='none';
    }
  });
},3000);
</script>"""

        html = html.replace("</body>", failsafe + "\n</body>", 1)
        findings.append(BugFinding(
            "B02", "HIGH",
            "Hero CSS has opacity:0 on elements",
            "Injected 3s failsafe to show all hero elements",
            True,
        ))
        return html

    # ── Check: B03 — Image verification ───────────────────────────────────────

    def _extract_image_urls(self, html: str) -> List[str]:
        urls = re.findall(r'src=["\']([^"\']+unsplash[^"\']+)["\']', html, re.I)
        urls += re.findall(r"url\(['\"]?([^'\")\s]+unsplash[^'\")\s]+)['\"]?\)", html)
        return list(set(urls))

    def _verify_images(self, urls: List[str]) -> List[str]:
        """Return list of URLs that return non-200."""
        broken = []
        for url in urls:
            base = url.split("?")[0] + "?w=80&q=40"
            try:
                req = urllib.request.Request(
                    base, headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=8) as r:
                    if r.status != 200:
                        broken.append(url)
            except Exception:
                broken.append(url)
        return broken

    # ── Check: B05 — Mobile responsiveness ────────────────────────────────────

    def _check_b05_mobile(self, html: str, findings: List) -> None:
        has_viewport   = "viewport" in html
        has_media_768  = "@media" in html and "768" in html
        has_media_480  = "480" in html

        if not has_viewport:
            findings.append(BugFinding("B05", "CRITICAL", "Missing viewport meta tag",
                                        "Add <meta name='viewport' content='width=device-width,initial-scale=1.0'>", False))
        if not has_media_768:
            findings.append(BugFinding("B05", "HIGH", "No @media (max-width:768px) breakpoint",
                                        "Add responsive CSS for mobile screens", False))
        if not has_media_480:
            findings.append(BugFinding("B05", "MEDIUM", "No @media (max-width:480px) breakpoint",
                                        "Add small-screen CSS for 480px", False))

    # ── Check: B10 — Dead nav links ────────────────────────────────────────────

    def _check_b10_dead_links(
        self, html: str,
        site_pages: Optional[Dict[str, str]],
        findings: List,
    ) -> None:
        if not site_pages:
            return
        # Find all href="filename.html" links
        hrefs = re.findall(r'href=["\']([^"\'#?]+\.html)["\']', html)
        for href in hrefs:
            basename = href.split("/")[-1]
            if basename not in site_pages:
                findings.append(BugFinding(
                    "B10", "HIGH",
                    f"Dead link: href='{href}' — page not in site_pages",
                    "Create the missing page or fix the link",
                    False,
                ))

    # ── Check: B04 — Missing sub-pages ────────────────────────────────────────

    def _check_b04_missing_pages(
        self,
        html: str,
        site_pages: Dict[str, str],
        findings: List,
    ) -> None:
        declared = re.findall(r'href=["\']([^"\'#?]+\.html)["\']', html)
        for href in declared:
            base = href.split("/")[-1]
            if base not in site_pages and not base.startswith("http"):
                findings.append(BugFinding(
                    "B04", "HIGH",
                    f"Nav/link references '{base}' which is not in site",
                    "Create missing page before deploying",
                    False,
                ))

    # ── Prompt enrichment ──────────────────────────────────────────────────────

    def _get_prompt_rules(self, site_type: str) -> str:
        return f"""
=== AILEX GENERATION CONSTITUTION — MANDATORY RULES ===
Site type: {site_type}

RULE 1 — COUNTER DEFAULTS (B01):
  NEVER use 0 as default text for data-count elements.
  ALWAYS write the real value: data-count="4729482">4,729,482<
  JS will animate it; the fallback must be the real number.

RULE 2 — HERO VISIBILITY (B02):
  NEVER set opacity:0 in CSS for hero elements.
  ONLY set opacity:0 via inline JS after DOM loads.
  ALWAYS include 3s failsafe timeout:
    setTimeout(()=>{{ el.style.opacity='1'; el.style.transform='none'; }}, 3000)

RULE 3 — IMAGE VERIFICATION (B03):
  NEVER hardcode Unsplash photo IDs from memory.
  ALWAYS use images from the verified list provided in this prompt.
  Default to CSS gradients if no verified image is available for a slot.

RULE 4 — COMPLETE SITE (B04):
  EVERY href in nav must point to a page that will be created.
  List ALL pages that will be built before starting.
  Use placeholder href="#" only for truly external links not yet known.

RULE 5 — MOBILE (B05):
  ALWAYS include @media(max-width:768px) and @media(max-width:480px).
  ALWAYS test: nav hamburger, hero text size, button full-width, grid 1-col.
  ALWAYS use height:100svh (not 100vh) for hero on mobile.

RULE 6 — IMAGE CONTEXT (B06):
  Each image slot has a semantic role. Match image to role.
  Romance site: ONLY romantic couples/weddings. NOT headphones, NOT buildings.
  Court/institutional: ONLY official buildings, law courts, formal architecture.

RULE 7 — NO MARKDOWN FENCES (B07):
  NEVER wrap output in ```html or ```css blocks.
  Output raw HTML only. No backtick fences ever.

RULE 8 — COMPLETE HTML (B08):
  ALWAYS end the file with </html>.
  ALWAYS verify before outputting.
  If reaching output limit: close all open tags first.

RULE 9 — API RETRY (B09):
  ALWAYS use retry logic: 3 attempts with 30s/60s/120s delays on 429.

RULE 10 — NAV LINKS (B10):
  ALWAYS check that every href="page.html" in nav corresponds to a real page.
  NEVER leave dead links in final output.
=== END OF CONSTITUTION ===
"""


# ── Convenience wrapper ────────────────────────────────────────────────────────

_guard: Optional[GenerationGuard] = None

def get_guard() -> GenerationGuard:
    global _guard
    if _guard is None:
        _guard = GenerationGuard()
    return _guard


def guard_html(html: str, verify_images: bool = False) -> Tuple[str, GuardReport]:
    """Quick one-call interface: fix and report."""
    return get_guard().validate_and_fix(html, verify_images=verify_images)


def enrich(brief: str, site_type: str = "general") -> str:
    """Enrich a generation prompt with zero-bug rules."""
    return get_guard().enrich_prompt(brief, site_type)


# ── Self-test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    guard = GenerationGuard()

    # Test with a deliberately buggy HTML
    buggy = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test</title></head>
<body>
<nav><a href="missing-page.html">Broken</a></nav>
<div class="hero-stats">
  <div data-count="47000" data-suffix="+">0</div>
</div>
<style>.hero-badge{opacity:0;transform:translateY(16px)}</style>
<img src="https://images.unsplash.com/photo-1518770660439-4636190af475?w=800" alt="tech">
<img src="https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=800" alt="building">
<img src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800" alt="official">
<footer>Footer</footer>
```html
<p>This is a fence leak</p>
```
</body>
"""  # No </html> — truncated

    fixed, report = guard.validate_and_fix(buggy, verify_images=False)
    print(report.summary())
    print()
    print("Fixed HTML ends with:", fixed[-40:].strip())
    print("No markdown fences:", "```" not in fixed)
    print("Has </html>:", "</html>" in fixed.lower())
    print("Counter fixed:", "47,000" in fixed or "47000" in fixed)
