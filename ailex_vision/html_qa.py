"""
AILEX — html_qa.py
HTML Quality Assurance: automated pre-deploy validation.
Catches ALL known error patterns before a site goes live.

This module runs AUTOMATICALLY before every deploy.
Zero tolerance: if any CRITICAL check fails, deploy is blocked.

Built from forensic analysis of 8 real bugs found in production.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class QACheck:
    id:          str
    name:        str
    severity:    str     # CRITICAL | HIGH | MEDIUM | LOW
    passed:      bool
    detail:      str = ""
    autofix:     str = ""   # suggested fix


@dataclass
class QAReport:
    html:        str
    checks:      List[QACheck]
    passed:      int
    failed:      int
    critical:    int
    score:       float
    deployable:  bool    # False = BLOCK deploy
    fixes:       List[str]


class HTMLQualityAssurance:
    """
    Pre-deploy HTML validator. 20+ checks across all known failure modes.
    Blocks deploy on CRITICAL failures. Warns on HIGH/MEDIUM.

    Every check maps to a real bug that hit production.
    """

    def validate(self, html: str, url: str = "") -> QAReport:
        checks: List[QACheck] = []

        # ── CRITICAL: Structure ───────────────────────────────────────────────
        checks.append(self._check_closing_html(html))
        checks.append(self._check_no_markdown_fences(html))
        checks.append(self._check_has_body(html))
        checks.append(self._check_encoding(html))

        # ── CRITICAL: JavaScript ─────────────────────────────────────────────
        checks.append(self._check_counter_observer(html))
        checks.append(self._check_no_template_literals_in_strings(html))
        checks.append(self._check_form_handler(html))

        # ── CRITICAL: Zero-Bug Constitution (GenerationGuard) ─────────────────
        checks.append(self._check_counter_defaults(html))    # B01
        checks.append(self._check_viewport_present(html))    # B05 critical
        checks.append(self._check_mobile_breakpoints(html))  # G003
        checks.append(self._check_closing_html_strict(html)) # G004 — same as C001 but explicit

        # ── HIGH: Content ─────────────────────────────────────────────────────
        checks.append(self._check_has_images(html))
        checks.append(self._check_no_empty_sections(html))
        checks.append(self._check_italian_content(html))
        checks.append(self._check_nav_exists(html))
        checks.append(self._check_footer_exists(html))

        # ── HIGH: Performance ─────────────────────────────────────────────────
        checks.append(self._check_hero_image_eager(html))
        checks.append(self._check_other_images_lazy(html))
        checks.append(self._check_fonts_linked(html))

        # ── MEDIUM: Accessibility & SEO ───────────────────────────────────────
        checks.append(self._check_meta_description(html))
        checks.append(self._check_title_tag(html))
        checks.append(self._check_lang_attribute(html))
        checks.append(self._check_alt_attributes(html))
        checks.append(self._check_no_console_logs(html))

        # ── LOW: Quality ──────────────────────────────────────────────────────
        checks.append(self._check_viewport_meta(html))
        checks.append(self._check_charset(html))
        checks.append(self._check_no_broken_urls(html))

        passed   = sum(1 for c in checks if c.passed)
        failed   = len(checks) - passed
        critical = sum(1 for c in checks if not c.passed and c.severity == "CRITICAL")
        score    = round(100 * passed / len(checks), 1)
        fixes    = [c.autofix for c in checks if not c.passed and c.autofix]

        return QAReport(
            html=html[:100],
            checks=checks,
            passed=passed,
            failed=failed,
            critical=critical,
            score=score,
            deployable=critical == 0,
            fixes=fixes,
        )

    # ── CRITICAL CHECKS ───────────────────────────────────────────────────────

    def _check_closing_html(self, html: str) -> QACheck:
        """E003: Token cutoff — HTML truncado."""
        passed = "</html>" in html.lower()
        return QACheck("C001", "HTML has closing </html>", "CRITICAL",
                        passed, "" if passed else "File truncated — token cutoff",
                        "Use phased generation. Verify </html> before saving.")

    def _check_no_markdown_fences(self, html: str) -> QACheck:
        """E001: Markdown fence leak — ```html visível na página."""
        fences = len(re.findall(r'```', html))
        passed = fences == 0
        return QACheck("C002", "No markdown fences (```)", "CRITICAL",
                        passed,
                        f"{fences} backtick groups found" if not passed else "",
                        "Call _strip_fences() before saving. Never skip this step.")

    def _check_has_body(self, html: str) -> QACheck:
        """Basic structure: must have <body>."""
        passed = "<body" in html.lower() and "</body>" in html.lower()
        return QACheck("C003", "Has complete <body>", "CRITICAL", passed,
                        "" if passed else "Body tag missing or incomplete")

    def _check_encoding(self, html: str) -> QACheck:
        """UTF-8 charset declared."""
        passed = 'charset="UTF-8"' in html or "charset='UTF-8'" in html or "charset=UTF-8" in html.lower()
        return QACheck("C004", "UTF-8 charset declared", "CRITICAL", passed,
                        "" if passed else "Add <meta charset='UTF-8'>")

    def _check_counter_observer(self, html: str) -> QACheck:
        """E002: Counter showing 0 — observer on wrong elements."""
        has_data_count  = "data-count" in html
        has_counter_obs = (
            # Must observe [data-count] directly, not only [data-animate]
            bool(re.search(r'querySelectorAll\(["\']?\[data-count\]', html)) or
            bool(re.search(r'data-count.*IntersectionObserver|counterObserver', html))
        )
        if not has_data_count:
            return QACheck("C005", "Counter animation correct", "CRITICAL", True, "No counters — OK")
        passed = has_counter_obs
        return QACheck("C005", "Counter observer watches [data-count] directly", "CRITICAL",
                        passed,
                        "Counters will show 0 — observer on wrong elements" if not passed else "",
                        "Use separate counterObserver that observes [data-count] directly.")

    def _check_no_template_literals_in_strings(self, html: str) -> QACheck:
        """E006 variant: {a} placeholder left in JS strings."""
        # Check for unfilled placeholders like '{a}' in color strings
        bad = re.findall(r"['\"]rgba\([^'\"]*\{[a-z]\}[^'\"]*['\"]", html)
        passed = len(bad) == 0
        return QACheck("C006", "No unfilled JS placeholders ({a})", "CRITICAL",
                        passed,
                        f"Unfilled placeholder: {bad[0][:50]}" if bad else "",
                        "Replace template placeholders with actual values before generating.")

    def _check_form_handler(self, html: str) -> QACheck:
        """Forms must have submit handler."""
        has_form = "<form" in html
        if not has_form:
            return QACheck("C007", "Form submit handler", "CRITICAL", True, "No form — OK")
        has_handler = "addEventListener('submit'" in html or 'addEventListener("submit"' in html
        return QACheck("C007", "Form has submit handler", "CRITICAL",
                        has_handler,
                        "" if has_handler else "Form submits to nowhere",
                        "Add form.addEventListener('submit', ...) in JS.")

    # ── HIGH CHECKS ───────────────────────────────────────────────────────────

    def _check_has_images(self, html: str) -> QACheck:
        """E005: Sections without images."""
        imgs = len(re.findall(r'<img[^>]+src=', html, re.I)) + \
               len(re.findall(r'background[^:]*:\s*url\(', html))
        passed = imgs >= 3
        return QACheck("H001", f"Has real images ({imgs} found)", "HIGH",
                        passed,
                        f"Only {imgs} images — sections will look empty" if not passed else "",
                        "Add Unsplash image URLs to prompt. Minimum 5 images.")

    def _check_no_empty_sections(self, html: str) -> QACheck:
        """Sections with no meaningful content."""
        empty = len(re.findall(
            r'<section[^>]*>\s*<div[^>]*>\s*</div>\s*</section>',
            html, re.I | re.S
        ))
        passed = empty == 0
        return QACheck("H002", "No empty sections", "HIGH",
                        passed,
                        f"{empty} empty sections found" if not passed else "")

    def _check_italian_content(self, html: str) -> QACheck:
        """For Italian sites: verify Italian text present."""
        italian_words = ["il", "la", "un", "una", "per", "con", "che", "del", "della",
                         "gli", "una", "delle", "profilo", "amore", "trova", "scopri"]
        found = sum(1 for w in italian_words
                   if re.search(rf'\b{w}\b', html, re.I))
        passed = found >= 6
        return QACheck("H003", "Italian content present", "HIGH",
                        passed,
                        f"Only {found}/15 Italian words — site may be in wrong language" if not passed else "")

    def _check_nav_exists(self, html: str) -> QACheck:
        has_nav = "<nav" in html.lower()
        return QACheck("H004", "Navigation exists", "HIGH",
                        has_nav, "" if has_nav else "No <nav> tag found")

    def _check_footer_exists(self, html: str) -> QACheck:
        has_footer = "<footer" in html.lower()
        return QACheck("H005", "Footer exists", "HIGH",
                        has_footer, "" if has_footer else "No <footer> tag found")

    # ── PERFORMANCE CHECKS ────────────────────────────────────────────────────

    def _check_hero_image_eager(self, html: str) -> QACheck:
        """Hero image should be eager (not lazy) for LCP."""
        has_hero_img = re.search(r'class="hero[^"]*"', html)
        if not has_hero_img:
            return QACheck("P001", "Hero image eager loading", "HIGH", True, "No hero — OK")
        # Look for lazy loading on hero background img
        lazy_in_hero = re.search(
            r'(hero[^>]{0,200}loading=["\']lazy["\']|loading=["\']lazy["\'][^>]{0,200}hero)',
            html, re.S
        )
        passed = lazy_in_hero is None
        return QACheck("P001", "Hero image loads eagerly (not lazy)", "HIGH",
                        passed,
                        "Hero has loading='lazy' — hurts LCP score" if not passed else "",
                        "Set loading='eager' on hero background image.")

    def _check_other_images_lazy(self, html: str) -> QACheck:
        """Non-hero images should be lazy."""
        all_imgs = re.findall(r'<img[^>]+>', html, re.I)
        non_lazy = [i for i in all_imgs
                   if 'loading="lazy"' not in i and "loading='lazy'" not in i
                   and 'hero' not in i.lower() and 'logo' not in i.lower()]
        passed = len(non_lazy) <= 2  # allow a couple without lazy
        return QACheck("P002", "Non-hero images have lazy loading", "HIGH",
                        passed,
                        f"{len(non_lazy)} images missing loading='lazy'" if not passed else "",
                        "Add loading='lazy' to all non-hero images.")

    def _check_fonts_linked(self, html: str) -> QACheck:
        """Google Fonts linked."""
        has_fonts = "fonts.googleapis.com" in html
        return QACheck("P003", "Google Fonts linked", "HIGH",
                        has_fonts, "" if has_fonts else "No Google Fonts — system font fallback only")

    # ── SEO / ACCESSIBILITY ───────────────────────────────────────────────────

    def _check_meta_description(self, html: str) -> QACheck:
        has_desc = bool(re.search(r'<meta[^>]+name=["\']description["\']', html, re.I))
        return QACheck("S001", "Meta description present", "MEDIUM",
                        has_desc, "" if has_desc else "Missing meta description — bad for SEO")

    def _check_title_tag(self, html: str) -> QACheck:
        has_title = bool(re.search(r'<title>[^<]+</title>', html, re.I))
        return QACheck("S002", "Title tag present and non-empty", "MEDIUM",
                        has_title, "" if has_title else "Missing or empty <title>")

    def _check_lang_attribute(self, html: str) -> QACheck:
        has_lang = 'lang="' in html or "lang='" in html
        return QACheck("S003", "HTML lang attribute", "MEDIUM",
                        has_lang, "" if has_lang else "Add lang='it' (or appropriate) to <html>")

    def _check_alt_attributes(self, html: str) -> QACheck:
        imgs = re.findall(r'<img[^>]+>', html, re.I)
        no_alt = [i for i in imgs if 'alt=' not in i.lower()]
        passed = len(no_alt) == 0
        return QACheck("S004", "All images have alt attributes", "MEDIUM",
                        passed,
                        f"{len(no_alt)} images missing alt" if not passed else "")

    def _check_no_console_logs(self, html: str) -> QACheck:
        logs = len(re.findall(r'console\.log\s*\(', html))
        passed = logs == 0
        return QACheck("S005", "No console.log in production JS", "LOW",
                        passed,
                        f"{logs} console.log found" if not passed else "")

    # ── ZERO-BUG CONSTITUTION CHECKS (GenerationGuard) ────────────────────────

    def _check_counter_defaults(self, html: str) -> QACheck:
        """B01: Counters must not have '0' as default text — visible before JS loads."""
        pattern = re.compile(
            r'data-count="([\d.]+)"[^>]*(?:data-suffix="[^"]*")?[^>]*>\s*0\s*</',
            re.DOTALL,
        )
        zeros = pattern.findall(html)
        passed = len(zeros) == 0
        return QACheck(
            "G001", "Counter defaults are real values (not 0)", "CRITICAL",
            passed,
            f"{len(zeros)} counter(s) default to '0' — invisible without JS" if not passed else "",
            "Set counter default text to the actual number, e.g. data-count='47000'>47,000<",
        )

    def _check_viewport_present(self, html: str) -> QACheck:
        """B05: viewport meta tag is mandatory."""
        passed = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I))
        return QACheck(
            "G002", "Viewport meta tag present", "CRITICAL",
            passed,
            "" if passed else "Missing viewport meta — mobile completely broken",
            "Add: <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        )

    def _check_mobile_breakpoints(self, html: str) -> QACheck:
        """G003: At least one @media breakpoint for mobile responsiveness."""
        # Check for at least one mobile-targeted media query
        has_768 = bool(re.search(r'@media[^{]*(?:max-width|min-width)[^{]*(?:768|640|480)', html))
        has_any  = bool(re.search(r'@media[^{]*(?:max-width|min-width)', html))
        passed  = has_768 or has_any
        return QACheck(
            "G003", "Mobile @media breakpoints present", "HIGH",
            passed,
            "" if passed else "No @media (max-width) breakpoints — mobile layout broken",
            "Add @media(max-width:768px) and @media(max-width:480px) CSS blocks",
        )

    def _check_closing_html_strict(self, html: str) -> QACheck:
        """G004: HTML must end with </html> (strict check — replicates C001 for explicitness)."""
        last_500 = html[-500:].lower()
        passed   = "</html>" in last_500
        return QACheck(
            "G004", "HTML closes with </html> (strict)", "CRITICAL",
            passed,
            "" if passed else "HTML file does not end with </html> — likely truncated",
            "Ensure the generator completes the HTML. Use GenerationGuard._fix_b08_token_cutoff()",
        )

    # ── STRUCTURE CHECKS ──────────────────────────────────────────────────────

    def _check_viewport_meta(self, html: str) -> QACheck:
        has_viewport = "viewport" in html
        return QACheck("T001", "Viewport meta tag", "LOW",
                        has_viewport, "" if has_viewport else "Missing viewport meta — mobile broken")

    def _check_charset(self, html: str) -> QACheck:
        has_charset = "charset" in html.lower()
        return QACheck("T002", "Charset declared", "LOW",
                        has_charset, "" if has_charset else "Missing charset declaration")

    def _check_no_broken_urls(self, html: str) -> QACheck:
        """Check for obviously broken URL patterns."""
        broken = re.findall(r'href="["\s]|src="["\s]|url\("["\s]', html)
        passed = len(broken) == 0
        return QACheck("T003", "No obviously broken URLs", "LOW",
                        passed,
                        f"{len(broken)} empty/broken URL found" if not passed else "")

    def format_report(self, r: QAReport) -> str:
        sep    = "─" * 60
        status = "✅ DEPLOYABLE" if r.deployable else "🚫 DEPLOY BLOCKED"
        lines  = [
            f"HTML QA Report — {status}",
            f"Score: {r.score}/100 | Passed: {r.passed}/{r.passed+r.failed} | Critical: {r.critical}",
            sep,
        ]
        for c in r.checks:
            if not c.passed:
                icon = {"CRITICAL":"🔴","HIGH":"🟡","MEDIUM":"🔵","LOW":"⚪"}.get(c.severity,"•")
                lines.append(f"{icon} [{c.id}] {c.name}")
                if c.detail: lines.append(f"     {c.detail}")
                if c.autofix: lines.append(f"     Fix: {c.autofix[:80]}")
        if r.deployable:
            lines.append(f"\n✅ All critical checks passed — safe to deploy")
        else:
            lines.append(f"\n🚫 {r.critical} critical issue(s) must be fixed before deploy")
        return "\n".join(lines)

    def autofix(self, html: str) -> Tuple[str, List[str]]:
        """Apply all safe automatic fixes. Returns (fixed_html, list_of_fixes)."""
        fixes = []

        # Fix E001: strip markdown fences
        original = html
        html = re.sub(r'(<style[^>]*>)\s*```\w*\s*', r'\1\n', html)
        html = re.sub(r'```\s*(</style>)', r'\1', html)
        html = re.sub(r'(</head>\s*<body>)\s*```\w*\s*', r'\1\n', html)
        html = re.sub(r'```\s*(</body>)', r'\1', html)
        html = re.sub(r'^\s*```\w*\s*$', '', html, flags=re.MULTILINE)
        if html != original:
            fixes.append("Removed markdown fence artifacts (```)")

        # Fix E006: decimal counter
        html = re.sub(
            r'(data-count="(\d+\.\d+)")',
            lambda m: f'{m.group(0)} data-decimal="true"',
            html
        )

        # Fix: add loading=lazy to non-hero images
        def add_lazy(m):
            tag = m.group(0)
            if 'loading=' not in tag and 'hero' not in tag.lower():
                tag = tag[:-1] + ' loading="lazy">'
                fixes.append("Added loading='lazy' to image")
            return tag
        html = re.sub(r'<img[^>]+>', add_lazy, html, flags=re.I)

        # Fix: add </html> if missing
        if "</html>" not in html.lower():
            html += "\n</body>\n</html>"
            fixes.append("Added missing </html> closing tag")

        return html, fixes


# ── Integration: wrap deploy function ────────────────────────────────────────

def qa_before_deploy(html_path: str, auto_fix: bool = True) -> bool:
    """
    Run QA on HTML file before deploy.
    Returns True if safe to deploy, False if blocked.
    Call this BEFORE every vercel/netlify deploy.
    """
    qa = HTMLQualityAssurance()
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    if auto_fix:
        html, fixes = qa.autofix(html)
        if fixes:
            print(f"  [QA] Auto-fixed {len(fixes)} issues:")
            for fix in fixes:
                print(f"    ✓ {fix}")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

    report = qa.validate(html)
    print(qa.format_report(report))

    if not report.deployable:
        print(f"\n🚫 DEPLOY BLOCKED — fix {report.critical} critical issue(s) first")
    return report.deployable


# ── @ensure_qa decorator — mandatory QA on all generated HTML ─────────────────

import functools
from typing import Callable as _Callable, TypeVar as _TypeVar
_F = _TypeVar("_F", bound=_Callable)

def ensure_qa(auto_fix: bool = True, min_score: float = 0.0, block_on_critical: bool = True):
    """
    Decorator that automatically runs QA on any function that returns HTML.
    Raises ValueError if critical checks fail (when block_on_critical=True).

    Usage:
        @ensure_qa()
        def generate_page(brief: str) -> str:
            return claude_generate(brief)

        @ensure_qa(auto_fix=True, min_score=90.0)
        def generate_homepage(**kw) -> str:
            return generate(kw)
    """
    def decorator(fn: _F) -> _F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            html = fn(*args, **kwargs)
            if not isinstance(html, str) or len(html) < 50:
                return html

            qa = HTMLQualityAssurance()

            if auto_fix:
                html, fixes = qa.autofix(html)

            report = qa.validate(html)

            if block_on_critical and report.critical > 0:
                critical_ids = [c.id for c in report.checks
                                if not c.passed and c.severity == "CRITICAL"]
                raise ValueError(
                    f"[ensure_qa] {fn.__name__}() produced HTML with "
                    f"{report.critical} CRITICAL issue(s): {critical_ids}. "
                    f"Score: {report.score}/100. Deploy blocked."
                )

            if min_score > 0 and report.score < min_score:
                raise ValueError(
                    f"[ensure_qa] {fn.__name__}() QA score {report.score:.1f} "
                    f"below minimum {min_score}. Deploy blocked."
                )

            return html
        return wrapper  # type: ignore
    return decorator
