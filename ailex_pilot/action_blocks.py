"""
AILEX Pilot — action_blocks.py
Single-responsibility action blocks — composable pipeline primitives.
Inspired by AutoGPT's block architecture. AILEX original implementation.

Each block does ONE thing. Blocks connect via a shared context dict.
Compose into workflows without writing pipeline code.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BlockResult:
    block:   str
    success: bool
    output:  Any
    error:   Optional[str] = None
    time_s:  float = 0.0


class ActionBlock:
    """Base class for all AILEX action blocks."""

    name:     str = "base"
    category: str = "general"

    def run(self, ctx: Dict) -> BlockResult:
        raise NotImplementedError

    def __call__(self, ctx: Dict) -> BlockResult:
        start = time.time()
        try:
            result = self.run(ctx)
            result.time_s = round(time.time() - start, 2)
            return result
        except Exception as e:
            return BlockResult(self.name, False, None,
                               error=str(e), time_s=round(time.time()-start, 2))


# ── Reading blocks ────────────────────────────────────────────────────────────

class ReadFileBlock(ActionBlock):
    name = "read_file"; category = "io"
    def run(self, ctx: Dict) -> BlockResult:
        path = ctx.get("file_path", "")
        if not os.path.exists(path):
            return BlockResult(self.name, False, None, f"Not found: {path}")
        content = open(path, encoding="utf-8", errors="ignore").read()
        ctx["file_content"] = content
        return BlockResult(self.name, True, content[:200])


class WriteFileBlock(ActionBlock):
    name = "write_file"; category = "io"
    def run(self, ctx: Dict) -> BlockResult:
        path    = ctx.get("output_path", "")
        content = ctx.get("generated_code", ctx.get("output", ""))
        if not path or not content:
            return BlockResult(self.name, False, None, "Missing output_path or content")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        ctx["written_path"] = path
        return BlockResult(self.name, True, f"Wrote {len(content)} chars to {path}")

class FetchURLBlock(ActionBlock):
    name = "fetch_url"; category = "io"
    def run(self, ctx: Dict) -> BlockResult:
        import urllib.request, re
        url = ctx.get("url", "")
        if not url:
            return BlockResult(self.name, False, None, "No URL provided")
        req = urllib.request.Request(url, headers={"User-Agent": "AILEX/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw  = r.read().decode(errors="ignore")
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()[:5000]
        ctx["url_content"] = text
        return BlockResult(self.name, True, text[:100])


# ── AI blocks ─────────────────────────────────────────────────────────────────

class AskAILEXBlock(ActionBlock):
    name = "ask_ailex"; category = "ai"
    def __init__(self, pipeline: Any):
        self._pl = pipeline
    def run(self, ctx: Dict) -> BlockResult:
        request = ctx.get("request", ctx.get("file_content", ""))[:2000]
        domain  = ctx.get("domain")
        result  = self._pl.process(request, domain=domain, run_code=False,
                                   include_context=True, fmt="concise")
        ctx["ailex_report"]    = result.get("report", "")
        ctx["ailex_domain"]    = result.get("domain", "")
        ctx["ailex_confidence"]= result.get("confidence", 0)
        return BlockResult(self.name, True, result.get("report","")[:100])


class GenerateCodeBlock(ActionBlock):
    name = "generate_code"; category = "ai"
    def __init__(self, pipeline: Any):
        self._pl = pipeline
    def run(self, ctx: Dict) -> BlockResult:
        import re
        request = ctx.get("request", "")
        domain  = ctx.get("domain", "code")
        result  = self._pl.process(request, domain=domain, run_code=False, fmt="full")
        report  = result.get("report", "")
        # Extract code block
        m = re.search(r"```\w*\n([\s\S]+?)\n```", report)
        code = m.group(1).strip() if m else report[:1000]
        ctx["generated_code"] = code
        ctx["code_language"]  = ctx.get("language", "python")
        return BlockResult(self.name, True, f"Generated {len(code)} chars")


# ── Execution blocks ──────────────────────────────────────────────────────────

class RunCodeBlock(ActionBlock):
    name = "run_code"; category = "exec"
    def __init__(self, executor: Any):
        self._ex = executor
    def run(self, ctx: Dict) -> BlockResult:
        code = ctx.get("generated_code", "")
        lang = ctx.get("code_language", "python")
        if not code:
            return BlockResult(self.name, False, None, "No code to run")
        result = self._ex.run_code(code, lang, timeout=30)
        ctx["exec_stdout"]  = result.stdout
        ctx["exec_stderr"]  = result.stderr
        ctx["exec_success"] = result.success
        return BlockResult(self.name, result.success,
                           result.stdout[:100] or result.stderr[:100])


class GitCommitBlock(ActionBlock):
    name = "git_commit"; category = "git"
    def __init__(self, git: Any):
        self._git = git
    def run(self, ctx: Dict) -> BlockResult:
        if not self._git.is_git_repo():
            return BlockResult(self.name, False, None, "Not a git repo")
        message = ctx.get("commit_message",
                          f"AILEX: {ctx.get('request','change')[:60]}")
        result  = self._git.commit_ailex(message)
        ctx["commit_sha"] = result.sha
        return BlockResult(self.name, result.success, result.sha)


class SecurityScanBlock(ActionBlock):
    name = "security_scan"; category = "quality"
    def __init__(self, project_dir: str = "."):
        self._dir = project_dir
    def run(self, ctx: Dict) -> BlockResult:
        from ailex_pilot.security import SecurityScanner
        report = SecurityScanner().scan_project(self._dir)
        ctx["security_score"]   = report.score
        ctx["security_secrets"] = len(report.secrets)
        ctx["security_sast"]    = len(report.sast)
        ok = len(report.secrets) == 0
        return BlockResult(self.name, ok,
                           f"score={report.score:.0%} secrets={len(report.secrets)}")


# ── Workflow composer ─────────────────────────────────────────────────────────

class BlockWorkflow:
    """Compose action blocks into a sequential workflow."""

    def __init__(self, name: str = "workflow"):
        self.name   = name
        self.blocks: List[ActionBlock] = []
        self.results: List[BlockResult] = []

    def add(self, block: ActionBlock) -> "BlockWorkflow":
        self.blocks.append(block)
        return self

    def run(self, initial_ctx: Dict = {}) -> Dict:
        ctx = dict(initial_ctx)
        self.results = []
        for block in self.blocks:
            result = block(ctx)
            self.results.append(result)
            if not result.success:
                ctx["_failed_block"] = block.name
                ctx["_error"]        = result.error
                break   # stop on failure (can make optional)
        ctx["_workflow_results"] = self.results
        return ctx

    def summary(self) -> str:
        lines = [f"Workflow: {self.name}"]
        for r in self.results:
            icon = "✓" if r.success else "✗"
            lines.append(f"  {icon} [{r.block}] {r.time_s}s — {r.output or r.error}")
        return "\n".join(lines)


# ── Pre-built workflows ───────────────────────────────────────────────────────

def build_code_review_workflow(pipeline: Any, executor: Any, git: Any) -> BlockWorkflow:
    """Read file → ask AILEX → run → commit."""
    return (BlockWorkflow("code_review")
            .add(ReadFileBlock())
            .add(AskAILEXBlock(pipeline))
            .add(GenerateCodeBlock(pipeline))
            .add(RunCodeBlock(executor))
            .add(GitCommitBlock(git)))


def build_security_audit_workflow(project_dir: str, pipeline: Any) -> BlockWorkflow:
    """Scan → ask AILEX about findings → write report."""
    return (BlockWorkflow("security_audit")
            .add(SecurityScanBlock(project_dir))
            .add(AskAILEXBlock(pipeline))
            .add(WriteFileBlock()))
