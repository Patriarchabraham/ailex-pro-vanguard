#!/usr/bin/env python3
"""
AILEX Activation Script v7.0
═══════════════════════════════════════════════════════════════════
Runs every time AILEX starts. Launches ALL systems:

  [1] InstrumentedPipeline — patches ailex_core._call_sync with:
       Cache + QualityGate + AILEXLogger + MetricsStore
  [2] WebResearcher    — Wikipedia + arXiv + Semantic Scholar + OpenAlex
  [3] KnowledgeUpdater — Stores research in SQLite (12 domains, 40+ queries)
  [4] GitHubResearcher — Trending AI/ML/WebGL repos from GitHub
  [5] AutoImprover     — Synthesizes findings → improvement suggestions
  [6] ResearchScheduler — Keeps everything updated every 6h
  [7] ContextCompressor — Auto-compresses ConversationMemory > 40k tokens

All run in BACKGROUND THREADS — AILEX continues immediately.
Results: ~/.aiox-core/ailex_knowledge.db
Metrics: ~/.aiox-core/ailex_metrics.db
Logs:    ~/.aiox-core/logs/ailex-YYYY-MM-DD.jsonl

Usage:
    python3 ~/.aiox-core/ailex_activate.py           # start all (background)
    python3 ~/.aiox-core/ailex_activate.py --now     # block until done
    python3 ~/.aiox-core/ailex_activate.py --status  # knowledge DB + metrics
    python3 ~/.aiox-core/ailex_activate.py --dash    # live metrics dashboard
    python3 ~/.aiox-core/ailex_activate.py --health  # subsystem health check
    python3 ~/.aiox-core/ailex_activate.py --search "transformer LLM"
    python3 ~/.aiox-core/ailex_activate.py --github "neural network"
    python3 ~/.aiox-core/ailex_activate.py --suggest # improvement suggestions
    python3 ~/.aiox-core/ailex_activate.py --recent  # recent pipeline events
"""

from __future__ import annotations

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ailex_pilot.web_researcher    import WebResearcher
from ailex_pilot.knowledge_updater import KnowledgeUpdater, auto_update_on_activation
from ailex_pilot.github_researcher import GitHubResearcher
from ailex_pilot.auto_improve      import AutoImprover, auto_improve_on_activation
from ailex_pilot.research_scheduler import ResearchScheduler, activate_research
from ailex_pilot.pipeline_v2       import activate_instrumentation, get_pipeline
from ailex_pilot.observability     import metrics, health
from ailex_pilot.metrics_dashboard import render_dashboard, render_health, render_recent_events


def banner():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  AILEX v7.0 — Full Observability & Auto-Improvement System       ║
║  Pipeline:  Cache · QualityGate · Logger · Metrics · Trace       ║
║  Research:  Wikipedia · arXiv · Semantic Scholar · OpenAlex      ║
║             CrossRef · PubMed · DuckDuckGo · GitHub              ║
║  Domains:   AI · LLM · WebGL · Web · Security · Neuro · UX · SWE ║
╚═══════════════════════════════════════════════════════════════════╝
""")


def activate_background(verbose: bool = True) -> None:
    """Start ALL AILEX systems in background (non-blocking)."""
    print("[AILEX] ⚡ Activating full pipeline instrumentation…")

    # 1. Instrument ailex_core._call_sync (Cache + QualityGate + Logger + Metrics)
    try:
        pipe = activate_instrumentation(verbose=False)
        print("[AILEX] ✅ Pipeline instrumented: Cache · QA · Logger · Metrics active")
    except Exception as e:
        print(f"[AILEX] ⚠️  Instrumentation: {e}")

    # 2. Quick web research (Wikipedia + DuckDuckGo)
    auto_update_on_activation(
        domains=["ai", "web", "webgl", "llm"],
        verbose=verbose,
        max_age_h=6.0,
    )

    # 3. GitHub research + auto-improve
    auto_improve_on_activation(verbose=verbose)

    # 4. Full scheduler (keeps everything updated every 6h)
    sched = activate_research(verbose=False)
    if verbose:
        print(f"[AILEX] ✅ ResearchScheduler running — updates every {sched.INTERVAL_HOURS}h")
        print(f"[AILEX] Knowledge DB: ~/.aiox-core/ailex_knowledge.db")


def activate_blocking(verbose: bool = True) -> None:
    """Run full research cycle and wait for completion."""
    banner()
    print("[AILEX] Running FULL research cycle (blocking)…\n")
    t0 = time.perf_counter()

    # Academic research
    ku = KnowledgeUpdater()
    print("📚 Academic sources (arXiv · Semantic Scholar · OpenAlex)…")
    report = ku.update_all(
        domains=["ai","llm","webgl","web","neuro","swe"],
        max_age_hours=0,
        verbose=verbose,
    )
    print(f"\n{report}\n")

    # GitHub research + improvements
    imp = AutoImprover(verbose=verbose)
    print("\n🔍 GitHub research (AI · Neural · WebGL · ML frameworks)…")
    gh_report = imp.run(
        github_domains=["ai","neuro","webgl","ml_frameworks","web"],
        academic_domains=["ai","llm","neuro"],
        verbose=verbose,
    )
    print(f"\n{gh_report}")

    print(f"\n✅ Total: {time.perf_counter()-t0:.1f}s")
    ku.print_latest(n=5)
    imp.print_top_suggestions(n=8)


def show_status() -> None:
    """Show knowledge base statistics."""
    ku = KnowledgeUpdater()
    imp = AutoImprover(verbose=False)
    print(ku.format_stats())
    print()
    print("─" * 50)
    print("Recent improvements:")
    imp.print_top_suggestions(n=5)


def do_search(query: str) -> None:
    """Immediate academic search."""
    print(f"\n🔍 Searching: '{query}'\n")
    r = WebResearcher()

    wiki = r.wikipedia(query)
    if wiki:
        print(f"[WIKIPEDIA] {wiki.title}")
        print(f"  {wiki.snippet(200)}")
        print()

    papers = r.arxiv(query, max_results=3)
    for p in papers:
        print(f"[arXiv] {p.title[:70]}")
        print(f"  {p.date} | {', '.join(p.authors[:2])} | {p.snippet(120)}")
        print()

    oa = r.openalex(query, limit=3)
    for p in oa:
        print(f"[OpenAlex] {p.title[:70]} | ★{p.citations}")
        print(f"  {p.snippet(120)}")
        print()


def do_github(query: str) -> None:
    """GitHub search."""
    print(f"\n🔍 GitHub search: '{query}'\n")
    gh = GitHubResearcher()
    repos = gh.search_repos(query, limit=8, min_stars=50)
    print(gh.format_results(repos))


def main():
    parser = argparse.ArgumentParser(description="AILEX v7 — Full System")
    parser.add_argument("--now",     action="store_true", help="Block until full cycle done")
    parser.add_argument("--status",  action="store_true", help="Show knowledge base + metrics stats")
    parser.add_argument("--dash",    action="store_true", help="Show live metrics dashboard")
    parser.add_argument("--health",  action="store_true", help="Run subsystem health check")
    parser.add_argument("--recent",  action="store_true", help="Show recent pipeline events")
    parser.add_argument("--search",  type=str, default="", help="Immediate academic search")
    parser.add_argument("--github",  type=str, default="", help="GitHub search")
    parser.add_argument("--suggest", action="store_true", help="Show improvement suggestions")
    parser.add_argument("--watch",   type=int, default=0,  help="Dashboard watch interval (seconds)")
    parser.add_argument("--quiet",   action="store_true", help="Suppress verbose output")
    args = parser.parse_args()

    verbose = not args.quiet

    if args.health:
        render_health()
    elif args.dash or args.watch:
        if args.watch:
            try:
                while True:
                    os.system("clear")
                    print(render_dashboard())
                    print(f"  [auto-refresh {args.watch}s — Ctrl+C to stop]\n")
                    time.sleep(args.watch)
            except KeyboardInterrupt:
                print("\nDashboard stopped.")
        else:
            print(render_dashboard())
    elif args.recent:
        print(render_recent_events())
    elif args.status:
        show_status()
        print()
        print(render_dashboard())
    elif args.search:
        do_search(args.search)
    elif args.github:
        do_github(args.github)
    elif args.suggest:
        AutoImprover(verbose=False).print_top_suggestions(n=15)
    elif args.now:
        activate_blocking(verbose=verbose)
    else:
        banner()
        activate_background(verbose=verbose)
        print("\n[AILEX] ✅ All systems running in background.")
        print("[AILEX] Commands:")
        print("  --dash     Live metrics dashboard")
        print("  --health   Subsystem health check (15 components)")
        print("  --status   Knowledge base + metrics stats")
        print("  --recent   Recent pipeline events")
        print("  --search   Academic search")
        print("  --github   GitHub repository search")


if __name__ == "__main__":
    main()
