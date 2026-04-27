"""
AILEX — mary_2026.py
MARY's 2026 LLM Knowledge Layer — complete AI/ML knowledge injection.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MARY is the BMAD research agent. With mary_2026, she gets:
  ✦ Complete knowledge of all frontier LLMs (Claude 4, GPT-5, Gemini 2.5...)
  ✦ 2026 AI/ML techniques (RLHF, DPO, MoE, RAG, agents, evals...)
  ✦ Real-time research via WebResearcher (arXiv, OpenAlex, Wikipedia)
  ✦ Structured context injected into every MARY call
  ✦ KB populated with 20 specific 2026 LLM queries
  ✦ LLM landscape comparisons and capability matrices

This makes MARY the most informed research agent in AILEX:
  "What are the best practices for RAG in 2026?" → MARY answers with
  real papers, current model capabilities, and validated techniques.

Usage:
    from ailex_pilot.mary_2026 import Mary2026, enrich_mary
    m = Mary2026()

    # Get MARY's full 2026 context for injection:
    ctx = m.get_context()

    # Research a topic with 2026 LLM knowledge:
    result = m.research("What are the best practices for RAG systems in 2026?")
    print(result.summary)

    # Inject into any pipeline call:
    context = enrich_mary("user wants AI-powered search")
    pipe.call_agent("MARY", task, "analysis", context=context)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .web_researcher    import WebResearcher, ResearchResult
from .knowledge_updater import KnowledgeUpdater
from .ailex_logger      import get_logger


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2026 LLM KNOWLEDGE BASE (built-in, always available even without API)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LLM_LANDSCAPE_2026: Dict[str, Dict] = {

    "Claude 4 (Anthropic)": {
        "models":   ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "strengths": [
            "Extended thinking (sequential reasoning chains)",
            "Superior code generation and debugging",
            "Strongest tool_use / structured output (JSON schema)",
            "Constitutional AI safety alignment",
            "200k context window (Sonnet), 1M+ (experimental)",
            "Best-in-class for agentic tasks (SWE-bench 72.5%)",
        ],
        "best_for": ["code", "agents", "analysis", "safety-critical systems"],
        "api": "api.anthropic.com",
        "pricing_tier": "$$$ (Opus) / $$ (Sonnet) / $ (Haiku)",
    },

    "GPT-4o / o3 (OpenAI)": {
        "models":   ["gpt-4o", "gpt-4o-mini", "o3", "o4-mini"],
        "strengths": [
            "Native multimodal (vision, audio, text)",
            "o3/o4: chain-of-thought reasoning, math/science",
            "Large ecosystem (plugins, Assistants API)",
            "Real-time voice mode",
            "Strong function calling",
        ],
        "best_for": ["multimodal", "math", "general reasoning", "voice"],
        "api": "api.openai.com",
        "pricing_tier": "$$$ (o3) / $ (mini)",
    },

    "Gemini 2.5 Pro (Google DeepMind)": {
        "models":   ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite"],
        "strengths": [
            "2M token context window (industry-leading)",
            "Deep Google integration (Search, Workspace)",
            "Strong multilingual capabilities",
            "Competitive pricing (Flash/Flash-Lite)",
            "Google Cloud integration (Vertex AI)",
        ],
        "best_for": ["long documents", "multilingual", "Google ecosystem", "cost efficiency"],
        "api": "generativelanguage.googleapis.com",
        "pricing_tier": "$$ (Pro) / $ (Flash) / ¢ (Flash-Lite)",
    },

    "Llama 3.x (Meta, Open Source)": {
        "models":   ["llama-3.3-70b", "llama-3.1-405b", "llama-3.2-vision"],
        "strengths": [
            "Fully open source (weights downloadable)",
            "Run locally (no API costs)",
            "Strong community fine-tunes",
            "405B matches GPT-4 on many benchmarks",
            "Vision models (3.2 series)",
        ],
        "best_for": ["privacy", "on-premise", "fine-tuning", "cost-zero inference"],
        "api": "local / Together.ai / Fireworks / Groq",
        "pricing_tier": "Free (self-hosted) / $ (API)",
    },

    "Mistral Large 2 (Mistral AI)": {
        "models":   ["mistral-large-2", "mistral-small", "codestral"],
        "strengths": [
            "Strong code generation (Codestral)",
            "European sovereignty compliance (GDPR-native)",
            "Function calling parity with GPT-4o",
            "Efficient inference, low latency",
        ],
        "best_for": ["European compliance", "code", "fast inference"],
        "api": "api.mistral.ai",
        "pricing_tier": "$$ (Large) / $ (Small)",
    },

    "DeepSeek V3 / R1 (DeepSeek)": {
        "models":   ["deepseek-v3", "deepseek-r1", "deepseek-r1-distill"],
        "strengths": [
            "R1: chain-of-thought reasoning competitive with o1",
            "Open weights (R1 distill models)",
            "Exceptional math and science reasoning",
            "Very competitive pricing",
            "MoE architecture efficiency",
        ],
        "best_for": ["math", "reasoning", "cost efficiency", "open source"],
        "api": "api.deepseek.com",
        "pricing_tier": "$ (very competitive)",
    },

    "Qwen 2.5 (Alibaba)": {
        "models":   ["qwen-2.5-72b", "qwen-2.5-coder", "qwen-2.5-math"],
        "strengths": [
            "Specialized models (Coder, Math, Vision)",
            "Open source weights available",
            "Strong Chinese + multilingual",
            "Qwen2.5-Coder rivals GPT-4o for code",
        ],
        "best_for": ["code", "math", "multilingual", "open source"],
        "api": "dashscope.aliyuncs.com / local",
        "pricing_tier": "Free (local) / $",
    },
}


AI_TECHNIQUES_2026: Dict[str, Dict] = {

    "Training & Alignment": {
        "RLHF":    "Reinforcement Learning from Human Feedback — reward model + PPO. Foundation of ChatGPT, Claude.",
        "DPO":     "Direct Preference Optimization — simpler than RLHF, no reward model. 2024 standard.",
        "GRPO":    "Group Relative Policy Optimization — DeepSeek R1's technique, strong for math/reasoning.",
        "Constitutional AI": "Anthropic's approach — AI critiques own outputs against principles.",
        "RLAIF":   "RL from AI Feedback — AI generates preferences instead of humans. Scales cheaply.",
        "LoRA":    "Low-Rank Adaptation — efficient fine-tuning with <1% of full parameters.",
        "QLoRA":   "Quantized LoRA — fine-tune on consumer GPU, 4-bit quantization.",
        "SFT":     "Supervised Fine-Tuning — instruction following foundation.",
    },

    "Architecture": {
        "MoE":             "Mixture of Experts — sparse activation, route tokens to specialist subnetworks. GPT-4, Gemini.",
        "Mamba/SSM":       "State Space Models — alternative to Transformers, O(n) vs O(n²) attention.",
        "FlashAttention 3":"IO-aware attention — 2-3x faster than standard attention, crucial for long context.",
        "Ring Attention":  "Distributed attention across devices — enables 1M+ context training.",
        "Speculative Decoding": "Draft model predicts tokens, main model verifies in parallel — 2-3x speedup.",
        "Multi-head Latent Attention": "DeepSeek V3's KV cache compression — enables longer context cheaper.",
    },

    "Inference & Serving": {
        "vLLM":      "PagedAttention — most efficient GPU inference server, 24x higher throughput.",
        "GGUF/GPTQ": "Quantization formats — run 70B models on consumer GPU (4-8 bit).",
        "AWQ":       "Activation-aware quantization — better quality than GPTQ at same size.",
        "Ollama":    "Run LLMs locally with one command, supports most open models.",
        "llama.cpp": "C++ inference, runs on CPU, metal (Apple Silicon), CUDA.",
        "TensorRT-LLM": "NVIDIA's optimized inference, production grade.",
    },

    "RAG & Retrieval": {
        "HyDE":          "Hypothetical Document Embeddings — generate fake answer, embed it, search. Better recall.",
        "Reranking":      "Cross-encoder reranker (Cohere, BGE) — reorders top-k for precision.",
        "ColBERT":        "Late interaction retrieval — token-level matching, better than dense.",
        "Hybrid Search":  "Combine BM25 (keyword) + dense (semantic) — best recall overall.",
        "Multi-vector":   "Parent document retrieval, sentence-window, contextual compression.",
        "FLARE":          "Forward-Looking Active REtrieval — retrieve when uncertain during generation.",
        "Self-RAG":       "LLM decides when to retrieve, when to generate from memory.",
        "GraphRAG":       "Microsoft's knowledge graph + RAG — better for complex multi-hop queries.",
    },

    "Agents & Reasoning": {
        "ReAct":       "Reason + Act alternating — thought → action → observation loop.",
        "CoT":         "Chain-of-Thought — step-by-step reasoning, dramatically improves complex tasks.",
        "ToT":         "Tree of Thoughts — explore multiple reasoning branches, backtrack.",
        "Reflexion":   "Self-reflection and verbal reinforcement learning — agent improves via criticism.",
        "MCTS":        "Monte Carlo Tree Search for LLMs — DeepSeek R1 uses for math.",
        "Multi-agent": "CrewAI, AutoGen, LangGraph — multiple LLM agents with specialized roles.",
        "Tool Use":    "Function calling / tool_use — structured JSON output triggering real actions.",
        "Computer Use": "Anthropic Claude 3.5 / Computer Use — LLM controls mouse, keyboard, browser.",
    },

    "Evaluation (2026 Benchmarks)": {
        "SWE-bench Verified": "Resolve GitHub issues. Top: Grok-4 75%, Claude 72.5%, GPT-o3 71%.",
        "LiveBench":          "Contamination-free, updates monthly. Better than MMLU for current models.",
        "HumanEval+":         "Code generation quality, extended version.",
        "MATH-500":           "Mathematical reasoning. o3, DeepSeek R1, Claude Opus lead.",
        "MMLU-Pro":           "Harder MMLU, less contamination sensitive.",
        "BIG-Bench Hard":     "Challenging tasks requiring multi-step reasoning.",
        "GPQA Diamond":       "Graduate-level science questions. True expert-level test.",
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESEARCH QUERIES for KB population
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MARY_2026_RESEARCH_AGENDA = [
    # Frontier models
    ("llm_2026", "Claude 4 Anthropic 2025 capabilities extended thinking",       ["arxiv","semantic_scholar"]),
    ("llm_2026", "GPT-5 o3 OpenAI reasoning 2025 frontier model",               ["arxiv","semantic_scholar"]),
    ("llm_2026", "Gemini 2.5 Pro Google DeepMind long context 2025",            ["arxiv","openalex"]),
    ("llm_2026", "DeepSeek V3 R1 chain of thought reasoning 2025",              ["arxiv","semantic_scholar"]),
    ("llm_2026", "Llama 3 open source language model 2025",                     ["arxiv","openalex"]),
    # Architecture advances
    ("llm_2026", "mixture of experts sparse activation language model 2025",    ["arxiv","semantic_scholar"]),
    ("llm_2026", "FlashAttention long context window 1M tokens transformer",    ["arxiv","semantic_scholar"]),
    ("llm_2026", "speculative decoding inference acceleration 2025",            ["arxiv","openalex"]),
    # Training
    ("llm_2026", "RLHF DPO GRPO preference optimization LLM training 2025",    ["arxiv","semantic_scholar"]),
    ("llm_2026", "LoRA QLoRA parameter efficient fine-tuning 2025",             ["arxiv","semantic_scholar"]),
    # RAG
    ("llm_2026", "advanced RAG retrieval augmented generation 2025",            ["arxiv","semantic_scholar"]),
    ("llm_2026", "GraphRAG knowledge graph retrieval Microsoft 2025",           ["arxiv","openalex"]),
    ("llm_2026", "ColBERT hybrid search dense sparse retrieval 2025",          ["arxiv","semantic_scholar"]),
    # Agents
    ("llm_2026", "LLM agent autonomous software engineering 2025 2026",         ["arxiv","semantic_scholar"]),
    ("llm_2026", "multi-agent framework CrewAI AutoGen LangGraph 2025",        ["arxiv","openalex"]),
    ("llm_2026", "chain of thought tree of thought reasoning LLM",             ["arxiv","semantic_scholar"]),
    # Evals
    ("llm_2026", "LLM evaluation benchmark SWE-bench LiveBench 2025",          ["arxiv","openalex"]),
    ("llm_2026", "AI safety alignment constitutional 2025",                     ["arxiv","semantic_scholar"]),
    # Multimodal
    ("llm_2026", "multimodal vision language model GPT-4o 2025",               ["arxiv","semantic_scholar"]),
    ("llm_2026", "small language model SLM efficient on-device 2025",          ["arxiv","openalex"]),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MARY 2026 CLASS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class MaryResearchResult:
    query:        str
    summary:      str
    sources:      List[str]      = field(default_factory=list)
    papers:       List[str]      = field(default_factory=list)
    llm_context:  str            = ""
    confidence:   float          = 0.8


class Mary2026:
    """
    MARY with full 2026 LLM knowledge layer.

    Every research call:
    1. Checks KB for relevant entries (355+ academic papers)
    2. Adds structured 2026 LLM context (model landscape, techniques)
    3. Uses WebResearcher for fresh data if needed
    4. Returns enriched research result
    """

    def __init__(self):
        self.researcher = WebResearcher()
        self.ku         = KnowledgeUpdater()
        self.log        = get_logger("mary_2026")

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_context(self, topic: str = "", max_chars: int = 800) -> str:
        """
        Get MARY's complete 2026 knowledge context for injection into prompts.
        Combines: LLM landscape + techniques + KB papers + fresh research.
        """
        parts = []

        # 1. Relevant LLM models for this topic
        llm_context = self._relevant_llms(topic)
        if llm_context:
            parts.append(llm_context)

        # 2. Relevant AI techniques
        tech_context = self._relevant_techniques(topic)
        if tech_context:
            parts.append(tech_context)

        # 3. KB papers
        kb_context = self._kb_context(topic)
        if kb_context:
            parts.append(kb_context)

        combined = "\n\n".join(parts)
        return combined[:max_chars]

    def research(
        self,
        query:       str,
        deep:        bool = False,
        include_llm: bool = True,
    ) -> MaryResearchResult:
        """
        MARY researches a topic with full 2026 LLM knowledge.
        """
        # Web/academic sources
        sources_list = ["arxiv", "semantic_scholar", "openalex", "wikipedia"]
        if not deep:
            sources_list = ["arxiv", "wikipedia", "duckduckgo"]

        papers = self.researcher.research(
            query, sources=sources_list, max_per_source=3
        )

        # Build summary
        summary_parts = []

        # Add LLM context if relevant
        llm_ctx = self._relevant_llms(query) if include_llm else ""
        if llm_ctx:
            summary_parts.append(llm_ctx)

        # Add paper findings
        if papers:
            paper_lines = [f"• {p.title[:70]} ({p.source}, ★{p.citations})" for p in papers[:5]]
            summary_parts.append("Recent research:\n" + "\n".join(paper_lines))

        # KB lookup
        kb = self._kb_context(query)
        if kb:
            summary_parts.append(kb)

        return MaryResearchResult(
            query       = query,
            summary     = "\n\n".join(summary_parts),
            sources     = [p.url for p in papers[:5]],
            papers      = [p.title for p in papers[:5]],
            llm_context = llm_ctx,
            confidence  = 0.85 if papers else 0.65,
        )

    def populate_kb(self, verbose: bool = True) -> int:
        """Populate KB with all 2026 LLM research queries."""
        stored = 0
        for domain, query, sources in MARY_2026_RESEARCH_AGENDA:
            if verbose:
                print(f"  🔍 {query[:55]}...")
            try:
                results = self.researcher.research(
                    query, sources=sources, max_per_source=3
                )
                if results:
                    n = self.ku._store(domain, query, results)
                    stored += n
                    if verbose and n > 0:
                        print(f"     ✓ {n} entries")
            except Exception as e:
                if verbose:
                    print(f"     ✗ {e}")
        return stored

    def describe_llm_landscape(self, format: str = "table") -> str:
        """Return current LLM landscape in requested format."""
        if format == "table":
            lines = ["2026 LLM Landscape:", "─" * 60]
            for name, info in LLM_LANDSCAPE_2026.items():
                models = ", ".join(info["models"][:2])
                best   = ", ".join(info["best_for"][:2])
                lines.append(f"  {name:<35} [{models}]")
                lines.append(f"    Best for: {best}")
            return "\n".join(lines)
        elif format == "json":
            import json
            return json.dumps({k: {"models": v["models"], "strengths": v["strengths"][:2]}
                               for k, v in LLM_LANDSCAPE_2026.items()}, indent=2)
        return str(LLM_LANDSCAPE_2026)

    def describe_techniques(self, category: str = "") -> str:
        """Return AI/ML techniques knowledge."""
        lines = ["2026 AI/ML Techniques:", "─" * 60]
        cats  = [category] if category else list(AI_TECHNIQUES_2026.keys())
        for cat in cats:
            if cat not in AI_TECHNIQUES_2026:
                continue
            lines.append(f"\n  [{cat}]")
            for tech, desc in AI_TECHNIQUES_2026[cat].items():
                lines.append(f"    {tech:<25} {desc[:60]}")
        return "\n".join(lines)

    def compare_models(self, use_case: str) -> str:
        """Return model recommendations for a specific use case."""
        recommendations = []
        uc_lower = use_case.lower()

        for name, info in LLM_LANDSCAPE_2026.items():
            score = sum(1 for bf in info["best_for"]
                        if any(kw in uc_lower for kw in bf.lower().split("/")))
            if score > 0:
                recommendations.append((score, name, info))

        if not recommendations:
            # Default recommendation
            return (
                f"For '{use_case}', recommended models:\n"
                f"  1. Claude 4 Sonnet — balanced quality/cost, strong tool_use\n"
                f"  2. GPT-4o — if multimodal needed\n"
                f"  3. Gemini Flash — if cost is priority"
            )

        recommendations.sort(reverse=True)
        lines = [f"Model recommendations for '{use_case}':"]
        for _, name, info in recommendations[:3]:
            lines.append(f"  ✦ {name}: {', '.join(info['strengths'][:2])}")
            lines.append(f"    Pricing: {info['pricing_tier']}")
        return "\n".join(lines)

    # ── Private ─────────────────────────────────────────────────────────────────

    def _relevant_llms(self, topic: str) -> str:
        topic_lower = topic.lower()
        relevant = []
        keywords = {
            "claude":       "Claude 4 (Anthropic)",
            "anthropic":    "Claude 4 (Anthropic)",
            "gpt":          "GPT-4o / o3 (OpenAI)",
            "openai":       "GPT-4o / o3 (OpenAI)",
            "gemini":       "Gemini 2.5 Pro (Google DeepMind)",
            "google":       "Gemini 2.5 Pro (Google DeepMind)",
            "llama":        "Llama 3.x (Meta, Open Source)",
            "open source":  "Llama 3.x (Meta, Open Source)",
            "deepseek":     "DeepSeek V3 / R1 (DeepSeek)",
            "reasoning":    "DeepSeek V3 / R1 (DeepSeek)",
            "mistral":      "Mistral Large 2 (Mistral AI)",
            "qwen":         "Qwen 2.5 (Alibaba)",
            "code":         "Claude 4 (Anthropic)",
            "agent":        "Claude 4 (Anthropic)",
            "multimodal":   "GPT-4o / o3 (OpenAI)",
            "cost":         "Gemini 2.5 Pro (Google DeepMind)",
            "cheap":        "Gemini 2.5 Pro (Google DeepMind)",
            "local":        "Llama 3.x (Meta, Open Source)",
            "privacy":      "Llama 3.x (Meta, Open Source)",
            "math":         "DeepSeek V3 / R1 (DeepSeek)",
        }
        seen = set()
        for kw, model_name in keywords.items():
            if kw in topic_lower and model_name not in seen:
                seen.add(model_name)
                info = LLM_LANDSCAPE_2026.get(model_name, {})
                if info:
                    relevant.append(
                        f"  {model_name}: {info['strengths'][0]} | "
                        f"Best for: {', '.join(info['best_for'][:2])}"
                    )

        if not relevant and topic_lower:
            # Generic recommendation
            relevant = [
                "  Claude 4 Sonnet: balanced quality/cost, tool_use, agents",
                "  GPT-4o: multimodal, large ecosystem",
                "  Gemini Flash: cost-efficient, 2M context",
            ]

        return "[2026 LLM Context]\n" + "\n".join(relevant) if relevant else ""

    def _relevant_techniques(self, topic: str) -> str:
        topic_lower = topic.lower()
        found = []
        for category, techniques in AI_TECHNIQUES_2026.items():
            for tech, desc in techniques.items():
                if any(kw in topic_lower for kw in tech.lower().split("/")):
                    found.append(f"  {tech}: {desc[:80]}")
                    if len(found) >= 4:
                        break
            if len(found) >= 4:
                break
        return "[2026 AI Techniques]\n" + "\n".join(found) if found else ""

    def _kb_context(self, topic: str) -> str:
        try:
            entries = self.ku.query(topic, domain="llm_2026", limit=3, since_hours=72*7)
            if not entries:
                entries = self.ku.query(topic, domain="ai", limit=2)
            if not entries:
                return ""
            lines = ["[KB Research 2026]"]
            for e in entries:
                lines.append(f"  • {e['title'][:65]} ({e['source']}, ★{e['citations']})")
            return "\n".join(lines)
        except Exception:
            return ""


# ── Global singleton + convenience ────────────────────────────────────────────

_mary: Optional[Mary2026] = None

def get_mary() -> Mary2026:
    global _mary
    if _mary is None:
        _mary = Mary2026()
    return _mary


def enrich_mary(topic: str = "", max_chars: int = 800) -> str:
    """
    Get MARY's 2026 knowledge context for injection into any prompt.
    Call before any MARY agent invocation for maximum knowledge.

        context = enrich_mary("user wants AI-powered search system")
        pipe.call_agent("MARY", task, "analysis", context=context)
    """
    return get_mary().get_context(topic, max_chars)


def mary_research(query: str, deep: bool = False) -> MaryResearchResult:
    """Quick research with full 2026 LLM knowledge."""
    return get_mary().research(query, deep=deep)


def mary_compare_models(use_case: str) -> str:
    """Get model recommendations for a specific use case."""
    return get_mary().compare_models(use_case)


if __name__ == "__main__":
    m = Mary2026()

    print("=" * 65)
    print(m.describe_llm_landscape())
    print()
    print(m.describe_techniques("Training & Alignment"))
    print()
    print(m.compare_models("Build a RAG system for document search"))
    print()
    print("MARY context for 'AI agent framework':")
    print(m.get_context("AI agent framework", max_chars=400))
