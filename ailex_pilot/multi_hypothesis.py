"""
AILEX Pilot — multi_hypothesis.py
Run the pipeline on 3 competing framings of a request simultaneously,
then synthesize across all three for the best answer.

Surpasses single-framing: catches the real problem when the stated problem is wrong.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


@dataclass
class Hypothesis:
    framing:    str
    domain:     str
    confidence: float
    loops_run:  int
    quality:    float
    report:     str
    tokens:     int = 0


@dataclass
class MultiHypothesisResult:
    original_request:  str
    hypotheses:        List[Hypothesis]
    best_framing:      str
    synthesis:         str
    winning_domain:    str
    total_tokens:      int
    duration_s:        float
    agreement_score:   float   # 0.0 = disagreement, 1.0 = full agreement


class MultiHypothesisEngine:
    """
    Generates 3 alternative framings of a request and runs them in parallel.
    Synthesizes across all framings for the most robust answer.
    """

    def __init__(self, pipeline: Any):
        self.pipeline = pipeline

    def _generate_framings(self, request: str) -> List[Tuple[str, str]]:
        """Generate 3 alternative framings (framing, domain override)."""
        framings = [
            (request, None),  # Original framing
            (f"Root cause analysis: {request}", "architecture"),
            (f"Quick pragmatic fix: {request}", "bug"),
        ]

        req_low = request.lower()
        # Context-aware alternative framings
        if any(w in req_low for w in ["slow", "performance", "fast"]):
            framings[1] = (f"What is causing the performance bottleneck: {request}", "performance")
            framings[2] = (f"Measure and fix: {request}", "code")
        elif any(w in req_low for w in ["deploy", "production", "release"]):
            framings[1] = (f"Zero-downtime deployment strategy: {request}", "deploy")
            framings[2] = (f"Rollback plan and risk mitigation: {request}", "security")
        elif any(w in req_low for w in ["design", "ui", "ux", "layout"]):
            framings[1] = (f"User experience perspective: {request}", "design")
            framings[2] = (f"Technical implementation: {request}", "code")
        elif any(w in req_low for w in ["architecture", "redesign", "refactor"]):
            framings[1] = (f"Long-term maintainability: {request}", "architecture")
            framings[2] = (f"Immediate incremental improvement: {request}", "refactor")

        return framings

    def run(self, request: str, fmt: str = "concise") -> MultiHypothesisResult:
        """Run 3 framings in parallel, synthesize."""
        start     = time.time()
        framings  = self._generate_framings(request)
        hypotheses: List[Hypothesis] = []

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                futures = [
                    pool.submit(self._run_one, framing, domain, fmt)
                    for framing, domain in framings
                ]
                for f in futures:
                    h = f.result()
                    if h:
                        hypotheses.append(h)
        except RuntimeError:
            for framing, domain in framings:
                h = self._run_one(framing, domain, fmt)
                if h:
                    hypotheses.append(h)

        if not hypotheses:
            return MultiHypothesisResult(
                original_request=request, hypotheses=[],
                best_framing=request, synthesis="No results",
                winning_domain="unknown", total_tokens=0,
                duration_s=0, agreement_score=0,
            )

        best = max(hypotheses, key=lambda h: h.confidence * h.quality)
        agreement = self._agreement_score(hypotheses)
        synthesis = self._synthesize(request, hypotheses)

        return MultiHypothesisResult(
            original_request=request,
            hypotheses=hypotheses,
            best_framing=best.framing,
            synthesis=synthesis,
            winning_domain=best.domain,
            total_tokens=sum(h.tokens for h in hypotheses),
            duration_s=round(time.time() - start, 2),
            agreement_score=agreement,
        )

    def _run_one(self, framing: str, domain: Optional[str], fmt: str) -> Optional[Hypothesis]:
        try:
            p, h, coda = self.pipeline.process(
                framing, override_domain=domain, output_format=fmt
            )
            report = self.pipeline.report(p, h, coda, fmt=fmt)
            return Hypothesis(
                framing=framing, domain=coda.domain,
                confidence=coda.final_confidence, loops_run=coda.loops_run,
                quality=coda.avg_quality, report=report,
                tokens=getattr(coda, "tokens_used", 0),
            )
        except Exception:
            return None

    def _agreement_score(self, hypotheses: List[Hypothesis]) -> float:
        if len(hypotheses) < 2:
            return 1.0
        domains = [h.domain for h in hypotheses]
        most_common = max(set(domains), key=domains.count)
        return domains.count(most_common) / len(domains)

    def _synthesize(self, request: str, hypotheses: List[Hypothesis]) -> str:
        lines = [f"Multi-Hypothesis Analysis: '{request}'", ""]
        for i, h in enumerate(hypotheses, 1):
            lines.append(
                f"Framing {i} [{h.domain}]: conf={h.confidence:.2f} q={h.quality:.2f} T={h.loops_run}"
            )
            lines.append(f"  {h.framing[:80]}")
            lines.append(f"  → {h.report[:200]}")
            lines.append("")
        best = max(hypotheses, key=lambda h: h.confidence * h.quality)
        lines.append(f"BEST: Framing '{best.framing[:60]}' (domain={best.domain})")
        return "\n".join(lines)

    def format_result(self, r: MultiHypothesisResult) -> str:
        lines = [
            f"Multi-Hypothesis | {len(r.hypotheses)} framings | "
            f"{r.duration_s}s | {r.total_tokens:,} tokens | "
            f"agreement={r.agreement_score:.0%}",
            f"Best domain: {r.winning_domain}",
            "",
            r.synthesis,
        ]
        return "\n".join(lines)
