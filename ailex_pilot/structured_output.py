"""
AILEX — structured_output.py  (P1)
Structured agent outputs via Anthropic tool_use.
Replaces brittle | pipe-separator regex parsing with validated JSON schemas.

Every agent is forced to return structured data via tool_use.
If the API doesn't support it or the call fails → graceful fallback to regex.

Usage:
    from ailex_pilot.structured_output import StructuredAgentCall, AGENT_TOOL
    result = StructuredAgentCall().call("DEX", task, domain, client)
    # result.analysis, result.confidence, result.flags — all validated

Architecture:
    tool_use forces the model to return:
    {
        "analysis":       str,   # detailed expert analysis
        "recommendation": str,   # concrete actionable recommendation
        "risk":           str,   # what could go wrong
        "confidence":     float, # 0.0-1.0
        "flags":          list   # ["BREAKING_CHANGE", "NEEDS_REVIEW", ...]
    }
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Schema ────────────────────────────────────────────────────────────────────

AGENT_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "agent_response",
    "description": "Structured expert analysis and recommendation",
    "input_schema": {
        "type": "object",
        "required": ["analysis", "recommendation", "confidence"],
        "properties": {
            "analysis": {
                "type": "string",
                "description": "Detailed expert analysis of the request"
            },
            "recommendation": {
                "type": "string",
                "description": "Concrete actionable recommendation"
            },
            "risk": {
                "type": "string",
                "description": "Primary risk or concern",
                "default": ""
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confidence in this analysis (0.0-1.0)"
            },
            "flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Important flags: BREAKING_CHANGE, NEEDS_REVIEW, URGENT, etc.",
                "default": []
            },
        },
    },
}

# ORION synthesis tool (different schema — aggregates agent contributions)
ORION_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "synthesis_response",
    "description": "Meta-cognitive synthesis of all agent contributions",
    "input_schema": {
        "type": "object",
        "required": ["synthesis", "consensus", "confidence"],
        "properties": {
            "synthesis":    {"type": "string", "description": "Unified understanding from all agents"},
            "consensus":    {"type": "string", "description": "What all agents agree on"},
            "divergence":   {"type": "string", "description": "Where agents disagree and why", "default": ""},
            "open_question":{"type": "string", "description": "Key unresolved question", "default": ""},
            "confidence":   {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "action_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete next steps",
                "default": []
            },
        },
    },
}


@dataclass
class AgentOutput:
    """Validated, structured output from one agent call."""
    agent:          str
    model:          str
    analysis:       str
    recommendation: str
    risk:           str       = ""
    confidence:     float     = 0.75
    flags:          List[str] = field(default_factory=list)
    tokens_in:      int       = 0
    tokens_out:     int       = 0
    duration_ms:    int       = 0
    via_tool_use:   bool      = True   # False = fell back to regex

    @property
    def approach(self) -> str:
        """Compatibility alias used by legacy code."""
        return self.analysis

    @property
    def insight(self) -> str:
        """Compatibility alias."""
        return self.recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent":          self.agent,
            "model":          self.model,
            "approach":       self.analysis,
            "insight":        self.recommendation,
            "risk":           self.risk,
            "confidence":     round(self.confidence, 3),
            "flags":          self.flags,
            "tokens_in":      self.tokens_in,
            "tokens_out":     self.tokens_out,
            "duration_ms":    self.duration_ms,
            "via_tool_use":   self.via_tool_use,
        }


@dataclass
class SynthesisOutput:
    """ORION synthesis output."""
    synthesis:     str
    consensus:     str
    divergence:    str        = ""
    open_question: str        = ""
    confidence:    float      = 0.85
    action_items:  List[str]  = field(default_factory=list)
    tokens_in:     int        = 0
    tokens_out:    int        = 0
    via_tool_use:  bool       = True

    @property
    def approach(self) -> str: return self.synthesis
    @property
    def insight(self)  -> str: return self.consensus
    @property
    def risk(self)     -> str: return self.divergence


# ── Regex fallback parser (legacy compatibility) ───────────────────────────────

def _regex_parse(text: str, agent: str) -> Dict[str, Any]:
    """Fallback: extract fields from pipe-separated text (legacy format)."""
    out = {
        "analysis":       text[:200],
        "recommendation": text[:100],
        "risk":           "",
        "confidence":     0.70,
        "flags":          [],
    }
    for part in text.split("|"):
        p, u = part.strip(), part.strip().upper()
        if u.startswith("APPROACH:"):      out["analysis"]       = p[9:].strip()
        elif u.startswith("INSIGHT:"):     out["recommendation"] = p[8:].strip()
        elif u.startswith("SYNTHESIS:"):   out["analysis"]       = p[10:].strip()
        elif u.startswith("CONSENSUS:"):   out["recommendation"] = p[10:].strip()
        elif u.startswith("RISK:"):        out["risk"]           = p[5:].strip()
        elif u.startswith("CONFIDENCE:"):
            try:
                out["confidence"] = min(1.0, max(0.0,
                    float(re.search(r"[\d.]+", p[11:]).group())))  # type: ignore
            except Exception:
                pass
    return out


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _http(payload: Dict, api_key: str, timeout: int = 45) -> Dict:
    import os
    url = "https://api.anthropic.com/v1/messages"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ── Main class ────────────────────────────────────────────────────────────────

class StructuredAgentCall:
    """
    Makes a tool_use structured call to one agent.
    Falls back to regex parsing on failure.

    Example:
        caller = StructuredAgentCall(api_key="sk-...")
        out = caller.call("DEX", "Fix the login bug", "bug")
        print(out.confidence, out.flags)
    """

    RETRY_DELAYS = [0, 15, 45]  # seconds

    def __init__(self, api_key: str = ""):
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def call(
        self,
        agent:   str,
        task:    str,
        domain:  str,
        model:   str = "claude-sonnet-4-6",
        context: str = "",
        system:  str = "",
        max_tokens: int = 400,
    ) -> AgentOutput:
        """Call one agent with tool_use, return structured AgentOutput."""
        tool    = AGENT_TOOL_SCHEMA if agent != "ORION" else ORION_TOOL_SCHEMA
        sys_msg = system or f"You are {agent} — an expert AI agent. Use the agent_response tool to provide structured analysis."
        user_msg = (
            f"TASK: {task}\n"
            f"Domain: {domain}\n"
            f"Context: {context[:400]}\n\n"
            f"Provide your {agent} expert analysis using the tool."
        )
        payload = {
            "model":       model,
            "max_tokens":  max_tokens,
            "system":      sys_msg,
            "tools":       [tool],
            "tool_choice": {"type": "tool", "name": tool["name"]},
            "messages":    [{"role": "user", "content": user_msg}],
        }

        t0 = time.perf_counter()
        last_err = None

        for delay in self.RETRY_DELAYS:
            if delay:
                time.sleep(delay)
            try:
                resp     = _http(payload, self.api_key)
                dur_ms   = int((time.perf_counter() - t0) * 1000)
                usage    = resp.get("usage", {})
                tok_in   = usage.get("input_tokens", 0)
                tok_out  = usage.get("output_tokens", 0)

                # Extract tool_use result
                for block in resp.get("content", []):
                    if block.get("type") == "tool_use":
                        inp = block.get("input", {})
                        # Clamp confidence
                        conf = float(inp.get("confidence", 0.75))
                        conf = min(1.0, max(0.0, conf))
                        return AgentOutput(
                            agent=agent, model=model,
                            analysis=inp.get("analysis", ""),
                            recommendation=inp.get("recommendation", inp.get("synthesis", "")),
                            risk=inp.get("risk", inp.get("divergence", "")),
                            confidence=conf,
                            flags=inp.get("flags", inp.get("action_items", [])),
                            tokens_in=tok_in, tokens_out=tok_out,
                            duration_ms=dur_ms, via_tool_use=True,
                        )

                # Tool_use block not found — fall through to text fallback
                text = next((b["text"] for b in resp.get("content", [])
                             if b.get("type") == "text"), "")
                parsed = _regex_parse(text, agent)
                return AgentOutput(
                    agent=agent, model=model,
                    analysis=parsed["analysis"],
                    recommendation=parsed["recommendation"],
                    risk=parsed["risk"],
                    confidence=parsed["confidence"],
                    flags=parsed["flags"],
                    tokens_in=tok_in, tokens_out=tok_out,
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    via_tool_use=False,
                )

            except urllib.error.HTTPError as e:
                last_err = e
                if e.code == 429:
                    continue   # rate limit → retry
                # Non-retryable: fall through to fallback
                break
            except Exception as e:
                last_err = e
                break

        # Full fallback: return a low-confidence placeholder
        return AgentOutput(
            agent=agent, model=model,
            analysis=f"[API error: {last_err}]",
            recommendation="Unable to reach API. Manual review required.",
            risk="API unavailable",
            confidence=0.0,
            flags=["API_ERROR"],
            duration_ms=int((time.perf_counter() - t0) * 1000),
            via_tool_use=False,
        )

    def call_many(
        self,
        agents:  List[str],
        task:    str,
        domain:  str,
        models:  Dict[str, str] = {},
        **kw,
    ) -> List[AgentOutput]:
        """Call multiple agents in parallel using asyncio."""
        import asyncio, concurrent.futures

        def _call_one(agent: str) -> AgentOutput:
            return self.call(agent, task, domain,
                             model=models.get(agent, "claude-sonnet-4-6"), **kw)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as ex:
            futs = {ex.submit(_call_one, a): a for a in agents}
            return [f.result() for f in concurrent.futures.as_completed(futs)]


if __name__ == "__main__":
    import os
    caller = StructuredAgentCall()
    if not caller.api_key:
        print("Demo mode (no API key) — showing schema only")
        print(json.dumps(AGENT_TOOL_SCHEMA, indent=2))
    else:
        out = caller.call("DEX", "Fix broken login on mobile", "bug")
        print(f"Agent: {out.agent} | Confidence: {out.confidence:.2f} | via_tool_use: {out.via_tool_use}")
        print(f"Analysis: {out.analysis[:120]}")
        print(f"Flags: {out.flags}")
