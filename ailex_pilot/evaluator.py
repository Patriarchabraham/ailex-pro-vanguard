"""
AILEX Pilot — evaluator.py
Quality benchmarking: measure AILEX output quality objectively.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkCase:
    id:          str
    request:     str
    domain:      str
    expected_keywords: List[str]    # words that should appear in synthesis
    forbidden:   List[str] = field(default_factory=list)  # words that should NOT appear
    min_confidence: float  = 0.90
    min_loops:   int       = 1
    max_loops:   int       = 16


@dataclass
class BenchmarkResult:
    case_id:      str
    passed:       bool
    confidence:   float
    loops_run:    int
    quality:      float
    keywords_hit: List[str]
    keywords_miss: List[str]
    forbidden_hit: List[str]
    duration_s:   float
    notes:        List[str] = field(default_factory=list)


@dataclass
class BenchmarkSuite:
    name:    str
    results: List[BenchmarkResult]
    passed:  int
    failed:  int
    avg_quality:    float
    avg_confidence: float
    avg_loops:      float
    total_time_s:   float


STANDARD_BENCHMARK: List[BenchmarkCase] = [
    BenchmarkCase(
        id="bug-001", domain="bug",
        request="fix broken login — users can't authenticate",
        expected_keywords=["auth", "session", "token", "fix", "login"],
        min_confidence=0.90, min_loops=2, max_loops=6,
    ),
    BenchmarkCase(
        id="arch-001", domain="architecture",
        request="redesign authentication system for HIPAA compliance",
        expected_keywords=["HIPAA", "compliance", "encrypt", "audit", "security"],
        min_confidence=0.92, min_loops=5, max_loops=12,
    ),
    BenchmarkCase(
        id="feat-001", domain="feature",
        request="add dark mode to the web app",
        expected_keywords=["dark", "theme", "CSS", "toggle", "preference"],
        min_confidence=0.88, min_loops=3, max_loops=8,
    ),
    BenchmarkCase(
        id="deploy-001", domain="deploy",
        request="deploy to production with zero downtime",
        expected_keywords=["rollback", "deploy", "canary", "monitoring", "zero-downtime"],
        min_confidence=0.90, min_loops=2, max_loops=6,
    ),
    BenchmarkCase(
        id="vague-001", domain="vague",
        request="make it better",
        expected_keywords=[],  # vague should early-exit or clarify
        min_confidence=0.0, min_loops=0, max_loops=16,
    ),
]


class Evaluator:
    """Benchmarks AILEX quality against known-good test cases."""

    def run_benchmark(
        self,
        pipeline: Any,
        cases: Optional[List[BenchmarkCase]] = None,
        demo: bool = True,
    ) -> BenchmarkSuite:
        cases = cases or STANDARD_BENCHMARK
        results: List[BenchmarkResult] = []
        start = time.time()

        for case in cases:
            result = self._run_case(pipeline, case, demo)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        return BenchmarkSuite(
            name="AILEX Standard Benchmark",
            results=results,
            passed=passed,
            failed=len(results) - passed,
            avg_quality    = sum(r.quality    for r in results) / len(results),
            avg_confidence = sum(r.confidence for r in results) / len(results),
            avg_loops      = sum(r.loops_run  for r in results) / len(results),
            total_time_s   = round(time.time() - start, 2),
        )

    def _run_case(self, pipeline: Any, case: BenchmarkCase, demo: bool) -> BenchmarkResult:
        start = time.time()
        notes: List[str] = []

        try:
            p, h, coda = pipeline.process(case.request, override_domain=case.domain)
        except Exception as e:
            return BenchmarkResult(
                case_id=case.id, passed=False, confidence=0.0,
                loops_run=0, quality=0.0, keywords_hit=[], keywords_miss=[],
                forbidden_hit=[], duration_s=round(time.time()-start, 2),
                notes=[f"EXCEPTION: {e}"],
            )

        # Get ORION synthesis text
        synthesis = ""
        if h.loop_history:
            for c in h.loop_history[-1].contributions:
                if c.agent == "ORION":
                    synthesis = c.signal
                    break

        all_text = (synthesis + " " + coda.domain + " " +
                    " ".join(coda.agents_activated)).lower()

        keywords_hit  = [k for k in case.expected_keywords if k.lower() in all_text]
        keywords_miss = [k for k in case.expected_keywords if k.lower() not in all_text]
        forbidden_hit = [k for k in case.forbidden         if k.lower() in all_text]

        # Evaluate
        passed = True
        if coda.final_confidence < case.min_confidence:
            passed = False
            notes.append(f"confidence {coda.final_confidence:.2f} < {case.min_confidence}")
        if coda.loops_run < case.min_loops:
            passed = False
            notes.append(f"loops {coda.loops_run} < min {case.min_loops}")
        if coda.loops_run > case.max_loops:
            notes.append(f"loops {coda.loops_run} > max {case.max_loops} (excessive)")
        if keywords_miss and len(keywords_miss) > len(case.expected_keywords) // 2:
            passed = False
            notes.append(f"missing keywords: {keywords_miss}")
        if forbidden_hit:
            passed = False
            notes.append(f"forbidden words found: {forbidden_hit}")

        return BenchmarkResult(
            case_id=case.id, passed=passed,
            confidence=coda.final_confidence,
            loops_run=coda.loops_run, quality=coda.avg_quality,
            keywords_hit=keywords_hit, keywords_miss=keywords_miss,
            forbidden_hit=forbidden_hit,
            duration_s=round(time.time()-start, 2),
            notes=notes,
        )

    def format_suite(self, suite: BenchmarkSuite) -> str:
        pct = suite.passed / max(1, suite.passed + suite.failed) * 100
        lines = [
            f"AILEX Benchmark: {suite.name}",
            f"  Passed:  {suite.passed}/{suite.passed+suite.failed} ({pct:.0f}%)",
            f"  Avg quality:     {suite.avg_quality:.3f}",
            f"  Avg confidence:  {suite.avg_confidence:.3f}",
            f"  Avg loops:       {suite.avg_loops:.1f}",
            f"  Total time:      {suite.total_time_s}s",
            "",
        ]
        for r in suite.results:
            status = "✓" if r.passed else "✗"
            lines.append(
                f"  {status} [{r.case_id:12s}] conf={r.confidence:.2f} "
                f"T={r.loops_run} q={r.quality:.2f} {r.duration_s:.1f}s"
            )
            if r.notes:
                for note in r.notes:
                    lines.append(f"      ↳ {note}")
        return "\n".join(lines)
