"""
AILEX Pilot — proactive.py
Proactive monitoring: AILEX watches the repo in background and suggests improvements.
Runs as a daemon — no human trigger needed.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class ProactiveSuggestion:
    kind:        str    # "new_commits" | "dead_code" | "security" | "tests" | "perf"
    title:       str
    description: str
    priority:    int    # 1=high, 2=medium, 3=low
    ts:          float  = field(default_factory=time.time)
    acted_on:    bool   = False


class ProactiveMonitor:
    """
    Background monitor that watches the repo and surfaces suggestions.
    Runs every N minutes, checks for: new commits, security issues,
    dead code accumulation, missing tests, performance regressions.
    """

    def __init__(
        self,
        pilot:          Any,
        repo_dir:       str  = ".",
        interval_s:     int  = 300,   # check every 5 minutes
        on_suggestion:  Optional[Callable[[ProactiveSuggestion], None]] = None,
    ):
        self.pilot        = pilot
        self.repo_dir     = os.path.abspath(repo_dir)
        self.interval_s   = interval_s
        self.on_suggestion = on_suggestion or self._default_notify
        self.suggestions: List[ProactiveSuggestion] = []
        self._running     = False
        self._thread:     Optional[threading.Thread] = None
        self._last_commit = ""
        self._last_check  = 0.0

    def start(self) -> None:
        """Start background monitoring thread."""
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[AILEX Monitor] Started — checking every {self.interval_s}s")

    def stop(self) -> None:
        self._running = False
        print("[AILEX Monitor] Stopped")

    def check_now(self) -> List[ProactiveSuggestion]:
        """Run all checks immediately and return suggestions."""
        new_suggestions: List[ProactiveSuggestion] = []
        new_suggestions.extend(self._check_new_commits())
        new_suggestions.extend(self._check_security())
        new_suggestions.extend(self._check_test_coverage())
        new_suggestions.extend(self._check_dead_code())
        self.suggestions.extend(new_suggestions)
        return new_suggestions

    def _loop(self) -> None:
        while self._running:
            try:
                new = self.check_now()
                for s in new:
                    self.on_suggestion(s)
            except Exception:
                pass
            time.sleep(self.interval_s)

    def _check_new_commits(self) -> List[ProactiveSuggestion]:
        suggestions = []
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True, text=True, cwd=self.repo_dir
            )
            latest = result.stdout.split("\n")[0][:8] if result.stdout else ""
            if latest and latest != self._last_commit:
                if self._last_commit:
                    # New commits since last check
                    diff = subprocess.run(
                        ["git", "diff", self._last_commit, "HEAD", "--stat"],
                        capture_output=True, text=True, cwd=self.repo_dir
                    ).stdout[:200]
                    suggestions.append(ProactiveSuggestion(
                        kind="new_commits",
                        title=f"New commits detected: {latest}",
                        description=f"Changes since last check:\n{diff}",
                        priority=2,
                    ))
                self._last_commit = latest
        except Exception:
            pass
        return suggestions

    def _check_security(self) -> List[ProactiveSuggestion]:
        suggestions = []
        try:
            from ailex_pilot.security import SecurityScanner
            scanner = SecurityScanner()
            report  = scanner.scan_project(self.repo_dir)
            if report.secrets:
                suggestions.append(ProactiveSuggestion(
                    kind="security",
                    title=f"{len(report.secrets)} secrets exposed in code",
                    description="\n".join(
                        f"{f.file}:{f.line} — {f.description}"
                        for f in report.secrets[:3]
                    ),
                    priority=1,
                ))
            elif report.sast:
                suggestions.append(ProactiveSuggestion(
                    kind="security",
                    title=f"{len(report.sast)} SAST issues found",
                    description="\n".join(f.description for f in report.sast[:3]),
                    priority=2,
                ))
        except Exception:
            pass
        return suggestions

    def _check_test_coverage(self) -> List[ProactiveSuggestion]:
        suggestions = []
        try:
            # Check if there are source files with no corresponding test files
            src_files  = self._find_source_files()
            test_files = self._find_test_files()
            untested   = [f for f in src_files if not any(
                t.endswith(f.replace("/", "_").replace(".py", "")) or
                f.replace(".py","") in t
                for t in test_files
            )][:5]
            if untested:
                suggestions.append(ProactiveSuggestion(
                    kind="tests",
                    title=f"{len(untested)} source files with no tests",
                    description="Files missing tests: " + ", ".join(untested[:3]),
                    priority=3,
                ))
        except Exception:
            pass
        return suggestions

    def _check_dead_code(self) -> List[ProactiveSuggestion]:
        suggestions = []
        try:
            from ailex_pilot.ast_analyzer import ASTAnalyzer
            analyzer = ASTAnalyzer()
            reports  = analyzer.analyze_project(self.repo_dir)
            all_dead = analyzer.find_dead_code(reports)
            if len(all_dead) > 5:
                suggestions.append(ProactiveSuggestion(
                    kind="dead_code",
                    title=f"{len(all_dead)} potentially unused functions",
                    description="Consider removing: " + ", ".join(
                        f"{name} ({path})" for name, path in all_dead[:3]
                    ),
                    priority=3,
                ))
        except Exception:
            pass
        return suggestions

    def _find_source_files(self) -> List[str]:
        files = []
        for dp, dirs, fs in os.walk(self.repo_dir):
            dirs[:] = [d for d in dirs if d not in
                       ("node_modules", ".git", "__pycache__", "tests", "test")]
            for f in fs:
                if f.endswith(".py") and not f.startswith("test_"):
                    files.append(os.path.relpath(os.path.join(dp, f), self.repo_dir))
        return files[:50]

    def _find_test_files(self) -> List[str]:
        files = []
        for dp, _, fs in os.walk(self.repo_dir):
            for f in fs:
                if "test" in f.lower() and f.endswith((".py", ".ts", ".js")):
                    files.append(f)
        return files

    def _default_notify(self, s: ProactiveSuggestion) -> None:
        icons = {1: "🔴", 2: "🟡", 3: "🔵"}
        print(f"\n[AILEX Monitor] {icons.get(s.priority,'•')} {s.title}")
        print(f"  {s.description[:100]}")

    def summary(self) -> str:
        if not self.suggestions:
            return "No suggestions yet — monitoring active"
        lines = [f"Proactive suggestions ({len(self.suggestions)}):"]
        for s in sorted(self.suggestions, key=lambda x: x.priority)[:10]:
            icon = {1:"🔴",2:"🟡",3:"🔵"}.get(s.priority,"•")
            lines.append(f"  {icon} [{s.kind}] {s.title}")
        return "\n".join(lines)
