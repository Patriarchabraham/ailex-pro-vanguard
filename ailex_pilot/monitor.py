"""
AILEX Pilot — monitor.py
Usage dashboard: cost, quality, sessions, model breakdown — rendered with Rich.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.table   import Table
    from rich.panel   import Panel
    from rich.bar_chart import BarChart
    RICH = True
except ImportError:
    RICH = False

from .cost_control import CostController, MODEL_PRICING


class Monitor:
    """Real-time dashboard for AILEX Pilot usage."""

    def __init__(self, cost: CostController, conv_db: Optional[str] = None):
        self.cost     = cost
        self.conv_db  = conv_db
        self._console = None

    @property
    def console(self):
        if self._console is None:
            from rich.console import Console
            self._console = Console()
        return self._console

    def dashboard(self) -> str:
        """Full text dashboard."""
        lines = [
            "═" * 60,
            "  AILEX PILOT — MONITORING DASHBOARD",
            "═" * 60,
            "",
            self.cost.report(),
        ]

        if self.conv_db:
            try:
                conn = sqlite3.connect(self.conv_db)
                conn.row_factory = sqlite3.Row
                sessions = conn.execute(
                    "SELECT COUNT(*) as n, SUM(total_tokens) as t "
                    "FROM sessions"
                ).fetchone()
                messages = conn.execute("SELECT COUNT(*) as n FROM messages").fetchone()
                conn.close()
                lines += [
                    "",
                    "Conversations:",
                    f"  Sessions:  {sessions['n']}",
                    f"  Messages:  {messages['n']}",
                    f"  Tokens:    {(sessions['t'] or 0):,}",
                ]
            except Exception:
                pass

        # Recent records
        recent = self.cost.records[-10:]
        if recent:
            lines += ["", "Recent API calls:"]
            for r in recent:
                ts  = time.strftime("%H:%M:%S", time.localtime(r.ts))
                lines.append(
                    f"  [{ts}] {r.operation:15s} {r.model:35s} "
                    f"in={r.tokens_in:5d} out={r.tokens_out:5d} ${r.cost_usd:.5f}"
                )

        lines.append("═" * 60)
        return "\n".join(lines)

    def print_dashboard(self) -> None:
        if RICH:
            self.console.print(self.dashboard())
        else:
            print(self.dashboard())

    def quality_trend(self, records: List[Dict]) -> str:
        """Show quality trend from session records."""
        if not records:
            return "No data"
        avg_q = sum(r.get("quality", 0) for r in records) / len(records)
        avg_c = sum(r.get("confidence", 0) for r in records) / len(records)
        trend = "↑" if avg_q > 0.7 else ("→" if avg_q > 0.5 else "↓")
        return f"Quality {trend} avg={avg_q:.2f} | Confidence avg={avg_c:.2f} | N={len(records)}"

    def cost_warning(self) -> Optional[str]:
        status = self.cost.check_budget()
        if status.over_budget:
            return f"OVER BUDGET: spent ${status.session_spent:.4f} / ${status.session_budget:.2f}"
        if status.warning:
            return f"Budget warning: {status.pct_used:.1f}% used (${status.remaining:.4f} remaining)"
        return None
