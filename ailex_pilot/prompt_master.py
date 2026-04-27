"""
AILEX — prompt_master.py
Omniscient Prompt Engineering System.

Domains: every field of human knowledge.
Architecture: ontology-grounded, terminology-precise, context-optimal,
harness-calibrated, multi-paradigm synthesis.

Modules:
  OntologyEngine         — formal knowledge graph of every domain
  TerminologyMaster      — precise vocabulary per domain + cross-domain bridges
  ContextEngineer        — optimal context window construction
  HarnessEngineer        — AILEX harness configuration per task
  PromptArchitect        — synthesis: generate perfect prompt for any task
  OmniscientSynthesiser  — cross-domain integration at maximum depth
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# ONTOLOGY ENGINE — formal knowledge structure for every domain
# ═══════════════════════════════════════════════════════════════════════════

DOMAIN_ONTOLOGY: Dict[str, Dict] = {
    "software_engineering": {
        "axioms": [
            "Abstraction reduces complexity by hiding implementation details",
            "Separation of concerns improves maintainability and testability",
            "Every system tends toward entropy without active maintenance",
            "The cost of a bug grows exponentially with discovery delay",
            "Premature optimisation is the root of most evil (Knuth)",
        ],
        "primitives": ["function","class","module","interface","contract","invariant"],
        "relationships": ["depends_on","implements","extends","composes","delegates"],
        "quality_axes": ["correctness","performance","security","maintainability","scalability"],
        "paradigms": ["imperative","functional","object-oriented","reactive","declarative"],
        "anti_patterns": ["god_object","magic_numbers","tight_coupling","premature_abstraction"],
    },
    "mathematics": {
        "axioms": [
            "A statement is either true or false (excluded middle)",
            "If P then Q; P is true; therefore Q is true (modus ponens)",
            "Proof by contradiction: assume ¬P, derive absurdity, conclude P",
            "Mathematical objects exist independently of physical reality (Platonism)",
        ],
        "primitives": ["set","function","relation","number","proof","theorem","lemma"],
        "relationships": ["implies","iff","isomorphic_to","homomorphic_to","maps_to"],
        "branches": ["algebra","analysis","topology","combinatorics","logic","geometry"],
    },
    "physics": {
        "axioms": [
            "Laws of physics are identical in all inertial frames (relativity)",
            "Energy is conserved in closed systems",
            "Entropy of isolated systems never decreases (second law)",
            "Wave function collapse upon measurement (Copenhagen)",
            "Information cannot be destroyed (Hawking radiation resolution)",
        ],
        "primitives": ["energy","force","field","particle","spacetime","entropy","information"],
        "relationships": ["causes","transforms_into","conserves","breaks_symmetry"],
        "scales": ["quantum","atomic","classical","relativistic","cosmological"],
    },
    "neuroscience": {
        "axioms": [
            "Neural activity is the physical substrate of cognition",
            "Neurons that fire together wire together (Hebbian learning)",
            "Brain function emerges from network topology, not individual neurons",
            "Consciousness correlates with integrated information (Tononi IIT)",
            "Prediction error minimisation drives perception and action (Friston)",
        ],
        "primitives": ["neuron","synapse","action_potential","receptor","neurotransmitter","circuit"],
        "mechanisms": ["LTP","LTD","NMDA","GABA","dopamine","serotonin","acetylcholine"],
        "systems": ["hippocampus","PFC","amygdala","cerebellum","basal_ganglia","thalamus"],
    },
    "philosophy": {
        "axioms": [
            "Cogito ergo sum — I think therefore I am (Descartes)",
            "The map is not the territory (Korzybski)",
            "All models are wrong; some are useful (Box)",
            "Ought cannot be derived from is alone (Hume's guillotine)",
        ],
        "branches": ["epistemology","ontology","ethics","logic","aesthetics","metaphysics"],
        "problems": ["hard_problem_of_consciousness","free_will","personal_identity","truth"],
        "paradigms": ["empiricism","rationalism","pragmatism","phenomenology","structuralism"],
    },
    "economics": {
        "axioms": [
            "Agents maximise utility subject to constraints",
            "Prices aggregate distributed information (Hayek)",
            "Markets clear when supply equals demand (equilibrium)",
            "Incentives shape behaviour more than intentions",
            "There are no free lunches — every benefit has a cost",
        ],
        "primitives": ["scarcity","preference","incentive","price","market","utility","capital"],
        "mechanisms": ["supply_demand","price_signals","externalities","public_goods","game_theory"],
    },
    "biology": {
        "axioms": [
            "All life descends from a common ancestor via evolution",
            "Natural selection acts on heritable variation",
            "DNA encodes biological information in universal code",
            "Cells are the basic unit of life",
            "Fitness is reproductive success, not strength",
        ],
        "primitives": ["gene","cell","organism","population","ecosystem","mutation","fitness"],
        "mechanisms": ["natural_selection","genetic_drift","horizontal_gene_transfer","epigenetics"],
    },
    "linguistics": {
        "axioms": [
            "Language is a system of arbitrary signs (Saussure)",
            "Grammar is innate — universal grammar underlies all languages (Chomsky)",
            "Meaning arises from use, not definition (Wittgenstein)",
            "Language shapes thought (Sapir-Whorf, weak version)",
        ],
        "levels": ["phonology","morphology","syntax","semantics","pragmatics","discourse"],
        "phenomena": ["recursion","compositionality","ambiguity","deixis","metaphor","implicature"],
    },
    "artificial_intelligence": {
        "axioms": [
            "Intelligence can be substrate-independent",
            "Learning from data generalises if distribution assumptions hold",
            "Representation determines what can be learnt",
            "Exploration-exploitation tradeoff is fundamental",
            "Alignment of objectives is harder than capability",
        ],
        "primitives": ["model","training","inference","loss","gradient","attention","embedding"],
        "paradigms": ["symbolic","connectionist","Bayesian","evolutionary","hybrid"],
        "challenges": ["alignment","interpretability","generalisation","robustness","efficiency"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# TERMINOLOGY MASTER — precise vocabulary per domain
# ═══════════════════════════════════════════════════════════════════════════

DOMAIN_TERMINOLOGY: Dict[str, Dict[str, str]] = {
    "prompt_engineering": {
        "few-shot":         "providing examples within the prompt to guide output format",
        "chain-of-thought": "instructing the model to reason step-by-step before answering",
        "self-consistency":  "sampling multiple reasoning paths and selecting the majority answer",
        "tree-of-thought":   "exploring multiple reasoning branches and evaluating each",
        "meta-prompt":       "a prompt that generates or improves other prompts",
        "system_prompt":     "persistent instructions defining model role and behaviour",
        "grounding":         "anchoring model outputs to verified factual context",
        "calibration":       "aligning model confidence with actual accuracy",
        "jailbreak":         "adversarial prompt that bypasses safety constraints",
        "injection":         "malicious user input that hijacks prompt context",
        "persona":           "a consistent identity and behaviour profile for an AI agent",
        "tool_use":          "structured model output that triggers external function calls",
        "RLHF":             "reinforcement learning from human feedback for alignment",
        "constitutional_AI": "training model to follow explicit principles (Anthropic)",
        "context_window":    "maximum token count model can process in one call",
        "temperature":       "sampling randomness — 0=deterministic, 1=creative, 2=chaotic",
        "top_p":            "nucleus sampling — sample from tokens summing to top_p probability",
        "logprobs":          "log-probabilities of output tokens — measures model confidence",
    },
    "context_engineering": {
        "context_budget":    "total token allocation for a conversation or pipeline call",
        "context_compression":"reducing context size while preserving semantic content",
        "relevance_ranking": "ordering context items by importance to current query",
        "sliding_window":    "moving context window discarding oldest tokens first",
        "hierarchical_context":"multi-level context: project→file→function→line",
        "episodic_context":   "context from past interactions (session memory)",
        "semantic_context":   "retrieved context based on meaning similarity",
        "structural_context": "codebase architecture, file relationships, call graphs",
        "temporal_context":   "recent changes, git history, deployment events",
        "interleaved_context":"alternating task instructions with relevant context chunks",
    },
    "harness_engineering": {
        "harness":           "the infrastructure that runs, monitors, and orchestrates AI agents",
        "eval_harness":       "automated testing framework measuring AI output quality",
        "pipeline":           "sequential or parallel chain of AI calls and tools",
        "scaffolding":        "code surrounding an AI call that manages input/output",
        "sampling_strategy":  "how many and which completions to generate and select",
        "retry_policy":       "rules for re-attempting failed or low-quality generations",
        "output_parser":      "structured extraction of model output into typed objects",
        "guardrails":         "constraints preventing harmful or off-policy model outputs",
        "routing":            "directing requests to appropriate models based on complexity",
        "batching":           "grouping multiple requests for efficiency",
        "caching":            "reusing previous outputs for identical or similar inputs",
        "streaming":          "progressive delivery of model output as tokens generate",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT ENGINEER
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ContextBudget:
    total_tokens:   int
    system_tokens:  int
    context_tokens: int
    query_tokens:   int
    reserve:        int
    efficiency:     float


@dataclass
class BuiltContext:
    system_prompt:   str
    context_block:   str
    query:           str
    total_tokens_est: int
    layers:          List[str]
    optimisations:   List[str]


class ContextEngineer:
    """
    Constructs maximally informative context within token budget.
    Applies: relevance ranking, compression, hierarchical structuring,
    episodic + semantic + structural context layers.
    """

    CHARS_PER_TOKEN = 3.8  # approximate

    def build(
        self,
        request:      str,
        project_ctx:  str = "",
        session_ctx:  str = "",
        domain:       str = "software_engineering",
        kb_ctx:       str = "",
        budget:       int = 8000,
        persona:      str = "AILEX",
    ) -> BuiltContext:
        layers:        List[str] = []
        optimisations: List[str] = []

        # Allocate budget
        alloc = self._allocate(budget, request, project_ctx, session_ctx)

        # System prompt (omniscient persona)
        system = self._build_system(persona, domain, alloc.system_tokens)
        layers.append("system_persona")

        # Structural context (project architecture)
        struct_ctx = ""
        if project_ctx:
            struct_ctx = self._compress(project_ctx, alloc.context_tokens // 3)
            layers.append("structural")
            optimisations.append(f"compressed project context to {len(struct_ctx)//4} tokens")

        # Episodic context (session memory)
        epis_ctx = ""
        if session_ctx:
            epis_ctx = self._compress(session_ctx, alloc.context_tokens // 4)
            layers.append("episodic")

        # Knowledge base context
        kb = ""
        if kb_ctx:
            kb = self._compress(kb_ctx, alloc.context_tokens // 4)
            layers.append("knowledge_base")

        # Domain ontology injection
        ontology = self._ontology_snippet(domain)
        layers.append("ontology")

        # Assemble context block
        parts = []
        if struct_ctx:
            parts.append(f"=== PROJECT CONTEXT ===\n{struct_ctx}")
        if epis_ctx:
            parts.append(f"=== SESSION HISTORY ===\n{epis_ctx}")
        if kb:
            parts.append(f"=== KNOWLEDGE BASE ===\n{kb}")
        if ontology:
            parts.append(f"=== DOMAIN AXIOMS [{domain}] ===\n{ontology}")

        context_block = "\n\n".join(parts)
        total_est     = int((len(system) + len(context_block) + len(request)) / self.CHARS_PER_TOKEN)

        return BuiltContext(
            system_prompt=system,
            context_block=context_block,
            query=request,
            total_tokens_est=total_est,
            layers=layers,
            optimisations=optimisations,
        )

    def _allocate(self, budget: int, *texts: str) -> ContextBudget:
        query_est  = int(len(texts[0]) / self.CHARS_PER_TOKEN) if texts else 100
        system_tok = min(1500, budget // 6)
        reserve    = max(500, budget // 10)
        ctx_tok    = budget - system_tok - query_est - reserve
        return ContextBudget(
            total_tokens=budget,
            system_tokens=system_tok,
            context_tokens=max(0, ctx_tok),
            query_tokens=query_est,
            reserve=reserve,
            efficiency=round((budget - reserve) / budget, 3),
        )

    def _compress(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        # Keep beginning and end (most informative parts)
        half = max_chars // 2 - 50
        return text[:half] + f"\n[... {len(text)-max_chars} chars compressed ...]\n" + text[-half:]

    def _build_system(self, persona: str, domain: str, max_tokens: int) -> str:
        return (
            f"You are {persona}, omniscient engineering intelligence.\n"
            f"Primary domain: {domain}.\n"
            "You reason with: formal ontological precision, terminological exactness, "
            "cross-domain synthesis, and multi-level abstraction.\n"
            "You never approximate when precision is available.\n"
            "You surface non-obvious implications and second-order effects.\n"
            "You distinguish between what is known, inferred, and assumed.\n"
            "You cite the strongest counterargument before your recommendation."
        )

    def _ontology_snippet(self, domain: str) -> str:
        onto = DOMAIN_ONTOLOGY.get(domain, {})
        if not onto:
            return ""
        axioms = onto.get("axioms", [])[:3]
        return "Axioms: " + " | ".join(axioms)


# ═══════════════════════════════════════════════════════════════════════════
# HARNESS ENGINEER
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class HarnessConfig:
    model:              str
    temperature:        float
    max_tokens:         int
    top_p:              float
    use_thinking:       bool
    thinking_budget:    int
    use_tool_use:       bool
    retry_attempts:     int
    retry_on_low_conf:  float
    sampling_strategy:  str
    output_format:      str
    guardrails:         List[str]
    estimated_cost_usd: float


class HarnessEngineer:
    """
    Configures the optimal AI harness for any task type.
    Selects model, parameters, thinking budget, retry policy,
    sampling strategy, and output format.
    """

    TASK_PROFILES = {
        "creative":       {"temp": 0.9, "model": "sonnet", "thinking": False},
        "analytical":     {"temp": 0.2, "model": "opus",   "thinking": True},
        "code":           {"temp": 0.1, "model": "opus",   "thinking": False},
        "reasoning":      {"temp": 1.0, "model": "opus",   "thinking": True},
        "classification": {"temp": 0.0, "model": "haiku",  "thinking": False},
        "extraction":     {"temp": 0.0, "model": "haiku",  "thinking": False},
        "synthesis":      {"temp": 0.3, "model": "sonnet", "thinking": True},
        "critique":       {"temp": 0.2, "model": "opus",   "thinking": True},
        "planning":       {"temp": 0.3, "model": "sonnet", "thinking": True},
        "conversation":   {"temp": 0.7, "model": "sonnet", "thinking": False},
    }

    MODEL_COSTS = {
        "opus":   {"input": 15.0, "output": 75.0},
        "sonnet": {"input": 3.0,  "output": 15.0},
        "haiku":  {"input": 0.8,  "output": 4.0},
    }

    def configure(
        self,
        task_type:    str = "analytical",
        domain:       str = "software_engineering",
        complexity:   float = 0.5,
        budget_usd:   float = 0.50,
        require_json: bool = False,
    ) -> HarnessConfig:
        profile  = self.TASK_PROFILES.get(task_type, self.TASK_PROFILES["analytical"])
        model    = profile["model"]
        temp     = profile["temp"]
        thinking = profile["thinking"]

        # Scale with complexity
        if complexity > 0.8:
            model    = "opus"
            thinking = True
        elif complexity < 0.3:
            model    = "haiku"
            thinking = False

        max_tokens      = self._token_budget(domain, task_type, complexity)
        thinking_budget = max_tokens // 2 if thinking else 0

        # Retry policy
        retry_attempts   = 3 if complexity > 0.7 else 2
        retry_conf       = 0.80 if complexity > 0.7 else 0.70

        # Sampling strategy
        if task_type in ("reasoning", "planning", "critique"):
            sampling = "best_of_3"   # generate 3, select highest confidence
        elif task_type == "creative":
            sampling = "diverse_beam"
        else:
            sampling = "single"

        output_fmt = "json_schema" if require_json else "structured_text"

        guardrails = [
            "no_hallucinated_citations",
            "flag_uncertainty_explicitly",
            "no_code_execution_claims",
        ]
        if domain == "security":
            guardrails.append("no_attack_code")
        if domain in ("medicine", "law", "finance"):
            guardrails.append("recommend_professional_review")

        cost = self._estimate_cost(model, max_tokens, thinking_budget)

        return HarnessConfig(
            model=model,
            temperature=temp,
            max_tokens=max_tokens,
            top_p=0.95 if temp > 0.5 else 1.0,
            use_thinking=thinking,
            thinking_budget=thinking_budget,
            use_tool_use=task_type in ("code", "extraction", "planning"),
            retry_attempts=retry_attempts,
            retry_on_low_conf=retry_conf,
            sampling_strategy=sampling,
            output_format=output_fmt,
            guardrails=guardrails,
            estimated_cost_usd=round(cost, 5),
        )

    def _token_budget(self, domain: str, task_type: str, complexity: float) -> int:
        base = {
            "analytical": 4000, "reasoning": 8000, "code": 6000,
            "creative": 3000, "synthesis": 5000, "critique": 4000,
            "planning": 6000, "classification": 500, "extraction": 1000,
        }.get(task_type, 4000)
        domain_mult = {
            "architecture": 1.5, "security": 1.4, "mathematics": 1.3,
            "philosophy": 1.2, "documentation": 0.7,
        }.get(domain, 1.0)
        return int(base * domain_mult * (0.7 + complexity * 0.6))

    def _estimate_cost(self, model: str, max_tokens: int, thinking: int) -> float:
        costs = self.MODEL_COSTS.get(model, self.MODEL_COSTS["sonnet"])
        input_est  = max_tokens * 0.3
        output_est = max_tokens * 0.7 + thinking
        return (input_est * costs["input"] + output_est * costs["output"]) / 1_000_000


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT ARCHITECT — generates perfect prompts for any task
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MasterPrompt:
    system:       str
    user:         str
    full_prompt:  str
    domain:       str
    technique:    str       # prompt technique used
    token_est:    int
    harness:      HarnessConfig
    context:      BuiltContext
    quality_score: float    # estimated prompt quality 0-1


class PromptArchitect:
    """
    Synthesises perfect prompts using every known prompt engineering technique.
    Selects optimal technique per task, injects domain ontology and terminology,
    applies chain-of-thought / tree-of-thought / self-consistency as needed.
    """

    TECHNIQUES = {
        "chain_of_thought": (
            "Reason step-by-step. Show your work explicitly before concluding."
        ),
        "tree_of_thought": (
            "Explore 3 distinct solution approaches. Evaluate each. Choose the best."
        ),
        "self_consistency": (
            "Solve this from 3 independent angles. If they agree, report that answer. "
            "If they disagree, explain why and give the most defensible answer."
        ),
        "socratic": (
            "Before answering, identify: (1) What do I know for certain? "
            "(2) What am I assuming? (3) What would disprove my conclusion?"
        ),
        "dialectical": (
            "State the thesis. State the strongest anti-thesis. "
            "Synthesise a position that transcends both."
        ),
        "first_principles": (
            "Decompose to the most fundamental truths. "
            "Build the answer from axioms upward."
        ),
        "adversarial": (
            "First, argue the opposite of your conclusion as strongly as possible. "
            "Then give your actual answer, having addressed that objection."
        ),
        "rubber_duck": (
            "Explain this problem as if to someone with no domain knowledge. "
            "Often the explanation reveals the answer."
        ),
        "counterfactual": (
            "Before answering, ask: In what world would the opposite be true? "
            "What would need to change? Use this to bound your confidence."
        ),
    }

    def __init__(self, client: Any = None):
        self.client  = client
        self.ctx_eng = ContextEngineer()
        self.harness = HarnessEngineer()

    def craft(
        self,
        request:      str,
        domain:       str = "software_engineering",
        task_type:    str = "analytical",
        complexity:   float = 0.5,
        project_ctx:  str = "",
        session_ctx:  str = "",
        kb_ctx:       str = "",
        require_json: bool = False,
        technique:    Optional[str] = None,
    ) -> MasterPrompt:
        """Craft the optimal prompt for this exact request."""

        # Select technique
        tech_name = technique or self._select_technique(task_type, complexity, domain)
        tech_instr = self.TECHNIQUES.get(tech_name, "")

        # Build context
        ctx = self.ctx_eng.build(
            request, project_ctx, session_ctx, domain, kb_ctx,
            budget=12000, persona="AILEX Omniscient"
        )

        # Configure harness
        harness = self.harness.configure(task_type, domain, complexity, require_json=require_json)

        # Build terminology injection
        term_block = self._terminology_block(domain, request)

        # Build the user prompt
        user = self._build_user(request, tech_instr, term_block, domain, ctx.context_block)

        # Assemble full prompt
        full = f"[SYSTEM]\n{ctx.system_prompt}\n\n[CONTEXT]\n{ctx.context_block}\n\n[USER]\n{user}"

        quality = self._estimate_quality(tech_name, domain, complexity, ctx, harness)

        return MasterPrompt(
            system=ctx.system_prompt,
            user=user,
            full_prompt=full,
            domain=domain,
            technique=tech_name,
            token_est=int(len(full) / 3.8),
            harness=harness,
            context=ctx,
            quality_score=quality,
        )

    def _select_technique(self, task_type: str, complexity: float, domain: str) -> str:
        if complexity > 0.8:
            return "tree_of_thought"
        if task_type == "critique":
            return "adversarial"
        if task_type in ("planning", "architecture"):
            return "first_principles"
        if domain in ("philosophy", "strategy"):
            return "dialectical"
        if task_type == "reasoning":
            return "chain_of_thought"
        if domain == "mathematics":
            return "first_principles"
        return "chain_of_thought"

    def _terminology_block(self, domain: str, request: str) -> str:
        terms = DOMAIN_TERMINOLOGY.get(domain, {})
        if not terms:
            # Try to find relevant terms from all domains
            req_words = set(request.lower().split())
            terms = {}
            for d, d_terms in DOMAIN_TERMINOLOGY.items():
                for term, defn in d_terms.items():
                    if term.replace("_"," ") in request.lower():
                        terms[term] = defn
        if not terms:
            return ""
        top = list(terms.items())[:6]
        lines = ["Precise terminology:"]
        for term, defn in top:
            lines.append(f"  {term}: {defn}")
        return "\n".join(lines)

    def _build_user(self, request: str, technique: str, terminology: str,
                    domain: str, context_block: str) -> str:
        parts = []
        if terminology:
            parts.append(terminology)
        if technique:
            parts.append(f"Reasoning approach: {technique}")
        parts.append(f"Task: {request}")
        onto = DOMAIN_ONTOLOGY.get(domain, {})
        if onto.get("axioms"):
            parts.append(f"Ground in: {onto['axioms'][0]}")
        return "\n\n".join(parts)

    def _estimate_quality(self, technique: str, domain: str, complexity: float,
                           ctx: BuiltContext, harness: HarnessConfig) -> float:
        base = 0.70
        if technique in ("tree_of_thought", "first_principles"): base += 0.10
        if "ontology" in ctx.layers:     base += 0.05
        if "episodic" in ctx.layers:     base += 0.03
        if harness.use_thinking:         base += 0.08
        if harness.sampling_strategy == "best_of_3": base += 0.05
        return min(0.99, round(base, 3))

    def format(self, p: MasterPrompt) -> str:
        lines = [
            f"Master Prompt | domain={p.domain} | technique={p.technique}",
            f"Quality: {p.quality_score:.0%} | Tokens: {p.token_est:,} | Cost: ${p.harness.estimated_cost_usd:.5f}",
            f"Model: {p.harness.model} | Thinking: {p.harness.use_thinking} | Sampling: {p.harness.sampling_strategy}",
            f"Context layers: {', '.join(p.context.layers)}",
            "─" * 60,
            "SYSTEM:",
            p.system[:200],
            "─" * 60,
            "USER:",
            p.user[:400],
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# OMNISCIENT SYNTHESISER — cross-domain integration at maximum depth
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class OmniscientResponse:
    primary_answer:   str
    cross_domain:     List[str]   # insights from other domains
    ontological:      str         # formal ontological framing
    second_order:     List[str]   # non-obvious implications
    uncertainty:      str         # what is unknown
    counterargument:  str         # strongest objection
    synthesis:        str         # final unified answer
    confidence:       float
    domains_activated: List[str]


class OmniscientSynthesiser:
    """
    Synthesises knowledge across ALL domains simultaneously.
    Never operates within a single domain — always cross-pollinates.
    IQ-300-equivalent: sees the full ontological landscape.
    """

    CROSS_DOMAIN_BRIDGES: Dict[str, List[str]] = {
        "software_engineering": ["mathematics", "linguistics", "neuroscience", "economics"],
        "mathematics":          ["physics", "philosophy", "computer_science", "biology"],
        "neuroscience":         ["artificial_intelligence", "philosophy", "biology", "physics"],
        "economics":            ["psychology", "mathematics", "philosophy", "biology"],
        "artificial_intelligence": ["neuroscience", "mathematics", "philosophy", "linguistics"],
        "physics":              ["mathematics", "philosophy", "biology", "economics"],
        "philosophy":           ["mathematics", "linguistics", "neuroscience", "physics"],
        "biology":              ["chemistry", "physics", "economics", "philosophy"],
    }

    def __init__(self, client: Any = None):
        self.client    = client
        self.architect = PromptArchitect(client)

    def synthesise(
        self,
        request:  str,
        domain:   str,
        context:  str = "",
    ) -> OmniscientResponse:
        """Generate an omniscient cross-domain synthesis."""

        if not self.client:
            return self._demo_synthesis(request, domain)

        bridges     = self.CROSS_DOMAIN_BRIDGES.get(domain, ["philosophy", "mathematics"])
        prompt_obj  = self.architect.craft(
            request, domain, "analytical", complexity=0.9,
            project_ctx=context, technique="tree_of_thought"
        )

        cross_instructions = (
            f"After your primary answer in {domain}, draw insights from: "
            + ", ".join(bridges[:3])
            + ". Find non-obvious connections."
        )

        full_prompt = (
            prompt_obj.user + "\n\n"
            + cross_instructions + "\n\n"
            "Structure your response:\n"
            "PRIMARY: [direct answer]\n"
            "CROSS-DOMAIN: [insights from other fields]\n"
            "ONTOLOGICAL: [formal framing of what is actually being asked]\n"
            "SECOND-ORDER: [non-obvious implications]\n"
            "UNCERTAINTY: [what we do not and cannot know]\n"
            "COUNTERARGUMENT: [strongest objection to your answer]\n"
            "SYNTHESIS: [unified answer incorporating all above]\n"
            "CONFIDENCE: [0.00-1.00]"
        )

        try:
            resp = self.client.messages.create(
                model="claude-opus-4-7",
                max_tokens=8000,
                thinking={"type": "enabled", "budget_tokens": 6000},
                temperature=1,
                system=prompt_obj.system,
                messages=[{"role": "user", "content": full_prompt}],
            )
            text = " ".join(b.text for b in resp.content if hasattr(b, "text")).strip()
            return self._parse_response(text, domain, bridges)
        except Exception as e:
            demo = self._demo_synthesis(request, domain)
            demo.uncertainty = str(e)
            return demo

    def _parse_response(self, text: str, domain: str, bridges: List[str]) -> OmniscientResponse:
        import re
        def section(key: str) -> str:
            m = re.search(rf"{key}:\s*(.+?)(?=\n[A-Z\-]+:|$)", text, re.I | re.S)
            return m.group(1).strip()[:600] if m else ""

        conf_m      = re.search(r"CONFIDENCE:\s*([\d.]+)", text, re.I)
        confidence  = float(conf_m.group(1)) if conf_m else 0.88

        cross_raw   = section("CROSS-DOMAIN")
        cross_items = [l.strip("- •") for l in cross_raw.split("\n") if l.strip()][:5]

        second_raw  = section("SECOND-ORDER")
        second      = [l.strip("- •") for l in second_raw.split("\n") if l.strip()][:4]

        return OmniscientResponse(
            primary_answer=section("PRIMARY"),
            cross_domain=cross_items,
            ontological=section("ONTOLOGICAL"),
            second_order=second,
            uncertainty=section("UNCERTAINTY"),
            counterargument=section("COUNTERARGUMENT"),
            synthesis=section("SYNTHESIS"),
            confidence=min(0.99, confidence),
            domains_activated=[domain] + bridges[:3],
        )

    def _demo_synthesis(self, request: str, domain: str) -> OmniscientResponse:
        bridges = self.CROSS_DOMAIN_BRIDGES.get(domain, ["philosophy"])
        onto    = DOMAIN_ONTOLOGY.get(domain, {})
        axiom   = onto.get("axioms", ["All systems tend toward entropy"])[0]
        return OmniscientResponse(
            primary_answer=f"[DEMO] Primary analysis of '{request[:60]}' from {domain} perspective.",
            cross_domain=[
                f"From mathematics: formalise the invariants of this system",
                f"From philosophy: what is the ontological status of this problem?",
                f"From biology: what evolutionary pressure shaped this pattern?",
            ],
            ontological=f"This is fundamentally a question about: {axiom}",
            second_order=[
                "Second-order: solving this creates a new class of problems",
                "The solution space is larger than it appears from the domain alone",
            ],
            uncertainty="Unknown: long-term emergent effects of this decision",
            counterargument="Strongest objection: the simplest solution may be sufficient",
            synthesis="[DEMO] Set ANTHROPIC_API_KEY for real omniscient synthesis.",
            confidence=0.85,
            domains_activated=[domain] + bridges[:2],
        )

    def format(self, r: OmniscientResponse) -> str:
        sep = "═" * 64
        lines = [
            sep,
            f"OMNISCIENT SYNTHESIS  conf={r.confidence:.0%}",
            f"Domains: {', '.join(r.domains_activated)}",
            sep,
            f"PRIMARY:\n  {r.primary_answer[:300]}",
            f"\nONTOLOGICAL:\n  {r.ontological[:200]}",
        ]
        if r.cross_domain:
            lines.append("\nCROSS-DOMAIN INSIGHTS:")
            for c in r.cross_domain[:3]:
                lines.append(f"  • {c[:100]}")
        if r.second_order:
            lines.append("\nSECOND-ORDER EFFECTS:")
            for s in r.second_order[:2]:
                lines.append(f"  → {s[:100]}")
        lines += [
            f"\nCOUNTERARGUMENT:\n  {r.counterargument[:150]}",
            f"\nUNCERTAINTY:\n  {r.uncertainty[:150]}",
            sep,
            f"SYNTHESIS:\n{r.synthesis[:500]}",
            sep,
        ]
        return "\n".join(lines)
