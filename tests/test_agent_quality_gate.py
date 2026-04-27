"""Tests for P2 — agent_quality_gate.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ailex_pilot'))
import unittest
from ailex_pilot.structured_output import AgentOutput
from ailex_pilot.agent_quality_gate import AgentQualityGate, QualityReport


def _make(analysis="Good analysis with substance", recommendation="Use TypeScript instead",
          confidence=0.82, flags=None, risk=""):
    return AgentOutput(
        agent="DEX", model="claude-sonnet-4-6",
        analysis=analysis, recommendation=recommendation,
        risk=risk, confidence=confidence, flags=flags or []
    )


class TestQualityGateChecks(unittest.TestCase):
    def setUp(self):
        self.gate = AgentQualityGate()

    def test_good_output_passes(self):
        out = _make(
            analysis="The authentication bug is caused by missing token validation in AuthMiddleware. The JWT library version 4.x changed the API signature.",
            recommendation="Update `verifyToken` to use the new `verify()` async API and add explicit null check on line 42.",
            confidence=0.88
        )
        report = self.gate.evaluate(out)
        self.assertTrue(report.passes)
        self.assertGreater(report.score, 0.65)

    def test_empty_output_fails(self):
        out = _make(analysis="", recommendation="", confidence=0.5)
        report = self.gate.evaluate(out)
        self.assertFalse(report.passes)
        self.assertLess(report.score, 0.5)  # fails, but C3/C4/C5 still pass

    def test_generic_phrase_fails_completeness(self):
        out = _make(
            analysis="I cannot determine the issue without more context.",
            recommendation="Please provide more information.",
            confidence=0.9
        )
        report = self.gate.evaluate(out)
        # Should fail completeness
        ids = [c.id for c in report.checks if not c.passed]
        self.assertIn("C1", ids)

    def test_no_action_verb_fails_actionability(self):
        out = _make(
            analysis="The component has several issues that need attention in the codebase.",
            recommendation="The situation requires consideration of multiple factors.",
            confidence=0.70
        )
        report = self.gate.evaluate(out)
        ids = [c.id for c in report.checks if not c.passed]
        self.assertIn("C2", ids)

    def test_perfect_confidence_flagged(self):
        out = _make(analysis="Fix the bug", recommendation="Remove line 42", confidence=1.0)
        report = self.gate.evaluate(out)
        ids = [c.id for c in report.checks if not c.passed]
        self.assertIn("C3", ids)

    def test_zero_confidence_flagged(self):
        out = _make(analysis="Analysis text here", recommendation="Use this approach", confidence=0.0)
        report = self.gate.evaluate(out)
        ids = [c.id for c in report.checks if not c.passed]
        self.assertIn("C3", ids)

    def test_placeholder_fails(self):
        out = _make(
            analysis="Replace {COMPONENT_NAME} with the actual component",
            recommendation="Update [TODO] in the codebase",
            confidence=0.75
        )
        report = self.gate.evaluate(out)
        ids = [c.id for c in report.checks if not c.passed]
        self.assertIn("C5", ids)

    def test_api_error_output_fails(self):
        out = _make(analysis="[API error: timeout]", recommendation="Manual review required",
                    confidence=0.0, flags=["API_ERROR"])
        report = self.gate.evaluate(out)
        self.assertFalse(report.passes)
        self.assertIn("LOW_QUALITY", out.flags)

    def test_score_is_between_0_and_1(self):
        out = _make()
        report = self.gate.evaluate(out)
        self.assertGreaterEqual(report.score, 0.0)
        self.assertLessEqual(report.score, 1.0)

    def test_overconfident_flag_added(self):
        out = _make(analysis="X", recommendation="Y", confidence=0.95)
        report = self.gate.evaluate(out)
        # Score will be low (short output) but confidence high → OVERCONFIDENT flag
        if report.score < 0.55:
            self.assertIn("OVERCONFIDENT", out.flags)

    def test_evaluate_batch(self):
        outputs = [_make(confidence=0.8 + i*0.02) for i in range(3)]
        reports = self.gate.evaluate_batch(outputs)
        self.assertEqual(len(reports), 3)
        for r in reports:
            self.assertIsInstance(r, QualityReport)

    def test_summary_string(self):
        outputs  = [_make(), _make(analysis="", recommendation="", confidence=0.5)]
        reports  = self.gate.evaluate_batch(outputs)
        summary  = self.gate.summary(reports)
        self.assertIn("AgentQualityGate", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
