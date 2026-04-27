"""
AILEX Pilot — role_handoff.py
Structured role handoff protocols between agents.
Inspired by MetaGPT's "Code = SOP(Team)" — AILEX original.

Defines formal handoff contracts: what each role produces,
what the next role expects, and how to validate the transfer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class HandoffContract:
    from_role:  str
    to_role:    str
    produces:   List[str]    # what from_role must provide
    expects:    List[str]    # what to_role needs to proceed
    validator:  Optional[Callable] = None


@dataclass
class HandoffResult:
    contract:   HandoffContract
    payload:    Dict          # data passed between roles
    valid:      bool
    missing:    List[str]
    enriched:   Dict = field(default_factory=dict)


# Standard AILEX handoff contracts (MetaGPT-inspired but original)
CONTRACTS: List[HandoffContract] = [
    HandoffContract(
        from_role="ORION", to_role="CHAOS",
        produces=["synthesis", "decision", "next_steps", "confidence"],
        expects=["synthesis"],
        validator=lambda p: bool(p.get("synthesis", "").strip()),
    ),
    HandoffContract(
        from_role="DEX", to_role="QUINN",
        produces=["implementation", "code_snippet", "approach"],
        expects=["implementation"],
        validator=lambda p: bool(p.get("implementation")),
    ),
    HandoffContract(
        from_role="ARIA", to_role="FELIX",
        produces=["architecture_decision", "components", "interfaces"],
        expects=["architecture_decision"],
        validator=lambda p: bool(p.get("architecture_decision")),
    ),
    HandoffContract(
        from_role="DARA", to_role="ARIA",
        produces=["data_model", "schema", "migration_plan"],
        expects=["data_model"],
        validator=lambda p: bool(p.get("data_model")),
    ),
    HandoffContract(
        from_role="NOVA", to_role="DEX",
        produces=["feature_spec", "acceptance_criteria", "scope"],
        expects=["feature_spec"],
        validator=lambda p: bool(p.get("feature_spec")),
    ),
]


class RoleHandoffManager:
    """
    Manages structured handoffs between AILEX agents.
    Ensures each agent receives what it needs before running.
    Validates outputs before passing to the next role.
    """

    def __init__(self):
        self.contracts: Dict[tuple, HandoffContract] = {
            (c.from_role, c.to_role): c for c in CONTRACTS
        }

    def extract_payload(self, agent_output: str, from_role: str) -> Dict:
        """Extract structured data from agent free-text output."""
        payload: Dict[str, str] = {}

        # Generic extraction patterns
        extractors = {
            "synthesis":             r"SYNTHESIS:\s*(.+?)(?=DECISION:|RISKS:|$)",
            "decision":              r"DECISION:\s*(.+?)(?=RISKS:|NEXT|$)",
            "next_steps":            r"NEXT STEPS:\s*(.+?)(?=CONFIDENCE:|$)",
            "confidence":            r"CONFIDENCE:\s*([\d.]+)",
            "implementation":        r"(?:implement|implementation):\s*(.+?)(?=\n\n|$)",
            "architecture_decision": r"(?:architecture|design):\s*(.+?)(?=\n\n|$)",
            "data_model":            r"(?:schema|model|table):\s*(.+?)(?=\n\n|$)",
            "feature_spec":          r"(?:feature|spec|scope):\s*(.+?)(?=\n\n|$)",
            "approach":              r"APPROACH:\s*(.+?)(?=RISK:|INSIGHT:|$)",
        }

        for key, pattern in extractors.items():
            m = re.search(pattern, agent_output, re.I | re.S)
            if m:
                payload[key] = m.group(1).strip()[:500]

        # Always include raw output
        payload["raw"] = agent_output[:1000]
        payload["from_role"] = from_role

        return payload

    def handoff(self, from_role: str, to_role: str,
                agent_output: str) -> HandoffResult:
        """Execute a handoff from one role to another."""
        contract = self.contracts.get((from_role, to_role))
        if not contract:
            # No formal contract — pass raw output
            return HandoffResult(
                contract=HandoffContract(from_role, to_role, [], [], None),
                payload={"raw": agent_output},
                valid=True,
                missing=[],
            )

        payload = self.extract_payload(agent_output, from_role)
        missing = [f for f in contract.expects if not payload.get(f)]
        valid   = (not missing) and (
            contract.validator(payload) if contract.validator else True
        )

        # Enrich payload for receiving role
        enriched = self._enrich(to_role, payload)

        return HandoffResult(
            contract=contract, payload=payload,
            valid=valid, missing=missing, enriched=enriched,
        )

    def _enrich(self, to_role: str, payload: Dict) -> Dict:
        """Add role-specific context to the payload."""
        enrichment: Dict[str, str] = {}
        enrichment_map = {
            "CHAOS":  "Focus: find the flaw in the synthesis above.",
            "QUINN":  "Focus: test the implementation above. What breaks?",
            "FELIX":  "Focus: deploy the architecture above safely.",
            "DEX":    "Focus: implement the spec above concretely.",
        }
        msg = enrichment_map.get(to_role, "")
        if msg:
            enrichment["role_instruction"] = msg
        return enrichment

    def build_handoff_prompt(self, result: HandoffResult) -> str:
        """Build the prompt to send to the receiving role."""
        lines = []
        for key, val in result.payload.items():
            if key != "raw" and val:
                lines.append(f"{key.upper()}: {val}")
        if result.enriched:
            for key, val in result.enriched.items():
                lines.append(f"\n{val}")
        if not lines:
            lines.append(result.payload.get("raw", "")[:500])
        return "\n".join(lines)

    def validate_pipeline_flow(self, contributions: List[Any]) -> List[str]:
        """Check that all expected handoffs are valid in a completed pipeline run."""
        issues = []
        agent_outputs = {c.agent: c.signal for c in contributions}
        for (from_r, to_r), contract in self.contracts.items():
            if from_r in agent_outputs and to_r in agent_outputs:
                result = self.handoff(from_r, to_r, agent_outputs[from_r])
                if not result.valid:
                    issues.append(
                        f"{from_r}→{to_r}: missing {result.missing}"
                    )
        return issues
