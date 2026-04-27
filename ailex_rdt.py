"""
AILEX RDT — Recurrent Depth Transformer Engine
Inspired by: OpenMythos (Kye Gomez) + Anthropic Mythos architecture hypothesis

Key insight from OpenMythos research:
  "A 770M-parameter RDT matches a 1.3B standard transformer.
   The same weights applied iteratively outperform more parameters."

AILEX translation:
  "The same agent queried iteratively with a growing hidden state
   outperforms many agents queried once in parallel."

Architecture:
  PRELUDE   — encode task into initial hidden state h0
  RECURRENT — apply block T times: h(t+1) = integrate(h(t), agent_signal, depth=t)
  CODA      — decode final hidden state hT into response

Adaptive Computation Time (ACT):
  T is not fixed. Halt when confidence > threshold OR max_depth reached.
  Simple tasks: T = 2-4. Complex: T = 8-16. Vague: T up to 24.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from ailex_core import _http_post, API_KEY, MODEL_ROUTING
    _HAS_API = bool(API_KEY)
except Exception:
    _HAS_API = False

# ── Domain depth curves (from v5 — battle-tested) ───────────────────────────

DEPTH_CURVES: dict[str, dict] = {
    "documentation": {"midpoint": 2.0, "steepness": 2.5, "max": 4},
    "bug":           {"midpoint": 3.0, "steepness": 2.0, "max": 5},
    "deploy":        {"midpoint": 3.5, "steepness": 1.8, "max": 6},
    "code":          {"midpoint": 4.0, "steepness": 1.5, "max": 7},
    "performance":   {"midpoint": 4.5, "steepness": 1.5, "max": 8},
    "mobile":        {"midpoint": 4.0, "steepness": 1.8, "max": 7},
    "testing":       {"midpoint": 3.0, "steepness": 2.0, "max": 5},
    "feature":       {"midpoint": 5.0, "steepness": 1.2, "max": 10},
    "refactor":      {"midpoint": 5.0, "steepness": 1.3, "max": 9},
    "security":      {"midpoint": 6.0, "steepness": 1.0, "max": 12},
    "design":        {"midpoint": 5.5, "steepness": 1.2, "max": 10},
    "architecture":  {"midpoint": 7.0, "steepness": 0.9, "max": 14},
    "strategy":      {"midpoint": 7.0, "steepness": 0.9, "max": 14},
    "philosophy":    {"midpoint": 8.0, "steepness": 0.8, "max": 18},
    "science":       {"midpoint": 7.5, "steepness": 0.9, "max": 16},
    "art":           {"midpoint": 6.0, "steepness": 1.1, "max": 12},
    "universal":     {"midpoint": 9.0, "steepness": 0.7, "max": 24},
    "vague":         {"midpoint": 8.0, "steepness": 0.7, "max": 16},
}

ACT_THRESHOLD  = 0.97   # halt when confidence reaches this
HALT_THRESHOLD = 0.99   # emergency halt

# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class HiddenState:
    """The recurrent hidden state — carries information between loops."""
    task:        str
    domain:      str
    loop:        int         = 0
    confidence:  float       = 0.0
    quality:     float       = 0.0
    insights:    list[str]   = field(default_factory=list)
    signals:     list[dict]  = field(default_factory=list)   # agent contributions per loop
    remainder:   float       = 1.0   # ACT remainder (Graves 2016)
    halted:      bool        = False
    accumulated: float       = 0.0   # ACT accumulated output
    phase:       str         = "exploration"   # exploration → refinement → precision


@dataclass
class LoopSignal:
    """Output of one recurrent loop."""
    loop:       int
    phase:      str
    agents:     list[str]
    insight:    str
    confidence: float
    halt_prob:  float
    tokens:     int


@dataclass
class RDTResult:
    """Final decoded output after all loops."""
    task:        str
    domain:      str
    loops_run:   int
    max_loops:   int
    final_state: HiddenState
    loop_trace:  list[LoopSignal]
    synthesis:   str
    confidence:  float
    quality:     float
    elapsed:     float
    api_used:    bool

# ── Agent selection per loop phase ───────────────────────────────────────────

PHASE_AGENTS: dict[str, dict[str, list[str]]] = {
    "exploration": {
        "bug":         ["DEX", "QUINN"],
        "feature":     ["DEX", "NOVA", "ARIA"],
        "deploy":      ["FELIX", "QUINN"],
        "architecture":["ARIA", "SAGE"],
        "science":     ["VEGA", "NEWTON"],
        "philosophy":  ["SAGE", "SOCRATES"],
        "art":         ["MUSE", "AURORA"],
        "strategy":    ["TITAN", "MINERVA"],
        "universal":   ["ORION", "NEXUS"],
    },
    "refinement": {
        "bug":         ["ARIA", "DEX"],
        "feature":     ["QUINN", "UMA", "ARIA"],
        "deploy":      ["ARIA", "FELIX"],
        "architecture":["DEX", "QUINN"],
        "science":     ["PYTHIA", "DARWIN"],
        "philosophy":  ["HEGEL", "LOGOS"],
        "art":         ["PROMETHEUS", "ECHO"],
        "strategy":    ["CAESAR", "MERCURY"],
        "universal":   ["ATLAS", "CHAOS"],
    },
    "precision": {
        "bug":         ["DEX", "QUINN", "ARIA"],
        "feature":     ["DEX", "QUINN", "UMA"],
        "deploy":      ["FELIX", "QUINN", "DEX"],
        "architecture":["ARIA", "DEX", "QUINN"],
        "science":     ["NEWTON", "VEGA", "PYTHIA"],
        "philosophy":  ["SAGE", "SPINOZA", "LOGOS"],
        "art":         ["MUSE", "AURORA", "PROMETHEUS"],
        "strategy":    ["TITAN", "MINERVA", "ORION"],
        "universal":   ["ORION", "SAGE", "NEXUS"],
    },
}

def _get_agents(phase: str, domain: str) -> list[str]:
    phase_map = PHASE_AGENTS.get(phase, PHASE_AGENTS["exploration"])
    return phase_map.get(domain, phase_map.get("universal", ["DEX", "ARIA", "ORION"]))

# ── Sigmoid ACT halt probability (Graves 2016 + AILEX domain curves) ─────────

def _sigmoid(x: float, midpoint: float, steepness: float) -> float:
    return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))

def _halt_probability(loop: int, domain: str, confidence: float) -> float:
    curve   = DEPTH_CURVES.get(domain, DEPTH_CURVES["code"])
    depth_p = _sigmoid(loop, curve["midpoint"], curve["steepness"])
    conf_p  = confidence ** 2.5
    return min(0.99, (depth_p * 0.5 + conf_p * 0.5))

def _determine_phase(loop: int, max_loops: int) -> str:
    frac = loop / max(max_loops, 1)
    if frac < 0.33: return "exploration"
    if frac < 0.67: return "refinement"
    return "precision"

# ── PRELUDE: encode task into h0 ──────────────────────────────────────────────

def prelude(task: str, domain: str) -> HiddenState:
    """
    PRELUDE — runs once. Encodes the task into an initial hidden state.
    Extracts: intent keywords, domain signals, initial confidence estimate.
    """
    keywords = [w for w in task.lower().split()
                if len(w) > 3 and w not in {"this","that","with","from","have","been","will","your","into","about"}]
    target = keywords[1] if len(keywords) > 1 else (keywords[0] if keywords else domain)

    initial_conf = {
        "bug": 0.35, "feature": 0.25, "deploy": 0.40,
        "architecture": 0.20, "science": 0.20, "philosophy": 0.15,
        "art": 0.25, "strategy": 0.20, "universal": 0.15,
    }.get(domain, 0.30)

    curve    = DEPTH_CURVES.get(domain, DEPTH_CURVES["code"])
    max_loop = curve["max"]

    return HiddenState(
        task=task, domain=domain, loop=0,
        confidence=initial_conf, quality=0.0,
        insights=[f"[PRELUDE] Target: {target} | Domain: {domain} | Max depth: {max_loop}"],
        signals=[], remainder=1.0, halted=False, accumulated=0.0,
        phase="exploration",
    )

# ── RECURRENT BLOCK — runs T times ────────────────────────────────────────────

def _run_recurrent_block(h: HiddenState, loop: int, max_loops: int) -> LoopSignal:
    """
    One iteration of the recurrent block.
    h(t+1) = integrate(h(t), agent_signal(t), depth=t)
    """
    phase  = _determine_phase(loop, max_loops)
    agents = _get_agents(phase, h.domain)

    if _HAS_API:
        insight, confidence = _api_loop(h, loop, phase, agents)
    else:
        insight, confidence = _sim_loop(h, loop, phase, agents)

    # Update hidden state — exponential moving average
    alpha         = 0.3 + (loop / max(max_loops, 1)) * 0.4   # grows with depth
    h.confidence  = h.confidence * (1 - alpha) + confidence * alpha
    h.quality     = min(1.0, h.quality + confidence * 0.08)
    h.insights.append(f"[L{loop:02d}|{phase[:3].upper()}] {insight[:120]}")
    h.phase       = phase

    halt_p = _halt_probability(loop, h.domain, h.confidence)

    # ACT accumulation (Graves 2016 corrected)
    p_halt   = halt_p * h.remainder
    h.accumulated += p_halt * h.confidence
    h.remainder   *= (1.0 - halt_p)

    return LoopSignal(
        loop=loop, phase=phase, agents=agents,
        insight=insight, confidence=confidence,
        halt_prob=halt_p, tokens=len(insight.split()) * 2,
    )


def _api_loop(h: HiddenState, loop: int, phase: str, agents: list[str]) -> tuple[str, float]:
    """Real API call for one recurrent loop."""
    ctx = "\n".join(h.insights[-3:]) if h.insights else ""
    system = (
        f"You are AILEX loop {loop} — {phase} phase. "
        f"Agents: {', '.join(agents)}. "
        f"Current confidence: {h.confidence:.2f}. "
        f"Build on prior context. Add ONE new non-redundant insight. "
        f"Format: INSIGHT: ... | CONFIDENCE: 0.X"
    )
    user = f"TASK: {h.task}\nDOMAIN: {h.domain}\nPRIOR:\n{ctx}\n\nNext insight:"
    try:
        resp = _http_post({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 150,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        })
        text = resp["content"][0]["text"]
        insight    = text.split("|")[0].replace("INSIGHT:", "").strip()
        conf_str   = text.split("CONFIDENCE:")[-1].strip()[:4]
        confidence = float(conf_str) if conf_str.replace(".", "").isdigit() else 0.78
        return insight[:150], min(1.0, max(0.0, confidence))
    except Exception:
        return _sim_loop(h, loop, phase, agents)


def _sim_loop(h: HiddenState, loop: int, phase: str, agents: list[str]) -> tuple[str, float]:
    """Contextual simulation when API unavailable."""
    keywords = h.task.lower().split()
    target   = next((w for w in keywords if len(w) > 4), h.domain)
    templates = {
        "exploration": f"Initial signal: {target} requires {h.domain} approach — identify key constraints",
        "refinement":  f"Refined: {target} — validate assumptions, check edge cases, tighten scope",
        "precision":   f"Precision: exact solution for {target} — implementation-ready, validated, ship-safe",
    }
    conf_by_loop = min(0.95, 0.45 + loop * 0.06)
    return templates.get(phase, f"Loop {loop}: processing {target}"), conf_by_loop

# ── CODA — decode final hidden state ──────────────────────────────────────────

def coda(h: HiddenState, trace: list[LoopSignal]) -> str:
    """
    CODA — runs once after all loops.
    Decodes accumulated hidden state into final human-readable synthesis.
    """
    key_insights = [s for s in h.insights if not s.startswith("[PRELUDE]")]
    depth_used   = len(trace)
    best_loop    = max(trace, key=lambda s: s.confidence) if trace else None

    synthesis = (
        f"RDT synthesis after {depth_used} loops "
        f"(confidence={h.confidence:.3f}, quality={h.quality:.3f}): "
    )

    if best_loop:
        synthesis += best_loop.insight

    if _HAS_API and key_insights:
        try:
            resp = _http_post({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "system": "You are ORION — the CODA synthesiser. Produce ONE clear, actionable synthesis from the loop trace. 2 sentences max.",
                "messages": [{"role": "user", "content": f"TASK: {h.task}\nDOMAIN: {h.domain}\nLOOP INSIGHTS:\n" + "\n".join(key_insights[-5:]) + "\n\nSynthesise:"}],
            })
            synthesis = resp["content"][0]["text"].strip()
        except Exception:
            pass

    return synthesis

# ── FULL RDT PIPELINE ─────────────────────────────────────────────────────────

def rdt_run(task: str, domain: str, force_depth: int = 0) -> RDTResult:
    """
    Full Recurrent Depth Transformer pipeline:
    PRELUDE → [RECURRENT × T] → CODA

    Adaptive depth: halts when confidence > ACT_THRESHOLD.
    Max depth from domain curve.
    """
    t0      = time.time()
    curve   = DEPTH_CURVES.get(domain, DEPTH_CURVES["code"])
    max_T   = force_depth or curve["max"]

    h     = prelude(task, domain)
    trace: list[LoopSignal] = []

    for loop in range(1, max_T + 1):
        h.loop = loop
        signal = _run_recurrent_block(h, loop, max_T)
        trace.append(signal)

        # ACT halt condition
        if signal.halt_prob >= HALT_THRESHOLD or h.remainder < 0.01:
            h.halted = True
            break

        if h.confidence >= ACT_THRESHOLD and loop >= 2:
            h.halted = True
            break

    synthesis = coda(h, trace)

    return RDTResult(
        task=task,
        domain=domain,
        loops_run=len(trace),
        max_loops=max_T,
        final_state=h,
        loop_trace=trace,
        synthesis=synthesis,
        confidence=h.confidence,
        quality=h.quality,
        elapsed=round(time.time() - t0, 3),
        api_used=_HAS_API,
    )


def format_rdt(r: RDTResult, verbose: bool = False) -> dict:
    out: dict = {
        "task":        r.task,
        "domain":      r.domain,
        "loops_run":   r.loops_run,
        "max_loops":   r.max_loops,
        "confidence":  round(r.confidence, 4),
        "quality":     round(r.quality, 4),
        "synthesis":   r.synthesis,
        "elapsed_sec": r.elapsed,
        "api_used":    r.api_used,
        "halted_early":r.final_state.halted,
    }
    if verbose:
        out["loop_trace"] = [
            {"loop": s.loop, "phase": s.phase, "agents": s.agents,
             "confidence": round(s.confidence, 3), "halt_prob": round(s.halt_prob, 3),
             "insight": s.insight[:100]}
            for s in r.loop_trace
        ]
        out["hidden_state_insights"] = r.final_state.insights
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AILEX RDT — Recurrent Depth Transformer")
    parser.add_argument("task",      help="Task to reason about")
    parser.add_argument("--domain",  default="code")
    parser.add_argument("--depth",   type=int, default=0, help="Force fixed depth (0=adaptive)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = rdt_run(args.task, args.domain, args.depth)
    print(json.dumps(format_rdt(result, args.verbose), indent=2, ensure_ascii=False))
