"""
AILEX Pilot — knowledge_base.py
Shared team knowledge base: decisions, patterns, lessons learned.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


KB_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ailex_knowledge.db"
)


@dataclass
class KBEntry:
    id:       str
    title:    str
    content:  str
    tags:     List[str]
    author:   str
    ts:       float = field(default_factory=time.time)
    kind:     str = "lesson"  # lesson | decision | pattern | warning


class KnowledgeBase:
    """Team-shared knowledge base. Persists across users and sessions."""

    def __init__(self, db_path: str = KB_DB):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id      TEXT PRIMARY KEY,
                title   TEXT, content TEXT,
                tags    TEXT, author  TEXT,
                ts      REAL, kind    TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
                USING fts5(title, content, tags, content='entries', content_rowid='rowid');
            CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
                INSERT INTO entries_fts(rowid,title,content,tags) VALUES(new.rowid,new.title,new.content,new.tags);
            END;
        """)
        self.conn.commit()

    def add(self, title: str, content: str, tags: List[str] = [],
            author: str = "ailex", kind: str = "lesson") -> str:
        eid = str(uuid.uuid4())[:8]
        self.conn.execute(
            "INSERT INTO entries VALUES(?,?,?,?,?,?,?)",
            (eid, title, content, json.dumps(tags), author, time.time(), kind)
        )
        self.conn.commit()
        return eid

    def search(self, query: str, limit: int = 10) -> List[KBEntry]:
        try:
            rows = self.conn.execute(
                "SELECT e.* FROM entries e JOIN entries_fts f ON e.rowid=f.rowid "
                "WHERE entries_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit)
            ).fetchall()
        except Exception:
            rows = self.conn.execute(
                "SELECT * FROM entries WHERE title LIKE ? OR content LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
        return [self._row(r) for r in rows]

    def get_context(self, query: str, max_chars: int = 2000) -> str:
        entries = self.search(query, limit=5)
        if not entries:
            return ""
        parts = ["=== TEAM KNOWLEDGE BASE ==="]
        total = 0
        for e in entries:
            chunk = f"[{e.kind.upper()}] {e.title}\n{e.content}"
            if total + len(chunk) > max_chars:
                break
            parts.append(chunk)
            total += len(chunk)
        parts.append("=== END KB ===")
        return "\n\n".join(parts)

    def _row(self, r) -> KBEntry:
        return KBEntry(id=r["id"], title=r["title"], content=r["content"],
                       tags=json.loads(r["tags"] or "[]"), author=r["author"],
                       ts=r["ts"], kind=r["kind"])

    def summary(self) -> str:
        n = self.conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        rows = self.conn.execute(
            "SELECT kind, COUNT(*) n FROM entries GROUP BY kind"
        ).fetchall()
        lines = [f"Knowledge Base: {n} entries"]
        for r in rows:
            lines.append(f"  {r['kind']}: {r['n']}")
        return "\n".join(lines)

    def close(self) -> None:
        self.conn.close()
