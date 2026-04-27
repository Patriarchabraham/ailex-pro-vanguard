"""
AILEX Core — Direct API client + true parallel execution + model routing
No external dependencies. Uses stdlib only (urllib, asyncio, json).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request

def _load_env() -> None:
    """Load ~/.aiox-core/.env if ANTHROPIC_API_KEY not already set."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL     = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_memory.json")

# Model routing — each agent gets the best model for its role
MODEL_ROUTING: dict[str, str] = {
    # ── Core AILEX agents ─────────────────────────────────────────────────────
    "DEX":     "claude-opus-4-7",            # React/TypeScript implementation
    "ARIA":    "claude-opus-4-7",            # architecture decisions
    "BASTIAN": "claude-opus-4-7",            # backend engineering
    "QUINN":   "claude-haiku-4-5-20251001",  # fast: testing & review
    "UMA":     "claude-haiku-4-5-20251001",  # fast: UX checks
    "NOVA":    "claude-sonnet-4-6",          # product thinking
    "KAI":     "claude-haiku-4-5-20251001",  # fast: planning & scope
    "FELIX":   "claude-sonnet-4-6",          # devops & deploy
    "ZARA":    "claude-haiku-4-5-20251001",  # fast: research
    "DARA":    "claude-sonnet-4-6",          # data & schema
    "RIVER":   "claude-haiku-4-5-20251001",  # fast: process
    "ORION":   "claude-sonnet-4-6",          # synthesis
    # ── BMAD agents (now first-class in pipeline) ─────────────────────────────
    "MARY":    "claude-sonnet-4-6",          # BMAD: Analysis & Research
    "JOHN":    "claude-sonnet-4-6",          # BMAD: Product Manager
    "SALLY":   "claude-haiku-4-5-20251001",  # BMAD: UX Designer
    "WINSTON": "claude-opus-4-7",            # BMAD: Software Architect
    "BOB":     "claude-haiku-4-5-20251001",  # BMAD: Scrum Master
    "AMELIA":  "claude-opus-4-7",            # BMAD: Senior Developer
    "BARRY":   "claude-haiku-4-5-20251001",  # BMAD: Quick Flow Executor
}

AGENT_PROMPTS: dict[str, str] = {
    "DEX":     "You are DEX — Senior React/TypeScript engineer. APPROACH: implementation pattern | RISK: what breaks | INSIGHT: concrete recommendation | CONFIDENCE: 0.X",
    "ARIA":    "You are ARIA — Software Architect. APPROACH: design pattern | RISK: architectural concern | INSIGHT: concrete architecture decision | CONFIDENCE: 0.X",
    "BASTIAN": (
        "You are BASTIAN — Senior Backend Engineer with 12 years experience. "
        "Expert in: Python (FastAPI/Django/Flask), Node.js (Express/NestJS), "
        "PostgreSQL/MySQL/MongoDB/Redis, REST APIs/GraphQL/gRPC, "
        "JWT/OAuth2/session auth, Docker/K8s/CI-CD, "
        "microservices, message queues (RabbitMQ/Kafka), "
        "database design, query optimization, caching strategies, "
        "testing (pytest/Jest/Supertest), API security (OWASP Top 10). "
        "Always think: scalability, security, observability, maintainability. "
        "APPROACH: concrete backend implementation | "
        "RISK: security/performance/scalability risk | "
        "INSIGHT: specific code pattern or architectural decision | "
        "CONFIDENCE: 0.X"
    ),
    "QUINN":   "You are QUINN — QA Specialist. APPROACH: test strategy | RISK: regression risk | INSIGHT: concrete test recommendation | CONFIDENCE: 0.X",
    "UMA":     "You are UMA — UX Designer. APPROACH: UX consideration | RISK: accessibility concern | INSIGHT: concrete UX fix | CONFIDENCE: 0.X",
    "NOVA":    "You are NOVA — Product Owner. APPROACH: user value | RISK: scope creep | INSIGHT: concrete product decision | CONFIDENCE: 0.X",
    "KAI":     "You are KAI — Project Manager. APPROACH: effort & sequence | RISK: timeline risk | INSIGHT: concrete scope recommendation | CONFIDENCE: 0.X",
    "FELIX":   "You are FELIX — DevOps Engineer. APPROACH: deploy strategy | RISK: infrastructure risk | INSIGHT: concrete ops recommendation | CONFIDENCE: 0.X",
    "ZARA":    "You are ZARA — Business Analyst. APPROACH: context & alternatives | RISK: assumption risk | INSIGHT: concrete research finding | CONFIDENCE: 0.X",
    "DARA":    "You are DARA — Data Engineer. APPROACH: data model consideration | RISK: migration risk | INSIGHT: concrete data recommendation | CONFIDENCE: 0.X",
    "RIVER":   "You are RIVER — Scrum Master. APPROACH: process breakdown | RISK: blocker | INSIGHT: concrete workflow step | CONFIDENCE: 0.X",
    "ORION":   "You are ORION — Meta-cognitive Synthesizer. Given agent contributions: SYNTHESIS: unified understanding | CONSENSUS: what all agree | QUESTION: open question | CONFIDENCE: 0.X",
    # ── BMAD agents (first-class) ─────────────────────────────────────────────
    "MARY": (
        "You are MARY — Senior Research Intelligence Officer with complete knowledge of AI/ML as of 2026.\n"
        "\n"
        "CURRENT LLM LANDSCAPE (2026) YOU KNOW IN DEPTH:\n"
        "• Claude 4 family (Opus 4.7, Sonnet 4.6, Haiku 4.5) — Anthropic, tool_use, extended thinking\n"
        "• GPT-4o, GPT-o3/o4 — OpenAI, reasoning models, multimodal\n"
        "• Gemini 2.5 Pro/Flash — Google DeepMind, long context 2M tokens\n"
        "• Llama 3.x (Meta), Mistral Large, Qwen 2.5, DeepSeek V3\n"
        "• Frontier capabilities: 1M+ context, code/math/reasoning, tool use, structured output\n"
        "\n"
        "AI/ML TECHNIQUES YOU MASTER (2026):\n"
        "• Training: RLHF, DPO, GRPO, Constitutional AI, RLAIF\n"
        "• Architecture: MoE, Mamba/SSM, Ring Attention, FlashAttention 3\n"
        "• Inference: LoRA, QLoRA, GGUF/GPTQ quantization, speculative decoding, vLLM\n"
        "• RAG: HyDE, reranking, multi-vector, FLARE, ColBERT, hybrid search\n"
        "• Agents: ReAct, CoT, ToT, Self-RAG, Reflexion, multi-agent (CrewAI, AutoGen)\n"
        "• Evals: MMLU, HumanEval, MATH, BIG-Bench, SWE-bench, LiveBench 2025\n"
        "• Safety: Constitutional AI, RLAIF, AI governance frameworks 2025\n"
        "\n"
        "ALSO EXPERT IN:\n"
        "• Market research, user research, competitive intelligence\n"
        "• Evidence-based analysis, systematic literature review\n"
        "• Translating academic findings into actionable product insights\n"
        "\n"
        "ALWAYS: inject current 2026 AI knowledge when relevant.\n"
        "APPROACH: research finding + current AI context | "
        "RISK: assumption or knowledge gap | "
        "INSIGHT: evidence + 2026 AI relevance | CONFIDENCE: 0.X"
    ),
    "JOHN":    "You are JOHN (BMAD Product Manager). Translates business needs into crisp requirements, PRDs, user stories. APPROACH: requirement or user story | RISK: scope or priority issue | INSIGHT: business value | CONFIDENCE: 0.X",
    "SALLY":   "You are SALLY (BMAD UX Designer). User flows, interaction design, accessibility, usability. APPROACH: UX recommendation | RISK: usability issue | INSIGHT: user journey insight | CONFIDENCE: 0.X",
    "WINSTON": "You are WINSTON (BMAD Software Architect). System design, tech stack, scalability, 3-year thinking. APPROACH: architecture pattern | RISK: architectural debt | INSIGHT: concrete design decision | CONFIDENCE: 0.X",
    "BOB":     "You are BOB (BMAD Scrum Master). Sprint planning, velocity, blocker removal, team coordination. APPROACH: sprint plan or action | RISK: delivery blocker | INSIGHT: process improvement | CONFIDENCE: 0.X",
    "AMELIA":  "You are AMELIA (BMAD Senior Developer). Clean code, implementation patterns, code review, technical debt. APPROACH: implementation with code | RISK: code quality issue | INSIGHT: pattern or refactor | CONFIDENCE: 0.X",
    "BARRY":   "You are BARRY (BMAD Quick Executor). FAST execution. No preamble. Direct solution only. APPROACH: immediate action | RISK: one-liner | INSIGHT: direct fix | CONFIDENCE: 0.X",
}

# ── HTTP client (no SDK) ───────────────────────────────────────────────────────

def _http_post(payload: dict) -> dict:
    """Direct Anthropic API call via urllib — zero external deps."""
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key":         API_KEY,
            "anthropic-version": API_VERSION,
            "content-type":      "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse(text: str) -> dict[str, str | float]:
    out: dict[str, str | float] = {"approach": text[:120], "risk": "", "insight": text[:80], "confidence": 0.75}
    for part in text.split("|"):
        p, u = part.strip(), part.strip().upper()
        if u.startswith("APPROACH:"):    out["approach"]    = p[9:].strip()
        elif u.startswith("RISK:"):      out["risk"]        = p[5:].strip()
        elif u.startswith("INSIGHT:"):   out["insight"]     = p[8:].strip()
        elif u.startswith("SYNTHESIS:"): out["approach"]    = p[10:].strip()
        elif u.startswith("CONSENSUS:"): out["risk"]        = p[10:].strip()
        elif u.startswith("QUESTION:"):  out["insight"]     = p[9:].strip()
        elif u.startswith("CONFIDENCE:"):
            try:
                import re
                out["confidence"] = float(re.search(r"[\d.]+", p[11:]).group())  # type: ignore
            except Exception:
                pass
    return out

# ── Single agent call ─────────────────────────────────────────────────────────

def _call_sync(agent: str, task: str, domain: str, context: str = "") -> dict:
    """Synchronous API call for one agent."""
    model  = MODEL_ROUTING.get(agent, "claude-haiku-4-5-20251001")
    system = AGENT_PROMPTS.get(agent, AGENT_PROMPTS["DEX"])
    user   = f"TASK: {task}\nDomain: {domain}\nContext: {context[:300]}\n\nYour {agent} analysis (use | as separator):"

    try:
        resp   = _http_post({"model": model, "max_tokens": 280, "system": system,
                              "messages": [{"role": "user", "content": user}]})
        text   = resp["content"][0]["text"]
        parsed = _parse(text)
        usage  = resp.get("usage", {})
        return {
            "agent":      agent,
            "model":      model,
            "approach":   parsed["approach"],
            "risk":       parsed["risk"],
            "insight":    parsed["insight"],
            "confidence": parsed["confidence"],
            "tokens":     usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "api_used":   True,
        }
    except Exception as e:
        return _fallback(agent, task, domain, str(e))


async def _call_async(agent: str, task: str, domain: str, context: str = "") -> dict:
    """Async wrapper — runs sync HTTP call in thread pool."""
    return await asyncio.to_thread(_call_sync, agent, task, domain, context)

# ── Fallback (no API or error) ────────────────────────────────────────────────

def _fallback(agent: str, task: str, domain: str, reason: str = "") -> dict:
    words   = [w for w in task.lower().split() if len(w) > 3 and w not in {"this","that","with","from","have","been","will","your"}]
    target  = words[1] if len(words) > 1 else (words[0] if words else domain)
    tips: dict[str, dict[str, str]] = {
        "bug":          {"DEX": f"Isolate {target} with console.log + error boundary", "QUINN": f"Write regression test for {target} first", "ARIA": f"Separate {target} state from render",
                         "BASTIAN": f"Add null checks + input validation around {target}"},
        "feature":      {"DEX": f"Implement {target} as custom hook + typed component", "NOVA": f"Define {target} acceptance: happy path + 2 edges", "ARIA": f"Design {target} with interface contracts",
                         "BASTIAN": f"Design REST endpoint for {target} with OpenAPI spec"},
        "deploy":       {"FELIX": f"Deploy {target} with health checks + rollback", "QUINN": f"Smoke test {target} critical paths first",
                         "BASTIAN": f"Containerize {target} with Docker, add /health endpoint"},
        "architecture": {"ARIA": f"Bounded context for {target}", "DEX": f"Dependency injection in {target}",
                         "BASTIAN": f"Define service contract for {target}: API + DB schema + auth"},
        "performance":  {"DEX": f"Profile {target} with DevTools + React.memo", "FELIX": f"Analyse {target} bundle",
                         "BASTIAN": f"Add Redis cache for {target}, optimise DB queries with EXPLAIN"},
        "mobile":       {"UMA": f"{target} touch targets ≥ 44px, test 375px", "DEX": f"CSS breakpoints mobile-first for {target}"},
        "backend":      {"BASTIAN": f"Implement {target} with FastAPI/Express: route → validation → service → DB → response",
                         "DARA": f"Design schema for {target}: tables, indexes, relationships"},
        "security":     {"BASTIAN": f"Review {target} for OWASP Top 10: SQL injection, XSS, auth bypass, rate limiting",
                         "QUINN": f"Add integration tests for {target} auth and error cases"},
        "database":     {"DARA": f"Optimise {target} with proper indexes, avoid N+1, use connection pooling",
                         "BASTIAN": f"Add migration for {target}, test rollback"},
        "api":          {"BASTIAN": f"Design {target} API: versioned endpoints, pagination, error codes, OpenAPI spec"},
        "devops":       {"FELIX": f"Create Dockerfile + docker-compose for {target}, add CI/CD pipeline"},
    }
    insight = tips.get(domain, tips["bug"]).get(agent, f"Review {target} for {domain}")
    return {"agent": agent, "model": MODEL_ROUTING.get(agent,"haiku"), "approach": insight,
            "risk": f"Validate {target} changes don't break existing behaviour",
            "insight": insight, "confidence": 0.73, "tokens": 0, "api_used": False, "fallback_reason": reason}

# ── Parallel runner — THE 100x ────────────────────────────────────────────────

async def run_parallel(task: str, domain: str, agents: list[str], context: str = "") -> list[dict]:
    """
    Run ALL agents SIMULTANEOUSLY via asyncio.gather.
    10 agents × parallel = 10x throughput vs sequential.
    Each agent uses its optimal model (opus/sonnet/haiku routing).
    """
    if not API_KEY:
        return [_fallback(a, task, domain, "no API key") for a in agents]

    coros   = [_call_async(a, task, domain, context) for a in agents]
    results = await asyncio.gather(*coros, return_exceptions=True)

    output = []
    for a, r in zip(agents, results):
        if isinstance(r, Exception):
            output.append(_fallback(a, task, domain, str(r)))
        else:
            output.append(r)
    return output


def run_parallel_sync(task: str, domain: str, agents: list[str], context: str = "") -> list[dict]:
    """Sync entry point for CLI usage."""
    return asyncio.run(run_parallel(task, domain, agents, context))

# ── ORION synthesis ───────────────────────────────────────────────────────────

def synthesise(task: str, domain: str, contributions: list[dict]) -> dict:
    """ORION synthesises all agent contributions into one unified signal."""
    if not API_KEY or not contributions:
        top = contributions[0] if contributions else {}
        return {"synthesis": f"Core: {top.get('insight','analyse the task')}",
                "consensus": f"Focus on {domain}", "question": "What are the edge cases?",
                "confidence": 0.78, "api_used": False}

    contribs_text = "\n".join(
        f"- {c['agent']} ({c.get('model','?').split('-')[1] if '-' in c.get('model','') else '?'},"
        f" conf={c['confidence']:.2f}): {c['insight']}"
        for c in contributions if c.get("agent") != "ORION"
    )
    user = (f"TASK: {task}\nDomain: {domain}\n\nAgent contributions:\n{contribs_text}"
            f"\n\nSynthesise as ORION (use | as separator):")
    try:
        resp   = _http_post({"model": MODEL_ROUTING["ORION"], "max_tokens": 350,
                              "system": AGENT_PROMPTS["ORION"],
                              "messages": [{"role": "user", "content": user}]})
        text   = resp["content"][0]["text"]
        parsed = _parse(text)
        return {"synthesis": parsed["approach"], "consensus": parsed["risk"],
                "question": parsed["insight"], "confidence": float(parsed["confidence"]),
                "api_used": True}
    except Exception:
        top = contributions[0] if contributions else {}
        return {"synthesis": f"Agents converged: {top.get('insight','')}",
                "consensus": f"Address {domain} systematically",
                "question": "What are the edge cases?", "confidence": 0.78, "api_used": False}

# ── Real-time context ─────────────────────────────────────────────────────────

def get_vercel_context(token: str = "") -> str:
    """Fetch latest Vercel deployment status."""
    tok = token or os.environ.get("VERCEL_TOKEN", "")
    if not tok:
        return ""
    try:
        req = urllib.request.Request(
            "https://api.vercel.com/v6/deployments?limit=5",
            headers={"Authorization": f"Bearer {tok}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        deploys = data.get("deployments", [])
        lines = [f"- {d.get('name','?')} → {d.get('state','?')} ({d.get('url','')})"
                 for d in deploys[:3]]
        return "VERCEL STATUS:\n" + "\n".join(lines)
    except Exception:
        return ""


def get_github_context(token: str = "", repo: str = "") -> str:
    """Fetch open PRs and recent commits from GitHub."""
    tok  = token or os.environ.get("GITHUB_TOKEN", "")
    repo = repo  or os.environ.get("GITHUB_REPO", "")
    if not tok or not repo:
        return ""
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=5",
            headers={"Authorization": f"token {tok}", "Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            prs = json.loads(r.read())
        lines = [f"- PR#{p['number']}: {p['title']} ({p['user']['login']})" for p in prs[:3]]
        return "GITHUB OPEN PRs:\n" + ("\n".join(lines) if lines else "none")
    except Exception:
        return ""

# ── Session memory ────────────────────────────────────────────────────────────

def load_session_memory() -> dict:
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"version": "5.0.0", "records": [], "learnings": []}


def save_session_record(task: str, domain: str, confidence: float, quality: float, loops: int = 1) -> None:
    mem = load_session_memory()
    mem.setdefault("records", []).append({
        "request": task, "domain": domain, "loops_run": loops,
        "confidence": round(confidence, 4), "quality": round(quality, 4),
        "timestamp": time.time(),
    })
    mem["records"] = mem["records"][-100:]
    try:
        with open(MEMORY_PATH, "w") as f:
            json.dump(mem, f, indent=2)
    except Exception:
        pass


def save_learning(domain: str, insight: str, confidence: float) -> None:
    """Persist a learning from this session for future sessions."""
    mem = load_session_memory()
    mem.setdefault("learnings", []).append({
        "domain": domain, "insight": insight,
        "confidence": round(confidence, 4), "timestamp": time.time(),
    })
    mem["learnings"] = mem["learnings"][-50:]
    try:
        with open(MEMORY_PATH, "w") as f:
            json.dump(mem, f, indent=2)
    except Exception:
        pass


def get_domain_stats() -> dict[str, dict]:
    """Compute avg confidence and quality per domain from session history."""
    mem     = load_session_memory()
    records = mem.get("records", [])
    stats: dict[str, list] = {}
    for r in records[-50:]:
        d = r.get("domain", "code")
        stats.setdefault(d, []).append((r.get("confidence", 0), r.get("quality", 0)))
    return {
        d: {
            "avg_confidence": round(sum(c for c, _ in v) / len(v), 3),
            "avg_quality":    round(sum(q for _, q in v) / len(v), 3),
            "n":              len(v),
        }
        for d, v in stats.items()
    }


# ── Auto-instrumentation (runs when ailex_core is imported) ───────────────────
# Patches _call_sync with: Cache + QualityGate + Logger + Metrics
# Zero-overhead if ailex_pilot is not available

def _try_instrument() -> None:
    """Silently instrument _call_sync if ailex_pilot stack is available."""
    global _call_sync
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ailex_pilot.pipeline_v2 import InstrumentedPipeline
        from ailex_pilot.observability import tracer, metrics

        _original = _call_sync
        if getattr(_original, "_instrumented", False):
            return   # already patched

        pipe = InstrumentedPipeline(api_key=API_KEY)

        def _instrumented(agent: str, task: str, domain: str,
                          context: str = "") -> dict:
            result = pipe.call_agent(agent, task, domain, context)
            return result.to_core_dict()

        _instrumented._instrumented = True  # type: ignore
        _call_sync = _instrumented          # type: ignore
        metrics.inc("startup.instrumented")
    except Exception:
        pass  # graceful degradation — core still works without instrumentation

_try_instrument()
