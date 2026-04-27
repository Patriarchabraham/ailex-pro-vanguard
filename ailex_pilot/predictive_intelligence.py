"""
AILEX — predictive_intelligence.py
Anticipates developer needs before they ask.

Based on:
  - Session history patterns (what typically follows X?)
  - Code change patterns (what's usually needed after this?)
  - Project state analysis (what's missing?)
  - Time patterns (what does this developer do at this time of day?)

Outputs: next 3 predicted needs + confidence scores.
Developer sees suggestions and one-taps to execute.

This is the difference between a reactive tool and a proactive partner.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Prediction:
    rank:        int
    action:      str          # what AILEX predicts the developer needs next
    domain:      str
    confidence:  float
    reasoning:   str
    one_tap_cmd: str          # the command to execute if accepted


# Pattern library: what typically follows what
SEQUENCE_PATTERNS: List[Tuple[List[str], str, str, float]] = [
    # (triggers, predicted_action, domain, confidence)
    (["fix", "bug", "error"],     "add regression test for fixed bug",         "testing",      0.88),
    (["add", "feature", "implement"], "write tests for new feature",            "testing",      0.85),
    (["test", "pass", "green"],   "review for edge cases not covered",          "code",         0.72),
    (["deploy", "prod"],          "monitor performance for 10 min",             "performance",  0.82),
    (["security", "auth", "jwt"], "run security scan on changes",               "security",     0.91),
    (["refactor", "clean"],       "verify no regression with test run",          "testing",      0.87),
    (["database", "schema"],      "create migration rollback plan",             "data",         0.79),
    (["api", "endpoint"],         "write API documentation",                    "documentation",0.75),
    (["performance", "slow"],     "profile and identify actual bottleneck",     "performance",  0.83),
    (["install", "dependency"],   "check for CVEs in new dependency",           "security",     0.86),
    (["commit", "pr"],            "update CHANGELOG and bump version",          "documentation",0.71),
    (["error", "production"],     "add error monitoring and alerting",          "deploy",       0.89),
]

# Project state predictions
PROJECT_STATE_PATTERNS: List[Tuple[str, str, str, float]] = [
    # (condition, action, domain, confidence)
    ("no_tests",       "write initial test suite",            "testing",      0.92),
    ("no_docs",        "generate API documentation",          "documentation",0.80),
    ("no_ci",          "set up GitHub Actions CI/CD",         "deploy",       0.85),
    ("no_error_bound", "add error boundaries to critical UI", "code",         0.88),
    ("large_bundle",   "implement code splitting",            "performance",  0.84),
    ("no_logging",     "add structured logging",              "code",         0.76),
    ("no_monitoring",  "set up basic monitoring",             "deploy",       0.79),
]


class PredictiveIntelligence:
    """
    Analyses session history, code changes, and project state
    to predict what the developer needs next.

    Think of it as AILEX reading your mind — not by magic,
    but by recognising patterns that always occur in this order.
    """

    def __init__(self, pilot: Any = None, memory: Any = None):
        self.pilot  = pilot
        self.memory = memory

    def predict(
        self,
        recent_request: str = "",
        project_state:  Dict[str, bool] = {},
        context:        str = "",
        n:              int = 3,
    ) -> List[Prediction]:
        """Generate top-N predictions for what developer needs next."""
        predictions: List[Prediction] = []

        # Pattern-based predictions from recent request
        if recent_request:
            preds = self._predict_from_sequence(recent_request)
            predictions.extend(preds)

        # Project state predictions
        state_preds = self._predict_from_state(project_state)
        predictions.extend(state_preds)

        # Session history predictions
        history_preds = self._predict_from_history()
        predictions.extend(history_preds)

        # Deduplicate and rank
        seen = set()
        ranked = []
        for p in sorted(predictions, key=lambda x: -x.confidence):
            key = p.action[:40]
            if key not in seen:
                seen.add(key)
                ranked.append(p)

        # Assign ranks
        for i, p in enumerate(ranked[:n]):
            p.rank = i + 1

        return ranked[:n]

    def _predict_from_sequence(self, request: str) -> List[Prediction]:
        req_lower = request.lower()
        predictions = []
        for triggers, action, domain, conf in SEQUENCE_PATTERNS:
            if any(t in req_lower for t in triggers):
                predictions.append(Prediction(
                    rank=0, action=action, domain=domain, confidence=conf,
                    reasoning=f"After '{triggers[0]}' tasks, '{action}' is typically needed",
                    one_tap_cmd=f"ask \"{action}\"",
                ))
        return predictions[:3]

    def _predict_from_state(self, state: Dict[str, bool]) -> List[Prediction]:
        predictions = []
        for condition, action, domain, conf in PROJECT_STATE_PATTERNS:
            if state.get(condition, False):
                predictions.append(Prediction(
                    rank=0, action=action, domain=domain, confidence=conf,
                    reasoning=f"Project state: {condition} — {action} is recommended",
                    one_tap_cmd=f"ask \"{action}\"",
                ))
        return predictions[:2]

    def _predict_from_history(self) -> List[Prediction]:
        if not self.memory:
            return []
        try:
            rows = self.memory.conn.execute(
                "SELECT domain, COUNT(*) n FROM records GROUP BY domain ORDER BY n DESC LIMIT 3"
            ).fetchall()
            predictions = []
            for row in rows:
                domain = row[0] if hasattr(row, '__getitem__') else row["domain"]
                n_calls = row[1] if hasattr(row, '__getitem__') else row["n"]
                if domain and n_calls >= 2:
                    predictions.append(Prediction(
                        rank=0, action=f"proactive review of {domain} changes",
                        domain=domain, confidence=0.65,
                        reasoning=f"You frequently work on {domain} ({n_calls} sessions)",
                        one_tap_cmd=f"ask \"review recent {domain} changes for issues\"",
                    ))
            return predictions[:2]
        except Exception:
            return []

    def analyse_project_state(self, project_reader: Any, root: str = ".") -> Dict[str, bool]:
        """Scan project to detect state conditions."""
        state: Dict[str, bool] = {}
        try:
            import os
            # No tests
            has_tests = any(
                any(f.startswith("test_") or "spec" in f for f in files)
                for _, _, files in os.walk(root)
                if not any(d in _ for d in ("node_modules", ".git"))
            )
            state["no_tests"] = not has_tests

            # No CI
            state["no_ci"] = not (
                os.path.exists(os.path.join(root, ".github", "workflows")) or
                os.path.exists(os.path.join(root, ".gitlab-ci.yml"))
            )

            # No error boundaries (React projects)
            has_error_boundary = any(
                "ErrorBoundary" in open(os.path.join(dp, f), errors="ignore").read()
                for dp, _, files in os.walk(root)
                for f in files if f.endswith((".tsx", ".jsx"))
            ) if True else False
            state["no_error_bound"] = not has_error_boundary

        except Exception:
            pass
        return state

    def format_predictions(self, predictions: List[Prediction]) -> str:
        if not predictions:
            return "No predictions available"
        lines = ["⚡ AILEX Predicts — what you need next:"]
        for p in predictions:
            lines.append(
                f"\n  [{p.rank}] {p.action[:70]}\n"
                f"      Domain: {p.domain} | Confidence: {p.confidence:.0%}\n"
                f"      Why: {p.reasoning[:80]}\n"
                f"      Execute: python -m ailex_pilot.cli {p.one_tap_cmd}"
            )
        return "\n".join(lines)
