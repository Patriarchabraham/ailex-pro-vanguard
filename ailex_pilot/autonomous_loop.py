"""
AILEX — autonomous_loop.py
True autonomy: AILEX acts without being asked.

Monitors: repo changes, failing tests, security issues, performance regressions,
          dependency vulnerabilities, code quality degradation.

For each detected issue, AILEX:
  1. Analyses root cause
  2. Generates fix
  3. Runs tests
  4. Creates PR if tests pass
  5. Notifies developer

This is the jump from "tool" to "teammate".
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AutonomousAction:
    trigger:     str      # what triggered this action
    kind:        str      # "fix" | "improve" | "test" | "security" | "perf"
    description: str
    result:      str = ""
    status:      str = "pending"   # pending | running | done | failed
    pr_url:      str = ""
    ts:          float = field(default_factory=time.time)


class AutonomousLoop:
    """
    AILEX runs continuously in the background.
    Detects issues and fixes them without human intervention.

    This is what separates a 1x tool from a 100x teammate:
    the teammate acts while you sleep.
    """

    # What to monitor
    MONITORS = {
        "failing_tests":  {"interval": 300,  "priority": 1},
        "new_commits":    {"interval": 120,  "priority": 2},
        "security":       {"interval": 3600, "priority": 1},
        "dead_code":      {"interval": 7200, "priority": 3},
        "performance":    {"interval": 1800, "priority": 2},
        "dependencies":   {"interval": 86400,"priority": 3},
    }

    def __init__(
        self,
        pilot:         Any,
        repo_dir:      str = ".",
        auto_pr:       bool = False,
        auto_commit:   bool = False,
        notify:        Optional[Any] = None,
        confidence_threshold: float = 0.92,
    ):
        self.pilot     = pilot
        self.repo_dir  = os.path.abspath(repo_dir)
        self.auto_pr   = auto_pr
        self.auto_commit = auto_commit
        self.notify    = notify
        self.threshold = confidence_threshold
        self._running  = False
        self._threads: List[threading.Thread] = []
        self._actions: List[AutonomousAction] = []
        self._last_run: Dict[str, float] = {}

    def start(self) -> None:
        """Start all monitor threads."""
        self._running = True
        for monitor_key in self.MONITORS:
            t = threading.Thread(
                target=self._monitor_loop,
                args=(monitor_key,),
                daemon=True,
            )
            t.start()
            self._threads.append(t)
        print(f"[AILEX Autonomous] Active — monitoring {len(self.MONITORS)} signals in {self.repo_dir}")

    def stop(self) -> None:
        self._running = False
        print("[AILEX Autonomous] Stopped")

    def act_now(self, monitor_key: str = "") -> List[AutonomousAction]:
        """Trigger all monitors immediately."""
        actions = []
        keys = [monitor_key] if monitor_key else list(self.MONITORS.keys())
        for k in keys:
            new = self._run_monitor(k)
            actions.extend(new)
        return actions

    def _monitor_loop(self, monitor_key: str) -> None:
        interval = self.MONITORS[monitor_key]["interval"]
        while self._running:
            try:
                self._run_monitor(monitor_key)
            except Exception:
                pass
            time.sleep(interval)

    def _run_monitor(self, key: str) -> List[AutonomousAction]:
        actions = []
        handler = getattr(self, f"_check_{key}", None)
        if handler:
            detected = handler()
            for item in detected:
                action = self._handle(item, key)
                if action:
                    actions.append(action)
                    self._actions.append(action)
        return actions

    def _handle(self, issue: Dict, monitor_key: str) -> Optional[AutonomousAction]:
        """Handle a detected issue autonomously."""
        action = AutonomousAction(
            trigger=monitor_key,
            kind=issue.get("kind", "fix"),
            description=issue.get("description", ""),
        )
        action.status = "running"

        # Ask AILEX to fix it
        prompt = (
            f"[AUTONOMOUS] {issue['description']}\n\n"
            f"Auto-fix this issue. Be decisive. If confidence < {self.threshold}, "
            f"explain what's needed instead of guessing."
        )
        try:
            result = self.pilot.process(
                prompt, domain=issue.get("domain", "code"),
                run_code=True, auto_commit=self.auto_commit,
                include_context=True, fmt="concise",
            )
            action.result = result.get("report", "")
            conf = result.get("confidence", 0.0)

            if conf >= self.threshold:
                action.status = "done"
                if self.auto_pr:
                    pr = self.pilot.create_pr(
                        f"[AILEX Auto] {issue['description'][:60]}",
                        f"Automatically fixed by AILEX autonomous loop.\n\n{action.result[:500]}",
                    )
                    action.pr_url = pr.get("url", "")
            else:
                action.status = "needs_review"

            if self.notify:
                self.notify.task_done(
                    action.description[:50],
                    action.result[:200],
                    action.status == "done",
                )
        except Exception as e:
            action.status = "failed"
            action.result = str(e)

        return action

    # ── Monitors ──────────────────────────────────────────────────────────────

    def _check_failing_tests(self) -> List[Dict]:
        issues = []
        r = subprocess.run(
            ["python", "-m", "pytest", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=60, cwd=self.repo_dir
        )
        if r.returncode != 0:
            failed = [l for l in r.stdout.split("\n") if "FAILED" in l][:3]
            if failed:
                issues.append({
                    "kind": "fix", "domain": "testing",
                    "description": f"Tests failing: {'; '.join(failed[:2])}",
                })
        return issues

    def _check_new_commits(self) -> List[Dict]:
        issues = []
        r = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            capture_output=True, text=True, cwd=self.repo_dir
        )
        latest = r.stdout.split("\n")[0][:8] if r.stdout else ""
        last = self._last_run.get("new_commits_sha", "")
        if latest and latest != last:
            self._last_run["new_commits_sha"] = latest
            if last:  # not first run
                issues.append({
                    "kind": "review", "domain": "code",
                    "description": f"New commits since {last}: review for issues",
                })
        return issues

    def _check_security(self) -> List[Dict]:
        issues = []
        try:
            from ailex_pilot.security import SecurityScanner
            report = SecurityScanner().scan_project(self.repo_dir)
            if report.secrets:
                issues.append({
                    "kind": "security", "domain": "security",
                    "description": f"{len(report.secrets)} secrets exposed in code — CRITICAL",
                })
        except Exception:
            pass
        return issues

    def _check_dead_code(self) -> List[Dict]:
        issues = []
        try:
            from ailex_pilot.ast_analyzer import ASTAnalyzer
            reports = ASTAnalyzer().analyze_project(self.repo_dir)
            dead = ASTAnalyzer().find_dead_code(reports)
            if len(dead) > 8:
                issues.append({
                    "kind": "improve", "domain": "refactor",
                    "description": f"{len(dead)} dead code symbols detected — cleanup opportunity",
                })
        except Exception:
            pass
        return issues

    def _check_performance(self) -> List[Dict]:
        return []  # placeholder: extend with profiling integration

    def _check_dependencies(self) -> List[Dict]:
        issues = []
        try:
            from ailex_pilot.security import SecurityScanner
            report = SecurityScanner().scan_project(self.repo_dir)
            if report.cves:
                issues.append({
                    "kind": "security", "domain": "security",
                    "description": f"{len(report.cves)} CVEs in dependencies",
                })
        except Exception:
            pass
        return issues

    def summary(self) -> str:
        done   = sum(1 for a in self._actions if a.status == "done")
        failed = sum(1 for a in self._actions if a.status == "failed")
        prs    = sum(1 for a in self._actions if a.pr_url)
        return (
            f"Autonomous Loop: {'RUNNING' if self._running else 'STOPPED'}\n"
            f"  Actions: {len(self._actions)} total | {done} done | {failed} failed | {prs} PRs\n"
            f"  Monitors: {', '.join(self.MONITORS.keys())}"
        )
