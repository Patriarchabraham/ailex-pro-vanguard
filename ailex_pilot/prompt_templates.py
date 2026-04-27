"""
AILEX Pilot — prompt_templates.py
Reusable prompt component library.
Inspired by Fabric's pattern library concept — AILEX original implementation.

Usage:
  from ailex_pilot.prompt_templates import PromptLibrary
  lib = PromptLibrary()
  prompt = lib.render("code_review", code="...", language="python")
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PromptTemplate:
    name:        str
    description: str
    template:    str          # {{variable}} placeholders
    category:    str          # code | security | docs | strategy | review
    variables:   List[str]    # required variable names
    tags:        List[str] = field(default_factory=list)
    domain:      str = ""     # AILEX domain hint


# Built-in AILEX prompt library
BUILTIN_TEMPLATES: List[PromptTemplate] = [
    PromptTemplate(
        name="code_review",
        description="Deep review of code for bugs, style, and security",
        category="code",
        domain="code",
        variables=["code", "language"],
        tags=["review", "quality"],
        template="""Review this {{language}} code thoroughly.

```{{language}}
{{code}}
```

Focus on:
1. Bugs and edge cases
2. Security vulnerabilities
3. Performance issues
4. Code style and readability
5. Missing error handling

Provide specific line-level feedback with fix suggestions.""",
    ),
    PromptTemplate(
        name="explain_code",
        description="Explain what code does in plain language",
        category="docs",
        domain="documentation",
        variables=["code", "audience"],
        tags=["explain", "docs"],
        template="""Explain this code to a {{audience}}.

```
{{code}}
```

Cover: what it does, how it works, key concepts, and any important caveats.
Be clear and use analogies where helpful.""",
    ),
    PromptTemplate(
        name="write_tests",
        description="Generate comprehensive unit tests",
        category="code",
        domain="testing",
        variables=["code", "language", "framework"],
        tags=["tests", "quality"],
        template="""Write comprehensive unit tests for this {{language}} code using {{framework}}.

```{{language}}
{{code}}
```

Include: happy path, edge cases, error cases, boundary conditions.
Tests must be independent, descriptive, and cover all branches.""",
    ),
    PromptTemplate(
        name="refactor",
        description="Refactor code for clarity and maintainability",
        category="code",
        domain="refactor",
        variables=["code", "language", "goal"],
        tags=["refactor", "clean"],
        template="""Refactor this {{language}} code. Goal: {{goal}}.

```{{language}}
{{code}}
```

Apply: SOLID principles, extract functions, improve naming, reduce complexity.
Return the refactored code with a brief explanation of each change.""",
    ),
    PromptTemplate(
        name="security_audit",
        description="Security audit focused on OWASP top 10",
        category="security",
        domain="security",
        variables=["code", "context"],
        tags=["security", "audit"],
        template="""Perform a security audit on this code. Context: {{context}}.

```
{{code}}
```

Check: injection attacks, authentication flaws, sensitive data exposure,
broken access control, security misconfiguration, XSS, CSRF, insecure deps.
Rate each finding: CRITICAL / HIGH / MEDIUM / LOW.""",
    ),
    PromptTemplate(
        name="architecture_review",
        description="Review system architecture for scalability and design patterns",
        category="strategy",
        domain="architecture",
        variables=["description", "constraints"],
        tags=["architecture", "design"],
        template="""Review this system architecture.

Description: {{description}}
Constraints: {{constraints}}

Evaluate: scalability, maintainability, coupling/cohesion, failure modes,
operational complexity, cost implications.
Suggest specific improvements with trade-off analysis.""",
    ),
    PromptTemplate(
        name="debug",
        description="Diagnose and fix a bug with full context",
        category="code",
        domain="bug",
        variables=["error", "code", "context"],
        tags=["debug", "fix"],
        template="""Debug this issue.

Error: {{error}}
Context: {{context}}

Code:
```
{{code}}
```

Identify: root cause, why it happens, how to reproduce.
Provide: minimal fix, test to prevent regression.""",
    ),
    PromptTemplate(
        name="api_design",
        description="Design a REST/GraphQL API",
        category="code",
        domain="architecture",
        variables=["resource", "operations", "constraints"],
        tags=["api", "design"],
        template="""Design an API for {{resource}}.

Required operations: {{operations}}
Constraints: {{constraints}}

Include: endpoints, HTTP methods, request/response schemas,
error codes, authentication strategy, versioning approach.
Follow REST best practices and OpenAPI conventions.""",
    ),
    PromptTemplate(
        name="commit_message",
        description="Generate a descriptive git commit message",
        category="docs",
        domain="documentation",
        variables=["diff", "context"],
        tags=["git", "docs"],
        template="""Generate a git commit message for this diff.

Context: {{context}}

Diff:
{{diff}}

Format: <type>(<scope>): <description>
Types: feat|fix|docs|style|refactor|test|chore
Keep under 72 chars. Add body if needed.""",
    ),
    PromptTemplate(
        name="pr_description",
        description="Write a pull request description",
        category="docs",
        domain="documentation",
        variables=["changes", "motivation", "testing"],
        tags=["git", "pr"],
        template="""Write a pull request description.

Changes: {{changes}}
Motivation: {{motivation}}
Testing: {{testing}}

Include: summary, what changed, why, how to test, screenshots if UI.""",
    ),
    PromptTemplate(
        name="performance_analysis",
        description="Analyse code for performance bottlenecks",
        category="code",
        domain="performance",
        variables=["code", "profiling_data"],
        tags=["performance", "optimise"],
        template="""Analyse this code for performance issues.

Profiling data: {{profiling_data}}

```
{{code}}
```

Identify: bottlenecks, O(n) complexity issues, unnecessary allocations,
blocking calls, caching opportunities.
Provide: specific optimisations with expected improvement.""",
    ),
    PromptTemplate(
        name="migration_plan",
        description="Plan a code or database migration",
        category="strategy",
        domain="architecture",
        variables=["from_state", "to_state", "constraints"],
        tags=["migration", "strategy"],
        template="""Plan this migration.

From: {{from_state}}
To: {{to_state}}
Constraints: {{constraints}}

Provide: step-by-step plan, rollback strategy, data integrity checks,
estimated effort, risks and mitigations.""",
    ),
]


class PromptLibrary:
    """
    Reusable prompt template library for AILEX.
    Templates can be loaded from built-ins, files, or custom directories.
    """

    CUSTOM_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "prompt_templates"
    )

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        os.makedirs(self.CUSTOM_DIR, exist_ok=True)
        self._load_builtin()
        self._load_custom()

    def _load_builtin(self) -> None:
        for t in BUILTIN_TEMPLATES:
            self._templates[t.name] = t

    def _load_custom(self) -> None:
        """Load .md or .txt templates from custom directory."""
        for fname in os.listdir(self.CUSTOM_DIR):
            if not fname.endswith((".md", ".txt")):
                continue
            path = os.path.join(self.CUSTOM_DIR, fname)
            try:
                content = open(path, encoding="utf-8").read()
                name    = os.path.splitext(fname)[0]
                # Parse frontmatter: --- key: value ---
                meta: Dict[str, str] = {}
                m = re.match(r"^---\n(.+?)\n---\n(.+)", content, re.S)
                if m:
                    for line in m.group(1).splitlines():
                        if ":" in line:
                            k, _, v = line.partition(":")
                            meta[k.strip()] = v.strip()
                    template_body = m.group(2).strip()
                else:
                    template_body = content
                variables = re.findall(r"\{\{(\w+)\}\}", template_body)
                self._templates[name] = PromptTemplate(
                    name=name,
                    description=meta.get("description", name),
                    category=meta.get("category", "custom"),
                    domain=meta.get("domain", ""),
                    variables=list(dict.fromkeys(variables)),
                    template=template_body,
                    tags=meta.get("tags", "").split(","),
                )
            except Exception:
                pass

    def render(self, name: str, **variables) -> str:
        """Render a template with given variables."""
        tmpl = self._templates.get(name)
        if not tmpl:
            raise KeyError(f"Template '{name}' not found. Available: {list(self._templates)}")
        result = tmpl.template
        for k, v in variables.items():
            result = result.replace(f"{{{{{k}}}}}", str(v))
        # Check for unfilled variables
        unfilled = re.findall(r"\{\{(\w+)\}\}", result)
        if unfilled:
            raise ValueError(f"Missing variables: {unfilled}")
        return result

    def get(self, name: str) -> Optional[PromptTemplate]:
        return self._templates.get(name)

    def list(self, category: str = "", tag: str = "") -> List[PromptTemplate]:
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        if tag:
            templates = [t for t in templates if tag in t.tags]
        return sorted(templates, key=lambda t: t.name)

    def add(self, template: PromptTemplate) -> None:
        self._templates[template.name] = template

    def save_custom(self, template: PromptTemplate) -> str:
        """Save a template to the custom directory."""
        content = (
            f"---\n"
            f"description: {template.description}\n"
            f"category: {template.category}\n"
            f"domain: {template.domain}\n"
            f"tags: {','.join(template.tags)}\n"
            f"---\n"
            f"{template.template}"
        )
        path = os.path.join(self.CUSTOM_DIR, f"{template.name}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def summary(self) -> str:
        cats: Dict[str, int] = {}
        for t in self._templates.values():
            cats[t.category] = cats.get(t.category, 0) + 1
        lines = [f"Prompt Library: {len(self._templates)} templates"]
        for cat, n in sorted(cats.items()):
            lines.append(f"  {cat}: {n}")
        return "\n".join(lines)
