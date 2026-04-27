"""
AILEX — knowledge_synthesis.py
Cross-session pattern synthesis: extracts wisdom from ALL past sessions.

Unlike session memory (which stores what happened),
knowledge synthesis extracts WHY things worked or failed,
and distils it into generalizable principles.

This is the difference between experience and wisdom.
A developer with 100 sessions of context is 100x more effective.
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
class SynthesisedPattern:
    pattern:      str         # generalizable principle
    domain:       str
    frequency:    int         # how many sessions confirm this
    confidence:   float
    examples:     List[str]
    actionable:   str         # what to do with this knowledge
    discovered:   float = field(default_factory=time.time)


class KnowledgeSynthesis:
    """
    Analyses all past sessions to extract generalizable patterns.

    Examples of what gets discovered:
    - "Auth bugs are always caused by session management, not credentials (seen 8 times)"
    - "Performance issues in this project trace to N+1 queries (seen 5 times)"
    - "Deploy failures consistently caused by missing env vars (seen 4 times)"

    These patterns are injected into new sessions as wisdom,
    dramatically reducing the time to solve similar problems.
    """

    SYNTHESIS_DB = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ailex_knowledge_synthesis.db"
    )

    def __init__(self, session_db: str = "", client: Any = None):
        self.session_db = session_db
        self.client     = client
        self._patterns: List[SynthesisedPattern] = []
        self._conn      = sqlite3.connect(self.SYNTHESIS_DB)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._load_patterns()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS patterns (
                id        INTEGER PRIMARY KEY,
                pattern   TEXT, domain TEXT,
                frequency INTEGER, confidence REAL,
                examples  TEXT, actionable TEXT,
                discovered REAL
            );
        """)

    def synthesise(self, n_patterns: int = 10) -> List[SynthesisedPattern]:
        """Analyse all sessions and extract patterns."""
        if not self.session_db or not os.path.exists(self.session_db):
            return self._demo_patterns()

        raw_data = self._load_session_data()
        if not raw_data:
            return []

        if self.client:
            patterns = self._synthesise_with_ai(raw_data, n_patterns)
        else:
            patterns = self._synthesise_heuristic(raw_data, n_patterns)

        self._save_patterns(patterns)
        self._patterns = patterns
        return patterns

    def inject_into_context(self, domain: str, request: str) -> str:
        """Return relevant patterns to inject into agent context."""
        relevant = [
            p for p in self._patterns
            if p.domain == domain or domain in p.pattern.lower()
        ]
        if not relevant:
            return ""
        lines = [f"[Knowledge Synthesis — {len(relevant)} patterns from {sum(p.frequency for p in relevant)} sessions]"]
        for p in sorted(relevant, key=lambda x: -x.frequency)[:3]:
            lines.append(f"  Pattern ({p.frequency}x): {p.pattern}")
            lines.append(f"  → {p.actionable}")
        return "\n".join(lines)

    def _load_session_data(self) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.session_db)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT request, domain, confidence, quality FROM records "
                "WHERE quality IS NOT NULL ORDER BY ts DESC LIMIT 200"
            ).fetchall()
            conn.close()
            return [{"request": r["request"], "domain": r["domain"],
                     "confidence": r["confidence"], "quality": r["quality"]}
                    for r in rows]
        except Exception:
            return []

    def _synthesise_with_ai(self, data: List[Dict], n: int) -> List[SynthesisedPattern]:
        """Use Claude to extract patterns from session data."""
        try:
            summary = "\n".join(
                f"[{d['domain']}] q={d['quality']:.2f} conf={d['confidence']:.2f}: {d['request'][:80]}"
                for d in data[:50]
            )
            resp = self.client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1500,
                messages=[{"role": "user", "content":
                    f"Analyse these AI engineering sessions and extract {n} generalizable patterns:\n\n{summary}\n\n"
                    "Format each pattern:\n"
                    "PATTERN: [generalizable principle]\nDOMAIN: [domain]\nFREQUENCY: [n]\n"
                    "ACTIONABLE: [what to do with this]\nEXAMPLES: [brief examples]"}],
            )
            return self._parse_patterns(resp.content[0].text)
        except Exception:
            return self._synthesise_heuristic(data, n)

    def _synthesise_heuristic(self, data: List[Dict], n: int) -> List[SynthesisedPattern]:
        """Extract patterns without AI using frequency analysis."""
        from collections import Counter
        domain_issues: Dict[str, List[str]] = {}
        for d in data:
            domain = d["domain"] or "code"
            if d.get("quality", 1.0) < 0.65:
                domain_issues.setdefault(domain, []).append(d["request"][:60])

        patterns = []
        for domain, issues in list(domain_issues.items())[:n]:
            patterns.append(SynthesisedPattern(
                pattern=f"{domain} requests often produce low-quality results",
                domain=domain, frequency=len(issues), confidence=0.70,
                examples=issues[:2],
                actionable=f"When working on {domain}, use more specific context and run extra validation",
            ))
        return patterns

    def _parse_patterns(self, text: str) -> List[SynthesisedPattern]:
        patterns = []
        for block in re.split(r"\n(?=PATTERN:)", text):
            if "PATTERN:" not in block:
                continue
            def get(k):
                m = re.search(rf"{k}:\s*(.+?)(?=\n[A-Z]+:|$)", block, re.I|re.S)
                return m.group(1).strip()[:200] if m else ""
            freq_str = get("FREQUENCY")
            freq = int(re.search(r"\d+", freq_str).group()) if re.search(r"\d+", freq_str) else 1
            ex = [e.strip() for e in get("EXAMPLES").split(";") if e.strip()]
            patterns.append(SynthesisedPattern(
                pattern=get("PATTERN"), domain=get("DOMAIN") or "code",
                frequency=freq, confidence=min(1.0, freq * 0.1 + 0.5),
                examples=ex[:2], actionable=get("ACTIONABLE"),
            ))
        return patterns

    def _save_patterns(self, patterns: List[SynthesisedPattern]) -> None:
        for p in patterns:
            self._conn.execute(
                "INSERT OR REPLACE INTO patterns(pattern,domain,frequency,confidence,examples,actionable,discovered) "
                "VALUES(?,?,?,?,?,?,?)",
                (p.pattern, p.domain, p.frequency, p.confidence,
                 json.dumps(p.examples), p.actionable, p.discovered)
            )
        self._conn.commit()

    def _load_patterns(self) -> None:
        rows = self._conn.execute(
            "SELECT * FROM patterns ORDER BY frequency DESC LIMIT 50"
        ).fetchall()
        self._patterns = [SynthesisedPattern(
            pattern=r["pattern"], domain=r["domain"],
            frequency=r["frequency"], confidence=r["confidence"],
            examples=json.loads(r["examples"] or "[]"),
            actionable=r["actionable"], discovered=r["discovered"],
        ) for r in rows]

    def _demo_patterns(self) -> List[SynthesisedPattern]:
        return [
            SynthesisedPattern("Auth issues trace to session management (7x)", "bug", 7, 0.89,
                ["broken login", "auth failing"], "Always check token expiry and session state first"),
            SynthesisedPattern("Performance issues caused by N+1 queries (5x)", "performance", 5, 0.82,
                ["slow API", "timeout"], "Profile database queries before optimising code"),
            SynthesisedPattern("Deploy failures from missing env vars (4x)", "deploy", 4, 0.91,
                ["build fails", "undefined env"], "Run env var audit before every production deploy"),
        ]

    @property
    def conn(self): return self._conn

    def summary(self) -> str:
        return (
            f"Knowledge Synthesis: {len(self._patterns)} patterns\n"
            + "\n".join(
                f"  ({p.frequency}x) [{p.domain}] {p.pattern[:60]}"
                for p in self._patterns[:5]
            )
        )
