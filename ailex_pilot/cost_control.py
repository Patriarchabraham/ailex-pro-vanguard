"""
AILEX Pilot — cost_control.py
Real-time cost tracking, budget enforcement, and usage reports.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Anthropic pricing (per million tokens, as of April 2026)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-7":           {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":         {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input":  0.80, "output":  4.00},
    "claude-opus-4-6":           {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5":         {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5":          {"input":  0.80, "output":  4.00},
    "demo":                      {"input":  0.00, "output":  0.00},
}

# Replicate approximate costs
REPLICATE_PRICING: Dict[str, float] = {
    "black-forest-labs/flux-schnell": 0.003,
    "black-forest-labs/flux-dev":     0.025,
    "wan-video/wan2.1-t2v-480p":      0.050,
    "wan-video/wan2.1-i2v-480p":      0.050,
    "lightricks/ltx-video":           0.040,
}


@dataclass
class CostRecord:
    ts:         float
    model:      str
    tokens_in:  int
    tokens_out: int
    cost_usd:   float
    operation:  str   # "agent_call", "orion", "chaos", "vision", "image_gen", "video_gen"
    domain:     str   = ""
    session_id: str   = ""


@dataclass
class BudgetStatus:
    session_budget:   float
    session_spent:    float
    total_spent:      float
    remaining:        float
    pct_used:         float
    over_budget:      bool
    warning:          bool    # > 80%
    records:          List[CostRecord]


class CostController:
    """Tracks API costs in real time and enforces per-session budgets."""

    def __init__(self, session_budget: float = 5.0):
        self.session_budget = session_budget
        self.session_spent  = 0.0
        self.total_spent    = 0.0
        self.records: List[CostRecord] = []

    def record_api_call(
        self,
        model:      str,
        tokens_in:  int,
        tokens_out: int,
        operation:  str = "agent_call",
        domain:     str = "",
        session_id: str = "",
    ) -> float:
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-6"])
        cost    = (tokens_in  / 1_000_000) * pricing["input"] \
                + (tokens_out / 1_000_000) * pricing["output"]
        rec = CostRecord(
            ts=time.time(), model=model, tokens_in=tokens_in,
            tokens_out=tokens_out, cost_usd=round(cost, 6),
            operation=operation, domain=domain, session_id=session_id,
        )
        self.records.append(rec)
        self.session_spent += cost
        self.total_spent   += cost
        return cost

    def record_replicate(self, model: str, operation: str = "image_gen") -> float:
        cost = REPLICATE_PRICING.get(model, 0.01)
        rec  = CostRecord(ts=time.time(), model=model, tokens_in=0, tokens_out=0,
                          cost_usd=cost, operation=operation)
        self.records.append(rec)
        self.session_spent += cost
        self.total_spent   += cost
        return cost

    def check_budget(self) -> BudgetStatus:
        remaining = max(0.0, self.session_budget - self.session_spent)
        pct       = (self.session_spent / self.session_budget * 100) if self.session_budget > 0 else 0
        return BudgetStatus(
            session_budget=self.session_budget,
            session_spent=round(self.session_spent, 4),
            total_spent=round(self.total_spent, 4),
            remaining=round(remaining, 4),
            pct_used=round(pct, 1),
            over_budget=self.session_spent >= self.session_budget,
            warning=pct >= 80,
            records=self.records[-20:],
        )

    def can_proceed(self, estimated_cost: float = 0.10) -> bool:
        return (self.session_spent + estimated_cost) <= self.session_budget

    def estimate_request(self, domain: str, loops: int = 5, agents: int = 5) -> float:
        """Rough cost estimate for a request before running it."""
        # Average mix: 2 opus, 2 sonnet, 1 haiku per loop
        opus_cost   = (1000 / 1_000_000) * 15.00  # ~1K tokens each
        sonnet_cost = (1000 / 1_000_000) * 3.00
        haiku_cost  = (500  / 1_000_000) * 0.80
        per_loop = 2 * opus_cost + 2 * sonnet_cost + 1 * haiku_cost
        return round(per_loop * loops, 4)

    def reset_session(self) -> None:
        self.session_spent = 0.0
        self.records = []

    def report(self) -> str:
        status = self.check_budget()
        lines  = [
            f"Cost Report",
            f"  Session budget:  ${status.session_budget:.2f}",
            f"  Session spent:   ${status.session_spent:.4f} ({status.pct_used:.1f}%)",
            f"  Remaining:       ${status.remaining:.4f}",
            f"  Total all-time:  ${status.total_spent:.4f}",
        ]
        if status.over_budget: lines.append("  ⚠ OVER BUDGET")
        elif status.warning:   lines.append("  ⚠ Approaching budget limit")

        # Breakdown by model
        by_model: Dict[str, float] = {}
        for r in self.records:
            by_model[r.model] = by_model.get(r.model, 0.0) + r.cost_usd
        if by_model:
            lines.append("\n  By model:")
            for model, cost in sorted(by_model.items(), key=lambda x: -x[1]):
                lines.append(f"    {model:40s} ${cost:.4f}")

        # Breakdown by operation
        by_op: Dict[str, float] = {}
        for r in self.records:
            by_op[r.operation] = by_op.get(r.operation, 0.0) + r.cost_usd
        if by_op:
            lines.append("\n  By operation:")
            for op, cost in sorted(by_op.items(), key=lambda x: -x[1]):
                lines.append(f"    {op:20s} ${cost:.4f}")

        return "\n".join(lines)
