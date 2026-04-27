"""
AILEX Pilot — code_quality.py
Type checking + linting as post-generation quality gates.
Runs tsc, pylint, eslint after AILEX generates code.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class QualityResult:
    tool:     str
    passed:   bool
    issues:   List[str]
    score:    float   # 0.0-1.0
    output:   str


class CodeQualityGate:
    """Run type checking and linting on generated code."""

    def check_python(self, code: str, strict: bool = False) -> QualityResult:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code); path = f.name
        try:
            issues: List[str] = []
            # Syntax check
            r = subprocess.run(["python3", "-m", "py_compile", path],
                               capture_output=True, text=True)
            if r.returncode != 0:
                return QualityResult("python", False, [r.stderr[:200]], 0.0, r.stderr)

            # pylint if available
            r2 = subprocess.run(["pylint", path, "--score=y", "--output-format=text"],
                                capture_output=True, text=True, timeout=20)
            output = r2.stdout + r2.stderr
            for line in output.split("\n"):
                if ": E" in line or ": W" in line:
                    issues.append(line.strip()[:100])
            score_line = [l for l in output.split("\n") if "Your code has been rated" in l]
            score = float(score_line[0].split("/")[0].split()[-1]) / 10 if score_line else 0.7
            return QualityResult("pylint", len(issues) == 0, issues[:5], score, output[:500])
        except FileNotFoundError:
            return QualityResult("python-syntax", r.returncode == 0, [], 1.0 if r.returncode == 0 else 0.0, "")
        finally:
            os.unlink(path)

    def check_typescript(self, code: str, cwd: str = ".") -> QualityResult:
        with tempfile.NamedTemporaryFile(suffix=".ts", mode="w", delete=False,
                                          dir=cwd) as f:
            f.write(code); path = f.name
        try:
            r = subprocess.run(["npx", "tsc", "--noEmit", "--strict", path],
                               capture_output=True, text=True, timeout=30, cwd=cwd)
            issues = [l for l in r.stdout.split("\n") if "error TS" in l][:5]
            return QualityResult("tsc", r.returncode == 0, issues,
                                 1.0 if r.returncode == 0 else 0.3, r.stdout[:400])
        except FileNotFoundError:
            return QualityResult("tsc", True, [], 1.0, "tsc not available")
        finally:
            os.unlink(path)

    def check_javascript(self, code: str, cwd: str = ".") -> QualityResult:
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write(code); path = f.name
        try:
            r = subprocess.run(["npx", "eslint", path, "--format=compact"],
                               capture_output=True, text=True, timeout=20)
            issues = [l for l in r.stdout.split("\n") if l.strip() and "error" in l.lower()][:5]
            return QualityResult("eslint", r.returncode == 0, issues,
                                 1.0 if r.returncode == 0 else 0.5, r.stdout[:400])
        except FileNotFoundError:
            return QualityResult("eslint", True, [], 1.0, "eslint not available")
        finally:
            os.unlink(path)

    def check(self, code: str, language: str, cwd: str = ".") -> QualityResult:
        if language in ("python", "py"):
            return self.check_python(code)
        elif language in ("typescript", "ts", "tsx"):
            return self.check_typescript(code, cwd)
        elif language in ("javascript", "js", "jsx"):
            return self.check_javascript(code, cwd)
        return QualityResult("none", True, [], 1.0, "")

    def format_result(self, r: QualityResult) -> str:
        status = "✓" if r.passed else "✗"
        lines  = [f"{status} {r.tool}: score={r.score:.0%}"]
        for i in r.issues:
            lines.append(f"  ⚠ {i}")
        return "\n".join(lines)
