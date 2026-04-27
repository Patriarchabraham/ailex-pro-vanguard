"""
AILEX Vision — accessibility.py
Automated WCAG accessibility audit for HTML/websites.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class AccessibilityIssue:
    rule:        str     # WCAG rule ID e.g. "1.1.1"
    level:       str     # "A" | "AA" | "AAA"
    severity:    str     # "critical" | "serious" | "moderate" | "minor"
    description: str
    element:     str
    fix:         str


@dataclass
class AccessibilityReport:
    url_or_file: str
    score:       float   # 0-100
    issues:      List[AccessibilityIssue]
    passed:      List[str]
    summary:     str


class AccessibilityAuditor:
    """
    WCAG 2.1 accessibility audit.
    Regex-based static analysis + Claude for deeper insights.
    """

    CHECKS = [
        # (rule_id, level, severity, pattern, description, fix)
        ("1.1.1", "A", "critical",
         r"<img(?![^>]*alt=)[^>]*>",
         "Image missing alt attribute",
         "Add alt='description' to all <img> tags"),
        ("1.3.1", "A", "serious",
         r"<(div|span)[^>]*(?:role\s*=\s*[\"']button[\"'])[^>]*>(?!.*aria-label)",
         "div/span with button role missing aria-label",
         "Add aria-label='...' to interactive elements"),
        ("1.4.3", "AA", "serious",
         r"color:\s*#(?:999|888|777|aaa|bbb|ccc|ddd)\b",
         "Potentially low contrast text color",
         "Ensure 4.5:1 contrast ratio for normal text"),
        ("2.1.1", "A", "critical",
         r"<(?:div|span)[^>]*onclick[^>]*>(?!.*tabindex)",
         "Clickable element not keyboard accessible",
         "Add tabindex='0' and onkeydown handler"),
        ("2.4.2", "A", "serious",
         r"<title\s*>\s*</title>|<title\s*/>",
         "Empty page title",
         "Add a descriptive <title> tag"),
        ("3.1.1", "A", "moderate",
         r"<html(?![^>]*lang=)[^>]*>",
         "HTML element missing lang attribute",
         "Add lang='en' (or appropriate language) to <html>"),
        ("4.1.2", "A", "serious",
         r"<input(?![^>]*(?:aria-label|id|aria-labelledby))[^>]*>",
         "Form input missing accessible label",
         "Add <label for='id'> or aria-label to input"),
        ("1.4.4", "AA", "moderate",
         r"font-size:\s*(?:[6-9]|1[01])px\b",
         "Text smaller than 12px may be unreadable",
         "Use minimum 12px font size (preferably 16px)"),
    ]

    def audit_html(self, html: str, source: str = "html") -> AccessibilityReport:
        issues:  List[AccessibilityIssue] = []
        passed:  List[str] = []
        checked: set = set()

        for rule_id, level, severity, pattern, desc, fix in self.CHECKS:
            matches = list(re.finditer(pattern, html, re.I | re.S))
            if matches:
                elem = html[matches[0].start():matches[0].start()+80].strip()
                issues.append(AccessibilityIssue(
                    rule=rule_id, level=level, severity=severity,
                    description=desc, element=elem[:80], fix=fix,
                ))
            else:
                passed.append(f"WCAG {rule_id}")
            checked.add(rule_id)

        critical = sum(1 for i in issues if i.severity == "critical")
        serious  = sum(1 for i in issues if i.severity == "serious")
        score    = max(0, 100 - critical * 20 - serious * 10 - len(issues) * 3)

        return AccessibilityReport(
            url_or_file=source, score=round(score), issues=issues,
            passed=passed,
            summary=self._summary(score, issues),
        )

    def audit_with_claude(self, html: str, client: Any) -> str:
        """Deeper Claude-powered accessibility analysis."""
        if not client:
            return "No API client — basic audit only"
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1500,
            messages=[{"role": "user", "content":
                f"Perform a WCAG 2.1 accessibility audit on this HTML.\n\n{html[:4000]}\n\n"
                "List: critical issues, ARIA improvements needed, color contrast concerns, "
                "keyboard navigation gaps. Provide specific HTML fixes."}],
        )
        return resp.content[0].text

    def _summary(self, score: float, issues: List) -> str:
        if score >= 90: return f"✓ Good accessibility ({score}/100)"
        if score >= 70: return f"⚠ Moderate issues ({score}/100) — {len(issues)} found"
        return f"✗ Poor accessibility ({score}/100) — {len(issues)} issues need fixing"

    def format_report(self, r: AccessibilityReport) -> str:
        lines = [
            f"Accessibility: {r.url_or_file}",
            f"Score: {r.score}/100",
            r.summary, "",
        ]
        if r.issues:
            lines.append("Issues:")
            for i in r.issues:
                icon = "🔴" if i.severity == "critical" else "🟡" if i.severity == "serious" else "🔵"
                lines.append(f"  {icon} WCAG {i.rule} [{i.level}]: {i.description}")
                lines.append(f"     Fix: {i.fix}")
        if r.passed:
            lines.append(f"\nPassed: {', '.join(r.passed[:6])}")
        return "\n".join(lines)
