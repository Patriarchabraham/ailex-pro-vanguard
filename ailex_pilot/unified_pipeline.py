"""
AILEX — unified_pipeline.py
AILEX + BMAD + GSD2 unified execution engine.

The three systems are complementary:
  AILEX  — Cognitive depth: 33 agents, 17 neural layers, adaptive ACT reasoning
  BMAD   — Structured process: 4-phase lifecycle, artifact-driven, sprint stories
  GSD2   — Context management: rot prevention, spec-driven, multi-provider, stuck detection

Unified pipeline:
  1. GSD2 Spec    — Structure the problem clearly before any execution
  2. BMAD Phase   — Select appropriate lifecycle phase for the task type
  3. AILEX Depth  — Execute with full cognitive depth (neural layers, CHAOS, etc.)
  4. GSD2 Context — Prevent context rot between tasks, detect stuck loops
  5. BMAD Artifact— Generate verifiable artifacts at each phase output
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .bmad_integration import BMADIntegration, BMAD_PHASES, BMADArtifact, BMADSprintStory
from .gsd2_integration  import GSD2Integration, GSD2Spec, GSD2Task, ContextRotDetector


@dataclass
class UnifiedResult:
    request:          str
    mode:             str          # "ailex" | "bmad" | "gsd2" | "unified"
    spec:             Optional[GSD2Spec]      = None
    artifacts:        List[BMADArtifact]      = field(default_factory=list)
    stories:          List[BMADSprintStory]   = field(default_factory=list)
    tasks:            List[GSD2Task]          = field(default_factory=list)
    ailex_report:     str = ""
    confidence:       float = 0.0
    total_tokens:     int   = 0
    duration_s:       float = 0.0
    context_cleared:  int   = 0    # times GSD2 cleared context
    agents_used:      List[str] = field(default_factory=list)
    phase:            str = ""


class UnifiedPipeline:
    """
    Unified AILEX + BMAD + GSD2 pipeline.

    Routing logic:
    - Simple task (bug, docs, refactor) → GSD2 quick flow + AILEX depth
    - Feature/product work → BMAD planning phase + AILEX execution
    - Complex systems → Full BMAD lifecycle + AILEX per-phase + GSD2 context mgmt
    - Research → GSD2 RESEARCHER + AILEX VEGA/NEWTON
    - Any → Stuck loop detection, context rot prevention always active
    """

    def __init__(
        self,
        pilot:    Any = None,
        provider: str = "anthropic",
        auto_mode: str = "smart",   # "smart" | "ailex_only" | "bmad_first" | "gsd2_first"
    ):
        self.pilot     = pilot
        self.auto_mode = auto_mode
        self.bmad      = BMADIntegration(client=getattr(pilot, "_ailex", None) and
                                          getattr(pilot._ailex, "client", None) if pilot else None)
        self.gsd2      = GSD2Integration(pilot=pilot, provider=provider)
        self._rot      = ContextRotDetector()

    def run(
        self,
        request:     str,
        mode:        str = "auto",   # "auto" | "ailex" | "bmad" | "gsd2" | "unified"
        epic:        str = "",
        n_stories:   int = 5,
        verbose:     bool = True,
    ) -> UnifiedResult:
        """
        Execute request through the unified pipeline.
        Mode 'auto' detects the best approach from the request content.
        """
        start    = time.time()
        use_mode = self._detect_mode(request) if mode == "auto" else mode

        if verbose:
            print(f"\n{'═'*60}")
            print(f"⚡ AILEX+BMAD+GSD2 Unified Pipeline [{use_mode.upper()}]")
            print(f"{'═'*60}")

        result = UnifiedResult(request=request, mode=use_mode)

        if use_mode == "ailex":
            result = self._run_ailex_only(request, result, verbose)

        elif use_mode == "gsd2":
            result = self._run_gsd2(request, result, verbose)

        elif use_mode == "bmad":
            result = self._run_bmad(request, result, epic, n_stories, verbose)

        elif use_mode in ("unified", "auto"):
            result = self._run_unified(request, result, epic, n_stories, verbose)

        result.duration_s = round(time.time() - start, 2)
        result.context_cleared = len([s for s in self._rot._history if s.trimmed])

        if verbose:
            print(f"\n{'─'*60}")
            print(f"  ✓ Mode: {use_mode} | Time: {result.duration_s}s")
            print(f"  ✓ Confidence: {result.confidence:.0%}")
            if result.artifacts:
                print(f"  ✓ Artifacts: {len(result.artifacts)}")
            if result.stories:
                print(f"  ✓ Stories: {len(result.stories)}")
            print(f"{'═'*60}\n")

        return result

    def _run_ailex_only(self, request: str, result: UnifiedResult, verbose: bool) -> UnifiedResult:
        """Pure AILEX: full cognitive depth, all 17 neural layers."""
        if not self.pilot:
            result.ailex_report = "[DEMO] AILEX analysis complete."
            result.confidence   = 0.85
            return result
        proc = self.pilot.process(request, run_code=True, include_context=True, fmt="full")
        result.ailex_report = proc.get("report", "")
        result.confidence   = proc.get("confidence", 0.0)
        result.total_tokens = proc.get("tokens", 0)
        result.agents_used  = ["AILEX-v6-33-agents"]
        return result

    def _run_gsd2(self, request: str, result: UnifiedResult, verbose: bool) -> UnifiedResult:
        """GSD2 pipeline: spec → plan → execute with context rot prevention."""
        if verbose: print("  [GSD2] Spec-driven execution...")
        gsd2_result = self.gsd2.run_pipeline(request)
        result.spec    = gsd2_result["spec"]
        result.tasks   = gsd2_result["tasks"]
        result.confidence = sum(1 for t in result.tasks if t.status == "done") / max(1, len(result.tasks))
        result.total_tokens = gsd2_result.get("tokens", 0)
        result.agents_used  = list({t.agent for t in result.tasks})
        if result.tasks:
            result.ailex_report = "\n".join(f"[{t.id}] {t.title}: {t.result[:100]}" for t in result.tasks)
        return result

    def _run_bmad(self, request: str, result: UnifiedResult, epic: str,
                  n_stories: int, verbose: bool) -> UnifiedResult:
        """BMAD lifecycle: create artifact + generate stories."""
        if verbose: print("  [BMAD] Artifact-driven development...")
        # Detect appropriate phase
        phase_key = self._detect_bmad_phase(request)
        result.phase = phase_key
        phase = BMAD_PHASES[phase_key]

        # Create primary artifact
        artifact_type = phase["outputs"][0]
        artifact = self.bmad.create_artifact(artifact_type, request, "create", self.pilot)
        result.artifacts.append(artifact)

        # Generate sprint stories if planning/implementation
        if phase_key in ("planning", "implementation") and self.pilot:
            stories = self.bmad.generate_sprint_stories(artifact.content, epic or request[:40], self.pilot, n_stories)
            result.stories = stories

        result.ailex_report = artifact.content[:500] if artifact.content else f"[DEMO BMAD artifact: {artifact_type}]"
        result.confidence   = 0.85
        result.agents_used  = phase["agents"]
        return result

    def _run_unified(self, request: str, result: UnifiedResult, epic: str,
                     n_stories: int, verbose: bool) -> UnifiedResult:
        """
        Full unified pipeline:
        GSD2 spec → BMAD artifact → AILEX deep execution → context management
        """
        # Step 1: GSD2 — structure the problem
        if verbose: print("  [1/4] GSD2: Creating spec...")
        result.spec = self.gsd2.create_spec(request)

        # Step 2: BMAD — create artifact for this phase
        if verbose: print("  [2/4] BMAD: Creating artifact...")
        phase_key = self._detect_bmad_phase(request)
        result.phase = phase_key
        artifact = self.bmad.create_artifact(
            BMAD_PHASES[phase_key]["outputs"][0],
            f"{request}\n\nSpec: {result.spec.goal}",
            "create", self.pilot,
        )
        result.artifacts.append(artifact)

        # Step 3: AILEX — deep execution with full neural layers
        if verbose: print("  [3/4] AILEX: Deep reasoning...")
        if self.pilot:
            context = (
                f"GSD2 Spec: {result.spec.goal}\n"
                f"BMAD Artifact ({artifact.type}): {artifact.content[:500]}\n\n"
                f"Request: {request}"
            )
            proc = self.pilot.process(
                context, run_code=True, include_context=True, fmt="full"
            )
            result.ailex_report = proc.get("report", "")
            result.confidence   = proc.get("confidence", 0.0)
            result.total_tokens += proc.get("tokens", 0)

            # Context rot check
            if self._rot.add_output(result.ailex_report, "unified"):
                if verbose: print("  [GSD2] Context rot — clearing...")
                self._rot.clear()

        # Step 4: BMAD — generate stories if appropriate
        if phase_key in ("planning", "implementation"):
            if verbose: print("  [4/4] BMAD: Generating sprint stories...")
            stories = self.bmad.generate_sprint_stories(
                result.ailex_report or result.spec.goal,
                epic or request[:40], self.pilot, n_stories,
            )
            result.stories = stories

        # Validate artifact
        if artifact.content and self.pilot:
            self.bmad.validate_artifact(artifact, self.pilot)

        # Collect all agents
        result.agents_used = (
            BMAD_PHASES[phase_key]["agents"]
            + list({t.agent for t in result.tasks})
            + ["AILEX-v6"]
        )

        return result

    def _detect_mode(self, request: str) -> str:
        """Smart mode detection from request content."""
        req = request.lower()

        # GSD2 mode: context-heavy, long-running, multi-file
        if any(w in req for w in ["spec", "plan then", "step by step", "refactor all", "migrate"]):
            return "gsd2"

        # BMAD mode: product/feature/sprint work
        if any(w in req for w in ["sprint", "story", "epic", "prd", "product", "roadmap", "backlog"]):
            return "bmad"

        # UNIFIED: complex, multi-domain
        if any(w in req for w in ["full", "complete", "all", "everything", "production", "system"]):
            return "unified"

        # Default: pure AILEX (most cases)
        return "ailex"

    def _detect_bmad_phase(self, request: str) -> str:
        req = request.lower()
        if any(w in req for w in ["research", "analyse", "brief", "understand"]):
            return "analysis"
        if any(w in req for w in ["plan", "story", "epic", "prd", "require"]):
            return "planning"
        if any(w in req for w in ["architect", "design", "structure", "solution"]):
            return "solutioning"
        return "implementation"

    def format_result(self, r: UnifiedResult) -> str:
        sep = "─" * 60
        lines = [
            f"Unified Pipeline Result [{r.mode.upper()}]",
            f"Phase: {r.phase or 'N/A'} | Conf: {r.confidence:.0%} | {r.duration_s}s",
            sep,
        ]
        if r.spec:
            lines += [f"GSD2 Spec: {r.spec.title}", f"  Goal: {r.spec.goal[:80]}"]
        if r.artifacts:
            lines.append(f"\nBMAD Artifacts ({len(r.artifacts)}):")
            for a in r.artifacts[:3]:
                lines.append(f"  📄 {a.type} [{a.mode}] by {a.agent}")
        if r.stories:
            lines.append(f"\nSprint Stories ({len(r.stories)}):")
            for s in r.stories[:4]:
                lines.append(f"  [{s.priority.upper()}] {s.id} ({s.story_points}pts): {s.title[:50]}")
        if r.ailex_report:
            lines += [f"\nAILEX Report:", r.ailex_report[:400]]
        if r.agents_used:
            lines.append(f"\nAgents: {', '.join(set(r.agents_used))[:80]}")
        lines.append(sep)
        return "\n".join(lines)

    def status(self) -> str:
        return (
            f"Unified Pipeline Status\n"
            f"  AILEX v6: {'✓ active' if self.pilot else '✗ demo'}\n"
            f"{self.bmad.status()}\n"
            f"{self.gsd2.status()}"
        )
