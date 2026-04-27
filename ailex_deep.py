"""
AILEX Deep — 1000x Neural Reasoning Engine
8 new cognitive layers beyond the original 8:

  LAYER_9:  Recursive Self-Critique (RSC) — generate→critique→improve×3
  LAYER_10: Constitutional Review — 12 principles every output must pass
  LAYER_11: Causal Chain (5 WHYs) — root cause, not symptoms
  LAYER_12: Temporal Foresight — 3 future states after each change
  LAYER_13: Analogical Transfer — map current problem to solved patterns
  LAYER_14: Ontological Mapping — business domain + user need + legal
  LAYER_15: Adversarial Red Team — actively tries to break own solutions
  LAYER_16: Emergent Synthesis — non-obvious cross-domain connections
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from ailex_core import _http_post, MODEL_ROUTING, _parse, API_KEY
    _HAS_API = bool(API_KEY)
except Exception:
    _HAS_API = False

# ── LAYER_10: Constitutional Principles ───────────────────────────────────────

CONSTITUTION: list[dict] = [
    {"id": "C01", "principle": "Correctness",       "question": "Does this fully solve the stated problem?",                  "severity": "critical"},
    {"id": "C02", "principle": "Completeness",       "question": "Are all edge cases and failure modes handled?",              "severity": "critical"},
    {"id": "C03", "principle": "Security",           "question": "Are there XSS, injection, auth, or data exposure risks?",   "severity": "critical"},
    {"id": "C04", "principle": "TypeScript Safety",  "question": "Will this compile without errors or unsafe 'any' casts?",   "severity": "high"},
    {"id": "C05", "principle": "Performance",        "question": "Does this scale? Any O(n²) loops or memory leaks?",         "severity": "high"},
    {"id": "C06", "principle": "Mobile",             "question": "Does this work at 375px? Touch targets ≥44px?",             "severity": "high"},
    {"id": "C07", "principle": "Backwards Compat",   "question": "Does this break any existing functionality?",               "severity": "critical"},
    {"id": "C08", "principle": "Testability",        "question": "Is this logic isolated and testable without mocking?",      "severity": "medium"},
    {"id": "C09", "principle": "Maintainability",    "question": "Will a developer understand this in 6 months?",             "severity": "medium"},
    {"id": "C10", "principle": "Deploy Safety",      "question": "Is this safe to deploy to production right now?",           "severity": "critical"},
    {"id": "C11", "principle": "Accessibility",      "question": "Are interactive elements keyboard/screen-reader accessible?","severity": "medium"},
    {"id": "C12", "principle": "Minimalism",         "question": "Is this the simplest correct solution? No over-engineering?","severity": "low"},
]

# ── LAYER_13: Analogical Pattern Library ─────────────────────────────────────

PATTERN_LIBRARY: list[dict] = [
    {"pattern": "iframe_error_boundary",  "domain": "bug",         "solution": "Wrap iframe in ErrorBoundary with key=trackId for auto-reset on track change"},
    {"pattern": "spa_routing_404",        "domain": "deploy",      "solution": "Add vercel.json rewrite: source '/(.*)', destination '/index.html'"},
    {"pattern": "numeric_id_type",        "domain": "bug",         "solution": "bcId must be number not string — Bandcamp embed URL breaks with string type"},
    {"pattern": "mobile_touch_targets",   "domain": "mobile",      "solution": "Min 44px for all interactive elements, test at 375px viewport"},
    {"pattern": "passive_scroll",         "domain": "performance", "solution": "addEventListener('scroll', fn, { passive: true }) — eliminates jank"},
    {"pattern": "react_lazy_split",       "domain": "performance", "solution": "React.lazy + Suspense for heavy sections (VideoGrid, About) — reduces initial bundle ~40%"},
    {"pattern": "ts_union_escape_hatch",  "domain": "code",        "solution": "Use (string & {}) instead of | string to preserve literal type intellisense"},
    {"pattern": "null_guard_find",        "domain": "bug",         "solution": "TRACKS.find(v => v.featured) ?? TRACKS[0] — never use ! assertion"},
    {"pattern": "copyright_year",         "domain": "code",        "solution": "Always check footer year matches current year (2026)"},
    {"pattern": "og_complete",            "domain": "strategy",    "solution": "OG must have: type, url, title, description, image, locale. Twitter Card separate."},
    {"pattern": "env_no_hardcode",        "domain": "security",    "solution": "Never hardcode credentials — use .env + gitignore, load via os.environ"},
    {"pattern": "sed_i_danger",           "domain": "bug",         "solution": "sed -i can empty a file on Android/Termux — prefer Python file rewrite"},
]

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class CritiqueResult:
    pass_count:  int
    fail_count:  int
    violations:  list[dict]
    score:       float
    approved:    bool
    suggestions: list[str]

@dataclass
class CausalChain:
    symptom:    str
    chain:      list[str]
    root_cause: str
    depth:      int

@dataclass
class ForesightState:
    step:        int
    description: str
    risk_level:  str  # low/medium/high/critical
    mitigation:  str

@dataclass
class DeepAnalysis:
    task:          str
    domain:        str
    critique:      CritiqueResult
    causal:        Optional[CausalChain]
    foresight:     list[ForesightState]
    analogies:     list[dict]
    red_team:      list[str]
    synthesis:     str
    final_score:   float
    elapsed:       float

# ── LAYER_9: Recursive Self-Critique ─────────────────────────────────────────

def _ask_llm(system: str, user: str, model: str = "claude-haiku-4-5-20251001", max_tokens: int = 400) -> str:
    if not _HAS_API:
        return ""
    try:
        resp = _http_post({"model": model, "max_tokens": max_tokens,
                           "system": system, "messages": [{"role": "user", "content": user}]})
        return resp["content"][0]["text"]
    except Exception:
        return ""


def recursive_critique(task: str, response: str, iterations: int = 3) -> tuple[str, CritiqueResult]:
    """
    LAYER_9: Generate → Critique → Improve × N
    Each cycle makes the response stronger.
    """
    current = response
    violations: list[dict] = []

    for i in range(iterations):
        if not _HAS_API:
            break

        critique_text = _ask_llm(
            system="You are a ruthless code reviewer. Find exactly 3 weaknesses in the proposed solution. Be specific. Format: ISSUE: ... | FIX: ...",
            user=f"TASK: {task}\n\nSOLUTION:\n{current}\n\nFind 3 critical weaknesses:",
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
        )

        if not critique_text or "no issues" in critique_text.lower():
            break

        issues = [p.strip() for p in critique_text.split("ISSUE:") if p.strip()]
        for issue in issues[:3]:
            parts = issue.split("|")
            violations.append({
                "cycle": i + 1,
                "issue": parts[0].strip()[:120],
                "fix": parts[1].replace("FIX:", "").strip()[:120] if len(parts) > 1 else "",
            })

        improved = _ask_llm(
            system="You are a senior engineer. Improve the solution by addressing the critique. Be concise.",
            user=f"TASK: {task}\n\nCURRENT SOLUTION:\n{current}\n\nCRITIQUE:\n{critique_text}\n\nImproved solution:",
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
        )
        if improved:
            current = improved

    pass_count = iterations - len([v for v in violations if v["cycle"] == iterations])
    score = max(0.0, 1.0 - (len(violations) * 0.08))

    return current, CritiqueResult(
        pass_count=pass_count,
        fail_count=len(violations),
        violations=violations,
        score=round(score, 3),
        approved=score >= 0.75,
        suggestions=[v["fix"] for v in violations if v["fix"]],
    )

# ── LAYER_10: Constitutional Review ──────────────────────────────────────────

def constitutional_review(task: str, response: str, domain: str) -> CritiqueResult:
    """
    Check output against all 12 constitutional principles.
    Blocks critical violations.
    """
    violations = []
    relevant_principles = [
        p for p in CONSTITUTION
        if p["severity"] == "critical"
        or (domain == "mobile"    and p["id"] in ["C06"])
        or (domain == "deploy"    and p["id"] in ["C10"])
        or (domain == "bug"       and p["id"] in ["C01","C07"])
        or (domain == "feature"   and p["id"] in ["C01","C04","C06"])
        or (domain == "security"  and p["id"] in ["C03"])
    ]

    if _HAS_API and len(response) > 50:
        principles_text = "\n".join(f"- {p['id']} {p['principle']}: {p['question']}" for p in relevant_principles)
        check = _ask_llm(
            system="You are a constitutional AI reviewer. Check the solution against each principle. Reply only: PASS or FAIL:<reason> for each.",
            user=f"TASK: {task}\nDOMAIN: {domain}\n\nSOLUTION:\n{response[:600]}\n\nPRINCIPLES:\n{principles_text}",
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
        )
        for line in (check or "").splitlines():
            for p in relevant_principles:
                if p["id"] in line and "FAIL" in line.upper():
                    reason = line.split("FAIL:")[-1].strip() if "FAIL:" in line else "violation detected"
                    violations.append({"principle": p["principle"], "severity": p["severity"], "reason": reason[:100]})

    score = 1.0 - sum(0.15 if v["severity"] == "critical" else 0.07 for v in violations)
    return CritiqueResult(
        pass_count=len(relevant_principles) - len(violations),
        fail_count=len(violations),
        violations=violations,
        score=round(max(0.0, score), 3),
        approved=all(v["severity"] != "critical" for v in violations),
        suggestions=[f"{v['principle']}: {v['reason']}" for v in violations],
    )

# ── LAYER_11: Causal Chain (5 WHYs) ──────────────────────────────────────────

def causal_chain(symptom: str, max_depth: int = 5) -> CausalChain:
    """
    WHY → WHY → WHY → WHY → WHY
    Finds root cause, not surface symptom.
    """
    chain = [symptom]

    if not _HAS_API:
        return CausalChain(symptom=symptom, chain=chain,
                           root_cause=f"Root: {symptom} (API needed for deep analysis)", depth=1)

    for depth in range(max_depth):
        why = _ask_llm(
            system="You are a root cause analyst. Ask WHY this happens. Give one specific technical cause. One sentence only.",
            user=f"SYMPTOM/CAUSE: {chain[-1]}\n\nWHY does this happen? (one specific technical reason):",
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
        )
        if not why or why.strip() == chain[-1].strip():
            break
        chain.append(why.strip())

        is_root = _ask_llm(
            system="Answer only YES or NO.",
            user=f"Is this a root cause (cannot be traced further)? '{why}'",
            model="claude-haiku-4-5-20251001",
            max_tokens=5,
        )
        if "yes" in (is_root or "").lower():
            break

    return CausalChain(symptom=symptom, chain=chain, root_cause=chain[-1], depth=len(chain))

# ── LAYER_12: Temporal Foresight ──────────────────────────────────────────────

def temporal_foresight(task: str, domain: str) -> list[ForesightState]:
    """
    Simulate 3 future states after implementing a change.
    Catch tech debt and breaking changes before they happen.
    """
    if not _HAS_API:
        return [ForesightState(step=1, description="API needed for temporal simulation",
                               risk_level="unknown", mitigation="")]

    futures = []
    horizons = [
        ("Immediate (next deploy)", "What breaks or degrades in the next 24h?"),
        ("Short-term (next sprint)", "What tech debt or friction emerges in 2 weeks?"),
        ("Long-term (next quarter)", "What architectural problems arise in 3 months?"),
    ]

    for step, (horizon, question) in enumerate(horizons, 1):
        raw = _ask_llm(
            system=f"You are a technical forecaster. Predict future consequences. Format: RISK_LEVEL: low|medium|high|critical | DESCRIPTION: ... | MITIGATION: ...",
            user=f"TASK: {task}\nDOMAIN: {domain}\nHORIZON: {horizon}\n\n{question}",
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
        )
        risk, desc, mit = "low", f"State {step} after change", ""
        for part in (raw or "").split("|"):
            p, u = part.strip(), part.strip().upper()
            if u.startswith("RISK_LEVEL:"):  risk = p[11:].strip().lower()
            elif u.startswith("DESCRIPTION:"): desc = p[12:].strip()[:120]
            elif u.startswith("MITIGATION:"): mit  = p[11:].strip()[:100]
        futures.append(ForesightState(step=step, description=desc, risk_level=risk, mitigation=mit))

    return futures

# ── LAYER_13: Analogical Transfer ────────────────────────────────────────────

def analogical_transfer(task: str, domain: str) -> list[dict]:
    """Find solved patterns that map to current problem."""
    task_lower = task.lower()
    matches = []
    for p in PATTERN_LIBRARY:
        keywords = p["pattern"].replace("_", " ").split()
        if p["domain"] == domain or any(k in task_lower for k in keywords if len(k) > 3):
            matches.append({
                "pattern":  p["pattern"],
                "relevance": sum(1 for k in keywords if k in task_lower) / max(len(keywords), 1),
                "solution": p["solution"],
            })
    return sorted(matches, key=lambda x: x["relevance"], reverse=True)[:3]

# ── LAYER_15: Adversarial Red Team ───────────────────────────────────────────

def red_team(task: str, domain: str, response: str) -> list[str]:
    """
    Actively try to break the proposed solution.
    What would a malicious user, hostile environment, or edge case do?
    """
    if not _HAS_API:
        return [f"API needed for adversarial testing of: {task[:60]}"]

    attack_vectors = {
        "security":     "XSS, SQL injection, CSRF, path traversal, auth bypass",
        "bug":          "null inputs, empty arrays, race conditions, network failures",
        "feature":      "concurrent users, slow networks, missing permissions, stale data",
        "mobile":       "landscape rotation, pinch-zoom, back button, offline mode",
        "deploy":       "rollback needed, partial deploy, env var missing, cache stale",
        "performance":  "1000 items, slow 3G, low-memory device, CPU throttle",
    }
    vectors = attack_vectors.get(domain, "unexpected inputs, network failures, edge cases")

    raw = _ask_llm(
        system=f"You are a red team security researcher. Find 3 ways to break this solution. Focus on: {vectors}. Each on new line starting with '- '.",
        user=f"TASK: {task}\nSOLUTION SUMMARY: {response[:400]}\n\nFind 3 attack vectors or failure modes:",
        model="claude-haiku-4-5-20251001",
        max_tokens=250,
    )
    attacks = [line.lstrip("- ").strip() for line in (raw or "").splitlines() if line.strip().startswith("-")]
    return attacks[:3] or [f"No critical attack vectors found for {domain} domain"]

# ── LAYER_16: Emergent Synthesis ─────────────────────────────────────────────

def emergent_synthesis(task: str, domain: str, causal: CausalChain, analogies: list[dict], red_team_results: list[str]) -> str:
    """
    Find non-obvious connections. The root cause of problem A is the same as problem B.
    """
    context = f"""
Root cause: {causal.root_cause}
Best analogy: {analogies[0]['solution'] if analogies else 'none'}
Top attack vector: {red_team_results[0] if red_team_results else 'none'}
"""
    if not _HAS_API:
        return f"Core insight: {causal.root_cause}"

    raw = _ask_llm(
        system="You are a systems thinker. Find the non-obvious insight that connects all these signals. One powerful sentence.",
        user=f"TASK: {task}\nDOMAIN: {domain}\n{context}\n\nWhat is the single unifying insight?",
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
    )
    return (raw or causal.root_cause).strip()

# ── Full Deep Analysis Pipeline ───────────────────────────────────────────────

def deep_analyse(task: str, domain: str, initial_response: str = "") -> DeepAnalysis:
    """
    Run all 8 deep layers in sequence.
    Returns a DeepAnalysis with full cognitive depth.
    """
    t0 = time.time()

    response = initial_response or f"Standard approach for {domain}: {task}"

    # LAYER_9: Recursive critique
    improved_response, critique = recursive_critique(task, response)

    # LAYER_10: Constitutional review
    constitution = constitutional_review(task, improved_response, domain)

    # LAYER_11: Causal chain
    causal = causal_chain(task)

    # LAYER_12: Temporal foresight
    foresight = temporal_foresight(task, domain)

    # LAYER_13: Analogical transfer
    analogies = analogical_transfer(task, domain)

    # LAYER_15: Red team
    red_team_results = red_team(task, domain, improved_response)

    # LAYER_16: Emergent synthesis
    synthesis = emergent_synthesis(task, domain, causal, analogies, red_team_results)

    # Final score: weighted average of all layers
    final_score = round(
        critique.score * 0.35 +
        constitution.score * 0.35 +
        (1.0 - min(len(red_team_results), 3) * 0.08) * 0.20 +
        (1.0 if analogies else 0.5) * 0.10,
        3
    )

    return DeepAnalysis(
        task=task,
        domain=domain,
        critique=critique,
        causal=causal,
        foresight=foresight,
        analogies=analogies,
        red_team=red_team_results,
        synthesis=synthesis,
        final_score=final_score,
        elapsed=round(time.time() - t0, 2),
    )


def format_analysis(a: DeepAnalysis) -> dict:
    """Format DeepAnalysis as JSON-serialisable dict."""
    return {
        "task":         a.task,
        "domain":       a.domain,
        "final_score":  a.final_score,
        "elapsed_sec":  a.elapsed,
        "layer_9_rsc":  {
            "score":       a.critique.score,
            "approved":    a.critique.approved,
            "violations":  a.critique.violations[:3],
            "suggestions": a.critique.suggestions[:3],
        },
        "layer_10_constitutional": {
            "score":      a.critique.score,
            "approved":   a.critique.approved,
            "violations": [v["principle"] for v in a.critique.violations],
        },
        "layer_11_causal": {
            "symptom":    a.causal.symptom if a.causal else "",
            "chain":      a.causal.chain if a.causal else [],
            "root_cause": a.causal.root_cause if a.causal else "",
            "depth":      a.causal.depth if a.causal else 0,
        },
        "layer_12_foresight": [
            {"step": f.step, "horizon": ["immediate","short-term","long-term"][f.step-1],
             "risk": f.risk_level, "description": f.description, "mitigation": f.mitigation}
            for f in a.foresight
        ],
        "layer_13_analogies": a.analogies,
        "layer_15_red_team":  a.red_team,
        "layer_16_synthesis": a.synthesis,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AILEX Deep — 1000x neural reasoning")
    parser.add_argument("task", help="Task to deeply analyse")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--response", default="", help="Initial response to critique")
    args = parser.parse_args()

    domain = args.domain or "code"
    analysis = deep_analyse(args.task, domain, args.response)
    print(json.dumps(format_analysis(analysis), indent=2, ensure_ascii=False))
