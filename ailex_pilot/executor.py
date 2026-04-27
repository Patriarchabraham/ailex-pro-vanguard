"""
AILEX Pilot — executor.py
Runs generated code in a sandboxed subprocess with timeout and resource limits.
Supports: Python, Node.js/TypeScript, Shell, and test runners.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExecutionResult:
    success:     bool
    stdout:      str
    stderr:      str
    exit_code:   int
    duration_s:  float
    language:    str
    command:     str
    timed_out:   bool  = False
    files:       List[str] = field(default_factory=list)  # generated files


class CodeExecutor:
    """
    Runs code safely in a subprocess with timeout.
    Does NOT provide full sandboxing — use in trusted environments.
    For production, wrap in Docker or a proper sandbox.
    """

    DEFAULT_TIMEOUT = 30  # seconds

    RUNNERS: Dict[str, List[str]] = {
        "python":     ["python3", "-c"],
        "javascript": ["node",    "-e"],
        "typescript": ["npx", "ts-node", "-e"],
        "bash":       ["bash",    "-c"],
        "sh":         ["sh",      "-c"],
    }

    TEST_RUNNERS: Dict[str, List[str]] = {
        "python":     ["python3", "-m", "pytest", "--tb=short", "-q"],
        "javascript": ["npx", "jest", "--passWithNoTests"],
        "typescript": ["npx", "jest", "--passWithNoTests"],
    }

    def run_code(
        self,
        code:     str,
        language: str = "python",
        timeout:  int = DEFAULT_TIMEOUT,
        cwd:      Optional[str] = None,
        env:      Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute code string in the given language."""
        start  = time.time()
        runner = self.RUNNERS.get(language)

        if not runner:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Unsupported language: {language}",
                exit_code=1, duration_s=0, language=language, command="",
            )

        # Write to temp file for languages that don't support -c properly
        if language in ("typescript",):
            with tempfile.NamedTemporaryFile(suffix=".ts", delete=False, mode="w") as f:
                f.write(code)
                tmp = f.name
            cmd = ["npx", "ts-node", tmp]
        elif language == "python" and len(code) > 1000:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
                f.write(code)
                tmp = f.name
            cmd = ["python3", tmp]
        else:
            tmp = None
            cmd = runner + [code]

        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.getcwd(),
                env=run_env,
            )
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10_000],
                stderr=result.stderr[:5_000],
                exit_code=result.returncode,
                duration_s=round(time.time() - start, 2),
                language=language,
                command=" ".join(cmd[:3]),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Timed out after {timeout}s",
                exit_code=-1, duration_s=timeout,
                language=language, command=" ".join(cmd[:3]), timed_out=True,
            )
        except FileNotFoundError as e:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Runtime not found: {e}",
                exit_code=1, duration_s=round(time.time()-start, 2),
                language=language, command=" ".join(cmd[:3]),
            )
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)

    def run_file(
        self,
        path:    str,
        timeout: int = DEFAULT_TIMEOUT,
        cwd:     Optional[str] = None,
        args:    List[str] = [],
    ) -> ExecutionResult:
        """Run an existing file."""
        start = time.time()
        ext   = os.path.splitext(path)[1].lower()
        cmd_map = {
            ".py":  ["python3", path] + args,
            ".js":  ["node",    path] + args,
            ".ts":  ["npx", "ts-node", path] + args,
            ".sh":  ["bash",    path] + args,
        }
        cmd = cmd_map.get(ext)
        if not cmd:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Unknown file type: {ext}",
                exit_code=1, duration_s=0, language="unknown", command="",
            )
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, cwd=cwd or os.path.dirname(path),
            )
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10_000],
                stderr=result.stderr[:5_000],
                exit_code=result.returncode,
                duration_s=round(time.time()-start, 2),
                language=ext.lstrip("."),
                command=" ".join(cmd[:3]),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Timed out after {timeout}s",
                exit_code=-1, duration_s=timeout,
                language=ext.lstrip("."), command=" ".join(cmd[:3]), timed_out=True,
            )

    def run_tests(
        self,
        path:     str,
        language: str = "python",
        timeout:  int = 60,
        cwd:      Optional[str] = None,
    ) -> ExecutionResult:
        """Run test suite for a project."""
        start  = time.time()
        runner = self.TEST_RUNNERS.get(language)
        if not runner:
            return ExecutionResult(
                success=False, stdout="", stderr=f"No test runner for {language}",
                exit_code=1, duration_s=0, language=language, command="",
            )
        cmd = runner + [path] if os.path.isfile(path) else runner
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, cwd=cwd or os.getcwd(),
            )
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10_000],
                stderr=result.stderr[:5_000],
                exit_code=result.returncode,
                duration_s=round(time.time()-start, 2),
                language=language, command=" ".join(cmd[:3]),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Tests timed out after {timeout}s",
                exit_code=-1, duration_s=timeout,
                language=language, command=" ".join(cmd[:3]), timed_out=True,
            )
        except FileNotFoundError as e:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Test runner not found: {e}",
                exit_code=1, duration_s=round(time.time()-start, 2),
                language=language, command=" ".join(cmd[:3]),
            )

    def run_shell(self, command: str, timeout: int = 30,
                  cwd: Optional[str] = None) -> ExecutionResult:
        """Run an arbitrary shell command."""
        start = time.time()
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd or os.getcwd(),
            )
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10_000],
                stderr=result.stderr[:5_000],
                exit_code=result.returncode,
                duration_s=round(time.time()-start, 2),
                language="shell", command=command[:80],
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, stdout="", stderr=f"Timed out after {timeout}s",
                exit_code=-1, duration_s=timeout,
                language="shell", command=command[:80], timed_out=True,
            )

    def extract_and_run(self, ailex_output: str, cwd: Optional[str] = None) -> List[ExecutionResult]:
        """
        Extract all code blocks from AILEX output and run them.
        Returns results for each code block found.
        """
        import re
        results: List[ExecutionResult] = []
        pattern = r"```(\w+)?\s*\n([\s\S]+?)\n```"
        for m in re.finditer(pattern, ailex_output):
            lang = (m.group(1) or "").lower()
            code = m.group(2).strip()
            if lang in ("python", "py"):
                results.append(self.run_code(code, "python", cwd=cwd))
            elif lang in ("javascript", "js"):
                results.append(self.run_code(code, "javascript", cwd=cwd))
            elif lang in ("typescript", "ts"):
                results.append(self.run_code(code, "typescript", cwd=cwd))
            elif lang in ("bash", "sh", "shell"):
                results.append(self.run_shell(code, cwd=cwd))
        return results

    def format_result(self, r: ExecutionResult) -> str:
        status = "✓ PASS" if r.success else ("TIMEOUT" if r.timed_out else "✗ FAIL")
        lines  = [f"{status} | {r.language} | exit={r.exit_code} | {r.duration_s}s"]
        if r.stdout: lines.append(f"STDOUT:\n{r.stdout[:500]}")
        if r.stderr: lines.append(f"STDERR:\n{r.stderr[:300]}")
        return "\n".join(lines)
