"""
AILEX Pilot — cli.py
Full-featured CLI for AILEX as a production co-pilot.

Commands:
  ask      <request>        — process a request with full project context
  context  [path]           — show project structure and summary
  run      <code>           — execute code directly
  test     [path]           — run test suite
  git      [diff|commit|pr] — git operations
  cost                      — show cost report
  monitor                   — full monitoring dashboard
  sessions                  — list conversation sessions
  resume   <session_id>     — resume a previous session
  bench                     — run quality benchmarks
  secrets                   — show API key status
  webhooks [port]           — start webhook server
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from rich.console import Console
    from rich.panel   import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH = True
except ImportError:
    RICH = False

from .pipeline import PilotPipeline
from .secrets  import SecretsManager


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AILEX Pilot — Production Co-Pilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ask AILEX with full project context
  ailex-pilot ask "fix the broken authentication middleware"
  ailex-pilot ask "add rate limiting to the API" --commit

  # Show project structure
  ailex-pilot context
  ailex-pilot context /path/to/project

  # Execute code
  ailex-pilot run "print('hello')" --lang python
  ailex-pilot test

  # Git operations
  ailex-pilot git diff
  ailex-pilot git commit "fix: authentication middleware"
  ailex-pilot git pr "fix: auth" --body "Fixes broken login"

  # Monitoring
  ailex-pilot cost
  ailex-pilot monitor
  ailex-pilot sessions
  ailex-pilot resume abc123

  # Quality
  ailex-pilot bench

  # Secrets
  ailex-pilot secrets

  # Webhooks
  ailex-pilot webhooks 8765

API Keys (set in .env):
  ANTHROPIC_API_KEY       — Claude agents (required)
  REPLICATE_API_TOKEN     — image/video generation
  GITHUB_TOKEN            — PR creation
        """
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ask
    p_ask = sub.add_parser("ask", help="Process request with project context")
    p_ask.add_argument("request", nargs="+")
    p_ask.add_argument("--domain",  default=None)
    p_ask.add_argument("--loops",   type=int, default=None)
    p_ask.add_argument("--commit",  action="store_true", help="Auto-commit if code runs")
    p_ask.add_argument("--no-exec", action="store_true", help="Skip code execution")
    p_ask.add_argument("--no-ctx",  action="store_true", help="Skip project context injection")
    p_ask.add_argument("--format",  default="full", choices=["full","concise","json","trace_only"])
    p_ask.add_argument("--session", default=None, help="Resume session by ID")
    p_ask.add_argument("--budget",  type=float, default=5.0)
    p_ask.add_argument("--dir",     default=".", help="Project directory")

    # context
    p_ctx = sub.add_parser("context", help="Show project context")
    p_ctx.add_argument("path", nargs="?", default=".")
    p_ctx.add_argument("--full", action="store_true", help="Show full file contents")

    # run
    p_run = sub.add_parser("run", help="Execute code")
    p_run.add_argument("code")
    p_run.add_argument("--lang", default="python", choices=["python","javascript","typescript","bash"])
    p_run.add_argument("--timeout", type=int, default=30)

    # test
    p_test = sub.add_parser("test", help="Run test suite")
    p_test.add_argument("path", nargs="?", default=".")
    p_test.add_argument("--lang", default="python")

    # git
    p_git = sub.add_parser("git", help="Git operations")
    p_git.add_argument("action", choices=["diff","status","commit","pr","log"])
    p_git.add_argument("message", nargs="?", default="")
    p_git.add_argument("--body", default="")
    p_git.add_argument("--dir", default=".")

    # cost
    sub.add_parser("cost", help="Show cost report")

    # monitor
    sub.add_parser("monitor", help="Full monitoring dashboard")

    # sessions
    sub.add_parser("sessions", help="List conversation sessions")

    # resume
    p_resume = sub.add_parser("resume", help="Resume session")
    p_resume.add_argument("session_id")

    # bench
    p_bench = sub.add_parser("bench", help="Run quality benchmarks")
    p_bench.add_argument("--demo", action="store_true", default=True)

    # secrets
    sub.add_parser("secrets", help="Show API key status")

    # webhooks
    p_wh = sub.add_parser("webhooks", help="Start webhook server")
    p_wh.add_argument("port", type=int, default=8765, nargs="?")

    args = parser.parse_args()

    console = Console() if RICH else None

    def print_out(text: str, title: str = "") -> None:
        if RICH and console:
            if title:
                console.print(Panel(text, title=title))
            else:
                console.print(text)
        else:
            if title:
                print(f"\n{'─'*60}\n{title}\n{'─'*60}")
            print(text)

    # ── Commands ──────────────────────────────────────────────────────────────

    if args.command == "ask":
        request = " ".join(args.request)
        pilot   = PilotPipeline(
            project_dir=args.dir,
            session_id=args.session,
            session_budget=args.budget,
        )
        if RICH:
            console.rule(f"[bold]AILEX PILOT[/bold]  session={pilot.session.id}")
            console.print(f"[dim]Project: {args.dir} | Budget: ${args.budget}[/dim]")

        def run_ask():
            return pilot.process(
                request,
                domain=args.domain,
                force_loops=args.loops,
                run_code=not args.no_exec,
                auto_commit=args.commit,
                include_context=not args.no_ctx,
                fmt=args.format,
            )

        if RICH:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                          console=console, transient=True) as prog:
                prog.add_task(f"Processing: {request[:60]}...", total=None)
                result = run_ask()
        else:
            print(f"Processing: {request[:60]}...")
            result = run_ask()

        if result.get("error"):
            print_out(f"ERROR: {result['error']}", "Error")
            return 1

        print_out(result["report"], f"AILEX | {result['domain']} | T={result['loops_run']} | conf={result['confidence']:.1%}")

        if result["exec_results"]:
            print_out("\n".join(result["exec_results"]), "Code Execution")

        if result["git_status"]:
            print_out(result["git_status"], "Git Status")

        if result["committed"]:
            c = result["committed"]
            print_out(f"Committed: {c.sha} — {c.message[:60]}", "Git Commit")

        pilot.close()

    elif args.command == "context":
        from .context import ProjectReader
        reader = ProjectReader()
        ctx    = reader.read(args.path)
        text   = ctx.summary + "\n\nStructure:\n" + ctx.structure
        if args.full:
            text += "\n\n" + reader.to_prompt(ctx)
        print_out(text, f"Project: {ctx.name}")

    elif args.command == "run":
        from .executor import CodeExecutor
        ex = CodeExecutor()
        r  = ex.run_code(args.code, args.lang, timeout=args.timeout)
        print_out(ex.format_result(r), "Code Execution")

    elif args.command == "test":
        from .executor import CodeExecutor
        ex = CodeExecutor()
        r  = ex.run_tests(args.path, args.lang)
        print_out(ex.format_result(r), "Test Results")
        return 0 if r.success else 1

    elif args.command == "git":
        from .git_integration import GitIntegration
        git = GitIntegration(getattr(args, "dir", "."))
        if args.action == "diff":
            print_out(git.diff() or "No changes", "Git Diff")
        elif args.action == "status":
            print_out(git.format_status(git.status()), "Git Status")
        elif args.action == "commit":
            if not args.message:
                print("Error: commit requires a message")
                return 1
            r = git.commit_ailex(args.message)
            print_out(f"Commit: {r.sha} — {r.message[:60]}" if r.success else f"Failed: {r.error}", "Git")
        elif args.action == "pr":
            pushed = git.push()
            if not pushed:
                print("Push failed")
                return 1
            r = git.create_pr(args.message, args.body)
            print_out(r.url if r.success else f"Failed: {r.error}", "Pull Request")
        elif args.action == "log":
            print_out(git.log(10), "Git Log")

    elif args.command == "cost":
        from .cost_control import CostController
        c = CostController()
        print_out(c.report(), "Cost Report")

    elif args.command == "monitor":
        from .cost_control import CostController
        from .monitor import Monitor
        c = CostController()
        m = Monitor(c)
        print_out(m.dashboard(), "AILEX Monitor")

    elif args.command == "sessions":
        from .conversation import ConversationMemory
        mem = ConversationMemory()
        print_out(mem.summary(), "Conversations")

    elif args.command == "resume":
        pilot = PilotPipeline(session_id=args.session_id)
        sess  = pilot.session
        print_out(
            f"Session: {sess.id} — {sess.name}\n"
            f"Messages: {len(sess.messages)}\n"
            f"Project: {sess.project_dir}",
            "Resumed Session"
        )
        pilot.close()

    elif args.command == "bench":
        pilot = PilotPipeline(demo=args.demo)
        print_out(pilot.run_benchmark(demo=args.demo), "Benchmark Results")
        pilot.close()

    elif args.command == "secrets":
        s = SecretsManager()
        s.load_all()
        print_out(s.status(), "API Keys")

    elif args.command == "webhooks":
        pilot = PilotPipeline(webhook_port=args.port)
        print_out(f"Webhook server running on port {args.port}\nPress Ctrl+C to stop.", "Webhooks")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pilot.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
