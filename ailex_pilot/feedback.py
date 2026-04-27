"""
AILEX Pilot — feedback.py
Human feedback loop: thumbs up/down calibrates agent routing weights over time.
AILEX improves with use — not just volume but quality of feedback.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

FEEDBACK_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ailex_feedback.db"
)


@dataclass
class FeedbackRecord:
    session_id:  str
    request:     str
    domain:      str
    agents_used: List[str]
    rating:      int     # 1=thumbs up, -1=thumbs down, 0=neutral
    comment:     str = ""
    ts:          float = field(default_factory=time.time)


class FeedbackLoop:
    """
    Tracks human ratings on AILEX outputs.
    Computes agent performance scores per domain.
    Feeds back into MoERouter priority weights.
    """

    def __init__(self, db_path: str = FEEDBACK_DB):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                request     TEXT,
                domain      TEXT,
                agents_used TEXT,
                rating      INTEGER,
                comment     TEXT DEFAULT '',
                ts          REAL
            );
            CREATE TABLE IF NOT EXISTS agent_scores (
                agent   TEXT,
                domain  TEXT,
                n_pos   INTEGER DEFAULT 0,
                n_neg   INTEGER DEFAULT 0,
                n_total INTEGER DEFAULT 0,
                score   REAL DEFAULT 0.5,
                PRIMARY KEY (agent, domain)
            );
            CREATE INDEX IF NOT EXISTS idx_fb_domain ON feedback(domain, ts);
        """)
        self.conn.commit()

    def record(self, session_id: str, request: str, domain: str,
               agents_used: List[str], rating: int, comment: str = "") -> None:
        """Record a rating (+1 / -1 / 0)."""
        self.conn.execute(
            "INSERT INTO feedback(session_id,request,domain,agents_used,rating,comment,ts) "
            "VALUES(?,?,?,?,?,?,?)",
            (session_id, request[:200], domain,
             json.dumps(agents_used), rating, comment, time.time())
        )
        self._update_agent_scores(agents_used, domain, rating)
        self.conn.commit()

    def _update_agent_scores(self, agents: List[str], domain: str, rating: int) -> None:
        for agent in agents:
            existing = self.conn.execute(
                "SELECT * FROM agent_scores WHERE agent=? AND domain=?", (agent, domain)
            ).fetchone()
            if existing:
                n_pos   = existing["n_pos"]   + (1 if rating > 0 else 0)
                n_neg   = existing["n_neg"]   + (1 if rating < 0 else 0)
                n_total = existing["n_total"] + 1
                score   = (n_pos - n_neg * 0.5) / max(1, n_total)
                score   = max(0.1, min(1.0, 0.5 + score * 0.5))
                self.conn.execute(
                    "UPDATE agent_scores SET n_pos=?,n_neg=?,n_total=?,score=? "
                    "WHERE agent=? AND domain=?",
                    (n_pos, n_neg, n_total, score, agent, domain)
                )
            else:
                score = 0.75 if rating > 0 else 0.35 if rating < 0 else 0.5
                self.conn.execute(
                    "INSERT INTO agent_scores VALUES(?,?,?,?,?,?)",
                    (agent, domain,
                     1 if rating > 0 else 0,
                     1 if rating < 0 else 0,
                     1, score)
                )

    def get_agent_boosts(self, domain: str) -> Dict[str, float]:
        """Return performance multipliers for agents in this domain (for MoERouter)."""
        rows = self.conn.execute(
            "SELECT agent, score FROM agent_scores WHERE domain=? AND n_total >= 2",
            (domain,)
        ).fetchall()
        return {r["agent"]: r["score"] for r in rows}

    def thumbs_up(self, session_id: str, request: str, domain: str,
                  agents: List[str], comment: str = "") -> None:
        self.record(session_id, request, domain, agents, 1, comment)

    def thumbs_down(self, session_id: str, request: str, domain: str,
                    agents: List[str], comment: str = "") -> None:
        self.record(session_id, request, domain, agents, -1, comment)

    def stats(self) -> str:
        total = self.conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        pos   = self.conn.execute("SELECT COUNT(*) FROM feedback WHERE rating=1").fetchone()[0]
        neg   = self.conn.execute("SELECT COUNT(*) FROM feedback WHERE rating=-1").fetchone()[0]
        lines = [
            f"Feedback: {total} total | {pos} positive | {neg} negative",
            f"Satisfaction: {pos/max(1,total):.0%}",
            "",
            "Top agents by domain:",
        ]
        rows = self.conn.execute(
            "SELECT agent, domain, score, n_total FROM agent_scores "
            "WHERE n_total >= 2 ORDER BY score DESC LIMIT 15"
        ).fetchall()
        for r in rows:
            bar = "█" * int(r["score"] * 10)
            lines.append(f"  {r['agent']:12s} [{r['domain']:15s}] {bar:10s} {r['score']:.2f} n={r['n_total']}")
        return "\n".join(lines)

    def close(self) -> None:
        self.conn.close()
