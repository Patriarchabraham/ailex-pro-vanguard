"""Tests for P1 — structured_output.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ailex_pilot'))
import unittest
from ailex_pilot.structured_output import (
    AgentOutput, StructuredAgentCall, AGENT_TOOL_SCHEMA, ORION_TOOL_SCHEMA, _regex_parse
)


class TestAgentOutput(unittest.TestCase):
    def setUp(self):
        self.out = AgentOutput(
            agent="DEX", model="claude-sonnet-4-6",
            analysis="Add null check in AuthMiddleware",
            recommendation="Use `if (!token) throw UnauthorizedException()`",
            risk="Breaking change for callers expecting undefined",
            confidence=0.88, flags=["BREAKING_CHANGE"],
        )

    def test_to_dict_keys(self):
        d = self.out.to_dict()
        for key in ["agent","model","approach","insight","risk","confidence","flags"]:
            self.assertIn(key, d)

    def test_aliases(self):
        self.assertEqual(self.out.approach, self.out.analysis)
        self.assertEqual(self.out.insight,  self.out.recommendation)

    def test_confidence_range(self):
        self.assertGreaterEqual(self.out.confidence, 0.0)
        self.assertLessEqual(self.out.confidence, 1.0)


class TestRegexFallback(unittest.TestCase):
    def test_pipe_format(self):
        text = "APPROACH: add null check | RISK: breaking change | INSIGHT: throw exception | CONFIDENCE: 0.85"
        parsed = _regex_parse(text, "DEX")
        self.assertIn("null", parsed["analysis"].lower())
        self.assertAlmostEqual(parsed["confidence"], 0.85, places=2)

    def test_partial_format(self):
        text = "APPROACH: fix the bug | CONFIDENCE: 0.72"
        parsed = _regex_parse(text, "DEX")
        self.assertIn("fix", parsed["analysis"].lower())
        self.assertAlmostEqual(parsed["confidence"], 0.72, places=2)

    def test_no_format_fallback(self):
        text = "Just some random text without format markers"
        parsed = _regex_parse(text, "DEX")
        self.assertIsInstance(parsed["analysis"], str)
        self.assertIsInstance(parsed["confidence"], float)

    def test_confidence_clamp(self):
        text = "CONFIDENCE: 1.5"  # out of range
        parsed = _regex_parse(text, "DEX")
        # Regex finds 1.5 but caller should clamp — raw parse allows it
        self.assertIsInstance(parsed["confidence"], float)


class TestToolSchema(unittest.TestCase):
    def test_agent_tool_has_required_fields(self):
        props = AGENT_TOOL_SCHEMA["input_schema"]["properties"]
        for field in ["analysis", "recommendation", "confidence"]:
            self.assertIn(field, props)

    def test_confidence_bounds_in_schema(self):
        conf = AGENT_TOOL_SCHEMA["input_schema"]["properties"]["confidence"]
        self.assertEqual(conf["minimum"], 0.0)
        self.assertEqual(conf["maximum"], 1.0)

    def test_orion_tool_has_synthesis(self):
        props = ORION_TOOL_SCHEMA["input_schema"]["properties"]
        self.assertIn("synthesis", props)
        self.assertIn("consensus", props)

    def test_tool_name_is_string(self):
        self.assertIsInstance(AGENT_TOOL_SCHEMA["name"], str)
        self.assertEqual(AGENT_TOOL_SCHEMA["name"], "agent_response")


class TestStructuredAgentCallInit(unittest.TestCase):
    def test_init_no_key(self):
        caller = StructuredAgentCall(api_key="")
        self.assertIsInstance(caller, StructuredAgentCall)

    def test_retry_delays_ordered(self):
        delays = StructuredAgentCall.RETRY_DELAYS
        self.assertEqual(delays, sorted(delays))
        self.assertEqual(delays[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
