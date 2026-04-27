"""
AILEX Pilot — prd_generator.py
Complete Product Requirements Document generator.
Takes any request and produces a structured PRD with user stories,
technical specs, success metrics, and execution plan.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UserStory:
    id:           str
    persona:      str
    action:       str
    value:        str
    acceptance:   List[str]
    priority:     str   # P0 | P1 | P2


@dataclass
class TechnicalRequirement:
    id:      str
    area:    str    # frontend | backend | data | infra | security
    title:   str
    detail:  str
    effort:  str    # XS | S | M | L | XL


@dataclass
class PRD:
    title:            str
    version:          str
    status:           str   # draft | review | approved
    created:          str
    summary:          str
    problem:          str
    goals:            List[str]
    non_goals:        List[str]
    personas:         List[Dict]
    user_stories:     List[UserStory]
    requirements:     List[TechnicalRequirement]
    success_metrics:  List[str]
    risks:            List[str]
    timeline:         List[Dict]
    dependencies:     List[str]
    open_questions:   List[str]
    raw_markdown:     str
    tokens_used:      int = 0
    duration_s:       float = 0.0


class PRDGenerator:
    """
    Generates complete Product Requirements Documents.

    Pipeline:
    1. Understand: extract problem space
    2. Define: personas, goals, non-goals
    3. Specify: user stories, acceptance criteria
    4. Technical: requirements by area
    5. Measure: success metrics, KPIs
    6. Plan: timeline, dependencies, risks
    """

    MODEL    = "claude-opus-4-7"
    SAVE_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ailex_prds"
    )

    def __init__(self, client: Any = None):
        self.client = client
        os.makedirs(self.SAVE_DIR, exist_ok=True)

    def generate(
        self,
        request:    str,
        context:    str = "",
        depth:      str = "full",   # minimal | standard | full
        domain:     str = "product",
    ) -> PRD:
        """Generate a complete PRD from any request."""
        start = time.time()
        if not self.client:
            return self._demo_prd(request)

        prompt = self._build_prompt(request, context, depth)
        try:
            resp = self.client.messages.create(
                model=self.MODEL,
                max_tokens=12000,
                thinking={"type": "enabled", "budget_tokens": 8000},
                temperature=1,
                messages=[{"role": "user", "content": prompt}],
            )
            text   = " ".join(b.text for b in resp.content if hasattr(b, "text")).strip()
            prd    = self._parse_prd(request, text)
            prd.tokens_used = resp.usage.output_tokens
            prd.duration_s  = round(time.time() - start, 2)
            self._save(prd)
            return prd
        except Exception as e:
            demo       = self._demo_prd(request)
            demo.risks = [str(e)]
            return demo

    def _build_prompt(self, request: str, context: str, depth: str) -> str:
        sections = {
            "minimal": "summary, goals, 3-5 user stories, success metrics",
            "standard": "summary, problem, goals/non-goals, personas, user stories, technical requirements, metrics, timeline",
            "full": "ALL sections including risks, dependencies, open questions, detailed acceptance criteria, effort estimates",
        }
        return f"""
Generate a complete Product Requirements Document (PRD) for:

REQUEST: {request}
{f"CONTEXT: {context}" if context else ""}
DEPTH: {sections.get(depth, sections['full'])}

Structure the PRD with these exact markdown sections:

# PRD: [Title]
**Version:** 1.0 | **Status:** Draft | **Date:** {time.strftime('%Y-%m-%d')}

## 1. Executive Summary
[2-3 sentence overview]

## 2. Problem Statement
[What problem are we solving? Who has this problem? What's the impact?]

## 3. Goals
- [Measurable goal 1]
- [Measurable goal 2]

## 4. Non-Goals
- [What we explicitly will NOT do]

## 5. User Personas
### Persona 1: [Name]
- **Role:** ...
- **Pain point:** ...
- **Goal:** ...

## 6. User Stories
### US-001: [Title]
**As a** [persona], **I want to** [action], **so that** [value].
**Priority:** P0/P1/P2
**Acceptance Criteria:**
- [ ] [criterion 1]
- [ ] [criterion 2]

[Repeat for each story]

## 7. Technical Requirements
### Frontend
- **FR-001:** [requirement] — Effort: S/M/L/XL
### Backend
- **BR-001:** [requirement] — Effort: S/M/L/XL
### Data
- **DR-001:** [requirement] — Effort: S/M/L/XL
### Security
- **SR-001:** [requirement] — Effort: S/M/L/XL
### Infrastructure
- **IR-001:** [requirement] — Effort: S/M/L/XL

## 8. Success Metrics
- [KPI 1]: [current baseline] → [target]
- [KPI 2]: [current baseline] → [target]

## 9. Risks
- **[Risk]:** [Mitigation]

## 10. Timeline
| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Discovery | 1 week | ... |
| Design | 1 week | ... |
| Development | N weeks | ... |
| Testing | 1 week | ... |
| Launch | 1 week | ... |

## 11. Dependencies
- [Dependency 1]

## 12. Open Questions
- [ ] [Question that needs answering before development]

Return ONLY the markdown PRD. No explanations outside the document.
"""

    def _parse_prd(self, request: str, text: str) -> PRD:
        def section(name: str) -> str:
            m = re.search(
                rf"##\s*\d*\.?\s*{re.escape(name)}[^\n]*\n([\s\S]+?)(?=##|\Z)",
                text, re.I
            )
            return m.group(1).strip() if m else ""

        def list_items(text_section: str) -> List[str]:
            return [
                re.sub(r"^[-*•\[\]x\s]+", "", l).strip()
                for l in text_section.split("\n")
                if l.strip() and re.match(r"^\s*[-*•\[]", l)
            ]

        # Parse user stories
        stories: List[UserStory] = []
        story_blocks = re.findall(
            r"### US-(\w+):?\s*(.+?)\n([\s\S]+?)(?=### US-|\Z)", text, re.I
        )
        for sid, title, body in story_blocks:
            as_match = re.search(r"I want to\s+(.+?),?\s+so that\s+(.+)", body, re.I)
            persona_m = re.search(r"As a\s+(.+?),", body, re.I)
            criteria  = [l.strip("- []x") for l in body.split("\n")
                         if "[ ]" in l or "- [" in l.lower()]
            prio_m    = re.search(r"Priority:\s*(P\d)", body, re.I)
            stories.append(UserStory(
                id=f"US-{sid}",
                persona=persona_m.group(1) if persona_m else "user",
                action=as_match.group(1) if as_match else title,
                value=as_match.group(2) if as_match else "",
                acceptance=criteria[:5],
                priority=prio_m.group(1) if prio_m else "P1",
            ))

        # Parse technical requirements
        reqs: List[TechnicalRequirement] = []
        for area in ("Frontend", "Backend", "Data", "Security", "Infrastructure"):
            area_m = re.search(
                rf"### {area}\n([\s\S]+?)(?=###|\Z)", text, re.I
            )
            if area_m:
                for m in re.finditer(r"\*\*(\w+-\d+):\*\*\s*(.+?)(?:—\s*Effort:\s*(\w+))?$",
                                     area_m.group(1), re.M):
                    reqs.append(TechnicalRequirement(
                        id=m.group(1), area=area.lower(),
                        title=m.group(2).strip()[:100],
                        detail=m.group(2).strip(),
                        effort=m.group(3) or "M",
                    ))

        # Title
        title_m = re.search(r"# PRD:\s*(.+)", text)
        title   = title_m.group(1).strip() if title_m else request[:60]

        return PRD(
            title=title,
            version="1.0",
            status="Draft",
            created=time.strftime("%Y-%m-%d"),
            summary=section("Executive Summary")[:500],
            problem=section("Problem Statement")[:500],
            goals=list_items(section("Goals"))[:8],
            non_goals=list_items(section("Non-Goals"))[:6],
            personas=[],
            user_stories=stories,
            requirements=reqs,
            success_metrics=list_items(section("Success Metrics"))[:8],
            risks=[re.sub(r"\*\*(.+?):\*\*", r"\1:", l).strip()
                   for l in section("Risks").split("\n") if l.strip() and "**" in l][:6],
            timeline=[],
            dependencies=list_items(section("Dependencies"))[:6],
            open_questions=list_items(section("Open Questions"))[:6],
            raw_markdown=text,
        )

    def _save(self, prd: PRD) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", prd.title.lower())[:40]
        path = os.path.join(self.SAVE_DIR, f"{slug}_{int(time.time())}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(prd.raw_markdown)
        return path

    def _demo_prd(self, request: str) -> PRD:
        return PRD(
            title=f"PRD: {request[:50]}",
            version="1.0", status="Draft",
            created=time.strftime("%Y-%m-%d"),
            summary=f"[DEMO] Product requirements for: {request}",
            problem="Set ANTHROPIC_API_KEY for real PRD generation.",
            goals=["Deliver core feature", "Achieve adoption target", "Meet performance SLA"],
            non_goals=["Out-of-scope feature A", "Integration with legacy system"],
            personas=[{"name": "Primary User", "role": "Engineer", "pain": "Manual work"}],
            user_stories=[UserStory(
                "US-001", "user", "accomplish the task", "save time",
                ["System responds < 2s", "No data loss"], "P0"
            )],
            requirements=[TechnicalRequirement(
                "FR-001", "frontend", "Implement UI", "Build responsive interface", "L"
            )],
            success_metrics=["Adoption rate > 80%", "Error rate < 0.1%", "P95 latency < 500ms"],
            risks=["Technical complexity may exceed estimate"],
            timeline=[{"phase": "Development", "duration": "4 weeks", "deliverable": "MVP"}],
            dependencies=["Auth service", "Database migration"],
            open_questions=["Which authentication provider?", "Data retention policy?"],
            raw_markdown=f"# PRD: {request}\n\n[DEMO — set ANTHROPIC_API_KEY for full generation]",
        )

    def to_squad_brief(self, prd: PRD) -> str:
        """Convert PRD to a squad execution brief."""
        areas = list({r.area for r in prd.requirements})
        return (
            f"EXECUTION BRIEF for: {prd.title}\n\n"
            f"GOALS: {'; '.join(prd.goals[:3])}\n\n"
            f"USER STORIES: {len(prd.user_stories)} stories\n"
            + "\n".join(f"  {s.id} [{s.priority}]: {s.action}" for s in prd.user_stories[:5])
            + f"\n\nTECHNICAL AREAS: {', '.join(areas)}\n"
            + f"REQUIREMENTS: {len(prd.requirements)} requirements\n"
            + f"SUCCESS: {'; '.join(prd.success_metrics[:2])}\n"
        )

    def format(self, prd: PRD) -> str:
        sep = "─" * 60
        lines = [
            f"PRD: {prd.title} v{prd.version} [{prd.status}]",
            f"Created: {prd.created} | {prd.tokens_used:,} tokens | {prd.duration_s}s",
            sep,
            f"SUMMARY: {prd.summary[:200]}",
            f"\nGOALS ({len(prd.goals)}):",
        ]
        for g in prd.goals[:4]:
            lines.append(f"  ✓ {g}")
        lines.append(f"\nUSER STORIES ({len(prd.user_stories)}):")
        for s in prd.user_stories[:5]:
            lines.append(f"  [{s.priority}] {s.id}: {s.action[:60]}")
        lines.append(f"\nTECHNICAL REQS ({len(prd.requirements)}):")
        for r in prd.requirements[:6]:
            lines.append(f"  [{r.area:10s}] {r.id}: {r.title[:50]} [{r.effort}]")
        lines += [
            f"\nSUCCESS METRICS:", *[f"  • {m}" for m in prd.success_metrics[:4]],
            f"\nRISKS:", *[f"  ⚠ {r}" for r in prd.risks[:3]],
            sep,
        ]
        return "\n".join(lines)
