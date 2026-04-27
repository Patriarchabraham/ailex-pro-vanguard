"""
AILEX Pilot — code_search.py
Semantic code search: find similar patterns, functions, and logic across codebase.
Uses embeddings when available, falls back to TF-IDF.
"""
from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SearchResult:
    file:       str
    line:       int
    symbol:     str
    snippet:    str
    score:      float
    kind:       str   # "function" | "class" | "block"


class SemanticCodeSearch:
    """
    Semantic search across codebase.
    Indexes functions/classes, searches by natural language query.
    """

    DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ailex_code_index.db"
    )

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or self.DB_PATH
        self.conn    = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        self._embedder = None

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS code_index (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                file     TEXT,
                line     INTEGER,
                symbol   TEXT,
                kind     TEXT,
                snippet  TEXT,
                tokens   TEXT   -- space-joined tokens for TF-IDF
            );
            CREATE INDEX IF NOT EXISTS idx_code_file ON code_index(file);
        """)
        self.conn.commit()

    def index_project(self, root: str) -> int:
        """Index all source files in root. Returns number of symbols indexed."""
        self.conn.execute("DELETE FROM code_index")
        count = 0
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__", "dist", "build")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in (".py", ".ts", ".tsx", ".js", ".jsx"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read()
                    count  += self._index_file(os.path.relpath(fpath, root), content, ext)
                except Exception:
                    pass
        self.conn.commit()
        return count

    def _index_file(self, relpath: str, content: str, ext: str) -> int:
        count   = 0
        pattern = (r"(?:def|async def)\s+(\w+)\s*\([^)]*\)(?:\s*->[^:]+)?:\s*(?:\"\"\"(.+?)\"\"\")?[\s\S]{0,300}"
                   if ext == ".py" else
                   r"(?:function|const|let)\s+(\w+)\s*[=(][^{]*\{[\s\S]{0,300}")
        for m in re.finditer(pattern, content, re.DOTALL):
            name    = m.group(1)
            snippet = m.group(0)[:300].strip()
            line    = content[:m.start()].count("\n") + 1
            tokens  = self._tokenize(name + " " + snippet)
            self.conn.execute(
                "INSERT INTO code_index(file,line,symbol,kind,snippet,tokens) VALUES(?,?,?,?,?,?)",
                (relpath, line, name, "function", snippet[:500], tokens)
            )
            count += 1
        return count

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Search codebase by natural language query."""
        # Try semantic embeddings first
        results = self._semantic_search(query, top_k)
        if results:
            return results
        # Fallback: keyword/TF-IDF search
        return self._keyword_search(query, top_k)

    def _semantic_search(self, query: str, top_k: int) -> List[SearchResult]:
        try:
            from sentence_transformers import SentenceTransformer, util
            import torch
            if self._embedder is None:
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")

            rows = self.conn.execute("SELECT * FROM code_index LIMIT 1000").fetchall()
            if not rows:
                return []

            snippets = [r["snippet"] for r in rows]
            q_emb    = self._embedder.encode(query, convert_to_tensor=True)
            s_emb    = self._embedder.encode(snippets, convert_to_tensor=True,
                                              batch_size=32, show_progress_bar=False)
            scores   = util.cos_sim(q_emb, s_emb)[0]

            top_idxs = scores.topk(min(top_k, len(rows))).indices.tolist()
            return [
                SearchResult(
                    file=rows[i]["file"], line=rows[i]["line"],
                    symbol=rows[i]["symbol"], snippet=rows[i]["snippet"][:200],
                    score=float(scores[i]), kind=rows[i]["kind"],
                )
                for i in top_idxs
            ]
        except ImportError:
            return []

    def _keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        query_tokens = set(self._tokenize(query).split())
        rows = self.conn.execute("SELECT * FROM code_index").fetchall()
        scored: List[Tuple[float, Any]] = []
        for row in rows:
            row_tokens = set(row["tokens"].split())
            score = len(query_tokens & row_tokens) / max(1, len(query_tokens | row_tokens))
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda x: -x[0])
        return [
            SearchResult(
                file=r["file"], line=r["line"], symbol=r["symbol"],
                snippet=r["snippet"][:200], score=s, kind=r["kind"],
            )
            for s, r in scored[:top_k]
        ]

    def _tokenize(self, text: str) -> str:
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # camelCase split
        text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
        return " ".join(text.lower().split())

    def format_results(self, results: List[SearchResult], query: str) -> str:
        if not results:
            return f"No results for: '{query}'"
        lines = [f"Search: '{query}' — {len(results)} results", ""]
        for r in results:
            lines.append(f"  {r.file}:{r.line}  [{r.kind}] {r.symbol}  (score={r.score:.2f})")
            lines.append(f"    {r.snippet[:100].strip()}")
            lines.append("")
        return "\n".join(lines)

    def close(self) -> None:
        self.conn.close()
