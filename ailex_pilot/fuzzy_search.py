"""
AILEX Pilot — fuzzy_search.py
Fuzzy search over sessions, files, symbols, templates.
Inspired by fzf's scoring model — AILEX original implementation.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class FuzzyMatch:
    item:    str
    display: str
    score:   float
    meta:    Dict  = field(default_factory=dict)


class FuzzyMatcher:
    """
    Fuzzy string matching with scoring.
    Consecutive matches score higher. Prefix matches score highest.
    """

    def score(self, query: str, target: str) -> float:
        if not query:
            return 1.0
        q = query.lower()
        t = target.lower()
        if q == t:
            return 1.0
        if t.startswith(q):
            return 0.95
        if q in t:
            return 0.85 - (t.index(q) / max(len(t), 1)) * 0.2

        # Character-by-character fuzzy match
        qi, ti    = 0, 0
        matches   = 0
        last_match= -1
        consecutive = 0
        bonus     = 0.0
        while qi < len(q) and ti < len(t):
            if q[qi] == t[ti]:
                matches += 1
                if ti == last_match + 1:
                    consecutive += 1
                    bonus += 0.1 * consecutive
                else:
                    consecutive = 0
                last_match = ti
                qi += 1
            ti += 1

        if qi < len(q):
            return 0.0  # not all chars matched
        base = matches / max(len(q), 1)
        pos  = 1.0 - (last_match / max(len(t), 1)) * 0.3
        return min(0.80, base * pos + bonus)

    def search(
        self,
        query:   str,
        items:   List[Tuple[str, str, Dict]],   # (key, display, meta)
        top_k:   int = 10,
        min_score: float = 0.2,
    ) -> List[FuzzyMatch]:
        results: List[FuzzyMatch] = []
        for key, display, meta in items:
            s = self.score(query, key)
            if s >= min_score:
                results.append(FuzzyMatch(key, display, s, meta))
        results.sort(key=lambda m: -m.score)
        return results[:top_k]


class AILEXFuzzySearch:
    """
    High-level fuzzy search over AILEX data: sessions, files, symbols, templates.
    """

    def __init__(self, pilot: Any):
        self.pilot   = pilot
        self._fuzzy  = FuzzyMatcher()

    def search_sessions(self, query: str) -> List[FuzzyMatch]:
        sessions = self.pilot.memory.list_sessions(50)
        items    = [
            (s["name"], f"[{s['id']}] {s['name']} ({_ts(s['updated_at'])})", s)
            for s in sessions
        ]
        return self._fuzzy.search(query, items)

    def search_files(self, query: str, root: str = "") -> List[FuzzyMatch]:
        root  = root or self.pilot.project_dir
        items: List[Tuple[str, str, Dict]] = []
        for dp, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__")]
            for f in files:
                if os.path.splitext(f)[1] in (".py",".ts",".js",".tsx",".jsx",".md"):
                    rel  = os.path.relpath(os.path.join(dp, f), root)
                    items.append((rel, rel, {"path": os.path.join(dp, f)}))
        return self._fuzzy.search(query, items)

    def search_templates(self, query: str) -> List[FuzzyMatch]:
        try:
            from ailex_pilot.prompt_templates import PromptLibrary
            lib   = PromptLibrary()
            items = [
                (t.name,
                 f"{t.name} — {t.description[:50]}",
                 {"template": t})
                for t in lib.list()
            ]
            return self._fuzzy.search(query, items)
        except Exception:
            return []

    def search_kb(self, query: str) -> List[FuzzyMatch]:
        try:
            from ailex_pilot.knowledge_base import KnowledgeBase
            kb      = KnowledgeBase()
            entries = kb.search(query, limit=20)
            items   = [
                (e.title, f"[{e.kind}] {e.title}", {"entry": e})
                for e in entries
            ]
            return self._fuzzy.search(query, [(i[0],i[1],i[2]) for i in items], min_score=0.0)
        except Exception:
            return []

    def interactive(self) -> Optional[str]:
        """Simple interactive fuzzy picker (no fzf dependency)."""
        try:
            categories = ["sessions", "files", "templates", "kb"]
            print("Fuzzy search — category:", " | ".join(f"{i+1}.{c}" for i,c in enumerate(categories)))
            cat_in = input("Category [1-4]: ").strip()
            cat    = categories[int(cat_in)-1] if cat_in.isdigit() and 1<=int(cat_in)<=4 else "files"
            query  = input(f"Search {cat}: ").strip()
            searcher = getattr(self, f"search_{cat}", self.search_files)
            results  = searcher(query)
            if not results:
                print("No results.")
                return None
            for i, r in enumerate(results[:10]):
                print(f"  {i+1}. {r.display} ({r.score:.0%})")
            sel = input("Select [1-10]: ").strip()
            if sel.isdigit() and 1<=int(sel)<=len(results):
                return results[int(sel)-1].item
        except (KeyboardInterrupt, EOFError):
            pass
        return None

    def format_results(self, results: List[FuzzyMatch], query: str) -> str:
        if not results:
            return f"No fuzzy matches for '{query}'"
        lines = [f"Fuzzy: '{query}' — {len(results)} results"]
        for r in results:
            lines.append(f"  {r.score:.0%}  {r.display}")
        return "\n".join(lines)


def _ts(unix: float) -> str:
    import time
    return time.strftime("%m/%d %H:%M", time.localtime(unix))
