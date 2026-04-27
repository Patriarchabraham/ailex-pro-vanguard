"""
AILEX Pilot — git_integration.py
Git operations: diff, commit, PR, blame, log.
Closes the loop: AILEX generates → code runs → git commits → PR created.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GitStatus:
    branch:       str
    modified:     List[str]
    untracked:    List[str]
    staged:       List[str]
    ahead:        int
    behind:       int
    clean:        bool


@dataclass
class CommitResult:
    success:  bool
    sha:      str
    message:  str
    files:    List[str]
    error:    Optional[str] = None


@dataclass
class PRResult:
    success: bool
    url:     str
    number:  int
    title:   str
    error:   Optional[str] = None


class GitIntegration:
    """Git + GitHub CLI integration for AILEX pilot."""

    def __init__(self, repo_dir: str = "."):
        self.repo_dir = os.path.abspath(repo_dir)

    def _run(self, cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=self.repo_dir, check=check,
        )

    # ── Status & info ─────────────────────────────────────────────────────────

    def status(self) -> GitStatus:
        r = self._run(["git", "status", "--porcelain=v1", "-b"])
        lines = r.stdout.splitlines()
        branch    = "unknown"
        modified  = []
        untracked = []
        staged    = []
        ahead = behind = 0

        for line in lines:
            if line.startswith("##"):
                parts = line[3:].split("...")
                branch = parts[0].strip()
                if len(parts) > 1:
                    m = __import__("re").search(r"ahead (\d+)", parts[1])
                    if m: ahead = int(m.group(1))
                    m = __import__("re").search(r"behind (\d+)", parts[1])
                    if m: behind = int(m.group(1))
                continue
            if len(line) < 2:
                continue
            xy   = line[:2]
            path = line[3:].strip()
            if xy[0] in "MADRCU":
                staged.append(path)
            if xy[1] in "MD":
                modified.append(path)
            if xy == "??":
                untracked.append(path)

        return GitStatus(
            branch=branch, modified=modified, untracked=untracked,
            staged=staged, ahead=ahead, behind=behind,
            clean=not (modified or untracked or staged),
        )

    def diff(self, staged: bool = False, file: str = "") -> str:
        cmd = ["git", "diff"]
        if staged: cmd.append("--staged")
        if file:   cmd.append(file)
        r = self._run(cmd)
        return r.stdout[:20_000]

    def log(self, n: int = 10, oneline: bool = True) -> str:
        fmt = "--oneline" if oneline else "--format=%h %an %ar %s"
        r   = self._run(["git", "log", f"-{n}", fmt])
        return r.stdout

    def blame(self, file: str, lines: Optional[str] = None) -> str:
        cmd = ["git", "blame", file]
        if lines: cmd += [f"-L{lines}"]
        r = self._run(cmd)
        return r.stdout[:5_000]

    def current_branch(self) -> str:
        r = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        return r.stdout.strip()

    def is_git_repo(self) -> bool:
        r = self._run(["git", "rev-parse", "--git-dir"])
        return r.returncode == 0

    # ── Mutations ─────────────────────────────────────────────────────────────

    def add(self, files: List[str] = []) -> bool:
        """Stage files. Empty list = stage all changed (not untracked)."""
        if files:
            r = self._run(["git", "add"] + files)
        else:
            r = self._run(["git", "add", "-u"])
        return r.returncode == 0

    def add_all(self) -> bool:
        r = self._run(["git", "add", "-A"])
        return r.returncode == 0

    def commit(self, message: str, files: List[str] = []) -> CommitResult:
        """Stage specific files and commit with the given message."""
        if files:
            self.add(files)
        r = self._run(["git", "commit", "-m", message])
        if r.returncode != 0:
            return CommitResult(success=False, sha="", message=message,
                                files=files, error=r.stderr[:200])
        sha_r = self._run(["git", "rev-parse", "--short", "HEAD"])
        return CommitResult(
            success=True, sha=sha_r.stdout.strip(),
            message=message, files=files,
        )

    def commit_ailex(self, ailex_message: str, summary: str = "") -> CommitResult:
        """Commit with AILEX co-author tag."""
        msg = ailex_message
        if summary:
            msg = f"{summary}\n\n{ailex_message}"
        msg += "\n\nCo-Authored-By: AILEX Pilot <ailex@anthropic.com>"
        return self.commit(msg)

    def create_branch(self, name: str) -> bool:
        r = self._run(["git", "checkout", "-b", name])
        return r.returncode == 0

    def push(self, remote: str = "origin", branch: str = "") -> bool:
        branch = branch or self.current_branch()
        r = self._run(["git", "push", "-u", remote, branch])
        return r.returncode == 0

    def create_pr(
        self,
        title:  str,
        body:   str,
        base:   str = "main",
        draft:  bool = False,
    ) -> PRResult:
        """Create GitHub PR via gh CLI."""
        cmd = ["gh", "pr", "create",
               "--title", title,
               "--body",  body,
               "--base",  base]
        if draft:
            cmd.append("--draft")
        r = self._run(cmd)
        if r.returncode != 0:
            return PRResult(success=False, url="", number=0, title=title,
                            error=r.stderr[:200] or r.stdout[:200])
        # Extract URL from output
        url = r.stdout.strip().split("\n")[-1].strip()
        num = 0
        import re
        m = re.search(r"/pull/(\d+)", url)
        if m: num = int(m.group(1))
        return PRResult(success=True, url=url, number=num, title=title)

    def generate_commit_message(self, diff: str, context: str = "") -> str:
        """Generate a commit message from diff (for use with AI)."""
        lines = [l for l in diff.splitlines() if l.startswith(("+", "-"))
                 and not l.startswith(("+++", "---"))][:50]
        changed_files = [l.split("b/")[-1] for l in diff.splitlines()
                         if l.startswith("+++ b/")]
        summary = f"Files: {', '.join(changed_files[:5])}" if changed_files else ""
        changes = "\n".join(lines[:20])
        return f"[AILEX] {context or 'Auto-generated'}\n{summary}\n\nChanges:\n{changes}"

    def format_status(self, s: GitStatus) -> str:
        lines = [f"Branch: {s.branch}" + (f" (↑{s.ahead} ↓{s.behind})" if s.ahead or s.behind else "")]
        if s.clean:
            lines.append("  ✓ Working tree clean")
        if s.staged:    lines.append(f"  Staged:    {', '.join(s.staged[:5])}")
        if s.modified:  lines.append(f"  Modified:  {', '.join(s.modified[:5])}")
        if s.untracked: lines.append(f"  Untracked: {', '.join(s.untracked[:5])}")
        return "\n".join(lines)
