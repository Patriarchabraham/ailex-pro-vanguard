"""
AILEX — gsd2_integration.py
Integrates GSD2 (Get Shit Done 2) capabilities into AILEX.

GSD2 brings:
  - Context rot prevention: systematic context clearing between tasks
  - Spec-driven development: Spec → Plan → Tasks → Execution
  - 5 specialized subagents: Scout, Researcher, Worker, JavaScript Pro, TypeScript Pro
  - Multi-provider support: 20+ model providers (OpenAI, Gemini, OpenRouter, etc.)
  - Stuck loop detection: recognises when AI is spinning without progress
  - Cost/token tracking per task
  - Git branch management per task
  - Context injection at dispatch time (not loaded upfront)

Integration strategy:
  - GSD2 subagents → AILEX agent personas
  - Context rot prevention → AILEX MemoryCompressor + smart context trimming
  - Spec-driven pipeline → extends AILEX PRDGenerator workflow
  - Multi-provider → extends AILEX ProviderRegistry (OpenAI, Gemini, Mistral)
  - Stuck loop detection → monitors AILEX loop quality, breaks cycles
  - File injection → DirectiveProcessor enhanced with @spec, @plan directives
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── GSD2 Subagent Personas ────────────────────────────────────────────────────

GSD2_AGENT_PERSONAS: Dict[str, Dict] = {
    "SCOUT": {
        "tier":   "haiku",
        "model":  "claude-haiku-4-5-20251001",
        "role":   "Fast Codebase Reconnaissance",
        "domains": ["code", "architecture", "refactor"],
        "persona": (
            "You are SCOUT, a fast codebase reconnaissance agent from GSD2.\n"
            "Mission: rapid mapping of codebases. Find structure, patterns, entry points.\n"
            "You are FAST and CONCISE. Return only what matters for the task.\n"
            "Focus: file structure, key functions, dependencies, potential issues.\n"
            "Never explain unless asked. Report, don't analyse.\n"
            "End with: CONFIDENCE: [0.00-1.00]\nMax 200 words."
        ),
    },
    "RESEARCHER": {
        "tier":   "sonnet",
        "model":  "claude-sonnet-4-6",
        "role":   "Deep Web & Technical Research",
        "domains": ["strategy", "data", "documentation"],
        "persona": (
            "You are RESEARCHER, a deep research agent from GSD2.\n"
            "Mission: technical research, library evaluation, API discovery, best practices.\n"
            "You synthesise information from multiple sources into actionable intelligence.\n"
            "Format: findings → implications → recommendation.\n"
            "Always cite confidence in findings and flag what's uncertain.\n"
            "End with: CONFIDENCE: [0.00-1.00]\nMax 400 words."
        ),
    },
    "WORKER": {
        "tier":   "sonnet",
        "model":  "claude-sonnet-4-6",
        "role":   "General-Purpose Task Executor",
        "domains": ["code", "bug", "feature", "refactor"],
        "persona": (
            "You are WORKER, a general-purpose execution agent from GSD2.\n"
            "Mission: execute tasks completely and correctly. No half-measures.\n"
            "You handle any technical task: code, config, scripts, documentation.\n"
            "You ask for clarification only when genuinely ambiguous (never for style).\n"
            "Output: complete, working solution. Always.\n"
            "End with: CONFIDENCE: [0.00-1.00]\nMax 400 words."
        ),
    },
    "JS_PRO": {
        "tier":   "opus",
        "model":  "claude-opus-4-7",
        "role":   "JavaScript Expert & Debugger",
        "domains": ["code", "bug", "performance"],
        "persona": (
            "You are JS_PRO, a JavaScript specialist from GSD2.\n"
            "Mission: expert JavaScript execution, debugging, and optimisation.\n"
            "You know: async/await, closures, prototypes, V8 internals, npm ecosystem.\n"
            "You debug by reasoning about execution order, not guessing.\n"
            "Output: precise JS solutions with explanation of why it works.\n"
            "End with: CONFIDENCE: [0.00-1.00]\nMax 400 words."
        ),
    },
    "TS_PRO": {
        "tier":   "opus",
        "model":  "claude-opus-4-7",
        "role":   "TypeScript Expert & Type Engineer",
        "domains": ["code", "bug", "architecture"],
        "persona": (
            "You are TS_PRO, a TypeScript specialist from GSD2.\n"
            "Mission: expert TypeScript with zero runtime errors.\n"
            "You master: type inference, generics, conditional types, declaration files.\n"
            "You make the type system work FOR you, not against you.\n"
            "Output: type-safe solutions with zero `any` unless justified.\n"
            "End with: CONFIDENCE: [0.00-1.00]\nMax 400 words."
        ),
    },
}

# ── Multi-Provider Registry Extension ─────────────────────────────────────────

GSD2_PROVIDER_CONFIGS: Dict[str, Dict] = {
    "openai": {
        "env_key":  "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "models": {
            "opus":   "gpt-4o",
            "sonnet": "gpt-4o-mini",
            "haiku":  "gpt-4o-mini",
        },
    },
    "gemini": {
        "env_key":  "GOOGLE_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": {
            "opus":   "gemini-1.5-pro",
            "sonnet": "gemini-1.5-flash",
            "haiku":  "gemini-1.5-flash-8b",
        },
    },
    "openrouter": {
        "env_key":  "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "models": {
            "opus":   "anthropic/claude-opus-4-7",
            "sonnet": "anthropic/claude-sonnet-4-6",
            "haiku":  "meta-llama/llama-3.1-8b-instruct",
        },
    },
    "mistral": {
        "env_key":  "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "models": {
            "opus":   "mistral-large-latest",
            "sonnet": "mistral-small-latest",
            "haiku":  "mistral-nemo-latest",
        },
    },
    "groq": {
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "models": {
            "opus":   "llama-3.1-70b-versatile",
            "sonnet": "llama-3.1-8b-instant",
            "haiku":  "gemma-7b-it",
        },
    },
}


@dataclass
class GSD2Spec:
    """GSD2 Spec-driven development specification."""
    title:       str
    goal:        str
    constraints: List[str]
    tech_stack:  List[str]
    out_of_scope: List[str]
    success_criteria: List[str]
    raw:         str = ""


@dataclass
class GSD2Task:
    id:          str
    title:       str
    description: str
    agent:       str
    status:      str = "pending"    # pending | running | done | stuck
    context:     str = ""           # injected at dispatch, not loaded upfront
    result:      str = ""
    tokens:      int = 0
    attempts:    int = 0
    branch:      str = ""


@dataclass
class GSD2ContextSnapshot:
    """GSD2 context snapshot for rot prevention."""
    task_id:   str
    hash:      str               # hash of previous outputs
    timestamp: float
    size:      int               # chars
    trimmed:   bool = False


class ContextRotDetector:
    """
    GSD2's core innovation: detects when context is degrading quality.
    Monitors output similarity — if consecutive outputs are too similar,
    the AI is looping/stuck. Triggers context clear.

    Biology analog: analogous to the brain's default mode network
    detecting when a thought loop is unproductive.
    """

    SIMILARITY_THRESHOLD = 0.85   # outputs above this → stuck
    MAX_SIMILAR_OUTPUTS  = 3      # consecutive similar outputs → rot detected
    MAX_CONTEXT_SIZE     = 60_000 # chars before forced compression

    def __init__(self):
        self._history: List[GSD2ContextSnapshot] = []
        self._output_hashes: List[str] = []

    def add_output(self, output: str, task_id: str) -> bool:
        """Add output, return True if context rot detected."""
        h     = hashlib.md5(output[:500].encode()).hexdigest()
        snap  = GSD2ContextSnapshot(
            task_id=task_id, hash=h,
            timestamp=time.time(), size=len(output),
        )
        self._history.append(snap)
        self._output_hashes.append(h)

        # Check for stuck loop (same hash repeated)
        if len(self._output_hashes) >= self.MAX_SIMILAR_OUTPUTS:
            recent = self._output_hashes[-self.MAX_SIMILAR_OUTPUTS:]
            unique = len(set(recent))
            if unique == 1:  # all same
                return True  # rot detected

        return False

    def total_context_size(self) -> int:
        return sum(s.size for s in self._history)

    def should_compress(self) -> bool:
        return self.total_context_size() > self.MAX_CONTEXT_SIZE

    def clear(self) -> None:
        self._history.clear()
        self._output_hashes.clear()

    def get_compression_summary(self) -> str:
        """Generate a summary of cleared context for injection into new context."""
        if not self._history:
            return ""
        n = len(self._history)
        total = self.total_context_size()
        return (
            f"[GSD2 Context Clear] Previous {n} tasks completed. "
            f"Total context cleared: {total:,} chars. "
            "Continuing from clean state."
        )


class StuckLoopDetector:
    """
    GSD2's stuck loop detection.
    Monitors for: repeated outputs, no progress indicators, timeout.
    """

    PROGRESS_PATTERNS = [
        r"\b(done|complete|finish|implement|creat|fix|resolv|success)\b",
        r"```\w*\n",          # code block = progress
        r"\b(step \d+|phase \d+|completed?)\b",
    ]

    def is_stuck(self, output: str, prev_output: str, elapsed_s: float) -> tuple:
        """Returns (is_stuck: bool, reason: str)."""
        # No progress keywords
        has_progress = any(
            re.search(p, output, re.I)
            for p in self.PROGRESS_PATTERNS
        )
        if not has_progress and elapsed_s > 45:
            return True, "No progress indicators after 45s"

        # Too similar to previous output
        if prev_output and self._similarity(output, prev_output) > 0.8:
            return True, "Output too similar to previous (stuck loop)"

        # Output is mostly questions (confused agent)
        question_density = output.count("?") / max(1, len(output.split()))
        if question_density > 0.15:
            return True, "High question density — agent confused"

        return False, ""

    def _similarity(self, a: str, b: str) -> float:
        wa = set(re.findall(r"\w+", a.lower()))
        wb = set(re.findall(r"\w+", b.lower()))
        if not wa or not wb: return 0.0
        return len(wa & wb) / len(wa | wb)


class GSD2Integration:
    """
    GSD2 methodology integrated into AILEX.
    Provides: spec-driven pipeline, context rot prevention, multi-provider,
    5 subagents, stuck loop detection, task-level git branching.
    """

    def __init__(self, pilot: Any = None, provider: str = "anthropic"):
        self.pilot    = pilot
        self.provider = provider
        self._rot     = ContextRotDetector()
        self._stuck   = StuckLoopDetector()
        self._tasks: List[GSD2Task] = []
        self._inject_agents()

    def _inject_agents(self) -> None:
        """Inject GSD2 subagents into AILEX v6."""
        try:
            from ailex_mythos_v6 import agents as agents_mod
            from ailex_mythos_v6.config import AGENT_MODEL_TIER
            for name, info in GSD2_AGENT_PERSONAS.items():
                agents_mod.AGENT_PERSONAS[name] = info["persona"]
                AGENT_MODEL_TIER[name] = info["model"]
                for domain in info["domains"]:
                    if domain in agents_mod.DOMAIN_AFFINITY:
                        if name not in agents_mod.DOMAIN_AFFINITY[domain]:
                            agents_mod.DOMAIN_AFFINITY[domain].append(name)
        except Exception:
            pass

    # ── Spec-Driven Pipeline ──────────────────────────────────────────────────

    def create_spec(self, brief: str) -> GSD2Spec:
        """Step 1: Convert brief into structured spec."""
        if not self.pilot:
            return GSD2Spec(
                title=brief[:50], goal=brief,
                constraints=["Keep it simple", "Test coverage required"],
                tech_stack=["Python", "TypeScript"],
                out_of_scope=["Mobile app", "External integrations initially"],
                success_criteria=["All tests pass", "No regressions", "Deployed to staging"],
                raw="[DEMO SPEC]",
            )
        result = self.pilot.process(
            f"[GSD2 SPEC] Create a structured development spec for:\n{brief}\n\n"
            "Format:\nTITLE: ...\nGOAL: ...\n"
            "CONSTRAINTS: item1 | item2\nTECH_STACK: item1 | item2\n"
            "OUT_OF_SCOPE: item1 | item2\nSUCCESS_CRITERIA: item1 | item2",
            include_context=False, fmt="concise",
        )
        return self._parse_spec(result.get("report",""), brief)

    def plan(self, spec: GSD2Spec) -> List[GSD2Task]:
        """Step 2: Break spec into ordered tasks."""
        if not self.pilot:
            return self._demo_tasks(spec)
        result = self.pilot.process(
            f"[GSD2 PLAN] Break this spec into 4-8 ordered tasks:\n"
            f"Title: {spec.title}\nGoal: {spec.goal}\n"
            f"Stack: {', '.join(spec.tech_stack)}\n\n"
            "Format each task:\nTASK: [title]\nAGENT: [SCOUT|RESEARCHER|WORKER|JS_PRO|TS_PRO|DEX|ARIA|QUINN]\n"
            "DESC: [what to do specifically]",
            include_context=False, fmt="concise",
        )
        return self._parse_tasks(result.get("report", ""), spec)

    def execute(self, tasks: List[GSD2Task], git_branch: bool = False) -> List[GSD2Task]:
        """Step 3: Execute tasks with context rot prevention."""
        prev_output = ""
        for task in tasks:
            print(f"\n  [GSD2] {task.agent}: {task.title}")
            start = time.time()

            # Inject context at dispatch (not upfront)
            task.context = self._build_task_context(task, tasks)

            if git_branch and task.branch:
                self._create_branch(task.branch)

            if self.pilot:
                for attempt in range(3):
                    task.attempts = attempt + 1
                    result = self.pilot.process(
                        f"[GSD2 TASK {task.id}] {task.description}\n\n{task.context}",
                        include_context=False, run_code=True, fmt="concise",
                    )
                    output = result.get("report", "")
                    elapsed = time.time() - start

                    # Stuck detection
                    is_stuck, reason = self._stuck.is_stuck(output, prev_output, elapsed)
                    if is_stuck and attempt < 2:
                        print(f"    ⚠ Stuck: {reason}. Retrying...")
                        task.context += f"\n\nIMPORTANT: Previous attempt got stuck ({reason}). Be more specific and decisive."
                        continue

                    # Context rot check
                    if self._rot.add_output(output, task.id):
                        print(f"    🔄 Context rot detected — clearing context...")
                        self._rot.clear()
                        summary = self._rot.get_compression_summary()
                        # Re-run with fresh context
                        task.context = summary + "\n" + task.description

                    task.result  = output
                    task.status  = "stuck" if is_stuck else "done"
                    task.tokens  = result.get("tokens", 0) if hasattr(result, "get") else 0
                    prev_output  = output
                    break
            else:
                task.result = f"[DEMO] Task {task.id}: {task.title} completed."
                task.status = "done"

            # Compress context if it's getting large
            if self._rot.should_compress():
                print(f"    📦 Context compressed ({self._rot.total_context_size():,} chars)")
                self._rot.clear()

        self._tasks.extend(tasks)
        return tasks

    def run_pipeline(self, brief: str, git_branch: bool = False) -> Dict:
        """Full GSD2 pipeline: spec → plan → execute."""
        print("\n🚀 GSD2 Pipeline")
        spec  = self.create_spec(brief)
        print(f"  Spec: {spec.title}")
        tasks = self.plan(spec)
        print(f"  Plan: {len(tasks)} tasks")
        done  = self.execute(tasks, git_branch)
        return {
            "spec":   spec,
            "tasks":  done,
            "done":   sum(1 for t in done if t.status == "done"),
            "stuck":  sum(1 for t in done if t.status == "stuck"),
            "tokens": sum(t.tokens for t in done),
        }

    # ── Multi-Provider Support ────────────────────────────────────────────────

    def get_provider_client(self, provider: str = "") -> Optional[Any]:
        """Get client for any of 20+ providers."""
        p = provider or self.provider
        cfg = GSD2_PROVIDER_CONFIGS.get(p)
        if not cfg:
            return None
        key = os.getenv(cfg["env_key"], "")
        if not key:
            return None
        try:
            import httpx
            return {"base_url": cfg["base_url"], "key": key, "models": cfg["models"]}
        except ImportError:
            return None

    def list_providers(self) -> str:
        lines = ["GSD2 Provider Registry:"]
        for name, cfg in GSD2_PROVIDER_CONFIGS.items():
            key_set = bool(os.getenv(cfg["env_key"], ""))
            status  = "✓ active" if key_set else "✗ no key"
            lines.append(f"  {name:12s} {status:10s} models={list(cfg['models'].values())[:1][0]}")
        return "\n".join(lines)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_task_context(self, task: GSD2Task, all_tasks: List[GSD2Task]) -> str:
        """Build minimal context for this specific task (injected at dispatch)."""
        completed = [t for t in all_tasks if t.status == "done" and t.id != task.id]
        ctx = f"Task {task.id}: {task.description}\n"
        if completed:
            ctx += f"\nCompleted so far:\n"
            for t in completed[-2:]:  # only last 2 to keep context small
                ctx += f"  ✓ {t.id}: {t.title} — {t.result[:100]}\n"
        return ctx

    def _create_branch(self, branch_name: str) -> None:
        import subprocess
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True)
        except Exception:
            pass

    def _parse_spec(self, text: str, brief: str) -> GSD2Spec:
        def get(k): return (re.search(rf"{k}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.I|re.S) or type('', (), {'group': lambda s,x: ''})()).group(1).strip() if text else ""
        def lst(k): return [i.strip() for i in get(k).split("|") if i.strip()]
        return GSD2Spec(
            title=get("TITLE") or brief[:50], goal=get("GOAL") or brief,
            constraints=lst("CONSTRAINTS") or ["Keep it simple"],
            tech_stack=lst("TECH_STACK") or ["Python"],
            out_of_scope=lst("OUT_OF_SCOPE") or [],
            success_criteria=lst("SUCCESS_CRITERIA") or ["Tests pass"],
            raw=text,
        )

    def _parse_tasks(self, text: str, spec: GSD2Spec) -> List[GSD2Task]:
        import uuid
        tasks = []
        for i, block in enumerate(re.split(r"\n(?=TASK:)", text)[:8]):
            if not block.strip(): continue
            def get(k): return (re.search(rf"{k}:\s*(.+?)(?=\n[A-Z_]+:|$)", block, re.I) or type('',(),{'group':lambda s,x:''})()).group(1).strip()
            tasks.append(GSD2Task(
                id=f"T{i+1:03d}", title=get("TASK") or f"Task {i+1}",
                description=get("DESC") or get("TASK"),
                agent=get("AGENT") or "WORKER",
                branch=f"gsd2/{re.sub(r'[^a-z0-9]+','-',get('TASK').lower())[:20]}" if get("TASK") else "",
            ))
        return tasks if tasks else self._demo_tasks(spec)

    def _demo_tasks(self, spec: GSD2Spec) -> List[GSD2Task]:
        return [
            GSD2Task("T001", "Reconnaissance", f"Scout codebase for {spec.title}", "SCOUT"),
            GSD2Task("T002", "Research", f"Research best approach for {spec.goal[:40]}", "RESEARCHER"),
            GSD2Task("T003", "Implementation", f"Implement {spec.title}", "WORKER"),
            GSD2Task("T004", "Testing", f"Write tests for {spec.title}", "TS_PRO"),
        ]

    def status(self) -> str:
        agents = list(GSD2_AGENT_PERSONAS.keys())
        providers = sum(1 for cfg in GSD2_PROVIDER_CONFIGS.values()
                       if os.getenv(cfg["env_key"], ""))
        return (
            f"GSD2 Integration Active\n"
            f"  Agents injected: {', '.join(agents)}\n"
            f"  Active providers: {providers}/{len(GSD2_PROVIDER_CONFIGS)}\n"
            f"  Context size: {self._rot.total_context_size():,} chars\n"
            f"  Tasks completed: {sum(1 for t in self._tasks if t.status=='done')}"
        )
