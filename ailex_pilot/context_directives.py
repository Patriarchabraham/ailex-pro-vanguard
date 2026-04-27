"""
AILEX Pilot — context_directives.py
@-directives for enriching requests with context.
Inspired by Aider's @file / Cline's context commands — AILEX original.

Supported directives:
  @file path/to/file          — include file content
  @folder path/to/dir         — include directory listing + key files
  @url https://...            — fetch and include webpage
  @git                        — include recent git log + diff
  @function name              — find and include function from codebase
  @test path                  — include test file for context
  @kb query                   — search knowledge base
  @session                    — include recent conversation history
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

class DirectiveProcessor:
    """
    Processes @-directives in user requests, replacing them with actual content.
    Makes it easy to inject precise context without typing long instructions.
    """

    MAX_FILE_SIZE  = 30_000    # chars
    MAX_URL_SIZE   = 10_000
    MAX_KB_RESULTS = 3

    def __init__(
        self,
        project_reader: Any = None,
        knowledge_base: Any = None,
        conversation:   Any = None,
        session_id:     str = "",
    ):
        self.reader    = project_reader
        self.kb        = knowledge_base
        self.conv      = conversation
        self.session_id= session_id

    def process(self, request: str, project_dir: str = ".") -> Tuple[str, List[str]]:
        """
        Parse @-directives in request, expand to content.
        Returns (expanded_request, list_of_directives_found).
        """
        directives_found: List[str] = []
        result = request

        patterns = [
            (r"@file\s+(\S+)",       self._expand_file),
            (r"@folder\s+(\S+)",     self._expand_folder),
            (r"@url\s+(https?://\S+)",self._expand_url),
            (r"@git\b",              lambda m, d: self._expand_git(d)),
            (r"@function\s+(\w+)",   lambda m, d: self._expand_function(m.group(1), d)),
            (r"@test\s+(\S+)",       self._expand_file),
            (r"@kb\s+(.+?)(?=@|\n|$)",lambda m, d: self._expand_kb(m.group(1).strip())),
            (r"@session\b",          lambda m, d: self._expand_session()),
        ]

        for pattern, handler in patterns:
            for match in re.finditer(pattern, result, re.IGNORECASE):
                try:
                    content = handler(match, project_dir)
                    if content:
                        result = result.replace(match.group(0), f"\n{content}\n", 1)
                        directives_found.append(match.group(0))
                except Exception as e:
                    result = result.replace(
                        match.group(0),
                        f"[ERROR expanding {match.group(0)}: {e}]", 1
                    )

        return result, directives_found

    def _expand_file(self, match: Any, project_dir: str) -> str:
        arg  = match.group(1)
        path = arg if os.path.isabs(arg) else os.path.join(project_dir, arg)
        if not os.path.exists(path):
            return f"[File not found: {path}]"
        content = open(path, encoding="utf-8", errors="ignore").read()
        ext     = os.path.splitext(path)[1].lstrip(".")
        return (
            f"=== @file: {arg} ===\n"
            f"```{ext}\n{content[:self.MAX_FILE_SIZE]}\n```"
            + (f"\n[... {len(content)-self.MAX_FILE_SIZE} more chars]"
               if len(content) > self.MAX_FILE_SIZE else "")
        )

    def _expand_folder(self, match: Any, project_dir: str) -> str:
        arg  = match.group(1)
        path = arg if os.path.isabs(arg) else os.path.join(project_dir, arg)
        if not os.path.exists(path):
            return f"[Folder not found: {path}]"
        lines  = [f"=== @folder: {arg} ==="]
        count  = 0
        for dp, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__")]
            rel = os.path.relpath(dp, path)
            prefix = "" if rel == "." else "  " * rel.count(os.sep)
            lines.append(f"{prefix}{os.path.basename(dp)}/")
            for f in files[:20]:
                lines.append(f"{prefix}  {f}")
            count += len(files)
            if count > 100:
                lines.append("  ... (truncated)")
                break
        return "\n".join(lines)

    def _expand_url(self, match: Any, _: str) -> str:
        url = match.group(1)
        try:
            import urllib.request
            req  = urllib.request.Request(
                url, headers={"User-Agent": "AILEX/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode(errors="ignore")
            # Strip HTML tags
            import re as re2
            text = re2.sub(r"<[^>]+>", " ", raw)
            text = re2.sub(r"\s+", " ", text).strip()
            return (
                f"=== @url: {url} ===\n"
                f"{text[:self.MAX_URL_SIZE]}"
                + (f"\n[... truncated]" if len(text) > self.MAX_URL_SIZE else "")
            )
        except Exception as e:
            return f"[Failed to fetch {url}: {e}]"

    def _expand_git(self, project_dir: str) -> str:
        import subprocess
        lines = ["=== @git ==="]
        for cmd in [
            ["git", "log", "--oneline", "-10"],
            ["git", "diff", "--stat", "HEAD"],
            ["git", "status", "--short"],
        ]:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir)
            if r.returncode == 0 and r.stdout.strip():
                lines.append(f"$ {' '.join(cmd)}")
                lines.append(r.stdout.strip()[:500])
        return "\n".join(lines)

    def _expand_function(self, name: str, project_dir: str) -> str:
        import re as re2
        results = []
        for dp, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in (".py", ".ts", ".js", ".tsx", ".jsx"):
                    continue
                path    = os.path.join(dp, fname)
                content = open(path, encoding="utf-8", errors="ignore").read()
                pattern = rf"(?:def |function |const |async function )\s*{re2.escape(name)}\s*[\(:]"
                for m in re2.finditer(pattern, content):
                    start   = m.start()
                    snippet = content[start:start+500]
                    rel     = os.path.relpath(path, project_dir)
                    results.append(f"--- {rel} ---\n```\n{snippet}\n```")
                    if len(results) >= 3:
                        break
            if len(results) >= 3:
                break
        if not results:
            return f"[Function '{name}' not found in codebase]"
        return f"=== @function: {name} ===\n" + "\n".join(results)

    def _expand_kb(self, query: str) -> str:
        if not self.kb:
            return f"[Knowledge base not available — @kb: {query}]"
        entries = self.kb.search(query, limit=self.MAX_KB_RESULTS)
        if not entries:
            return f"[No KB results for: {query}]"
        lines = [f"=== @kb: {query} ==="]
        for e in entries:
            lines.append(f"[{e.kind}] {e.title}: {e.content[:200]}")
        return "\n".join(lines)

    def _expand_session(self) -> str:
        if not self.conv or not self.session_id:
            return "[No session available]"
        session = self.conv.get_session(self.session_id)
        if not session:
            return "[Session not found]"
        return self.conv.build_context(session, max_messages=5)

    def available_directives(self) -> str:
        return (
            "Available @-directives:\n"
            "  @file path         — include file content\n"
            "  @folder path       — include directory tree\n"
            "  @url https://...   — fetch webpage content\n"
            "  @git               — recent commits + diff + status\n"
            "  @function name     — find function in codebase\n"
            "  @test path         — include test file\n"
            "  @kb query          — search team knowledge base\n"
            "  @session           — recent conversation history\n\n"
            "Example: 'fix the bug in @file src/auth.py — also check @git'"
        )
