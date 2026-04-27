"""
AILEX Pilot — tdd_loop.py
Test-Driven Generation: generate code → run tests → fix failures → iterate.
Closes the quality loop: AILEX doesn't ship until tests pass.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class TDDIteration:
    iteration:   int
    code:        str
    test_result: Any      # ExecutionResult
    passed:      bool
    fixed:       bool = False
    error_msg:   str  = ""


@dataclass
class TDDResult:
    request:       str
    final_code:    str
    test_output:   str
    passed:        bool
    iterations:    List[TDDIteration]
    total_time_s:  float
    saved_path:    Optional[str] = None


class TDDLoop:
    """
    Generate → Test → Fix → Repeat until tests pass or max_iterations reached.
    The missing piece: AILEX code that actually works, verified.
    """

    def __init__(self, pipeline: Any, executor: Any, max_iterations: int = 4):
        self.pipeline   = pipeline
        self.executor   = executor
        self.max_iters  = max_iterations

    def run(
        self,
        request:     str,
        language:    str = "python",
        test_cmd:    Optional[str] = None,
        save_dir:    str = "/tmp/ailex_tdd",
        domain:      str = "code",
    ) -> TDDResult:
        """Full TDD cycle: generate → test → fix → commit."""
        start      = time.time()
        iterations: List[TDDIteration] = []
        os.makedirs(save_dir, exist_ok=True)

        # Step 1: Generate initial code
        result  = self.pipeline.process(request, override_domain=domain,
                                         run_code=False, include_context=True,
                                         fmt="full")
        code    = self._extract_code(result.get("report",""), language)
        passed  = False

        for i in range(1, self.max_iters + 1):
            # Save code to file
            ext      = {"python":"py","typescript":"ts","javascript":"js"}.get(language,"py")
            path     = os.path.join(save_dir, f"ailex_gen_{i}.{ext}")
            with open(path, "w") as f:
                f.write(code)

            # Run tests
            if test_cmd:
                test_res = self.executor.run_shell(
                    f"cd {save_dir} && {test_cmd}", timeout=60
                )
            else:
                test_res = self.executor.run_file(path, timeout=30)

            it = TDDIteration(
                iteration=i, code=code,
                test_result=test_res, passed=test_res.success,
            )
            iterations.append(it)

            if test_res.success:
                passed = True
                break

            # Step 2: Fix based on error
            if i < self.max_iters:
                error_ctx = f"{test_res.stderr[:800]}\n{test_res.stdout[:400]}"
                fix_req   = (
                    f"Fix this {language} code. Tests are failing.\n\n"
                    f"Error:\n{error_ctx}\n\n"
                    f"Original code:\n```{language}\n{code}\n```\n\n"
                    f"Return ONLY the fixed code, no explanation."
                )
                fix_result = self.pipeline.process(
                    fix_req, override_domain="bug",
                    run_code=False, include_context=False, fmt="full"
                )
                new_code = self._extract_code(fix_result.get("report",""), language)
                if new_code and new_code != code:
                    code       = new_code
                    it.fixed   = True
                else:
                    break  # Can't improve

        final_path = os.path.join(save_dir, f"ailex_final.{ext}")
        with open(final_path, "w") as f:
            f.write(code)

        return TDDResult(
            request=request, final_code=code,
            test_output=iterations[-1].test_result.stdout if iterations else "",
            passed=passed, iterations=iterations,
            total_time_s=round(time.time()-start, 2),
            saved_path=final_path,
        )

    def _extract_code(self, text: str, language: str) -> str:
        """Extract first code block from AILEX output."""
        for lang in (language, "python", "typescript", "javascript", ""):
            m = re.search(rf"```{lang}\s*\n([\s\S]+?)\n```", text, re.I)
            if m:
                return m.group(1).strip()
        # Fallback: take last substantial paragraph
        lines = [l for l in text.split("\n") if l.strip() and not l.startswith("#")]
        return "\n".join(lines[:50]) if lines else text[:500]

    def format_result(self, r: TDDResult) -> str:
        status = "✓ PASSED" if r.passed else "✗ FAILED"
        lines  = [
            f"TDD Result: {status} | {len(r.iterations)} iterations | {r.total_time_s}s",
            f"Saved: {r.saved_path}",
        ]
        for it in r.iterations:
            icon = "✓" if it.passed else ("→" if it.fixed else "✗")
            lines.append(f"  {icon} Iter {it.iteration}: {'pass' if it.passed else 'fail'}"
                         + (" [fixed]" if it.fixed else ""))
        if not r.passed:
            lines.append(f"\nLast error: {r.test_output[:200]}")
        return "\n".join(lines)
