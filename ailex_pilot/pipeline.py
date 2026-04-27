"""
AILEX Pilot — pipeline.py
PilotPipeline: wraps AILEXMythosPipeline with all pilot capabilities.

Adds to the base pipeline:
  - Project context injection (reads actual codebase)
  - Multi-turn conversation memory
  - Code execution after generation
  - Git integration (diff, commit, PR)
  - Cost control with budget enforcement
  - Retry/resume on failure
  - Real-time monitoring
  - Quality evaluation
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from typing import Optional, Tuple

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from .context        import ProjectContext, ProjectReader
from .conversation   import ConversationMemory, Session
from .cost_control   import CostController
from .evaluator      import Evaluator
from .executor       import CodeExecutor, ExecutionResult
from .git_integration import GitIntegration
from .monitor        import Monitor
from .retry          import RetryManager
from .secrets        import SecretsManager
from .webhooks       import WebhookServer


class PilotPipeline:
    """
    AILEX Pilot — production-ready pipeline.
    Wraps AILEXMythosPipeline v6 with all missing capabilities.
    """

    def __init__(
        self,
        project_dir:    str   = ".",
        session_id:     Optional[str] = None,
        session_budget: float = 5.0,
        webhook_port:   Optional[int] = None,
        demo:           bool  = False,
    ):
        # Load secrets first
        self.secrets = SecretsManager()
        self.secrets.load_all()

        # Import AILEX v6
        try:
            from ailex_mythos_v6 import AILEXMythosPipeline, MythosCognitiveConfig
            cfg          = MythosCognitiveConfig()
            self._ailex  = AILEXMythosPipeline(demo=demo)
            self.real_api = self._ailex.real_api
        except ImportError:
            try:
                from ailex_mythos_v5 import AILEXMythosPipeline, MythosCognitiveConfig
                self._ailex  = AILEXMythosPipeline(demo=demo)
                self.real_api = self._ailex.real_api
            except ImportError:
                self._ailex  = None
                self.real_api = False

        # Components
        self.project_dir = os.path.abspath(project_dir)
        self.reader      = ProjectReader()
        self.executor    = CodeExecutor()
        self.git         = GitIntegration(project_dir)
        self.memory      = ConversationMemory()
        self.cost        = CostController(session_budget=session_budget)
        self.monitor     = Monitor(self.cost)
        self.retry       = RetryManager()
        self.evaluator   = Evaluator()

        # Session
        if session_id:
            self.session = self.memory.get_session(session_id) or self.memory.new_session(
                project_dir=project_dir
            )
        else:
            self.session = self.memory.new_session(
                name=os.path.basename(self.project_dir),
                project_dir=self.project_dir,
            )

        # Project context (lazy)
        self._project_ctx: Optional[ProjectContext] = None

        # Webhooks
        self._webhook: Optional[WebhookServer] = None
        if webhook_port:
            self.start_webhooks(webhook_port)

    # ── Project context ───────────────────────────────────────────────────────

    def load_project(self, path: Optional[str] = None) -> ProjectContext:
        """Read and index the project codebase."""
        root = path or self.project_dir
        self._project_ctx = self.reader.read(root)
        return self._project_ctx

    def project_summary(self) -> str:
        if not self._project_ctx:
            self.load_project()
        return self._project_ctx.summary  # type: ignore

    # ── Main process ──────────────────────────────────────────────────────────

    def process(
        self,
        request:         str,
        domain:          Optional[str] = None,
        force_loops:     Optional[int] = None,
        run_code:        bool = True,
        auto_commit:     bool = False,
        include_context: bool = True,
        fmt:             str  = "full",
    ) -> dict:
        """
        Full pilot process: context + AILEX + execute + git + cost tracking.
        Returns a structured result dict.
        """
        start_time = time.time()

        # Budget check
        estimated = self.cost.estimate_request(domain or "code")
        if not self.cost.can_proceed(estimated):
            return {
                "error":   "Budget limit reached",
                "budget":  self.cost.check_budget().__dict__,
                "request": request,
            }

        # Build augmented request with project context + conversation history
        augmented = request
        if include_context:
            if not self._project_ctx:
                self.load_project()
            ctx_str  = self.reader.to_prompt(self._project_ctx, max_files=10)  # type: ignore
            conv_str = self.memory.build_context(self.session, max_messages=6)
            augmented = f"{ctx_str}\n\n{conv_str}\n\n=== CURRENT REQUEST ===\n{request}"

        # Store user message
        self.memory.add_message(self.session.id, "user", request)

        # Run AILEX pipeline
        p = h = coda = None
        error = None
        exec_results = []

        try:
            if self._ailex:
                p, h, coda = self._ailex.process(
                    augmented,
                    override_domain=domain,
                    force_loops=force_loops,
                    output_format=fmt,
                )
                # Track cost
                if coda and hasattr(coda, "tokens_used"):
                    self.cost.record_api_call(
                        model="claude-sonnet-4-6",  # approximate mix
                        tokens_in=coda.tokens_used,
                        tokens_out=coda.tokens_used // 3,
                        operation="ailex_pipeline",
                        domain=coda.domain,
                        session_id=self.session.id,
                    )
            else:
                error = "AILEX pipeline not available (import failed)"
        except Exception as e:
            error = str(e)

        # Execute generated code
        if run_code and coda and not error:
            synthesis = ""
            if h and h.loop_history:
                for c in h.loop_history[-1].contributions:
                    if c.agent == "ORION":
                        synthesis = c.signal
                        break
            if synthesis:
                exec_results = self.executor.extract_and_run(synthesis, cwd=self.project_dir)

        # Git status
        git_status = None
        if self.git.is_git_repo():
            git_status = self.git.status()

        # Auto commit if requested and code ran successfully
        committed = None
        if auto_commit and exec_results and all(r.success for r in exec_results):
            if git_status and not git_status.clean:
                msg = f"AILEX: {request[:60]}"
                committed = self.git.commit_ailex(msg)

        # Store assistant message
        if coda:
            report = self._ailex.report(p, h, coda, fmt=fmt) if self._ailex else ""
            self.memory.add_message(
                self.session.id, "assistant", report,
                domain=coda.domain, loops_run=coda.loops_run,
                confidence=coda.final_confidence,
                tokens=getattr(coda, "tokens_used", 0),
            )

        return {
            "request":       request,
            "session_id":    self.session.id,
            "domain":        coda.domain if coda else domain,
            "loops_run":     coda.loops_run if coda else 0,
            "confidence":    coda.final_confidence if coda else 0,
            "quality":       coda.avg_quality if coda else 0,
            "report":        self._ailex.report(p, h, coda, fmt=fmt) if (self._ailex and coda) else error or "",
            "exec_results":  [self.executor.format_result(r) for r in exec_results],
            "git_status":    self.git.format_status(git_status) if git_status else "",
            "committed":     committed,
            "cost_usd":      round(self.cost.session_spent, 5),
            "duration_s":    round(time.time() - start_time, 2),
            "error":         error,
        }

    # ── Convenience ───────────────────────────────────────────────────────────

    def git_commit_ailex(self, message: str = "") -> dict:
        """Stage all changed files and commit with AILEX message."""
        status = self.git.status()
        if status.clean:
            return {"committed": False, "reason": "Working tree clean"}
        diff    = self.git.diff()
        msg     = message or f"AILEX: implement changes from pilot session {self.session.id}"
        result  = self.git.commit_ailex(msg, summary=self.session.name)
        return {"committed": result.success, "sha": result.sha, "error": result.error}

    def create_pr(self, title: str = "", body: str = "") -> dict:
        """Push and create a GitHub PR."""
        pushed = self.git.push()
        if not pushed:
            return {"success": False, "error": "Push failed"}
        result = self.git.create_pr(title or f"AILEX: {self.session.name}", body or "")
        return {"success": result.success, "url": result.url, "error": result.error}

    def run_benchmark(self, demo: bool = True) -> str:
        """Run quality benchmarks."""
        suite = self.evaluator.run_benchmark(self._ailex or object(), demo=demo)
        return self.evaluator.format_suite(suite)

    def dashboard(self) -> str:
        """Full monitoring dashboard."""
        return self.monitor.dashboard()

    def cost_report(self) -> str:
        return self.cost.report()

    def start_webhooks(self, port: int = 8765) -> None:
        """Start webhook server for GitHub/Slack integration."""
        self._webhook = WebhookServer(port=port)
        if self._ailex:
            from .webhooks import make_github_pr_handler, make_push_handler
            self._webhook.on("pull_request", make_github_pr_handler(self._ailex))
            self._webhook.on("push",         make_push_handler(self._ailex))
        self._webhook.start()

    def close(self) -> None:
        self.memory.close()
        if self._webhook:
            self._webhook.stop()
