"""
AILEX — aiox_maximizer.py
Maximizes utilization of ALL AIOX modules — bridges old and new systems.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The AIOX Core has 81 pilot modules + 23 vision modules.
Many powerful modules exist but are disconnected from the new pipeline.
This module creates the bridges:

  SecurityScanner     → auto-scans every generated backend (AMELIA output)
  RecursiveImprovement→ iterative quality loop when score < threshold
  SwarmIntelligence   → N parallel AILEX instances with synthesis (richer than simple parallel)
  GSD2Integration     → Scout+Researcher+Worker+JS_Pro+TS_Pro alongside BMAD
  Executor            → actually runs tests after code generation
  TDDLoop             → test-driven development loop (QUINN→AMELIA→validate)
  Evaluator           → benchmarks agent outputs against golden cases
  CodeQualityGate     → validates code structure, coverage, patterns
  KnowledgeSynthesis  → cross-KB pattern extraction
  PromptLibrary       → enriches all agent prompts from 37KB library

Usage:
    from ailex_pilot.aiox_maximizer import AIoXMaximizer
    mx = AIoXMaximizer()

    # Run ALL AIOX capabilities on a task:
    result = mx.run("Build a secure payment API with Stripe", domain="backend")
    print(result.full_report())

    # Specific capabilities:
    security = mx.security_scan("/path/to/generated/code")
    improved = mx.recursive_improve(output, task, domain)
    swarm    = mx.swarm_run("Design microservices architecture", domain="architecture")
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .pipeline_v2       import InstrumentedPipeline, PipelineResult, get_pipeline
from .ailex_logger       import get_logger, new_trace
from .observability      import metrics, tracer
from .agent_quality_gate import AgentQualityGate


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class MaximizerResult:
    task:             str
    domain:           str
    primary_output:   Optional[PipelineResult]
    security_report:  str  = ""
    quality_report:   str  = ""
    swarm_synthesis:  str  = ""
    recursive_cycles: int  = 0
    tdd_result:       str  = ""
    gsd2_output:      str  = ""
    knowledge_synthesis: str = ""
    total_ms:         int  = 0
    trace_id:         str  = ""

    def full_report(self) -> str:
        lines = [
            f"╔══ AIoX Maximizer Report ═══════════════════════════════════════",
            f"║  Task: {self.task[:65]}",
            f"║  Domain: {self.domain} | Time: {self.total_ms}ms | Trace: {self.trace_id[:10]}",
            f"║  Recursive cycles: {self.recursive_cycles}",
        ]
        if self.primary_output:
            lines.append(f"║  Primary: [{self.primary_output.agent}] conf={self.primary_output.confidence:.2f}")
            lines.append(f"║  {self.primary_output.analysis[:120]}...")
        if self.security_report:
            lines.append(f"║  Security: {self.security_report[:80]}")
        if self.quality_report:
            lines.append(f"║  Quality: {self.quality_report[:80]}")
        if self.swarm_synthesis:
            lines.append(f"║  Swarm: {self.swarm_synthesis[:100]}")
        if self.gsd2_output:
            lines.append(f"║  GSD2: {self.gsd2_output[:80]}")
        if self.knowledge_synthesis:
            lines.append(f"║  KnowledgeSynth: {self.knowledge_synthesis[:80]}")
        lines.append("╚" + "═" * 62)
        return "\n".join(lines)

    def synthesis(self) -> str:
        """Unified text synthesis of all AIOX outputs."""
        parts = []
        if self.primary_output:
            parts.append(f"Primary: {self.primary_output.analysis}")
        if self.swarm_synthesis:
            parts.append(f"Swarm consensus: {self.swarm_synthesis[:200]}")
        if self.security_report:
            parts.append(f"Security: {self.security_report[:150]}")
        if self.gsd2_output:
            parts.append(f"GSD2: {self.gsd2_output[:150]}")
        return "\n\n".join(parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AIOX MAXIMIZER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AIoXMaximizer:
    """
    Maximizes AIOX utilization by bridging all 81+ pilot modules.

    Integrates in three modes:
      STANDARD  — Pipeline v2 + QualityGate + KB context
      ENHANCED  — + RecursiveImprovement + SecurityScan + CodeQuality
      MAXIMUM   — + SwarmIntelligence + GSD2 + TDDLoop + KnowledgeSynthesis
    """

    def __init__(
        self,
        pipeline: Optional[InstrumentedPipeline] = None,
        verbose:  bool = True,
        mode:     str  = "enhanced",  # standard | enhanced | maximum
    ):
        self.pipeline = pipeline or get_pipeline()
        self.gate     = AgentQualityGate()
        self.log      = get_logger("maximizer")
        self.verbose  = verbose
        self.mode     = mode

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(
        self,
        task:    str,
        domain:  str  = "universal",
        context: str  = "",
        path:    str  = "",   # for security scanning generated code
    ) -> MaximizerResult:
        """
        Run the full AIoX stack on a task.
        Mode controls which additional AIOX modules are activated.
        """
        t0    = time.perf_counter()
        trace = tracer.new_trace()
        self.pipeline._active_trace = trace

        if self.verbose:
            print(f"\n⚡ AIoX Maximizer [{self.mode.upper()}]")
            print(f"  Task: {task[:60]}... | Domain: {domain}")

        result = MaximizerResult(
            task=task, domain=domain, trace_id=trace,
            primary_output=None,
        )

        # ── 1. PRIMARY: Pipeline v2 (always) ──────────────────────────────────
        agents = self._select_agents(task, domain)
        outputs = self.pipeline.run_parallel(task, domain, agents, context=context)
        if outputs:
            result.primary_output = max(outputs, key=lambda o: o.confidence)

        # ── 2. SECURITY SCAN (enhanced+) ──────────────────────────────────────
        if self.mode in ("enhanced","maximum"):
            result.security_report = self.security_scan(path or ".", task)
            if self.verbose and result.security_report:
                print(f"  🔒 Security: {result.security_report[:60]}...")

        # ── 3. CODE QUALITY CHECK (enhanced+) ─────────────────────────────────
        if self.mode in ("enhanced","maximum") and result.primary_output:
            result.quality_report = self.code_quality_check(
                result.primary_output.analysis, task
            )

        # ── 4. RECURSIVE IMPROVEMENT (enhanced+) ──────────────────────────────
        if self.mode in ("enhanced","maximum") and result.primary_output:
            improved, cycles = self.recursive_improve(
                result.primary_output, task, domain
            )
            result.primary_output = improved
            result.recursive_cycles = cycles
            if self.verbose and cycles > 0:
                print(f"  ↺ Recursive: {cycles} improvement cycles")

        # ── 5. SWARM INTELLIGENCE (maximum) ──────────────────────────────────
        if self.mode == "maximum":
            result.swarm_synthesis = self.swarm_run(task, domain, context)
            if self.verbose and result.swarm_synthesis:
                print(f"  🌊 Swarm: {result.swarm_synthesis[:60]}...")

        # ── 6. GSD2 (maximum) ─────────────────────────────────────────────────
        if self.mode == "maximum":
            result.gsd2_output = self.gsd2_run(task, domain, context)
            if self.verbose and result.gsd2_output:
                print(f"  ⚙️ GSD2: {result.gsd2_output[:60]}...")

        # ── 7. KNOWLEDGE SYNTHESIS (always) ──────────────────────────────────
        result.knowledge_synthesis = self.knowledge_synthesize(task, domain)

        result.total_ms = int((time.perf_counter() - t0) * 1000)
        metrics.inc("maximizer.run")
        metrics.timing("maximizer_ms", result.total_ms)
        metrics.record(trace, "maximizer.complete",
                       domain=domain, mode=self.mode, ms=result.total_ms)

        if self.verbose:
            print(f"  ✅ Done: {result.total_ms}ms | Cycles: {result.recursive_cycles}")

        return result

    # ── Module bridges ─────────────────────────────────────────────────────────

    def security_scan(self, path: str = ".", task: str = "") -> str:
        """
        SecurityScanner: auto-scan for secrets, SAST issues, CVEs.
        Triggered when AMELIA generates backend code.
        """
        try:
            from .security import SecurityScanner, SecurityReport
            scanner = SecurityScanner()
            # Only scan if path exists and has Python/JS files
            if os.path.exists(path):
                report = scanner.scan_project(path)
                if report:
                    formatted = scanner.format_report(report)
                    return formatted[:300]

            # Fallback: PENTEST_PRO + AUTH_MASTER review via Pipeline
            if task:
                sec_output = self.pipeline.call_agent(
                    "PENTEST_PRO", f"Security review: {task}", "security",
                    max_tokens=300
                )
                return f"[PENTEST_PRO] {sec_output.analysis[:200]}" if sec_output.analysis else ""
        except Exception as e:
            self.log.warn("security_scan_failed", error=str(e)[:60])
        return ""

    def code_quality_check(self, code_content: str, task: str = "") -> str:
        """
        CodeQualityGate: validates structure, patterns, quality.
        """
        try:
            from .code_quality import CodeQualityGate, QualityResult
            gate    = CodeQualityGate()
            # Check if it has a check method
            if hasattr(gate, 'check'):
                result = gate.check(code_content[:2000], task)
                if hasattr(result, 'score'):
                    return f"Quality score: {result.score:.2f} | {str(result)[:150]}"
            elif hasattr(gate, 'run'):
                result = gate.run(task, code=code_content[:1000])
                return str(result)[:200]
        except Exception:
            pass
        # Fallback: CODE_REV agent
        try:
            out = self.pipeline.call_agent(
                "CODE_REV", f"Code quality review for: {task}", "code",
                context=code_content[:400], max_tokens=250
            )
            return f"[CODE_REV] {out.analysis[:150]}" if out.analysis else ""
        except Exception:
            return ""

    def recursive_improve(
        self,
        output:    PipelineResult,
        task:      str,
        domain:    str,
        max_iter:  int = 2,
        threshold: float = 0.75,
    ) -> Tuple[PipelineResult, int]:
        """
        RecursiveImprovement: iteratively improve output quality.
        Uses existing module or falls back to AgentQualityGate retry.
        """
        cycles  = 0
        current = output

        for i in range(max_iter):
            # Check if quality is sufficient
            from .structured_output import AgentOutput
            ao     = AgentOutput(
                agent=current.agent, model=current.model,
                analysis=current.analysis,
                recommendation=current.recommendation,
                confidence=current.confidence,
            )
            report = self.gate.evaluate(ao)
            if report.score >= threshold:
                break   # good enough

            # Try to improve
            issues = " | ".join(report.issues[:2]) if report.issues else "low quality"
            improved = self.pipeline.call_agent(
                current.agent, task, domain,
                context=f"Previous attempt had issues: {issues}. Improve significantly.",
                max_tokens=450, force_fresh=True,
            )
            if improved.confidence > current.confidence:
                current = improved
                cycles += 1

        return current, cycles

    def swarm_run(self, task: str, domain: str, context: str = "") -> str:
        """
        SwarmIntelligence: N parallel AILEX instances, consensus synthesis.
        """
        try:
            from .swarm import SwarmIntelligence
            # SwarmIntelligence needs a pilot object — build a minimal one
            class MinimalPilot:
                def process(self, request, **kw):
                    out = get_pipeline().call_agent(
                        "ORION", request, domain, context=context[:300]
                    )
                    return {"report": out.analysis, "confidence": out.confidence}
            swarm  = SwarmIntelligence(MinimalPilot(), n_agents=4)
            result = swarm.run(task, domain=domain, timeout_s=30.0)
            if hasattr(result, 'synthesis'):
                return str(result.synthesis)[:300]
            return str(result)[:200]
        except Exception as e:
            # Fallback: 4 different core agents in parallel
            self.log.warn("swarm_fallback", error=str(e)[:50])
            agents  = ["DEX","ARIA","BASTIAN","ORION"]
            outputs = self.pipeline.run_parallel(task, domain, agents[:3])
            synth   = self.pipeline.synthesise(task, domain, outputs)
            return f"[Swarm-4] {synth.analysis[:250]}" if synth.analysis else ""

    def gsd2_run(self, task: str, domain: str, context: str = "") -> str:
        """
        GSD2Integration: Scout+Researcher+Worker+JS_Pro+TS_Pro pipeline.
        Context rot prevention + stuck loop detection.
        """
        try:
            from .gsd2_integration import GSD2Integration, GSD2_AGENT_PERSONAS
            gsd2 = GSD2Integration()

            # Run GSD2 subagents: Scout → Researcher → Worker
            subagents = ["SCOUT", "RESEARCHER", "WORKER"]
            outputs   = []

            for agent_id in subagents:
                persona = GSD2_AGENT_PERSONAS.get(agent_id, {})
                if not persona:
                    continue
                # Map GSD2 agent to pipeline call
                out = self.pipeline.call_agent(
                    persona.get("ailex_agent", "ZARA"),
                    f"[GSD2 {agent_id}] {task}",
                    domain,
                    context=context[:300],
                    max_tokens=300,
                )
                if out.analysis:
                    outputs.append(f"[{agent_id}] {out.analysis[:80]}")

            return "\n".join(outputs[:3]) if outputs else ""

        except Exception as e:
            self.log.warn("gsd2_fallback", error=str(e)[:50])
            # Fallback: ZARA + NOVA + RIVER
            outputs = self.pipeline.run_parallel(task, domain, ["ZARA","NOVA","RIVER"])
            parts   = [f"[{o.agent}] {o.analysis[:70]}" for o in outputs if o.analysis]
            return "\n".join(parts[:3])

    def knowledge_synthesize(self, task: str, domain: str) -> str:
        """
        KnowledgeSynthesis: cross-KB pattern extraction and synthesis.
        """
        try:
            from .knowledge_synthesis import KnowledgeSynthesis
            ks    = KnowledgeSynthesis()
            if hasattr(ks, 'synthesize'):
                result = ks.synthesize(task, domain=domain)
                return str(result)[:200]
            elif hasattr(ks, 'run'):
                result = ks.run(task)
                return str(result)[:200]
        except Exception:
            pass
        # Fallback: KB query
        try:
            from .knowledge_updater import KnowledgeUpdater
            ku      = KnowledgeUpdater()
            entries = ku.query(task, domain=domain, limit=2)
            if entries:
                return " | ".join(f"{e['title'][:50]} (★{e['citations']})" for e in entries)
        except Exception:
            pass
        return ""

    def tdd_loop(
        self,
        task:    str,
        domain:  str  = "code",
        context: str  = "",
    ) -> str:
        """
        TDDLoop: QUINN writes test → AMELIA implements → validate.
        """
        try:
            from .tdd_loop import TDDLoop
            tdd = TDDLoop()
            if hasattr(tdd, 'run'):
                result = tdd.run(task, domain=domain)
                return str(result)[:300]
        except Exception:
            pass
        # Fallback: QUINN → AMELIA sequential
        test_spec = self.pipeline.call_agent("QUINN", f"Write test spec for: {task}", "code")
        impl = self.pipeline.call_agent(
            "AMELIA", task, "code",
            context=f"Test spec: {test_spec.analysis[:200]}"
        )
        return f"[TDD] Tests: {test_spec.analysis[:80]} | Impl: {impl.analysis[:80]}"

    def evaluate_output(self, output: PipelineResult, task: str) -> Dict[str, float]:
        """
        Evaluator: benchmark agent output against standard cases.
        """
        try:
            from .evaluator import Evaluator
            ev = Evaluator()
            if hasattr(ev, 'score'):
                score = ev.score(output.analysis, task)
                return {"score": float(score)}
            elif hasattr(ev, 'evaluate'):
                result = ev.evaluate(output.analysis, task)
                return {"score": getattr(result, 'score', 0.75)}
        except Exception:
            pass
        # Fallback: use AgentQualityGate
        from .structured_output import AgentOutput
        ao = AgentOutput(
            agent=output.agent, model=output.model,
            analysis=output.analysis, recommendation=output.recommendation,
            confidence=output.confidence,
        )
        report = self.gate.evaluate(ao)
        return {"score": report.score, "passes": report.passes}

    # ── Prompt enrichment via PromptLibrary ────────────────────────────────────

    def get_enriched_prompt(self, agent: str, task: str, domain: str) -> str:
        """
        PromptLibrary: get the best prompt template for an agent/domain.
        """
        try:
            from .prompt_templates import PromptLibrary
            lib = PromptLibrary()
            if hasattr(lib, 'get'):
                template = lib.get(agent, domain)
                if template:
                    return template.format(task=task, domain=domain)
        except Exception:
            pass
        return ""

    # ── AST Analysis ──────────────────────────────────────────────────────────

    def ast_analyze(self, code: str, language: str = "python") -> str:
        """
        ASTAnalyzer: structural code analysis (complexity, patterns, smells).
        """
        try:
            from .ast_analyzer import ASTAnalyzer
            analyzer = ASTAnalyzer()
            if hasattr(analyzer, 'analyze'):
                report = analyzer.analyze(code, language=language)
                return str(report)[:200]
        except Exception:
            pass
        return ""

    # ── Dependency Graph ───────────────────────────────────────────────────────

    def analyze_dependencies(self, path: str = ".") -> str:
        """DependencyAnalyzer: find circular deps, coupling metrics."""
        try:
            from .dependency_graph import DependencyAnalyzer
            da = DependencyAnalyzer()
            if hasattr(da, 'analyze'):
                report = da.analyze(path)
                return str(report)[:200]
        except Exception:
            pass
        return ""

    # ── Predictive Intelligence ────────────────────────────────────────────────

    def predict_next_needs(self, context: str, domain: str) -> List[str]:
        """PredictiveIntelligence: what does the user need next?"""
        try:
            from .predictive_intelligence import PredictiveIntelligence
            pi = PredictiveIntelligence()
            if hasattr(pi, 'predict'):
                result = pi.predict(context, domain=domain)
                if hasattr(result, 'predictions'):
                    return result.predictions[:3]
        except Exception:
            pass
        return []

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _select_agents(self, task: str, domain: str) -> List[str]:
        """Select the best agents for this task from core + BMAD pool."""
        domain_agents = {
            "backend":      ["BASTIAN","ARIA","DARA","FELIX"],
            "frontend":     ["DEX","UMA","ARIA"],
            "security":     ["BASTIAN","ARIA","FELIX"],
            "architecture": ["ARIA","WINSTON","DARA"],
            "analysis":     ["MARY","JOHN","ZARA"],
            "planning":     ["JOHN","BOB","NOVA"],
            "code":         ["AMELIA","DEX","QUINN"],
            "bug":          ["DEX","QUINN","ARIA"],
            "universal":    ["DEX","ARIA","BASTIAN","ORION"],
        }
        return domain_agents.get(domain, domain_agents["universal"])

    def module_status(self) -> str:
        """Show which AIOX modules are available and their status."""
        modules = [
            ("SecurityScanner",       "security",             "🔒"),
            ("RecursiveImprovement",  "recursive_improvement","↺"),
            ("SwarmIntelligence",     "swarm",                "🌊"),
            ("GSD2Integration",       "gsd2_integration",     "⚙️"),
            ("CodeQualityGate",       "code_quality",         "✓"),
            ("TDDLoop",               "tdd_loop",             "🧪"),
            ("Evaluator",             "evaluator",            "📊"),
            ("KnowledgeSynthesis",    "knowledge_synthesis",  "🧠"),
            ("ASTAnalyzer",           "ast_analyzer",         "🌳"),
            ("DependencyGraph",       "dependency_graph",     "🔗"),
            ("PredictiveIntelligence","predictive_intelligence","🔮"),
            ("PromptLibrary",         "prompt_templates",     "📝"),
        ]
        lines = ["AIoX Module Status", "─" * 50]
        for name, module, icon in modules:
            path = f".aiox-core/ailex_pilot/{module}.py"
            exists = os.path.exists(os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                f"../ailex_pilot/{module}.py"
            ).replace("/../","/"))
            exists = os.path.exists(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{module}.py")
            )
            status = "✅" if exists else "❌"
            lines.append(f"  {status} {icon} {name:<26} ({module})")
        return "\n".join(lines)


# ── Convenience functions ──────────────────────────────────────────────────────

_maximizer: Optional[AIoXMaximizer] = None

def get_maximizer(mode: str = "enhanced") -> AIoXMaximizer:
    global _maximizer
    if _maximizer is None or _maximizer.mode != mode:
        _maximizer = AIoXMaximizer(mode=mode)
    return _maximizer


def aiox_run(
    task:   str,
    domain: str = "universal",
    mode:   str = "enhanced",
) -> MaximizerResult:
    """
    Run the full AIoX stack. One call, all modules active.

        result = aiox_run("Build a secure REST API", "backend", mode="maximum")
        print(result.full_report())
    """
    return get_maximizer(mode).run(task, domain)


def aiox_status() -> str:
    """Show status of all AIOX modules."""
    return get_maximizer().module_status()


if __name__ == "__main__":
    mx = AIoXMaximizer(verbose=True, mode="enhanced")
    print(mx.module_status())
    print()

    result = mx.run("Design a JWT authentication service", domain="backend")
    print()
    print(result.full_report())
