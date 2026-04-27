"""
AILEX Pilot — conversation.py
Persistent multi-turn conversation with session memory.
Each session maintains context across multiple requests.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


CONV_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ailex_conversations.db"
)


@dataclass
class Message:
    id:         str
    session_id: str
    role:       str          # "user" | "assistant" | "system"
    content:    str
    domain:     str  = ""
    loops_run:  int  = 0
    confidence: float = 0.0
    tokens:     int  = 0
    ts:         float = field(default_factory=time.time)
    metadata:   Dict = field(default_factory=dict)


@dataclass
class Session:
    id:          str
    name:        str
    project_dir: str
    messages:    List[Message]
    created_at:  float
    updated_at:  float
    total_tokens: int  = 0
    total_cost:   float = 0.0


class ConversationMemory:
    """
    Persistent multi-turn conversation storage.
    Each session = one working context (e.g. one project, one debug session).
    """

    def __init__(self, db_path: str = CONV_DB):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                name        TEXT,
                project_dir TEXT DEFAULT '',
                created_at  REAL,
                updated_at  REAL,
                total_tokens INTEGER DEFAULT 0,
                total_cost   REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                domain      TEXT DEFAULT '',
                loops_run   INTEGER DEFAULT 0,
                confidence  REAL DEFAULT 0.0,
                tokens      INTEGER DEFAULT 0,
                ts          REAL,
                metadata    TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id, ts);
            CREATE INDEX IF NOT EXISTS idx_session_updated ON sessions(updated_at);
        """)
        self.conn.commit()

    # ── Session management ────────────────────────────────────────────────────

    def new_session(self, name: str = "", project_dir: str = "") -> Session:
        sid = str(uuid.uuid4())[:8]
        now = time.time()
        name = name or f"session-{sid}"
        self.conn.execute(
            "INSERT INTO sessions(id,name,project_dir,created_at,updated_at) VALUES(?,?,?,?,?)",
            (sid, name, project_dir, now, now),
        )
        self.conn.commit()
        return Session(id=sid, name=name, project_dir=project_dir,
                       messages=[], created_at=now, updated_at=now)

    def get_session(self, session_id: str) -> Optional[Session]:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not row:
            return None
        messages = self._load_messages(session_id)
        return Session(
            id=row["id"], name=row["name"], project_dir=row["project_dir"],
            messages=messages, created_at=row["created_at"],
            updated_at=row["updated_at"], total_tokens=row["total_tokens"],
            total_cost=row["total_cost"],
        )

    def latest_session(self) -> Optional[Session]:
        row = self.conn.execute(
            "SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        return self.get_session(row["id"]) if row else None

    def list_sessions(self, limit: int = 20) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT id, name, project_dir, updated_at, total_tokens, total_cost "
            "FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        self.conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        self.conn.commit()

    # ── Message management ────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role:       str,
        content:    str,
        domain:     str   = "",
        loops_run:  int   = 0,
        confidence: float = 0.0,
        tokens:     int   = 0,
        metadata:   Dict  = {},
    ) -> Message:
        mid = str(uuid.uuid4())[:12]
        now = time.time()
        self.conn.execute(
            "INSERT INTO messages(id,session_id,role,content,domain,loops_run,"
            "confidence,tokens,ts,metadata) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (mid, session_id, role, content, domain, loops_run,
             confidence, tokens, now, json.dumps(metadata)),
        )
        self.conn.execute(
            "UPDATE sessions SET updated_at=?, total_tokens=total_tokens+? WHERE id=?",
            (now, tokens, session_id),
        )
        self.conn.commit()
        return Message(id=mid, session_id=session_id, role=role, content=content,
                       domain=domain, loops_run=loops_run, confidence=confidence,
                       tokens=tokens, ts=now, metadata=metadata)

    def _load_messages(self, session_id: str, limit: int = 50) -> List[Message]:
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY ts DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        msgs = []
        for row in reversed(rows):
            msgs.append(Message(
                id=row["id"], session_id=row["session_id"],
                role=row["role"], content=row["content"],
                domain=row["domain"], loops_run=row["loops_run"],
                confidence=row["confidence"], tokens=row["tokens"],
                ts=row["ts"], metadata=json.loads(row["metadata"] or "{}"),
            ))
        # Auto-compress if context is getting large (ContextCompressor integration)
        if len(msgs) > 30:
            try:
                from .context_compressor import ContextCompressor
                from .observability import metrics
                cc = ContextCompressor()
                raw_msgs = [{"role": m.role, "content": m.content} for m in msgs]
                result = cc.compress(raw_msgs, budget_tokens=40_000, recency=15)
                if result.messages_removed > 0:
                    metrics.inc("context.compressed")
                    metrics.inc("context.messages_removed", result.messages_removed)
            except Exception:
                pass
        return msgs

    def build_context(self, session: Session, max_messages: int = 10) -> str:
        """Build conversation context string for injection into agent prompts."""
        if not session.messages:
            return ""
        recent = session.messages[-max_messages:]
        lines  = ["=== CONVERSATION HISTORY ==="]
        for m in recent:
            role_label = "USER" if m.role == "user" else "AILEX"
            extra = ""
            if m.domain:    extra += f" [domain={m.domain}"
            if m.loops_run: extra += f", T={m.loops_run}"
            if m.confidence: extra += f", conf={m.confidence:.2f}"
            if extra: extra += "]"
            lines.append(f"\n[{role_label}{extra}]")
            lines.append(m.content[:500] + ("..." if len(m.content) > 500 else ""))
        lines.append("=== END CONVERSATION HISTORY ===")
        return "\n".join(lines)

    def update_cost(self, session_id: str, cost: float) -> None:
        self.conn.execute(
            "UPDATE sessions SET total_cost=total_cost+? WHERE id=?", (cost, session_id)
        )
        self.conn.commit()

    def summary(self, limit: int = 10) -> str:
        sessions = self.list_sessions(limit)
        if not sessions:
            return "No conversations yet."
        lines = [f"AILEX Conversations ({len(sessions)} recent):"]
        for s in sessions:
            ts   = time.strftime("%m/%d %H:%M", time.localtime(s["updated_at"]))
            lines.append(
                f"  [{s['id']}] {s['name'][:30]:30s} | {ts} | "
                f"tokens={s['total_tokens']:,} | cost=${s['total_cost']:.3f}"
            )
        return "\n".join(lines)

    def close(self) -> None:
        self.conn.close()

    def __del__(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
