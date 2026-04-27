"""
AILEX — metrics_dashboard.py
Real-time terminal dashboard for AILEX pipeline observability.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Shows live metrics: calls, cache hits, quality scores, costs, errors.
Reads from MetricsStore (SQLite) and AILEXLogger (JSONL).
Updates every N seconds in terminal.

Usage:
    python3 ~/.aiox-core/ailex_pilot/metrics_dashboard.py
    python3 ~/.aiox-core/ailex_pilot/metrics_dashboard.py --once
    python3 ~/.aiox-core/ailex_pilot/metrics_dashboard.py --watch 5
    python3 ~/.aiox-core/ailex_pilot/metrics_dashboard.py --health
    python3 ~/.aiox-core/ailex_pilot/metrics_dashboard.py --recent
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ailex_pilot.observability import metrics, health
from ailex_pilot.ailex_logger  import LOG_DIR, tail_logs


# ── Colours ───────────────────────────────────────────────────────────────────
R   = "\033[0m"
BOLD= "\033[1m"
GRN = "\033[92m"
RED = "\033[91m"
YLW = "\033[93m"
BLU = "\033[94m"
CYN = "\033[96m"
GRY = "\033[90m"
MGT = "\033[95m"


def _bar(value: float, max_val: float = 100, width: int = 20, color: str = GRN) -> str:
    filled = int(width * min(value, max_val) / max(1, max_val))
    return f"{color}{'█' * filled}{GRY}{'░' * (width - filled)}{R}"


def _pct_color(pct: float) -> str:
    if pct >= 80: return GRN
    if pct >= 50: return YLW
    return RED


def render_dashboard() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d   = metrics.dashboard_data()
    s   = metrics.stats() if hasattr(metrics, "stats") else {}

    # Recent errors from log
    recent_errors = []
    try:
        entries = tail_logs(50, "WARNING")
        recent_errors = [e for e in entries if e.get("level") in ("ERROR", "WARNING")][-5:]
    except Exception:
        pass

    # Recent agent calls from metrics
    recent_calls = metrics.recent_events("agent.call", limit=8)
    cache_pct = float(d["cache_rate"].rstrip("%")) if "%" in d["cache_rate"] else 0
    err_pct   = float(d["error_rate"].rstrip("%"))  if "%" in d["error_rate"]  else 0

    lines = [
        "",
        f"{BOLD}{CYN}  ⚡ AILEX Pipeline — Observability Dashboard{R}   {GRY}{now}{R}",
        f"  {GRY}{'─' * 62}{R}",
        "",
        f"  {BOLD}PIPELINE ACTIVITY{R}",
        f"  {'Calls today:':<22} {BLU}{d['calls_today']:>6}{R}   {'This hour:':<14} {BLU}{d['calls_hour']:>4}{R}",
        f"  {'Total all-time:':<22} {GRY}{d['calls_total']:>6}{R}   {'QA blocked:':<14} {RED if int(d['qa_blocked']) else GRN}{d['qa_blocked']:>4}{R}",
        "",
        f"  {BOLD}CACHE PERFORMANCE{R}",
        f"  Hit rate: {_bar(cache_pct)} {_pct_color(cache_pct)}{d['cache_rate']}{R}",
        f"  {GRN}Hits: {d['cache_hits']}{R}   {GRY}Misses: {d['cache_miss']}{R}",
        "",
        f"  {BOLD}QUALITY & COST{R}",
        f"  Avg confidence: {BOLD}{MGT}{d['avg_conf']}{R}   Avg latency: {CYN}{d['avg_ms']}{R}",
        f"  Tokens today:   {d['tokens_today']:,}   Est. cost: {GRN}{d['cost_est_usd']}{R}",
        "",
        f"  {BOLD}ERROR RATE{R}",
        f"  {_bar(err_pct, max_val=10)} {_pct_color(100-err_pct*10)}{d['error_rate']}{R} ({d['errors_today']} errors today)",
        "",
    ]

    if recent_calls:
        lines.append(f"  {BOLD}RECENT AGENT CALLS{R}")
        for ev in recent_calls[:6]:
            data = ev.get("data", {})
            age  = ev.get("age_s", 0)
            agent = data.get("agent", "?")
            conf  = data.get("confidence", 0)
            ms    = data.get("ms", 0)
            dom   = data.get("domain", "?")
            c_col = GRN if conf >= 0.8 else YLW if conf >= 0.65 else RED
            lines.append(
                f"  {GRY}{age:>4}s ago{R}  {CYN}{agent:<6}{R}  {c_col}conf={conf:.2f}{R}"
                f"  {GRY}{ms}ms  {dom}{R}"
            )
        lines.append("")

    if recent_errors:
        lines.append(f"  {BOLD}{RED}RECENT ERRORS{R}")
        for e in recent_errors[-3:]:
            ts  = e.get("ts", "")[:16]
            msg = e.get("msg", "")[:60]
            lines.append(f"  {RED}⚠  {GRY}{ts}{R}  {msg}")
        lines.append("")

    # Knowledge base stats
    try:
        from ailex_pilot.knowledge_updater import KnowledgeUpdater
        ku = KnowledgeUpdater()
        s  = ku.stats()
        lines.append(f"  {BOLD}KNOWLEDGE BASE{R}")
        lines.append(f"  {GRN}{s['total']:,}{R} entries · {GRY}{s['recent_24h']} last 24h{R} · {len(s.get('by_domain',{}))} domains")
        lines.append("")
    except Exception:
        pass

    lines.append(f"  {GRY}{'─' * 62}{R}")
    lines.append(f"  {GRY}Commands: --health  --recent  --watch N  --once{R}")
    lines.append("")

    return "\n".join(lines)


def render_health() -> str:
    print(f"\n{BOLD}{CYN}  ⚡ AILEX — Subsystem Health Check{R}\n  {'─'*50}")
    results = health.check_all(verbose=True)
    ok  = sum(1 for r in results if r.ok)
    total = len(results)
    col = GRN if ok == total else YLW if ok >= total * 0.8 else RED
    print(f"\n  {col}{ok}/{total} subsystems healthy{R}")
    return ""


def render_recent_events(n: int = 20) -> str:
    lines = [f"\n{BOLD}{CYN}  ⚡ AILEX — Recent Pipeline Events{R}\n  {'─'*56}"]
    events = metrics.recent_events(limit=n)
    if not events:
        lines.append("  No events recorded yet. Run a pipeline task first.")
    for ev in events:
        age  = ev.get("age_s", 0)
        name = ev.get("event", "?")
        data = ev.get("data", {})
        trace = ev.get("trace", "")[:8]
        col  = RED if "error" in name else GRN if "ok" in name else CYN
        summary = " ".join(f"{k}={v}" for k, v in list(data.items())[:3])
        lines.append(f"  {GRY}{age:>5}s{R}  {col}{name:<25}{R}  {GRY}{trace}{R}  {summary[:40]}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="AILEX Metrics Dashboard")
    ap.add_argument("--once",   action="store_true", help="Print once and exit")
    ap.add_argument("--watch",  type=int, default=0,  help="Refresh interval in seconds")
    ap.add_argument("--health", action="store_true", help="Run health checks")
    ap.add_argument("--recent", action="store_true", help="Show recent events")
    args = ap.parse_args()

    if args.health:
        render_health()
        return

    if args.recent:
        print(render_recent_events())
        return

    if args.watch:
        try:
            while True:
                os.system("clear" if os.name != "nt" else "cls")
                print(render_dashboard())
                print(f"  {GRY}[auto-refresh every {args.watch}s — Ctrl+C to stop]{R}\n")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n  Dashboard stopped.")
        return

    # Default: once
    print(render_dashboard())


if __name__ == "__main__":
    main()
