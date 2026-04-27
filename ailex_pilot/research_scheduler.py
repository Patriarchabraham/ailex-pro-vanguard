"""
AILEX — research_scheduler.py
Scheduled research that runs continuously in the background.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Integrates WebResearcher + KnowledgeUpdater into AILEX's lifecycle:

  ON ACTIVATION:
    • Instantly fetches quick Wikipedia + DuckDuckGo summaries
    • Starts background thread for deep academic research
    • Injects latest knowledge into AILEX context

  EVERY 6 HOURS (configurable):
    • Re-searches all 12 domains
    • Detects "breaking" developments (papers >100 citations in last 7 days)
    • Updates knowledge base
    • Logs research summary

  ON DEMAND:
    • researcher.search("query") — instant multi-source search
    • scheduler.get_context(domain) — inject into AILEX prompt

Usage:
    from ailex_pilot.research_scheduler import ResearchScheduler
    sched = ResearchScheduler()
    sched.start()              # starts background research loop
    context = sched.get_context("ai")   # inject into prompt
    results = sched.search("GSAP 2025") # immediate search
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from .web_researcher import WebResearcher, ResearchResult, quick_research
from .knowledge_updater import KnowledgeUpdater, auto_update_on_activation


# ── Quick context snippets for each domain ────────────────────────────────────

ACTIVATION_QUERIES = {
    "ai":       "latest AI language model breakthroughs 2025",
    "web":      "modern CSS JavaScript web development best practices 2025",
    "webgl":    "Three.js WebGL advanced techniques rendering",
    "security": "blockchain cryptography security latest research",
    "ux":       "modern UX design dark theme luxury premium interface",
    "swe":      "software engineering patterns AI-assisted development",
    "neuro":    "neuroscience cognitive computing brain-computer interface",
    "legaltech":"legal technology blockchain smart contracts regulation",
}


class ResearchScheduler:
    """
    Schedules and manages all background research for AILEX.
    Keeps the knowledge base current and provides context injection.
    """

    INTERVAL_HOURS = 6.0   # full update every 6 hours
    QUICK_SOURCES  = ["wikipedia", "duckduckgo", "arxiv"]
    DEEP_SOURCES   = ["arxiv", "semantic_scholar", "openalex", "crossref"]

    def __init__(self, verbose: bool = True):
        self.verbose    = verbose
        self.researcher = WebResearcher()
        self.updater    = KnowledgeUpdater()
        self._running   = False
        self._thread: Optional[threading.Thread] = None
        self._quick_cache: Dict[str, List[ResearchResult]] = {}
        self._last_full_update: float = 0.0

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self, run_now: bool = True) -> None:
        """
        Start the background research scheduler.
        Optionally runs an immediate update.
        """
        if self._running:
            return
        self._running = True

        if run_now:
            self._quick_activation()

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        if self.verbose:
            print(f"[ResearchScheduler] ✅ Started — updates every {self.INTERVAL_HOURS}h")

    def stop(self) -> None:
        self._running = False
        if self.verbose:
            print("[ResearchScheduler] Stopped")

    # ── Quick activation (instant, blocking) ──────────────────────────────────

    def _quick_activation(self) -> None:
        """
        Run fast searches on activation — Wikipedia + DuckDuckGo only.
        Returns quickly (~5s) without blocking AILEX startup.
        """
        if self.verbose:
            print("[ResearchScheduler] 🌐 Quick activation search…")

        for domain, query in list(ACTIVATION_QUERIES.items())[:4]:  # first 4 domains
            try:
                wiki = self.researcher.wikipedia(query)
                ddg  = self.researcher.duckduckgo(query)
                results = [r for r in [wiki, ddg] if r]
                if results:
                    self._quick_cache[domain] = results
                time.sleep(0.2)
            except Exception:
                pass

        if self.verbose:
            print(f"[ResearchScheduler] ⚡ Quick cache: {len(self._quick_cache)} domains")

    # ── Background loop ────────────────────────────────────────────────────────

    def _loop(self) -> None:
        # Run deep update immediately after quick activation
        time.sleep(3)
        self._deep_update()

        while self._running:
            elapsed = time.time() - self._last_full_update
            if elapsed >= self.INTERVAL_HOURS * 3600:
                self._deep_update()
            time.sleep(300)  # check every 5 minutes

    def _deep_update(self) -> None:
        if self.verbose:
            print(f"\n[ResearchScheduler] 🔬 Deep research update at {datetime.now().strftime('%H:%M')}…")
        try:
            report = self.updater.update_all(verbose=self.verbose)
            self._last_full_update = time.time()
            if self.verbose:
                print(f"[ResearchScheduler] ✅ {report.new_entries} new entries | {report.total_entries} total")
        except Exception as e:
            if self.verbose:
                print(f"[ResearchScheduler] ⚠️ Deep update error: {e}")

    # ── Context injection ──────────────────────────────────────────────────────

    def get_context(
        self,
        domain:        str,
        max_entries:   int  = 8,
        include_quick: bool = True,
    ) -> str:
        """
        Get a formatted context block for injecting into an AILEX prompt.
        Combines cached quick results + knowledge base entries.

        Example:
            ctx = scheduler.get_context("ai")
            prompt = f"Task: {task}\n\n{ctx}\n\nAnswer:"
        """
        sections: List[str] = []

        # Quick cache (Wikipedia/DuckDuckGo)
        if include_quick and domain in self._quick_cache:
            quick = self._quick_cache[domain]
            sections.append(
                f"[RECENT WEB KNOWLEDGE — {domain.upper()}]\n" +
                "\n".join(f"• {r.title}: {r.snippet(150)}" for r in quick[:2])
            )

        # Knowledge base (academic papers)
        db_entries = self.updater.query("", domain=domain, limit=max_entries)
        if db_entries:
            sections.append(
                f"[ACADEMIC KNOWLEDGE BASE — {domain.upper()} — {len(db_entries)} papers]\n" +
                "\n".join(
                    f"• {e['title'][:70]} ({e['source']}, {e['date']}, ★{e['citations']})\n"
                    f"  {(e['abstract'] or '')[:120]}"
                    for e in db_entries
                )
            )

        if not sections:
            return f"[No knowledge available for domain: {domain}]"

        return "\n\n".join(sections)

    # ── Immediate search ───────────────────────────────────────────────────────

    def search(
        self,
        query:  str,
        domain: str           = "general",
        deep:   bool          = False,
        limit:  int           = 5,
    ) -> List[ResearchResult]:
        """
        Immediate search across sources.
        deep=False: Wikipedia + DuckDuckGo (fast, ~2s)
        deep=True:  arXiv + Semantic Scholar + OpenAlex (thorough, ~10s)
        """
        sources = self.DEEP_SOURCES if deep else self.QUICK_SOURCES
        results = self.researcher.research(query, sources=sources, max_per_source=limit)

        # Store in knowledge base for future use
        if results:
            threading.Thread(
                target=self.updater._store,
                args=(domain, query, results),
                daemon=True,
            ).start()

        return results

    def search_and_summarize(self, query: str, deep: bool = False) -> str:
        """Search and return formatted results."""
        results = self.search(query, deep=deep)
        return self.researcher.format_results(results)

    # ── Status ─────────────────────────────────────────────────────────────────

    def status(self) -> str:
        stats = self.updater.stats()
        next_update = max(0, self.INTERVAL_HOURS * 3600 - (time.time() - self._last_full_update))
        lines = [
            f"ResearchScheduler Status",
            f"  Running:     {'Yes' if self._running else 'No'}",
            f"  Next update: {int(next_update/60)} min",
            f"  KB entries:  {stats['total']:,} ({stats['recent_24h']} last 24h)",
            f"  Quick cache: {len(self._quick_cache)} domains",
            f"  Sources:     Wikipedia · arXiv · Semantic Scholar · OpenAlex · CrossRef · PubMed · DuckDuckGo",
        ]
        return "\n".join(lines)


# ── Global scheduler ──────────────────────────────────────────────────────────

_scheduler: Optional[ResearchScheduler] = None


def get_scheduler(auto_start: bool = False) -> ResearchScheduler:
    """
    Get or create the global ResearchScheduler instance.
    If auto_start=True, starts background research on first call.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = ResearchScheduler()
        if auto_start:
            _scheduler.start()
    return _scheduler


def activate_research(verbose: bool = True) -> ResearchScheduler:
    """
    Called on AILEX activation.
    Starts the research scheduler and returns it.

    Add to your AILEX init:
        from ailex_pilot.research_scheduler import activate_research
        sched = activate_research()
    """
    sched = get_scheduler()
    if not sched._running:
        sched.verbose = verbose
        sched.start(run_now=True)
    return sched


# ── Quick convenience functions ───────────────────────────────────────────────

def research(query: str, deep: bool = False, limit: int = 5) -> List[ResearchResult]:
    """Quick research — auto-starts scheduler if needed."""
    return get_scheduler(auto_start=False).search(query, deep=deep, limit=limit)


def inject_context(domain: str) -> str:
    """Get research context for a domain — for prompt injection."""
    return get_scheduler().get_context(domain)


if __name__ == "__main__":
    print("Testing ResearchScheduler…")
    sched = ResearchScheduler(verbose=True)
    sched.start(run_now=True)

    time.sleep(8)  # let quick activation complete

    print("\n" + sched.status())
    print("\nContext for 'ai' domain:")
    print(sched.get_context("ai")[:500])

    print("\nImmediate search: 'GSAP animation performance'")
    results = sched.search("GSAP animation easing performance", deep=False)
    for r in results[:3]:
        print(f"  [{r.source}] {r.title[:60]}")

    print("\n✅ ResearchScheduler working")
