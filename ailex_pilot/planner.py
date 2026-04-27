"""
AILEX Pilot — planner.py
Long-horizon planning: break complex requests into ordered subtasks,
execute them sequentially with dependency tracking.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, List, Optional

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


@dataclass
class PlanStep:
    index:      int
    title:      str
    description: str
    domain:     str
    depends_on: List[int] = field(default_factory=list)
    status:     str = "pending"
    result:     str = ""


@dataclass
class Plan:
    goal:    str
    steps:   List[PlanStep]
    context: str = ""


class LongHorizonPlanner:
    """
    Breaks complex goals into sequential subtasks.
    Uses Claude to plan, then executes step by step.
    """

    def __init__(self, client: Any = None):
        self.client = client

    def plan(self, goal: str, context: str = "") -> Plan:
        """Use Claude to break a goal into ordered steps."""
        if not self.client:
            return self._demo_plan(goal)

        prompt = (
            f"Break this software engineering goal into 3-8 concrete, ordered steps.\n\n"
            f"Goal: {goal}\n"
            + (f"Context: {context[:500]}\n" if context else "")
            + "\nFor each step provide:\n"
            "STEP N: [title]\n"
            "DESC: [what to do — specific, actionable]\n"
            "DOMAIN: [bug|code|feature|architecture|deploy|testing|refactor]\n"
            "DEPENDS: [comma-separated step numbers, or 'none']\n\n"
            "Make steps small enough to complete in one AILEX request."
        )
        resp = self.client.messages.create(
            model="claude-sonnet-4-6", max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_plan(goal, resp.content[0].text, context)

    def execute(self, plan: Plan, pipeline: Any,
                auto_commit: bool = False) -> Plan:
        """Execute plan steps sequentially, respecting dependencies."""
        completed: set = set()
        for step in plan.steps:
            # Check all dependencies done
            if not all(d - 1 in completed for d in step.depends_on):
                step.status = "blocked"
                continue
            print(f"  Step {step.index}/{len(plan.steps)}: {step.title}")
            try:
                context = (
                    f"Plan context: {plan.context}\n"
                    f"Overall goal: {plan.goal}\n"
                    f"Previous steps done: {[plan.steps[i-1].title for i in completed]}\n\n"
                    f"Current step: {step.description}"
                )
                proc = pipeline.process(
                    context, override_domain=step.domain,
                    run_code=True, auto_commit=auto_commit,
                    include_context=True, fmt="concise"
                )
                step.result = proc.get("report", "")
                step.status = "done"
                completed.add(step.index - 1)
            except Exception as e:
                step.status = "failed"
                step.result = str(e)
                break  # stop on failure
        return plan

    def plan_and_execute(self, goal: str, pipeline: Any,
                          auto_commit: bool = False) -> Plan:
        """Full pipeline: plan → execute → return completed plan."""
        ctx  = pipeline.project_summary() if hasattr(pipeline, "project_summary") else ""
        plan = self.plan(goal, ctx)
        print(f"\nPlan: {len(plan.steps)} steps for '{goal}'")
        return self.execute(plan, pipeline, auto_commit)

    def _parse_plan(self, goal: str, text: str, context: str) -> Plan:
        steps: List[PlanStep] = []
        blocks = re.split(r"STEP\s+(\d+):", text)
        for i in range(1, len(blocks), 2):
            idx   = int(blocks[i])
            body  = blocks[i + 1] if i + 1 < len(blocks) else ""
            title = (re.search(r"^(.+?)(?:\n|DESC:)", body) or
                     re.search(r"(.+)", body))
            title = title.group(1).strip() if title else f"Step {idx}"
            desc  = re.search(r"DESC:\s*(.+?)(?=DOMAIN:|DEPENDS:|STEP\s+\d+:|$)", body, re.S)
            dom   = re.search(r"DOMAIN:\s*(\w+)", body)
            deps  = re.search(r"DEPENDS:\s*([^\n]+)", body)
            dep_list: List[int] = []
            if deps and "none" not in deps.group(1).lower():
                dep_list = [int(n) for n in re.findall(r"\d+", deps.group(1))
                            if int(n) != idx]
            steps.append(PlanStep(
                index=idx,
                title=title,
                description=desc.group(1).strip() if desc else title,
                domain=dom.group(1).lower() if dom else "code",
                depends_on=dep_list,
            ))
        return Plan(goal=goal, steps=steps or [PlanStep(1, goal, goal, "code")], context=context)

    def _demo_plan(self, goal: str) -> Plan:
        return Plan(goal=goal, steps=[
            PlanStep(1, "Analyse current state", f"Analyse codebase for: {goal}", "code"),
            PlanStep(2, "Implement solution", f"Implement: {goal}", "code", depends_on=[1]),
            PlanStep(3, "Add tests", f"Write tests for: {goal}", "testing", depends_on=[2]),
            PlanStep(4, "Review and refine", f"Review and clean up: {goal}", "refactor", depends_on=[3]),
        ])

    def format_plan(self, plan: Plan) -> str:
        lines = [f"Plan: {plan.goal}", f"{len(plan.steps)} steps:", ""]
        for s in plan.steps:
            icon = {"done": "✓", "failed": "✗", "blocked": "◌", "pending": "○", "running": "◎"}.get(s.status, "○")
            dep  = f" [after {s.depends_on}]" if s.depends_on else ""
            lines.append(f"  {icon} {s.index}. [{s.domain}] {s.title}{dep}")
            if s.result:
                lines.append(f"      → {s.result[:80]}")
        return "\n".join(lines)
