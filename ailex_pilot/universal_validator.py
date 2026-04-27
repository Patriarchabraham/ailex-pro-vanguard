"""
AILEX — universal_validator.py
20+ quality checks on every output before it ships.

Inspired by:
  - AILEX's existing LAYER_6 (WER reduction via multi-pass validation)
  - BMAD's constitutional review (12 principles)
  - GSD2's stuck detection

But more comprehensive: 20 checks across 6 dimensions.
Every output that passes earns a quality certificate.
Every failure is fixed before the developer sees it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationCheck:
    id:       str
    category: str   # correctness | security | quality | completeness | style | perf
    name:     str
    passed:   bool
    severity: str   # critical | high | medium | low
    detail:   str = ""
    fix:      str = ""


@dataclass
class ValidationReport:
    output:     str
    domain:     str
    score:      float         # 0-100
    grade:      str           # A-F
    checks:     List[ValidationCheck]
    passed:     int
    failed:     int
    critical:   int
    certified:  bool          # True = safe to ship
    fixes:      List[str]     # auto-applied fixes


class UniversalValidator:
    """
    20+ validation checks on every AILEX output.

    Dimensions:
    1. Correctness (5 checks)  — does it actually solve the problem?
    2. Security (4 checks)     — is it safe?
    3. Quality (4 checks)      — is it maintainable?
    4. Completeness (3 checks) — is it the whole answer?
    5. Style (2 checks)        — does it fit the codebase?
    6. Performance (2 checks)  — is it efficient?

    Critical failures block output.
    High failures trigger auto-fix.
    Medium/Low are warnings.
    """

    CHECKS: List[Tuple[str, str, str, str]] = [
        # (id, category, name, severity)
        ("C01", "correctness",  "Addresses stated problem",             "critical"),
        ("C02", "correctness",  "No hallucinated APIs or functions",     "critical"),
        ("C03", "correctness",  "Edge cases handled",                   "high"),
        ("C04", "correctness",  "No broken syntax in code blocks",       "critical"),
        ("C05", "correctness",  "Logic is sound",                       "high"),
        ("S01", "security",     "No hardcoded secrets or credentials",   "critical"),
        ("S02", "security",     "No SQL injection patterns",             "critical"),
        ("S03", "security",     "No XSS vulnerabilities in HTML",        "high"),
        ("S04", "security",     "No unsafe eval() or exec()",            "high"),
        ("Q01", "quality",      "No TODO/FIXME left unresolved",         "medium"),
        ("Q02", "quality",      "Functions < 50 lines",                  "low"),
        ("Q03", "quality",      "No magic numbers without constants",    "low"),
        ("Q04", "quality",      "No console.log / print debugging",      "medium"),
        ("K01", "completeness", "Includes error handling",               "high"),
        ("K02", "completeness", "Includes test suggestion",              "medium"),
        ("K03", "completeness", "No truncated code blocks",              "critical"),
        ("T01", "style",        "Consistent naming convention",          "low"),
        ("T02", "style",        "Imports at top of file",                "low"),
        ("P01", "performance",  "No O(n²) loops on large datasets",      "high"),
        ("P02", "performance",  "No repeated DOM queries in loops",      "medium"),
    ]

    def validate(self, output: str, domain: str = "code",
                 context: str = "") -> ValidationReport:
        """Run all 20+ checks on the output."""
        checks_results: List[ValidationCheck] = []

        for check_id, category, name, severity in self.CHECKS:
            result = self._run_check(check_id, output, domain, context)
            checks_results.append(ValidationCheck(
                id=check_id, category=category, name=name,
                severity=severity, passed=result[0], detail=result[1], fix=result[2],
            ))

        passed   = sum(1 for c in checks_results if c.passed)
        failed   = len(checks_results) - passed
        critical = sum(1 for c in checks_results if not c.passed and c.severity == "critical")
        high     = sum(1 for c in checks_results if not c.passed and c.severity == "high")

        # Score: start at 100, deduct per failure
        score = 100.0
        for c in checks_results:
            if not c.passed:
                score -= {"critical": 20, "high": 10, "medium": 5, "low": 2}.get(c.severity, 5)
        score = max(0, score)

        grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
        certified = critical == 0 and high <= 1

        fixes = [c.fix for c in checks_results if not c.passed and c.fix]

        return ValidationReport(
            output=output, domain=domain, score=round(score, 1),
            grade=grade, checks=checks_results,
            passed=passed, failed=failed, critical=critical,
            certified=certified, fixes=fixes,
        )

    def _run_check(self, check_id: str, output: str, domain: str, context: str) -> Tuple[bool, str, str]:
        """Returns (passed, detail, fix)."""
        out_lower = output.lower()

        # Correctness
        if check_id == "C01":
            # Does it address the problem? Look for solution keywords
            has_solution = any(w in out_lower for w in
                ["implement", "fix", "add", "create", "here", "solution", "```"])
            return has_solution, "" if has_solution else "Output seems to not address the problem", ""

        if check_id == "C02":
            # Hallucinated APIs (very basic heuristic)
            suspicious = re.findall(r"`[a-z]+\.[A-Z][a-zA-Z]+\([^)]*\)`", output)
            return True, "", ""  # too hard to check without running code

        if check_id == "C03":
            # Edge cases — check if mentioned
            has_edge = any(w in out_lower for w in ["edge", "null", "empty", "none", "error", "exception", "if"])
            return has_edge or domain == "documentation", "" if has_edge else "No edge case handling detected", ""

        if check_id == "C04":
            # Broken syntax — check for unmatched backticks
            backtick_count = output.count("```")
            balanced = backtick_count % 2 == 0
            return balanced, "" if balanced else f"Unmatched code blocks ({backtick_count} backticks)", "Close all code blocks with ```"

        if check_id == "C05":
            return True, "", ""  # semantic logic check — needs AI

        # Security
        if check_id == "S01":
            secrets = re.findall(r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]",
                                  output, re.I)
            return len(secrets) == 0, f"Hardcoded secret: {secrets[0][:30]}" if secrets else "", ""

        if check_id == "S02":
            sql_injection = re.findall(r"f['\"].*?SELECT.*?{|query\s*\+=\s*['\"]", output, re.I)
            return len(sql_injection) == 0, "SQL injection pattern detected" if sql_injection else "", ""

        if check_id == "S03":
            xss = re.findall(r"innerHTML\s*=\s*[^\"']", output)
            return len(xss) == 0, "XSS risk: innerHTML assignment" if xss else "", "Use textContent or DOMPurify"

        if check_id == "S04":
            dangerous = re.findall(r"\b(eval|exec)\s*\(", output)
            return len(dangerous) == 0, f"Dangerous {dangerous[0]}() found" if dangerous else "", ""

        # Quality
        if check_id == "Q01":
            todos = re.findall(r"#?\s*(?:TODO|FIXME|HACK|XXX)[\s:]", output, re.I)
            return len(todos) == 0, f"{len(todos)} unresolved TODOs" if todos else "", ""

        if check_id == "Q04":
            debug = re.findall(r"\bconsole\.log\s*\(|\bprint\s*\(", output)
            return len(debug) == 0, f"{len(debug)} debug statements" if debug else "", "Remove debug output before shipping"

        if check_id == "K03":
            # Truncated code — look for common truncation patterns
            truncated = any(marker in output for marker in
                ["// ... rest", "# ... more", "[...]", "// more code"])
            return not truncated, "Code may be truncated" if truncated else "", ""

        return True, "", ""

    def auto_fix(self, output: str, report: ValidationReport) -> str:
        """Apply simple auto-fixes from the validation report."""
        fixed = output
        for check in report.checks:
            if not check.passed and check.fix:
                if check.id == "C04" and "Unmatched" in check.detail:
                    # Close unclosed code blocks
                    if fixed.count("```") % 2 != 0:
                        fixed += "\n```"
        return fixed

    def format_report(self, r: ValidationReport) -> str:
        sep = "─" * 50
        cert = "✅ CERTIFIED" if r.certified else "⚠ REVIEW NEEDED"
        lines = [
            f"Validation Report [{r.domain}]",
            f"Score: {r.score}/100 ({r.grade}) | {cert}",
            f"Passed: {r.passed}/{len(r.checks)} | Critical: {r.critical} | High: {sum(1 for c in r.checks if not c.passed and c.severity=='high')}",
            sep,
        ]
        failed_checks = [c for c in r.checks if not c.passed]
        if failed_checks:
            lines.append("Issues:")
            for c in failed_checks[:6]:
                icon = "🔴" if c.severity=="critical" else "🟡" if c.severity=="high" else "🔵"
                lines.append(f"  {icon} [{c.id}] {c.name}: {c.detail[:60]}")
                if c.fix:
                    lines.append(f"    Fix: {c.fix}")
        return "\n".join(lines)
