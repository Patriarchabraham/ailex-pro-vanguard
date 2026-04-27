"""
AILEX — wave_orchestrator.py
Multi-wave agent orchestration: agents separated by domain/theme,
each wave feeds context into the next, ORION synthesises at the end.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Architecture:
  Each domain has a predefined sequence of WAVES.
  Each wave is a group of agents with a specific THEME/role.
  The output of wave N becomes context for wave N+1.
  ORION synthesises all waves into a final output.

  Wave 1 (RESEARCH)     → gather knowledge, establish context
  Wave 2 (ANALYSIS)     → architecture, data model, risk assessment
  Wave 3 (IMPLEMENTATION)→ code, implementation, tools
  Wave 4 (QUALITY)      → tests, security, edge cases
  Wave 5 (SYNTHESIS)    → ORION unifies all waves into final answer

Domain-specific wave configs:
  frontend    — Design → Layout → Implementation → Quality → Synthesis
  backend     — Architecture → Database → API → Security → Quality → Synthesis
  fullstack   — Research → Frontend → Backend → Integration → Quality → Synthesis
  analysis    — Research → Data → Insights → Recommendations → Synthesis
  security    — Threat Model → Attack Surface → Defence → Audit → Synthesis
  mobile      — UX → Architecture → Implementation → Performance → Synthesis
  devops      — Infrastructure → CI/CD → Monitoring → Security → Synthesis
  creative    — Vision → Design → Content → Motion → Synthesis
  universal   — All waves, all agents

Usage:
    from ailex_pilot.wave_orchestrator import WaveOrchestrator
    orch = WaveOrchestrator()

    # Run all waves for a task:
    result = orch.run("Build a JWT auth system for FastAPI", domain="backend")
    print(result.final_synthesis)
    print(result.wave_by_wave_summary())

    # Single domain wave:
    result = orch.run("Design the login UX flow", domain="frontend")

    # Custom wave config:
    result = orch.run("Analyse security of auth module", domain="security")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .pipeline_v2    import InstrumentedPipeline, PipelineResult, get_pipeline
from .ailex_logger   import get_logger, new_trace
from .observability  import metrics, tracer


# ── Wave definition ────────────────────────────────────────────────────────────

@dataclass
class Wave:
    name:        str          # "RESEARCH", "ANALYSIS", ...
    theme:       str          # Short description of what this wave does
    agents:      List[str]    # Agent IDs to run in this wave
    max_tokens:  int = 400    # Tokens per agent call
    parallel:    bool = True  # Run agents in parallel or sequential
    required:    bool = True  # If False, skip if previous wave confidence is high


@dataclass
class WaveResult:
    wave_name:   str
    agents:      List[str]
    outputs:     List[PipelineResult]
    duration_ms: int
    avg_confidence: float
    best_output: Optional[PipelineResult]
    summary:     str          # Aggregated text from all agents in this wave

    @property
    def insights(self) -> str:
        """Key insights from this wave for context injection."""
        lines = [f"[{self.wave_name}]"]
        for out in self.outputs:
            if out.analysis:
                lines.append(f"  {out.agent}: {out.analysis[:120]}")
        return "\n".join(lines)


@dataclass
class OrchestrationResult:
    task:            str
    domain:          str
    waves:           List[WaveResult]
    final_synthesis: str
    total_ms:        int
    trace_id:        str
    confidence:      float
    halted_early:    bool
    halt_reason:     str = ""

    def wave_by_wave_summary(self) -> str:
        """Rich text summary of what each wave contributed."""
        lines = [
            f"Wave Orchestration: {self.domain.upper()} — {self.task[:60]}",
            f"Trace: {self.trace_id} | Duration: {self.total_ms}ms | Confidence: {self.confidence:.3f}",
            "─" * 65,
        ]
        for wr in self.waves:
            agents_str = " + ".join(wr.agents)
            lines.append(
                f"\n◆ Wave {self.waves.index(wr)+1}: {wr.wave_name}  [{agents_str}]"
                f"  ({wr.duration_ms}ms, conf={wr.avg_confidence:.2f})"
            )
            lines.append(f"  Theme: {wr.theme}")
            for out in wr.outputs:
                lines.append(f"  [{out.agent}] {(out.analysis or '')[:90]}")
        lines.append("\n" + "─" * 65)
        lines.append(f"\n◆ ORION SYNTHESIS:\n{self.final_synthesis}")
        if self.halted_early:
            lines.append(f"\n⚡ Halted early: {self.halt_reason}")
        return "\n".join(lines)

    def to_context(self) -> str:
        """Extract context string for injection into subsequent prompts."""
        parts = []
        for wr in self.waves:
            parts.append(wr.insights)
        parts.append(f"[SYNTHESIS]\n{self.final_synthesis[:400]}")
        return "\n\n".join(parts)


# ── Domain Wave Configs ────────────────────────────────────────────────────────

DOMAIN_WAVES: Dict[str, List[Wave]] = {

    # ── FRONTEND ──────────────────────────────────────────────────────────────
    "frontend": [
        Wave("RESEARCH",      "Understand requirements, gather UX patterns",
             ["ZARA"],         max_tokens=300),
        Wave("DESIGN",        "UX flow, component hierarchy, visual system",
             ["UMA"],          max_tokens=400),
        Wave("ARCHITECTURE",  "Component structure, state management, routing",
             ["ARIA", "DEX"],  max_tokens=400),
        Wave("IMPLEMENTATION","Code implementation, hooks, styling, animation",
             ["DEX"],          max_tokens=500),
        Wave("QUALITY",       "Tests, accessibility, performance, edge cases",
             ["QUINN"],        max_tokens=350),
        Wave("SYNTHESIS",     "ORION final recommendation",
             ["ORION"],        max_tokens=450),
    ],

    # ── BACKEND ───────────────────────────────────────────────────────────────
    "backend": [
        Wave("RESEARCH",      "Gather requirements, existing patterns, best practices",
             ["ZARA"],         max_tokens=300),
        Wave("ARCHITECTURE",  "API design, service boundaries, patterns",
             ["ARIA"],         max_tokens=400),
        Wave("DATABASE",      "Schema design, indexes, migrations, queries",
             ["DARA"],         max_tokens=400),
        Wave("IMPLEMENTATION","Endpoints, auth, validation, error handling",
             ["BASTIAN"],      max_tokens=500),
        Wave("SECURITY",      "OWASP checks, auth flows, input validation",
             ["BASTIAN", "QUINN"], max_tokens=350),
        Wave("DEVOPS",        "Docker, CI/CD, env config, deployment",
             ["FELIX"],        max_tokens=350),
        Wave("SYNTHESIS",     "ORION final recommendation",
             ["ORION"],        max_tokens=500),
    ],

    # ── FULLSTACK ─────────────────────────────────────────────────────────────
    "fullstack": [
        Wave("RESEARCH",      "Gather requirements, tech stack decision",
             ["ZARA", "ARIA"], max_tokens=350),
        Wave("ARCHITECTURE",  "Overall system design, API contract, DB schema",
             ["ARIA", "DARA"], max_tokens=450),
        Wave("FRONTEND",      "UI components, state, routing, UX",
             ["DEX", "UMA"],   max_tokens=450),
        Wave("BACKEND",       "API endpoints, auth, validation, DB queries",
             ["BASTIAN"],      max_tokens=500),
        Wave("INTEGRATION",   "Frontend-backend contract, error handling, loading states",
             ["DEX", "BASTIAN"], max_tokens=400),
        Wave("QUALITY",       "Tests, security, performance, edge cases",
             ["QUINN", "FELIX"], max_tokens=400),
        Wave("SYNTHESIS",     "ORION final unified implementation plan",
             ["ORION"],        max_tokens=550),
    ],

    # ── CODE / BUG ────────────────────────────────────────────────────────────
    "code": [
        Wave("DIAGNOSIS",     "Root cause analysis, reproduce the issue",
             ["DEX", "QUINN"], max_tokens=350),
        Wave("ANALYSIS",      "Architecture impact, risk of change",
             ["ARIA"],         max_tokens=350),
        Wave("IMPLEMENTATION","Fix implementation, test cases",
             ["DEX"],          max_tokens=500),
        Wave("VERIFICATION",  "Edge cases, regression risk, test coverage",
             ["QUINN"],        max_tokens=350),
        Wave("SYNTHESIS",     "ORION final fix recommendation",
             ["ORION"],        max_tokens=400),
    ],

    # ── BUG ───────────────────────────────────────────────────────────────────
    "bug": [
        Wave("TRIAGE",        "Identify symptom, isolate root cause (5 WHYs)",
             ["DEX", "QUINN"], max_tokens=350),
        Wave("DIAGNOSIS",     "Trace data flow, find broken invariant",
             ["ARIA", "DEX"],  max_tokens=400),
        Wave("FIX",           "Implement minimal correct fix, no side effects",
             ["DEX"],          max_tokens=500),
        Wave("REGRESSION",    "Test coverage, what else could break",
             ["QUINN"],        max_tokens=300),
        Wave("SYNTHESIS",     "ORION: root cause + fix + prevention",
             ["ORION"],        max_tokens=400),
    ],

    # ── ARCHITECTURE ──────────────────────────────────────────────────────────
    "architecture": [
        Wave("REQUIREMENTS",  "Functional + non-functional requirements",
             ["NOVA", "ZARA"], max_tokens=350),
        Wave("DESIGN",        "High-level architecture, component decomposition",
             ["ARIA"],         max_tokens=500),
        Wave("DATA",          "Data model, storage, consistency, migrations",
             ["DARA"],         max_tokens=400),
        Wave("RESILIENCE",    "Failure modes, circuit breakers, fallbacks",
             ["FELIX", "BASTIAN"], max_tokens=400),
        Wave("TRADE_OFFS",    "CAP theorem, build vs buy, complexity vs simplicity",
             ["ARIA", "NOVA"], max_tokens=400),
        Wave("SYNTHESIS",     "ORION: recommended architecture with rationale",
             ["ORION"],        max_tokens=600),
    ],

    # ── SECURITY ──────────────────────────────────────────────────────────────
    "security": [
        Wave("THREAT_MODEL",  "Identify assets, threats, attack vectors (STRIDE)",
             ["BASTIAN"],      max_tokens=400),
        Wave("ATTACK_SURFACE","Map entry points, data flows, trust boundaries",
             ["BASTIAN", "ARIA"], max_tokens=400),
        Wave("OWASP_CHECK",   "OWASP Top 10 review: injection, auth, XSS, etc.",
             ["BASTIAN", "QUINN"], max_tokens=400),
        Wave("DEFENCE",       "Security controls, encryption, rate limiting, logging",
             ["BASTIAN", "FELIX"], max_tokens=450),
        Wave("SYNTHESIS",     "ORION: security assessment + priority fixes",
             ["ORION"],        max_tokens=500),
    ],

    # ── PERFORMANCE ───────────────────────────────────────────────────────────
    "performance": [
        Wave("PROFILING",     "Identify bottlenecks, measure baselines",
             ["DEX", "FELIX"], max_tokens=350),
        Wave("DATABASE",      "Query optimization, indexes, N+1 detection",
             ["DARA"],         max_tokens=400),
        Wave("FRONTEND",      "Bundle size, lazy loading, Core Web Vitals",
             ["DEX", "UMA"],   max_tokens=400),
        Wave("INFRASTRUCTURE","Caching, CDN, horizontal scaling",
             ["FELIX"],        max_tokens=350),
        Wave("SYNTHESIS",     "ORION: prioritised performance improvements",
             ["ORION"],        max_tokens=450),
    ],

    # ── FEATURE ───────────────────────────────────────────────────────────────
    "feature": [
        Wave("DISCOVERY",     "User need, business value, acceptance criteria",
             ["NOVA", "ZARA"], max_tokens=350),
        Wave("UX_DESIGN",     "User flow, wireframe, interaction design",
             ["UMA"],          max_tokens=400),
        Wave("ARCHITECTURE",  "Technical design, API contract, DB changes",
             ["ARIA", "DARA"], max_tokens=450),
        Wave("IMPLEMENTATION","Frontend + backend code",
             ["DEX", "BASTIAN"], max_tokens=500),
        Wave("TESTING",       "Test strategy, edge cases, acceptance tests",
             ["QUINN"],        max_tokens=350),
        Wave("DEPLOYMENT",    "Feature flags, rollout, monitoring",
             ["FELIX"],        max_tokens=300),
        Wave("SYNTHESIS",     "ORION: complete implementation plan",
             ["ORION"],        max_tokens=550),
    ],

    # ── DEPLOY ────────────────────────────────────────────────────────────────
    "deploy": [
        Wave("PRE_CHECK",     "Build validity, test pass, env vars",
             ["QUINN", "FELIX"], max_tokens=350),
        Wave("RISK",          "Breaking changes, rollback plan, health checks",
             ["FELIX", "ARIA"], max_tokens=400),
        Wave("EXECUTION",     "Deploy steps, smoke tests, monitoring",
             ["FELIX"],        max_tokens=400),
        Wave("SYNTHESIS",     "ORION: deployment plan with rollback",
             ["ORION"],        max_tokens=400),
    ],

    # ── ANALYSIS ──────────────────────────────────────────────────────────────
    "analysis": [
        Wave("DATA_GATHER",   "Collect facts, metrics, observations",
             ["ZARA", "DARA"], max_tokens=350),
        Wave("PATTERN",       "Find patterns, correlations, anomalies",
             ["DARA", "ARIA"], max_tokens=400),
        Wave("INSIGHT",       "Business implications, root causes",
             ["NOVA", "ZARA"], max_tokens=400),
        Wave("RECOMMENDATION","Actionable next steps with priority",
             ["NOVA", "KAI"],  max_tokens=400),
        Wave("SYNTHESIS",     "ORION: complete analysis report",
             ["ORION"],        max_tokens=500),
    ],

    # ── CREATIVE / DESIGN ─────────────────────────────────────────────────────
    "creative": [
        Wave("VISION",        "Aesthetic intent, emotional register, reference points",
             ["UMA"],          max_tokens=350),
        Wave("DESIGN_SYSTEM", "Colors, typography, spacing, components",
             ["UMA", "DEX"],   max_tokens=400),
        Wave("MOTION",        "Animation strategy, transitions, interactions",
             ["DEX"],          max_tokens=400),
        Wave("CONTENT",       "Copy, imagery, voice, tone",
             ["NOVA", "ZARA"], max_tokens=350),
        Wave("SYNTHESIS",     "ORION: complete design brief",
             ["ORION"],        max_tokens=450),
    ],

    # ── UNIVERSAL (all domains) ───────────────────────────────────────────────
    "universal": [
        Wave("RESEARCH",      "Broad context, facts, best practices",
             ["ZARA"],         max_tokens=300),
        Wave("ANALYSIS",      "Architecture, data, security, UX perspective",
             ["ARIA", "DARA", "UMA"], max_tokens=400),
        Wave("IMPLEMENTATION","Code, deployment, operations",
             ["DEX", "BASTIAN", "FELIX"], max_tokens=450),
        Wave("QUALITY",       "Tests, security, performance",
             ["QUINN"],        max_tokens=350),
        Wave("SYNTHESIS",     "ORION: unified multi-domain recommendation",
             ["ORION"],        max_tokens=600),
    ],
}

# Alias map
DOMAIN_ALIASES: Dict[str, str] = {
    "front":     "frontend",
    "back":      "backend",
    "full":      "fullstack",
    "fix":       "bug",
    "test":      "code",
    "arch":      "architecture",
    "sec":       "security",
    "perf":      "performance",
    "speed":     "performance",
    "feat":      "feature",
    "create":    "creative",
    "design":    "creative",
    "all":       "universal",
}


# ── Main orchestrator ─────────────────────────────────────────────────────────

class WaveOrchestrator:
    """
    Multi-wave agent orchestration.
    Runs agents in sequential domain-specific waves,
    each wave feeding context into the next.
    ORION synthesises all waves at the end.

    Example:
        orch = WaveOrchestrator()
        result = orch.run("Build a user authentication system", "backend")
        print(result.wave_by_wave_summary())
    """

    HALT_CONFIDENCE = 0.97   # Stop early if confidence is very high
    MIN_WAVES       = 2      # Always run at least N waves

    def __init__(
        self,
        pipeline:   Optional[InstrumentedPipeline] = None,
        verbose:    bool = True,
        stream:     bool = False,
    ):
        self.pipeline = pipeline or get_pipeline()
        self.verbose  = verbose
        self.stream   = stream
        self.log      = get_logger("wave_orchestrator")

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        task:       str,
        domain:     str  = "universal",
        context:    str  = "",
        max_waves:  Optional[int] = None,
    ) -> OrchestrationResult:
        """
        Run the full wave orchestration for a task in a given domain.

        Args:
            task:      The task to solve
            domain:    Domain key (see DOMAIN_WAVES) — "backend", "frontend", etc.
            context:   Additional context to inject into all waves
            max_waves: Limit number of waves (None = all)

        Returns:
            OrchestrationResult with wave-by-wave analysis + ORION synthesis
        """
        # Resolve domain alias
        domain = DOMAIN_ALIASES.get(domain, domain)
        waves  = DOMAIN_WAVES.get(domain, DOMAIN_WAVES["universal"])
        if max_waves:
            waves = waves[:max_waves]

        t0 = time.perf_counter()
        trace = tracer.new_trace()
        self.pipeline._active_trace = trace

        self.log.info("wave_start", trace=trace, domain=domain,
                      waves=len(waves), task=task[:60])
        metrics.inc(f"wave.start.{domain}")

        if self.verbose:
            print(f"\n⚡ AILEX Wave Orchestrator")
            print(f"  Domain: {domain.upper()} | Waves: {len(waves)} | Task: {task[:55]}...")
            print(f"  Trace: {trace}\n")

        wave_results: List[WaveResult] = []
        accumulated_context = context
        halted_early = False
        halt_reason  = ""

        for i, wave in enumerate(waves):
            wave_t0 = time.perf_counter()

            # Build context from previous waves
            wave_context = self._build_wave_context(
                task, accumulated_context, wave_results, wave
            )

            if self.verbose:
                agents_str = " + ".join(wave.agents)
                print(f"  ▶ Wave {i+1}/{len(waves)}: {wave.name}")
                print(f"    Theme: {wave.theme}")
                print(f"    Agents: {agents_str}")

            # Run this wave's agents
            if wave.parallel and len(wave.agents) > 1:
                outputs = self.pipeline.run_parallel(
                    task=task, domain=domain,
                    agents=wave.agents,
                    context=wave_context,
                )
            else:
                outputs = []
                for agent in wave.agents:
                    out = self.pipeline.call_agent(
                        agent, task, domain,
                        context=wave_context,
                        max_tokens=wave.max_tokens,
                    )
                    outputs.append(out)

            # Build wave result
            dur_ms = int((time.perf_counter() - wave_t0) * 1000)
            avg_conf = sum(o.confidence for o in outputs) / max(1, len(outputs))
            best = max(outputs, key=lambda o: o.confidence) if outputs else None
            summary = self._summarise_wave(wave, outputs)

            wr = WaveResult(
                wave_name       = wave.name,
                agents          = wave.agents,
                outputs         = outputs,
                duration_ms     = dur_ms,
                avg_confidence  = avg_conf,
                best_output     = best,
                summary         = summary,
            )
            wave_results.append(wr)

            # Accumulate context for next wave
            accumulated_context = f"{accumulated_context}\n\n{wr.insights}".strip()

            if self.verbose:
                print(f"    ✓ Done in {dur_ms}ms | conf={avg_conf:.2f}")
                if best:
                    print(f"    ↳ Best ({best.agent}): {best.analysis[:80]}...")

            # Early halt check (only after MIN_WAVES)
            if (i + 1) >= self.MIN_WAVES and avg_conf >= self.HALT_CONFIDENCE:
                # Skip remaining waves except SYNTHESIS
                remaining_required = [w for w in waves[i+1:] if w.name == "SYNTHESIS"]
                if remaining_required:
                    waves = waves[:i+1] + remaining_required
                halted_early = True
                halt_reason  = f"Wave {i+1} confidence {avg_conf:.3f} ≥ {self.HALT_CONFIDENCE}"
                if self.verbose:
                    print(f"\n  ⚡ Early halt: {halt_reason}")
                break

            metrics.record(trace, f"wave.complete.{wave.name}",
                           domain=domain, agents=len(outputs), ms=dur_ms,
                           confidence=avg_conf)

        # Final synthesis from ORION
        final_synthesis = self._final_synthesis(task, domain, wave_results)

        total_ms    = int((time.perf_counter() - t0) * 1000)
        all_confs   = [o.confidence for wr in wave_results for o in wr.outputs]
        global_conf = sum(all_confs) / max(1, len(all_confs))

        result = OrchestrationResult(
            task             = task,
            domain           = domain,
            waves            = wave_results,
            final_synthesis  = final_synthesis,
            total_ms         = total_ms,
            trace_id         = trace,
            confidence       = global_conf,
            halted_early     = halted_early,
            halt_reason      = halt_reason,
        )

        self.log.info("wave_done", trace=trace, domain=domain,
                      waves_run=len(wave_results), total_ms=total_ms,
                      confidence=global_conf, halted=halted_early)
        metrics.inc("wave.completed")
        metrics.timing("wave_total_ms", total_ms)

        if self.verbose:
            print(f"\n  ✅ Orchestration complete")
            print(f"     Waves: {len(wave_results)} | Time: {total_ms}ms | Confidence: {global_conf:.3f}")
            print(f"\n  ORION SYNTHESIS:")
            print(f"  {final_synthesis[:300]}...")

        return result

    def list_domains(self) -> List[str]:
        return sorted(DOMAIN_WAVES.keys())

    def get_waves(self, domain: str) -> List[Wave]:
        domain = DOMAIN_ALIASES.get(domain, domain)
        return DOMAIN_WAVES.get(domain, DOMAIN_WAVES["universal"])

    def describe(self) -> str:
        lines = ["WaveOrchestrator — Domain Wave Configurations", "─" * 60]
        for domain, waves in DOMAIN_WAVES.items():
            wave_names = " → ".join(w.name for w in waves)
            lines.append(f"  {domain:<14} {wave_names}")
        return "\n".join(lines)

    # ── Private ────────────────────────────────────────────────────────────────

    def _build_wave_context(
        self,
        task:          str,
        base_context:  str,
        prev_waves:    List[WaveResult],
        current_wave:  Wave,
    ) -> str:
        parts = []
        if base_context:
            parts.append(f"Context: {base_context[:200]}")

        # Add insights from previous waves
        for wr in prev_waves[-3:]:  # last 3 waves only
            parts.append(wr.insights)

        # Add research KB context for this domain
        try:
            from .research_scheduler import get_scheduler
            sched = get_scheduler()
            kb_ctx = sched.get_context(current_wave.name.lower()[:8], max_entries=2)
            if kb_ctx and "No knowledge" not in kb_ctx:
                parts.append(kb_ctx[:200])
        except Exception:
            pass

        return "\n\n".join(parts)[:800]

    def _summarise_wave(self, wave: Wave, outputs: List[PipelineResult]) -> str:
        """Build a concise text summary of a wave's outputs."""
        lines = [f"Wave {wave.name} ({wave.theme}):"]
        for out in outputs:
            if out.analysis:
                lines.append(f"  [{out.agent}] {out.analysis[:100]}")
            if out.risk:
                lines.append(f"  [{out.agent}·risk] {out.risk[:80]}")
        return "\n".join(lines)

    def _final_synthesis(
        self,
        task:        str,
        domain:      str,
        wave_results: List[WaveResult],
    ) -> str:
        """
        Get ORION's final synthesis of all waves.
        Checks if last wave was already ORION synthesis.
        """
        # Check if the last wave was ORION SYNTHESIS
        last_wave = wave_results[-1] if wave_results else None
        if last_wave and "ORION" in last_wave.agents and "SYNTHESIS" in last_wave.wave_name:
            # Already synthesised — return ORION's output
            orion_out = last_wave.best_output
            if orion_out and orion_out.analysis:
                return f"{orion_out.analysis}\n\nRecommendation: {orion_out.recommendation}"

        # Run explicit synthesis
        context = "\n\n".join(wr.insights for wr in wave_results)
        synth = self.pipeline.call_agent(
            "ORION", task, domain,
            context=f"Wave results:\n{context[:600]}",
            max_tokens=600,
        )
        if synth.analysis:
            parts = [synth.analysis]
            if synth.recommendation:
                parts.append(f"\n→ Recommendation: {synth.recommendation}")
            if synth.risk:
                parts.append(f"\n→ Risk: {synth.risk}")
            return "\n".join(parts)
        return "See wave-by-wave analysis above."


# ── Global orchestrator + convenience ─────────────────────────────────────────

_orchestrator: Optional[WaveOrchestrator] = None

def get_orchestrator() -> WaveOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WaveOrchestrator()
    return _orchestrator


def wave_run(
    task:    str,
    domain:  str = "universal",
    context: str = "",
    verbose: bool = True,
) -> OrchestrationResult:
    """
    Run wave orchestration in one call.

        result = wave_run("Add Redis caching to FastAPI", "backend")
        print(result.wave_by_wave_summary())
    """
    return get_orchestrator().run(task, domain, context)


def wave_context(result: OrchestrationResult) -> str:
    """Extract context from a wave result for injection into next call."""
    return result.to_context()


if __name__ == "__main__":
    print(WaveOrchestrator().describe())
    print()

    orch = WaveOrchestrator(verbose=True)

    print("Demo: backend wave (no API key — fallback mode)")
    result = orch.run(
        "Build a JWT authentication system with refresh tokens",
        domain="backend",
        max_waves=3,   # Quick demo: only first 3 waves
    )
    print()
    print("Wave-by-wave summary:")
    print(result.wave_by_wave_summary())
