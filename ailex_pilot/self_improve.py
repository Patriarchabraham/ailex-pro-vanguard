"""
AILEX Pilot — self_improve.py
AILEX analyzes its own failed sessions and updates agent prompts.
Benchmark regression detection. Token budget optimizer.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImprovementSuggestion:
    agent:       str
    domain:      str
    issue:       str
    old_prompt:  str
    new_prompt:  str
    confidence:  float
    source:      str   # "failed_sessions" | "feedback" | "benchmark"


@dataclass
class BenchmarkSnapshot:
    ts:             float
    avg_quality:    float
    avg_confidence: float
    avg_loops:      float
    pass_rate:      float
    domain_scores:  Dict[str, float]


class SelfImprover:
    """
    AILEX-on-AILEX: analyzes own performance and improves agent prompts.
    Detects benchmark regressions. Optimizes token allocation.
    """

    IMPROVE_DB = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ailex_improvements.db"
    )

    def __init__(self, client: Any = None):
        self.client = client
        self.conn   = sqlite3.connect(self.IMPROVE_DB, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS improvements (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent       TEXT, domain TEXT, issue TEXT,
                old_prompt  TEXT, new_prompt TEXT,
                confidence  REAL, source TEXT, applied INTEGER DEFAULT 0, ts REAL
            );
            CREATE TABLE IF NOT EXISTS benchmarks (
                ts             REAL PRIMARY KEY,
                avg_quality    REAL, avg_confidence REAL,
                avg_loops      REAL, pass_rate REAL,
                domain_scores  TEXT
            );
        """)
        self.conn.commit()

    def analyze_failures(self, session_db: str, feedback_db: str) -> List[ImprovementSuggestion]:
        """Scan failed sessions + negative feedback to find patterns."""
        suggestions: List[ImprovementSuggestion] = []

        # Load failed sessions
        try:
            conn = sqlite3.connect(session_db)
            conn.row_factory = sqlite3.Row
            failures = conn.execute(
                "SELECT domain, content FROM messages WHERE role='user' "
                "AND session_id IN (SELECT DISTINCT session_id FROM messages "
                "WHERE role='assistant' AND content LIKE '%ERROR%' LIMIT 20)"
            ).fetchall()
            conn.close()
        except Exception:
            failures = []

        # Load negative feedback
        try:
            conn = sqlite3.connect(feedback_db)
            conn.row_factory = sqlite3.Row
            neg_feedback = conn.execute(
                "SELECT domain, agents_used, request FROM feedback WHERE rating=-1 LIMIT 30"
            ).fetchall()
            conn.close()
        except Exception:
            neg_feedback = []

        if not failures and not neg_feedback and not self.client:
            return suggestions

        # Cluster failures by domain
        domain_issues: Dict[str, List[str]] = {}
        for f in failures:
            domain = f["domain"] or "code"
            domain_issues.setdefault(domain, []).append(f["content"][:200])
        for f in neg_feedback:
            domain = f["domain"] or "code"
            domain_issues.setdefault(domain, []).append(f["request"][:200])

        # Use Claude to suggest improvements
        if self.client and domain_issues:
            for domain, issues in list(domain_issues.items())[:3]:
                sugg = self._generate_improvement(domain, issues)
                if sugg:
                    suggestions.append(sugg)
                    self._save_suggestion(sugg)

        return suggestions

    def _generate_improvement(self, domain: str, issues: List[str]) -> Optional[ImprovementSuggestion]:
        sample = "\n".join(f"- {i}" for i in issues[:5])
        try:
            resp = self.client.messages.create(
                model="claude-sonnet-4-6", max_tokens=800,
                messages=[{"role": "user", "content":
                    f"AILEX agent for domain '{domain}' had these failures:\n{sample}\n\n"
                    "Suggest a specific improvement to the agent's system prompt that would prevent these.\n"
                    "Format:\nISSUE: [root cause]\nAGENT: [agent name]\n"
                    "IMPROVEMENT: [specific addition to system prompt, 1-2 sentences]\n"
                    "CONFIDENCE: [0.0-1.0]"}],
            )
            text  = resp.content[0].text
            agent = re.search(r"AGENT:\s*(\w+)", text)
            issue = re.search(r"ISSUE:\s*(.+?)(?=\n|$)", text)
            impr  = re.search(r"IMPROVEMENT:\s*(.+?)(?=CONFIDENCE:|$)", text, re.S)
            conf  = re.search(r"CONFIDENCE:\s*([\d.]+)", text)
            if agent and impr:
                return ImprovementSuggestion(
                    agent=agent.group(1), domain=domain,
                    issue=issue.group(1).strip() if issue else "",
                    old_prompt="", new_prompt=impr.group(1).strip()[:300],
                    confidence=float(conf.group(1)) if conf else 0.7,
                    source="failed_sessions",
                )
        except Exception:
            pass
        return None

    def _save_suggestion(self, s: ImprovementSuggestion) -> None:
        self.conn.execute(
            "INSERT INTO improvements(agent,domain,issue,old_prompt,new_prompt,confidence,source,ts) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (s.agent, s.domain, s.issue, s.old_prompt, s.new_prompt,
             s.confidence, s.source, time.time())
        )
        self.conn.commit()

    def save_benchmark(self, evaluator: Any, pipeline: Any) -> BenchmarkSnapshot:
        """Run benchmarks and save snapshot for regression detection."""
        suite  = evaluator.run_benchmark(pipeline, demo=True)
        scores = {r.case_id: r.confidence for r in suite.results}
        snap   = BenchmarkSnapshot(
            ts=time.time(),
            avg_quality=suite.avg_quality,
            avg_confidence=suite.avg_confidence,
            avg_loops=suite.avg_loops,
            pass_rate=suite.passed / max(1, suite.passed + suite.failed),
            domain_scores=scores,
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO benchmarks VALUES(?,?,?,?,?,?)",
            (snap.ts, snap.avg_quality, snap.avg_confidence,
             snap.avg_loops, snap.pass_rate, json.dumps(scores))
        )
        self.conn.commit()
        return snap

    def detect_regression(self) -> Optional[str]:
        """Return warning string if quality has regressed vs previous snapshot."""
        rows = self.conn.execute(
            "SELECT * FROM benchmarks ORDER BY ts DESC LIMIT 2"
        ).fetchall()
        if len(rows) < 2:
            return None
        latest, prev = rows[0], rows[1]
        issues = []
        if latest["avg_quality"] < prev["avg_quality"] - 0.05:
            issues.append(f"quality dropped {prev['avg_quality']:.2f}→{latest['avg_quality']:.2f}")
        if latest["pass_rate"] < prev["pass_rate"] - 0.1:
            issues.append(f"pass rate dropped {prev['pass_rate']:.0%}→{latest['pass_rate']:.0%}")
        return "REGRESSION: " + " | ".join(issues) if issues else None

    def optimize_token_budget(self, session_db: str) -> Dict[str, int]:
        """Compute optimal token budget per domain from session history."""
        try:
            conn = sqlite3.connect(session_db)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT domain, avg_loops, calls FROM domain_stats WHERE calls >= 5"
            ).fetchall()
            conn.close()
        except Exception:
            return {}
        budgets: Dict[str, int] = {}
        for row in rows:
            avg_loops = row["avg_loops"]
            budgets[row["domain"]] = max(2000, min(15000, int(avg_loops * 1500)))
        return budgets

    def report(self) -> str:
        suggestions = self.conn.execute(
            "SELECT * FROM improvements ORDER BY ts DESC LIMIT 10"
        ).fetchall()
        regression  = self.detect_regression()
        lines = ["AILEX Self-Improvement Report", ""]
        if regression:
            lines.append(f"⚠ {regression}")
        lines.append(f"Suggestions: {len(suggestions)}")
        for s in suggestions:
            lines.append(f"  [{s['domain']}] {s['agent']}: {s['issue'][:60]}")
            lines.append(f"    → {s['new_prompt'][:80]}")
        return "\n".join(lines)

    def close(self) -> None:
        self.conn.close()


class ABTestingEngine:
    """A/B test different agent prompt variations, measure quality."""

    def __init__(self, client: Any = None):
        self.client  = client
        self._results: List[Dict] = []

    def run_ab(self, agent: str, prompt_a: str, prompt_b: str,
               test_requests: List[str], pipeline_factory) -> Dict:
        """Run same requests with two prompt variants, compare quality."""
        scores_a, scores_b = [], []
        for req in test_requests[:5]:
            for variant, prompt, scores in [("A", prompt_a, scores_a),
                                             ("B", prompt_b, scores_b)]:
                try:
                    # Temporarily patch the agent persona
                    import ailex_mythos_v6.agents as agents_mod
                    original = agents_mod.AGENT_PERSONAS.get(agent, "")
                    agents_mod.AGENT_PERSONAS[agent] = prompt
                    pl = pipeline_factory()
                    _, _, coda = pl.process(req, output_format="concise")
                    scores.append(coda.avg_quality * coda.final_confidence)
                    agents_mod.AGENT_PERSONAS[agent] = original
                except Exception:
                    scores.append(0.0)

        avg_a = sum(scores_a) / max(1, len(scores_a))
        avg_b = sum(scores_b) / max(1, len(scores_b))
        winner = "A" if avg_a >= avg_b else "B"
        result = {
            "agent": agent, "avg_a": round(avg_a, 3), "avg_b": round(avg_b, 3),
            "winner": winner, "delta": round(abs(avg_a - avg_b), 3),
            "winning_prompt": prompt_a if winner == "A" else prompt_b,
        }
        self._results.append(result)
        return result

    def format_result(self, r: Dict) -> str:
        return (
            f"A/B Test: {r['agent']}\n"
            f"  A: {r['avg_a']:.3f} | B: {r['avg_b']:.3f}\n"
            f"  Winner: {r['winner']} (Δ={r['delta']:.3f})\n"
            f"  Winning prompt: {r['winning_prompt'][:80]}..."
        )
