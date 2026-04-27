"""
AILEX Pilot — human_loop.py
Human-in-the-loop checkpoints: pause, inspect, approve/reject, modify.
Inspired by Cline's approval gates + LangGraph's human checkpoint pattern.
100% original AILEX implementation.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CheckpointDecision:
    approved:  bool
    modified:  Optional[str] = None   # modified request/data
    comment:   str = ""
    ts:        float = field(default_factory=time.time)


@dataclass
class HumanCheckpoint:
    id:         str
    stage:      str     # "pre_agents" | "post_agents" | "pre_commit" | "pre_exec"
    data:       Dict
    decision:   Optional[CheckpointDecision] = None
    auto_approved: bool = False


class HumanInTheLoop:
    """
    Approval gates for AILEX pipeline stages.
    Inspired by Cline's explicit human approval before every action.
    Three modes: interactive (CLI), auto-approve, callback-based (for UIs).

    AILEX original — concept from Cline/LangGraph but fully independent.
    """

    STAGES = ["pre_agents", "post_synthesis", "pre_execute", "pre_commit", "pre_pr"]

    def __init__(
        self,
        mode:         str = "interactive",    # "interactive" | "auto" | "callback"
        auto_stages:  List[str] = [],         # stages that never need approval
        callback:     Optional[Callable] = None,
        confidence_threshold: float = 0.85,   # auto-approve above this
    ):
        self.mode            = mode
        self.auto_stages     = set(auto_stages)
        self.callback        = callback
        self.threshold       = confidence_threshold
        self.history: List[HumanCheckpoint] = []

    def checkpoint(
        self,
        stage:      str,
        data:       Dict,
        summary:    str = "",
        confidence: float = 1.0,
    ) -> CheckpointDecision:
        """
        Pause at a checkpoint and get human decision.
        Returns immediately if auto-approved.
        """
        cp = HumanCheckpoint(
            id=f"{stage}_{int(time.time())}",
            stage=stage, data=data,
        )

        # Auto-approve conditions
        if (stage in self.auto_stages
                or self.mode == "auto"
                or confidence >= self.threshold):
            cp.auto_approved = True
            cp.decision      = CheckpointDecision(approved=True, comment="auto")
            self.history.append(cp)
            return cp.decision

        # Callback mode (for Web UI / Telegram)
        if self.mode == "callback" and self.callback:
            decision = self.callback(stage, summary, data)
            cp.decision = decision
            self.history.append(cp)
            return decision

        # Interactive CLI
        cp.decision = self._cli_prompt(stage, summary, data, confidence)
        self.history.append(cp)
        return cp.decision

    def _cli_prompt(self, stage: str, summary: str, data: Dict,
                    confidence: float) -> CheckpointDecision:
        sep = "─" * 60
        print(f"\n{sep}")
        print(f"⏸  AILEX CHECKPOINT — {stage.upper()}")
        print(f"   Confidence: {confidence:.0%}")
        if summary:
            print(f"   {summary[:200]}")
        print(sep)
        print("   [a] Approve  [r] Reject  [m] Modify  [s] Skip all")

        while True:
            try:
                choice = input("   Decision: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "a"  # non-interactive → auto-approve

            if choice in ("a", ""):
                return CheckpointDecision(approved=True, comment="approved")
            elif choice == "r":
                reason = input("   Reason (optional): ").strip()
                return CheckpointDecision(approved=False, comment=reason)
            elif choice == "m":
                mod = input("   Modified request: ").strip()
                return CheckpointDecision(approved=True, modified=mod, comment="modified")
            elif choice == "s":
                self.mode = "auto"
                return CheckpointDecision(approved=True, comment="skip-all")
            else:
                print("   [a] Approve  [r] Reject  [m] Modify  [s] Skip all")

    def wrap_pipeline(self, pipeline: Any) -> "GuardedPipeline":
        """Wrap a PilotPipeline with human approval gates."""
        return GuardedPipeline(pipeline, self)

    def report(self) -> str:
        if not self.history:
            return "No checkpoints recorded."
        approved = sum(1 for c in self.history if c.decision and c.decision.approved)
        lines    = [f"Checkpoints: {len(self.history)} total, {approved} approved"]
        for cp in self.history[-5:]:
            d = cp.decision
            if d:
                status = "✓" if d.approved else "✗"
                mod    = " [modified]" if d.modified else ""
                auto   = " [auto]" if cp.auto_approved else ""
                lines.append(f"  {status} {cp.stage}{mod}{auto}")
        return "\n".join(lines)


class GuardedPipeline:
    """PilotPipeline wrapper with human-in-the-loop gates at key stages."""

    def __init__(self, pipeline: Any, hitl: HumanInTheLoop):
        self._pipeline = pipeline
        self._hitl     = hitl

    def process(self, request: str, **kwargs) -> Dict:
        # Gate 1: before running agents
        decision = self._hitl.checkpoint(
            "pre_agents",
            {"request": request, **kwargs},
            summary=f"About to process: '{request[:80]}'",
        )
        if not decision.approved:
            return {"error": "Rejected at pre_agents", "request": request}
        if decision.modified:
            request = decision.modified

        # Run pipeline
        result = self._pipeline.process(request, **kwargs)

        # Gate 2: after synthesis, before code execution
        confidence = result.get("confidence", 1.0)
        decision2  = self._hitl.checkpoint(
            "post_synthesis",
            result,
            summary=result.get("report", "")[:200],
            confidence=confidence,
        )
        if not decision2.approved:
            return {"error": "Rejected at post_synthesis", **result}

        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._pipeline, name)
