"""
AILEX Pilot — task_queue.py
Autonomous task queue: AILEX processes a list of tickets without human intervention.
Each task has dependencies, priority, status, and auto-commits on success.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


QUEUE_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ailex_tasks.db"
)


@dataclass
class QueueTask:
    id:           str
    title:        str
    description:  str
    domain:       str
    priority:     int         # 1=high, 2=medium, 3=low
    status:       str         # pending | running | done | failed | blocked
    depends_on:   List[str]   # task IDs that must complete first
    result:       str = ""
    error:        str = ""
    created_at:   float = field(default_factory=time.time)
    started_at:   float = 0.0
    finished_at:  float = 0.0
    auto_commit:  bool  = False
    auto_pr:      bool  = False


class TaskQueue:
    """
    Persistent autonomous task queue.
    AILEX picks tasks in priority+dependency order and executes them.
    """

    def __init__(self, db_path: str = QUEUE_DB):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT NOT NULL,
                domain      TEXT DEFAULT 'code',
                priority    INTEGER DEFAULT 2,
                status      TEXT DEFAULT 'pending',
                depends_on  TEXT DEFAULT '[]',
                result      TEXT DEFAULT '',
                error       TEXT DEFAULT '',
                created_at  REAL,
                started_at  REAL DEFAULT 0,
                finished_at REAL DEFAULT 0,
                auto_commit INTEGER DEFAULT 0,
                auto_pr     INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, priority);
        """)
        self.conn.commit()

    def add(self, title: str, description: str, domain: str = "code",
            priority: int = 2, depends_on: List[str] = [],
            auto_commit: bool = False, auto_pr: bool = False) -> str:
        tid = str(uuid.uuid4())[:8]
        self.conn.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, title, description, domain, priority, "pending",
             json.dumps(depends_on), "", "", time.time(), 0, 0,
             int(auto_commit), int(auto_pr))
        )
        self.conn.commit()
        return tid

    def next_task(self) -> Optional[QueueTask]:
        """Get next runnable task (all dependencies done, ordered by priority)."""
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE status='pending' ORDER BY priority, created_at"
        ).fetchall()
        done_ids = {r["id"] for r in
                    self.conn.execute("SELECT id FROM tasks WHERE status='done'").fetchall()}
        for row in rows:
            deps = json.loads(row["depends_on"] or "[]")
            if all(d in done_ids for d in deps):
                return self._row_to_task(row)
        return None

    def run_all(self, pipeline: Any, max_tasks: int = 50) -> List[QueueTask]:
        """Process all pending tasks autonomously."""
        results: List[QueueTask] = []
        for _ in range(max_tasks):
            task = self.next_task()
            if not task:
                break
            result = self.run_task(task, pipeline)
            results.append(result)
        return results

    def run_task(self, task: QueueTask, pipeline: Any) -> QueueTask:
        self._set_status(task.id, "running", started_at=time.time())
        try:
            proc = pipeline.process(
                task.description, override_domain=task.domain,
                run_code=True, auto_commit=task.auto_commit,
                include_context=True, fmt="concise"
            )
            result = proc.get("report", "")
            if task.auto_pr and proc.get("committed"):
                pr = pipeline.create_pr(f"AILEX: {task.title}")
                result += f"\nPR: {pr.get('url', '')}"
            self._set_status(task.id, "done", result=result, finished_at=time.time())
            task.status, task.result = "done", result
        except Exception as e:
            self._set_status(task.id, "failed", error=str(e), finished_at=time.time())
            task.status, task.error = "failed", str(e)
        return task

    def _set_status(self, tid: str, status: str, result: str = "",
                    error: str = "", started_at: float = 0, finished_at: float = 0) -> None:
        self.conn.execute(
            "UPDATE tasks SET status=?, result=?, error=?, "
            "started_at=CASE WHEN ? > 0 THEN ? ELSE started_at END, "
            "finished_at=CASE WHEN ? > 0 THEN ? ELSE finished_at END "
            "WHERE id=?",
            (status, result, error, started_at, started_at,
             finished_at, finished_at, tid)
        )
        self.conn.commit()

    def _row_to_task(self, row: Any) -> QueueTask:
        return QueueTask(
            id=row["id"], title=row["title"], description=row["description"],
            domain=row["domain"], priority=row["priority"], status=row["status"],
            depends_on=json.loads(row["depends_on"] or "[]"),
            result=row["result"], error=row["error"],
            created_at=row["created_at"], started_at=row["started_at"],
            finished_at=row["finished_at"],
            auto_commit=bool(row["auto_commit"]), auto_pr=bool(row["auto_pr"]),
        )

    def list_tasks(self) -> List[QueueTask]:
        return [self._row_to_task(r) for r in
                self.conn.execute("SELECT * FROM tasks ORDER BY priority,created_at").fetchall()]

    def summary(self) -> str:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) n FROM tasks GROUP BY status"
        ).fetchall()
        counts = {r["status"]: r["n"] for r in rows}
        total  = sum(counts.values())
        lines  = [f"Task Queue: {total} total"]
        for s in ("pending", "running", "done", "failed", "blocked"):
            if counts.get(s, 0):
                lines.append(f"  {s:8s}: {counts[s]}")
        return "\n".join(lines)

    def close(self) -> None:
        self.conn.close()
