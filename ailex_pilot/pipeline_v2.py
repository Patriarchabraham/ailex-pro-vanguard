"""
AILEX — pipeline_v2.py
Fully integrated pipeline: Cache + QualityGate + Logger + Research + MultiProvider.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the PRODUCTION pipeline. Replaces the raw _call_sync() in ailex_core.py
with a fully instrumented, cached, quality-gated version.

Pipeline stages (per agent call):
  [1] TRACE      — generate trace_id, start span
  [2] CACHE      — check SmartCacheV2 (skip API if hit)
  [3] CONTEXT    — inject research KB context if available
  [4] CALL       — StructuredAgentCall (tool_use JSON, retry on 429)
  [5] QUALITY    — AgentQualityGate (5 checks, auto-retry if score < 0.65)
  [6] LOG        — AILEXLogger (JSON lines + trace_id)
  [7] METRICS    — MetricsStore (counters, timings, events)
  [8] CACHE_STORE— SmartCacheV2.set() for future reuse
  [9] RETURN     — validated, cached, observed result

Usage:
    from ailex_pilot.pipeline_v2 import InstrumentedPipeline
    pipe = InstrumentedPipeline()

    # Call one agent:
    result = pipe.call_agent("DEX", "Fix login bug", "bug")
    print(result.analysis, result.confidence)

    # Call all agents in parallel:
    results = pipe.run_parallel("Fix login bug", "bug", agents=["DEX","QUINN","ARIA"])

    # ORION synthesis:
    synthesis = pipe.synthesise("Fix login bug", "bug", results)

    # Monkey-patch ailex_core to use instrumented version:
    pipe.patch_ailex_core()   # ← call once at startup
"""

from __future__ import annotations

import sys
import os
import time
import asyncio
import concurrent.futures
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .ailex_logger       import get_logger, new_trace, AILEXLogger
from .smart_cache_v2     import get_cache, SmartCacheV2
from .agent_quality_gate import AgentQualityGate, QualityReport
from .structured_output  import StructuredAgentCall, AgentOutput, SynthesisOutput
from .observability      import tracer, metrics, observe
from .context_compressor import ContextCompressor
from .multi_provider     import MultiProvider


# ── Config ────────────────────────────────────────────────────────────────────

CACHE_TTL_BY_DOMAIN: Dict[str, int] = {
    "bug":          1800,    # 30 min — bugs change
    "feature":      3600,    # 1h
    "code":         7200,    # 2h
    "architecture": 21600,   # 6h
    "deploy":       900,     # 15 min
    "performance":  7200,    # 2h
    "default":      3600,    # 1h
}


# ── Result enriched with pipeline metadata ────────────────────────────────────

class PipelineResult(AgentOutput):
    """AgentOutput + pipeline metadata."""
    cache_hit:      bool       = False
    quality_score:  float      = 0.0
    quality_report: Optional[QualityReport] = None
    trace_id:       str        = ""
    pipeline_ms:    int        = 0
    kb_context_used: bool      = False

    def to_core_dict(self) -> Dict:
        """Convert to legacy ailex_core dict format for backwards compatibility."""
        return {
            "agent":      self.agent,
            "model":      self.model,
            "approach":   self.analysis,
            "risk":       self.risk,
            "insight":    self.recommendation,
            "confidence": self.confidence,
            "tokens":     self.tokens_in + self.tokens_out,
            "api_used":   not self.cache_hit,
            "cache_hit":  self.cache_hit,
            "quality":    self.quality_score,
            "trace_id":   self.trace_id,
            "duration_ms":self.pipeline_ms,
        }


# ── Instrumented Pipeline ─────────────────────────────────────────────────────

class InstrumentedPipeline:
    """
    Production-grade AILEX pipeline with full observability.
    All 9 stages: Trace → Cache → Context → Call → Quality → Log → Metrics → Store → Return
    """

    def __init__(
        self,
        api_key:        str = "",
        cache:          Optional[SmartCacheV2] = None,
        quality_gate:   Optional[AgentQualityGate] = None,
        logger:         Optional[AILEXLogger] = None,
        multi_provider: Optional[MultiProvider] = None,
        inject_research: bool = True,
    ):
        self.cache      = cache or get_cache()
        self.gate       = quality_gate or AgentQualityGate()
        self.log        = logger or get_logger("pipeline")
        self.caller     = StructuredAgentCall(api_key=api_key)
        self.mp         = multi_provider or MultiProvider()
        self.inject_research = inject_research
        self._active_trace: str = ""

    # ── Single agent call ──────────────────────────────────────────────────────

    def call_agent(
        self,
        agent:       str,
        task:        str,
        domain:      str,
        context:     str      = "",
        model:       str      = "",
        max_tokens:  int      = 400,
        force_fresh: bool     = False,
    ) -> PipelineResult:
        """
        Full instrumented agent call through all 9 pipeline stages.

        Returns a PipelineResult (extends AgentOutput) with:
        - .analysis, .recommendation, .confidence (from QualityGated output)
        - .cache_hit, .quality_score, .trace_id, .pipeline_ms
        """
        t0 = time.perf_counter()

        # [1] TRACE
        trace = self._active_trace or tracer.new_trace()
        self._active_trace = trace

        # [2] CACHE CHECK
        cache_key = f"agent:{agent}:{hash(task[:200])}:{domain}"
        if not force_fresh:
            cached = self.cache.get("analysis", cache_key)
            if cached:
                metrics.inc("cache.hit")
                metrics.inc(f"cache.hit.{agent}")
                self.log.info("cache_hit", trace=trace, agent=agent, domain=domain)
                r = PipelineResult(
                    agent=agent,
                    model=cached.get("model",""),
                    analysis=cached.get("approach", cached.get("analysis","")),
                    recommendation=cached.get("insight", cached.get("recommendation","")),
                    risk=cached.get("risk",""),
                    confidence=cached.get("confidence", 0.75),
                    flags=cached.get("flags",[]),
                )
                r.cache_hit = True
                r.trace_id  = trace
                r.pipeline_ms = int((time.perf_counter()-t0)*1000)
                return r

        metrics.inc("cache.miss")

        # [3] CONTEXT INJECTION — prepend research KB if available
        enriched_context = context
        if self.inject_research:
            kb_ctx = self._get_kb_context(domain)
            if kb_ctx:
                enriched_context = f"{kb_ctx}\n\n{context}".strip()
                metrics.inc("kb_context.injected")

        # Determine model
        import importlib
        try:
            ailex_core = importlib.import_module("ailex_core")
            resolved_model = model or ailex_core.MODEL_ROUTING.get(agent, "claude-haiku-4-5-20251001")
        except Exception:
            resolved_model = model or "claude-sonnet-4-6"

        # [4] STRUCTURED AGENT CALL
        self.log.info("agent_call_start", trace=trace, agent=agent, domain=domain)
        output: AgentOutput = self.caller.call(
            agent=agent, task=task, domain=domain,
            model=resolved_model, context=enriched_context[:500],
            max_tokens=max_tokens,
        )

        # [5] QUALITY GATE
        qreport = self.gate.evaluate(output)
        metrics.inc("qa.evaluated")
        if not qreport.passes:
            metrics.inc("qa.blocked")
            self.log.qa(trace=trace, check="AgentQualityGate",
                        passed=False, score=qreport.score,
                        issues=str(qreport.issues[:2]))
            # Auto-retry once with enriched prompt
            if qreport.score > 0.3:
                retry_ctx = f"{enriched_context[:300]} [RETRY: improve specificity and actionability]"
                output = self.caller.call(agent, task, domain, resolved_model,
                                          retry_ctx, max_tokens=max_tokens)
                qreport = self.gate.evaluate(output)
                metrics.inc("qa.retry")

        # [6] LOG
        dur_ms = int((time.perf_counter() - t0) * 1000)
        self.log.agent(
            agent, trace=trace, duration_ms=dur_ms,
            confidence=output.confidence,
            tokens=output.tokens_in + output.tokens_out,
            quality=qreport.score,
            domain=domain, cache_hit=False,
            via_tool_use=output.via_tool_use,
        )

        # [7] METRICS
        metrics.inc("agent.call.total")
        metrics.inc(f"agent.call.{agent}")
        metrics.inc(f"agent.call.domain.{domain}")
        metrics.timing("agent_ms", dur_ms)
        metrics.record(trace, "agent.call",
                       agent=agent, domain=domain, ms=dur_ms,
                       confidence=output.confidence,
                       tokens=output.tokens_in + output.tokens_out,
                       quality=qreport.score)

        # Build PipelineResult
        result = PipelineResult(
            agent=agent, model=output.model,
            analysis=output.analysis,
            recommendation=output.recommendation,
            risk=output.risk,
            confidence=output.confidence,
            flags=output.flags,
            tokens_in=output.tokens_in,
            tokens_out=output.tokens_out,
            duration_ms=dur_ms,
            via_tool_use=output.via_tool_use,
        )
        result.cache_hit       = False
        result.quality_score   = qreport.score
        result.quality_report  = qreport
        result.trace_id        = trace
        result.pipeline_ms     = dur_ms
        result.kb_context_used = bool(kb_ctx if self.inject_research else "")

        # [8] CACHE STORE
        ttl = CACHE_TTL_BY_DOMAIN.get(domain, CACHE_TTL_BY_DOMAIN["default"])
        self.cache.set("analysis", cache_key, result.to_core_dict(), ttl=ttl)

        return result

    # ── Parallel execution ─────────────────────────────────────────────────────

    def run_parallel(
        self,
        task:     str,
        domain:   str,
        agents:   List[str],
        context:  str = "",
    ) -> List[PipelineResult]:
        """Run multiple agents in parallel. Returns list of PipelineResults."""
        trace = tracer.new_trace()
        self._active_trace = trace
        self.log.pipeline("parallel_start", trace=trace, domain=domain,
                          agents=len(agents))
        t0 = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as ex:
            futs = {ex.submit(self.call_agent, a, task, domain, context): a for a in agents}
            results = []
            for fut in concurrent.futures.as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as e:
                    agent = futs[fut]
                    self.log.error("agent_fail", trace=trace, agent=agent, error=str(e))
                    metrics.inc("agent.error")
                    # Fallback
                    fallback = PipelineResult(
                        agent=agent, model="", analysis=f"Agent unavailable: {e}",
                        recommendation="Retry", confidence=0.0, flags=["ERROR"])
                    results.append(fallback)

        dur_ms = int((time.perf_counter()-t0)*1000)
        self.log.pipeline("parallel_done", trace=trace, domain=domain,
                          agents=len(results), total_ms=dur_ms)
        metrics.timing("parallel_ms", dur_ms)
        self._active_trace = ""
        return results

    # ── ORION synthesis ────────────────────────────────────────────────────────

    def synthesise(
        self,
        task:         str,
        domain:       str,
        contributions: List[PipelineResult],
    ) -> AgentOutput:
        """ORION meta-synthesis of all agent outputs."""
        if not contributions:
            return AgentOutput(agent="ORION", model="", analysis="No contributions",
                               recommendation="Run agents first", confidence=0.5)

        context = "\n".join(
            f"- {r.agent} (conf={r.confidence:.2f}): {r.analysis[:100]}"
            for r in contributions if r.agent != "ORION"
        )
        trace = self._active_trace or tracer.new_trace()
        orion = self.call_agent("ORION", task, domain,
                                context=f"Agent contributions:\n{context}")
        self.log.pipeline("synthesis_done", trace=trace, domain=domain,
                          confidence=orion.confidence)
        return orion

    # ── Monkey-patch ──────────────────────────────────────────────────────────

    def patch_ailex_core(self) -> None:
        """
        Replace ailex_core._call_sync with the instrumented pipeline.
        Call ONCE at startup to instrument all existing code.

            pipe = InstrumentedPipeline()
            pipe.patch_ailex_core()
            # Now ALL ailex_core._call_sync calls are instrumented
        """
        try:
            import ailex_core as core

            pipe = self   # capture self

            def _instrumented_call_sync(agent: str, task: str, domain: str,
                                         context: str = "") -> dict:
                result = pipe.call_agent(agent, task, domain, context)
                return result.to_core_dict()

            core._call_sync  = _instrumented_call_sync  # type: ignore
            core._call_sync._instrumented = True  # type: ignore
            core._original_call_sync_patched = True     # type: ignore

            self.log.info("ailex_core_patched",
                          trace=tracer.new_trace(),
                          message="ailex_core._call_sync → InstrumentedPipeline")
            metrics.inc("pipeline.patch.applied")
            print("[InstrumentedPipeline] ✅ ailex_core._call_sync patched — full observability active")

        except ImportError as e:
            self.log.warn("patch_failed", error=str(e))

    # ── Context injection ──────────────────────────────────────────────────────

    def _get_kb_context(self, domain: str) -> str:
        """Pull latest research context from knowledge base."""
        try:
            from .knowledge_updater import KnowledgeUpdater
            ku      = KnowledgeUpdater()
            entries = ku.query("", domain=domain, limit=3, since_hours=72)
            if not entries:
                return ""
            lines = [f"• {e['title'][:70]} ({e['source']}, ★{e['citations']})"
                     for e in entries]
            return f"[Recent {domain.upper()} research]\n" + "\n".join(lines)
        except Exception:
            return ""


# ── Global singleton ──────────────────────────────────────────────────────────

_pipeline: Optional[InstrumentedPipeline] = None

def get_pipeline(api_key: str = "") -> InstrumentedPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InstrumentedPipeline(api_key=api_key)
    return _pipeline


def activate_instrumentation(api_key: str = "", verbose: bool = True) -> InstrumentedPipeline:
    """
    Activate full pipeline instrumentation.
    Patches ailex_core + starts metrics collection.
    Call ONCE at AILEX startup.

        from ailex_pilot.pipeline_v2 import activate_instrumentation
        pipe = activate_instrumentation()
    """
    pipe = get_pipeline(api_key)
    pipe.patch_ailex_core()

    if verbose:
        d = metrics.dashboard_data()
        print(f"[AILEX Pipeline v2] Calls today: {d['calls_today']} | "
              f"Cache: {d['cache_rate']} | Avg conf: {d['avg_conf']}")
    return pipe


if __name__ == "__main__":
    print("InstrumentedPipeline — demo (no API key)")
    pipe = InstrumentedPipeline()
    pipe.patch_ailex_core()

    # Test cache
    print("\nTest: cache miss → hit")
    import ailex_core as core
    result1 = core._call_sync("DEX", "Fix the login bug", "bug")
    result2 = core._call_sync("DEX", "Fix the login bug", "bug")  # should be cache hit
    print(f"  Call 1: cache_hit={result1.get('cache_hit', False)}")
    print(f"  Call 2: cache_hit={result2.get('cache_hit', False)}")

    print("\nDashboard:")
    d = metrics.dashboard_data()
    for k, v in d.items():
        print(f"  {k:<22} {v}")
