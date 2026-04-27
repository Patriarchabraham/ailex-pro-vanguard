"""
AILEX Pilot — database.py
Generate, validate and execute SQL queries via natural language.
Supports: SQLite, PostgreSQL, MySQL (via connectors).
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class QueryResult:
    success:    bool
    sql:        str
    rows:       List[Dict]
    columns:    List[str]
    row_count:  int
    error:      Optional[str] = None
    duration_s: float = 0.0


class DatabaseAssistant:
    """
    Natural language → SQL → execute.
    Inspects schema, generates safe queries, executes and formats results.
    """

    def __init__(self, connection_string: str = "", client: Any = None):
        self.conn_str = connection_string
        self.client   = client
        self._conn: Optional[sqlite3.Connection] = None

    def connect_sqlite(self, path: str) -> bool:
        try:
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            return True
        except Exception:
            return False

    def get_schema(self) -> str:
        """Extract full schema as text for AI context."""
        if not self._conn:
            return "No database connected"
        schema_parts = []
        tables = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for tbl in tables:
            name = tbl[0]
            cols = self._conn.execute(f"PRAGMA table_info({name})").fetchall()
            col_defs = ", ".join(f"{c[1]} {c[2]}" for c in cols)
            schema_parts.append(f"TABLE {name} ({col_defs})")
            # Sample 3 rows
            try:
                rows = self._conn.execute(f"SELECT * FROM {name} LIMIT 3").fetchall()
                if rows:
                    schema_parts.append(f"  Sample: {[dict(r) for r in rows[:2]]}")
            except Exception:
                pass
        return "\n".join(schema_parts)

    def nl_to_sql(self, question: str) -> str:
        """Convert natural language question to SQL using Claude."""
        if not self.client:
            return f"-- Cannot generate SQL without API client\n-- Question: {question}"
        schema = self.get_schema()
        resp = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content":
                f"Database schema:\n{schema}\n\n"
                f"Generate a safe, read-only SQL query for: {question}\n"
                "Return ONLY the SQL, no explanation. "
                "Use SELECT only. No DROP, DELETE, UPDATE, INSERT."}],
        )
        sql = resp.content[0].text.strip()
        import re
        m = re.search(r"```sql\s*([\s\S]+?)\s*```", sql, re.I)
        return m.group(1).strip() if m else sql

    def execute(self, sql: str) -> QueryResult:
        """Execute a SQL query safely (read-only enforcement)."""
        import time
        start = time.time()
        if not self._conn:
            return QueryResult(success=False, sql=sql, rows=[], columns=[],
                               row_count=0, error="No database connected")

        # Safety: only allow SELECT
        sql_clean = sql.strip().upper()
        if not sql_clean.startswith("SELECT") and not sql_clean.startswith("WITH"):
            return QueryResult(success=False, sql=sql, rows=[], columns=[],
                               row_count=0, error="Only SELECT queries allowed")
        try:
            cursor = self._conn.execute(sql)
            cols   = [d[0] for d in (cursor.description or [])]
            rows   = [dict(zip(cols, r)) for r in cursor.fetchall()[:500]]
            return QueryResult(
                success=True, sql=sql, rows=rows, columns=cols,
                row_count=len(rows), duration_s=round(time.time()-start, 3)
            )
        except Exception as e:
            return QueryResult(success=False, sql=sql, rows=[], columns=[],
                               row_count=0, error=str(e),
                               duration_s=round(time.time()-start, 3))

    def ask(self, question: str) -> QueryResult:
        """Natural language → SQL → execute → return results."""
        sql = self.nl_to_sql(question)
        return self.execute(sql)

    def format_result(self, r: QueryResult, max_rows: int = 20) -> str:
        if not r.success:
            return f"Query failed: {r.error}\nSQL: {r.sql}"
        if not r.rows:
            return f"No results.\nSQL: {r.sql}"
        lines = [f"SQL: {r.sql}", f"Rows: {r.row_count} ({r.duration_s}s)", ""]
        # Table header
        widths = {c: max(len(c), max(len(str(row.get(c,""))) for row in r.rows[:max_rows]))
                  for c in r.columns}
        header = " | ".join(c.ljust(widths[c]) for c in r.columns)
        lines.append(header)
        lines.append("-" * len(header))
        for row in r.rows[:max_rows]:
            lines.append(" | ".join(str(row.get(c,"")).ljust(widths[c]) for c in r.columns))
        if r.row_count > max_rows:
            lines.append(f"... {r.row_count - max_rows} more rows")
        return "\n".join(lines)
