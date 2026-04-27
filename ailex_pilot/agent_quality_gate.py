"""
AILEX — agent_quality_gate.py  (P2)
Automatic quality evaluation of agent outputs before use.
Like html_qa.py for websites, but for agent responses.

Every agent output passes through 5 checks:
    C1 completeness    — analysis is substantive (not generic)
    C2 actionability   — recommendation is concrete and specific
    C3 confidence_cal  — confidence matches output quality
    C4 coherence       — analysis and recommendation are consistent
    C5 no_placeholders — no unfilled template markers

Responses below threshold → auto-retry with improved prompt.
Max 2 retries. If still failing → log + accept with LOW_QUALITY flag.

Usage:
    from ailex_pilot.agent_quality_gate import AgentQualityGate
    gate = AgentQualityGate()
    result = gate.evaluate(agent_output)
    if not result.passes: print(result.issues)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .structured_output import AgentOutput


# ── Check results ─────────────────────────────────────────────────────────────

@dataclass
class QACheck:
    id:       str
    name:     str
    passed:   bool
    score:    float       # 0.0 – 1.0
    detail:   str = ""


@dataclass
class QualityReport:
    output:     AgentOutput
    checks:     List[QACheck]
    score:      float         # 0.0 – 1.0 (weighted average)
    passes:     bool          # True if score >= threshold
    issues:     List[str]     # human-readable problems
    flags_added: List[str]    # flags appended to output


# ── The gate ──────────────────────────────────────────────────────────────────

class AgentQualityGate:
    """
    5-check quality evaluator for agent outputs.
    Threshold 0.65 = pass. Below → retry or flag.

    Checks are lightweight (no API calls) — pure heuristic.
    Designed to run in <1ms per output.
    """

    THRESHOLD     = 0.65     # minimum score to pass
    RETRY_MAX     = 2        # max auto-retries on failure
    WEIGHTS       = {
        "C1": 0.30,  # completeness is most important
        "C2": 0.30,  # actionability is equally important
        "C3": 0.15,  # confidence calibration
        "C4": 0.15,  # coherence
        "C5": 0.10,  # no placeholders
    }

    # Generic non-answers that signal the agent gave up
    GENERIC_PHRASES = [
        "i cannot", "i can't", "i don't know", "not sure", "no information",
        "unable to", "i would need", "please provide", "more context",
        "as an ai", "i am an ai", "this is complex",
    ]

    # Unfilled template markers
    PLACEHOLDER_RE = re.compile(r'\{[A-Z_]+\}|\[INSERT\]|\[TODO\]|\[PLACEHOLDER\]|XXX')

    def evaluate(self, output: AgentOutput) -> QualityReport:
        """Run all checks and return a QualityReport."""
        checks = [
            self._check_completeness(output),
            self._check_actionability(output),
            self._check_confidence_calibration(output),
            self._check_coherence(output),
            self._check_no_placeholders(output),
        ]

        # Weighted score
        score = sum(
            c.score * self.WEIGHTS[c.id]
            for c in checks
        )

        passes     = score >= self.THRESHOLD
        issues     = [f"[{c.id}] {c.detail}" for c in checks if not c.passed]
        flags_added = []

        if not passes:
            flags_added.append("LOW_QUALITY")
        if score < 0.40:
            flags_added.append("VERY_LOW_QUALITY")
        if output.confidence > 0.85 and score < 0.55:
            flags_added.append("OVERCONFIDENT")

        # Append flags to output
        output.flags.extend(flags_added)

        return QualityReport(
            output=output,
            checks=checks,
            score=round(score, 3),
            passes=passes,
            issues=issues,
            flags_added=flags_added,
        )

    def evaluate_batch(self, outputs: List[AgentOutput]) -> List[QualityReport]:
        return [self.evaluate(o) for o in outputs]

    def summary(self, reports: List[QualityReport]) -> str:
        passed = sum(1 for r in reports if r.passes)
        avg    = sum(r.score for r in reports) / max(1, len(reports))
        lines  = [
            f"AgentQualityGate: {passed}/{len(reports)} passed | avg score {avg:.2f}",
        ]
        for r in reports:
            icon = "✅" if r.passes else "⚠️ "
            lines.append(f"  {icon} {r.output.agent:<6} {r.score:.2f} | {', '.join(r.issues) or 'OK'}")
        return "\n".join(lines)

    # ── Individual checks ──────────────────────────────────────────────────────

    def _check_completeness(self, out: AgentOutput) -> QACheck:
        """C1: Analysis is substantive — not empty, not generic."""
        text = (out.analysis + " " + out.recommendation).lower()

        # Too short
        if len(text.strip()) < 30:
            return QACheck("C1", "completeness", False, 0.0,
                           "Output too short (< 30 chars)")

        # Generic non-answers
        for phrase in self.GENERIC_PHRASES:
            if phrase in text:
                return QACheck("C1", "completeness", False, 0.3,
                               f"Generic non-answer detected: '{phrase}'")

        # Missing error context (if API error)
        if "API_ERROR" in out.flags:
            return QACheck("C1", "completeness", False, 0.0, "API error — no content")

        # Length heuristic: good analysis is ≥80 chars
        score = min(1.0, len(text) / 200)
        return QACheck("C1", "completeness", score >= 0.5, score)

    def _check_actionability(self, out: AgentOutput) -> QACheck:
        """C2: Recommendation has a concrete action verb."""
        rec = out.recommendation.lower()

        if len(rec.strip()) < 15:
            return QACheck("C2", "actionability", False, 0.1,
                           "Recommendation too vague/short")

        # Action verbs that signal concrete recommendation
        ACTION_VERBS = [
            "use ", "add ", "remove ", "replace ", "update ", "create ",
            "implement ", "refactor ", "extract ", "move ", "rename ",
            "fix ", "change ", "set ", "define ", "wrap ", "split ",
            "merge ", "delete ", "install ", "configure ", "migrate ",
            "enable ", "disable ", "convert ", "test ", "deploy ",
        ]
        has_action = any(v in rec for v in ACTION_VERBS)

        score = 0.9 if has_action else 0.4
        return QACheck("C2", "actionability", has_action, score,
                       "" if has_action else "No concrete action verb found in recommendation")

    def _check_confidence_calibration(self, out: AgentOutput) -> QACheck:
        """C3: Confidence score isn't pathologically high or low."""
        c = out.confidence

        # Perfectly round numbers suggest not thinking about it
        if c in {0.0, 1.0}:
            return QACheck("C3", "confidence_calibration", False, 0.3,
                           f"Suspiciously extreme confidence: {c}")

        # Very high confidence on very short outputs is a red flag
        if c > 0.92 and len(out.analysis) < 60:
            return QACheck("C3", "confidence_calibration", False, 0.5,
                           f"High confidence ({c:.2f}) on short output")

        # API error shouldn't have confidence > 0.1
        if "API_ERROR" in out.flags and c > 0.1:
            return QACheck("C3", "confidence_calibration", False, 0.0,
                           "API error but non-zero confidence")

        return QACheck("C3", "confidence_calibration", True, 1.0)

    def _check_coherence(self, out: AgentOutput) -> QACheck:
        """C4: Analysis and recommendation aren't contradictory."""
        a = out.analysis.lower()
        r = out.recommendation.lower()

        # Check for direct contradiction signals
        CONTRADICTION_PAIRS = [
            ("good", "bad"),
            ("safe", "dangerous"),
            ("simple", "complex"),
            ("works", "broken"),
            ("success", "failure"),
        ]
        for pos, neg in CONTRADICTION_PAIRS:
            if pos in a and neg in r and pos not in r:
                return QACheck("C4", "coherence", False, 0.5,
                               f"Possible contradiction: analysis says '{pos}' but recommendation says '{neg}'")

        # If confidence > 0.9 but risk is non-empty, that's also suspicious
        if out.confidence > 0.9 and len(out.risk) > 50:
            return QACheck("C4", "coherence", True, 0.75,
                           "High confidence with significant risk — double-check")

        return QACheck("C4", "coherence", True, 1.0)

    def _check_no_placeholders(self, out: AgentOutput) -> QACheck:
        """C5: No unfilled template markers in output."""
        full_text = f"{out.analysis} {out.recommendation} {out.risk}"
        matches   = self.PLACEHOLDER_RE.findall(full_text)

        if matches:
            return QACheck("C5", "no_placeholders", False, 0.0,
                           f"Unfilled placeholders: {matches[:3]}")
        return QACheck("C5", "no_placeholders", True, 1.0)


# ── Retry wrapper ─────────────────────────────────────────────────────────────

class QualityGuardedCall:
    """
    Wraps StructuredAgentCall with automatic quality gating and retry.

    Example:
        caller = QualityGuardedCall(api_key="sk-...")
        output = caller.call("DEX", "Fix the login bug", "bug")
        # If first attempt scores < 0.65 → auto-retry with enriched prompt
    """

    def __init__(self, api_key: str = ""):
        from .structured_output import StructuredAgentCall
        self.caller = StructuredAgentCall(api_key=api_key)
        self.gate   = AgentQualityGate()

    def call(
        self,
        agent:      str,
        task:       str,
        domain:     str,
        model:      str = "claude-sonnet-4-6",
        context:    str = "",
        max_tokens: int = 400,
    ) -> Tuple[AgentOutput, QualityReport]:
        """Call agent, evaluate, retry if needed. Returns (output, report)."""
        best_out    = None
        best_report = None

        for attempt in range(AgentQualityGate.RETRY_MAX + 1):
            # Enrich prompt on retries
            enriched_context = context
            if attempt > 0:
                prev_issues = best_report.issues if best_report else []
                enriched_context = (
                    f"{context}\n\n[RETRY {attempt}: Previous attempt had issues: "
                    f"{'; '.join(prev_issues[:2])}. Be more specific and concrete.]"
                )

            out    = self.caller.call(agent, task, domain, model,
                                      enriched_context, max_tokens=max_tokens)
            report = self.gate.evaluate(out)

            if best_out is None or report.score > best_report.score:  # type: ignore
                best_out    = out
                best_report = report

            if report.passes:
                break   # good enough — don't retry

        return best_out, best_report  # type: ignore


if __name__ == "__main__":
    from .structured_output import AgentOutput

    # Test with a synthetic output
    gate = AgentQualityGate()

    good = AgentOutput(
        agent="DEX", model="claude-sonnet-4-6",
        analysis="The login bug is caused by a missing null check in AuthMiddleware.validate(). When the JWT token is expired, the function returns undefined instead of throwing, which causes downstream code to fail silently.",
        recommendation="Add explicit null check: `if (!token) throw new UnauthorizedException('Token expired')` in AuthMiddleware.validate() at line 42.",
        risk="Breaking change for callers that catch undefined returns",
        confidence=0.88, flags=[],
    )

    bad = AgentOutput(
        agent="QUINN", model="claude-haiku-4-5-20251001",
        analysis="I cannot determine the issue without more context.",
        recommendation="Please provide more information.",
        confidence=1.0, flags=[],
    )

    for out in [good, bad]:
        r = gate.evaluate(out)
        print(f"\n{out.agent}: score={r.score:.2f} passes={r.passes}")
        if r.issues: print(f"  Issues: {r.issues}")
