"""
AILEX Pilot — interactive_shell.py
Interactive REPL shell with auto-complete, history, @-directives.
Inspired by prompt-toolkit's interaction model — AILEX original.
"""
from __future__ import annotations

import os
import sys
from typing import Any, List, Optional


COMMANDS = [
    "/help", "/cost", "/context", "/sessions", "/bench",
    "/clear", "/exit", "/quit", "/save", "/load",
    "/template", "/watch", "/plan", "/queue", "/security",
    "/complexity", "/search", "/providers",
]

DIRECTIVES = [
    "@file", "@folder", "@url", "@git",
    "@function", "@kb", "@session", "@test",
]

DOMAINS = [
    "bug", "feature", "architecture", "deploy", "security",
    "code", "testing", "refactor", "documentation", "data",
    "strategy", "performance", "design", "mobile",
]


class AILEXShell:
    """
    Interactive AILEX shell with history, completion, @-directives.
    Works in Termux without prompt-toolkit (falls back to input()).
    Upgrades to readline/prompt-toolkit if available.
    """

    HISTORY_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".ailex_history"
    )

    def __init__(self, pilot: Any):
        self.pilot    = pilot
        self._history: List[str] = []
        self._load_history()
        self._setup_readline()

    def _setup_readline(self) -> None:
        try:
            import readline
            # Load history
            if os.path.exists(self.HISTORY_FILE):
                readline.read_history_file(self.HISTORY_FILE)
            readline.set_history_length(1000)

            # Auto-complete
            completions = COMMANDS + DIRECTIVES + DOMAINS
            def completer(text, state):
                options = [c for c in completions if c.startswith(text)]
                return options[state] if state < len(options) else None
            readline.set_completer(completer)
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass

    def _load_history(self) -> None:
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE) as f:
                    self._history = [l.strip() for l in f if l.strip()]
            except Exception:
                pass

    def _save_history(self) -> None:
        try:
            import readline
            readline.write_history_file(self.HISTORY_FILE)
        except Exception:
            with open(self.HISTORY_FILE, "w") as f:
                f.write("\n".join(self._history[-500:]))

    def run(self) -> None:
        """Start interactive REPL."""
        self._print_banner()
        while True:
            try:
                raw = input("\n\033[1;36mailex\033[0m \033[2m▶\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break
            if not raw:
                continue
            self._history.append(raw)
            if raw in ("/exit", "/quit", "exit", "quit"):
                break
            self._dispatch(raw)
        self._save_history()

    def _dispatch(self, raw: str) -> None:
        # Built-in commands
        if raw.startswith("/"):
            self._handle_command(raw)
            return

        # Process @-directives
        try:
            from ailex_pilot.context_directives import DirectiveProcessor
            dp = DirectiveProcessor(
                project_reader=getattr(self.pilot, "reader", None),
                knowledge_base=None,
                conversation=getattr(self.pilot, "memory", None),
                session_id=getattr(self.pilot.session, "id", ""),
            )
            request, found = dp.process(raw, self.pilot.project_dir)
            if found:
                print(f"\033[2m  Expanded: {', '.join(found)}\033[0m")
        except Exception:
            request = raw

        # Run AILEX
        print("\033[2m  Processing…\033[0m", end="\r")
        try:
            result = self.pilot.process(
                request, run_code=False, include_context=True, fmt="concise"
            )
            report = result.get("report", result.get("error", ""))
            domain = result.get("domain", "")
            conf   = result.get("confidence", 0)
            loops  = result.get("loops_run", 0)
            cost   = result.get("cost_usd", 0)
            print(f"\033[2m  [{domain} T={loops} {conf:.0%} ${cost:.4f}]\033[0m")
            print(f"\n{report}")
        except Exception as e:
            print(f"\033[31m  Error: {e}\033[0m")

    def _handle_command(self, cmd: str) -> None:
        parts = cmd.split(None, 1)
        c     = parts[0].lower()
        arg   = parts[1] if len(parts) > 1 else ""

        handlers = {
            "/help":       self._cmd_help,
            "/cost":       lambda a: print(self.pilot.cost_report()),
            "/context":    lambda a: print(self.pilot.project_summary()),
            "/sessions":   lambda a: print(self.pilot.memory.summary()),
            "/bench":      lambda a: print(self.pilot.run_benchmark(demo=True)),
            "/clear":      lambda a: os.system("clear"),
            "/providers":  self._cmd_providers,
            "/template":   self._cmd_template,
            "/complexity": self._cmd_complexity,
            "/security":   self._cmd_security,
            "/search":     self._cmd_search,
            "/save":       self._cmd_save,
        }
        fn = handlers.get(c)
        if fn:
            fn(arg)
        else:
            print(f"Unknown command: {c}. Type /help.")

    def _cmd_help(self, _: str) -> None:
        print("\033[1mAILEX Shell Commands:\033[0m")
        for cmd in COMMANDS:
            desc = {
                "/help": "show this help",
                "/cost": "show cost report",
                "/context": "show project structure",
                "/sessions": "list sessions",
                "/bench": "run benchmarks",
                "/clear": "clear screen",
                "/providers": "show LLM providers",
                "/template": "list prompt templates",
                "/complexity": "analyse code complexity",
                "/security": "run security scan",
                "/search": "semantic code search <query>",
                "/save": "save last response",
            }.get(cmd, "")
            print(f"  {cmd:15s} {desc}")
        print("\n\033[1m@-Directives:\033[0m")
        for d in DIRECTIVES:
            print(f"  {d}")
        print("\nExample: fix the bug in @file src/auth.py using @git context")

    def _cmd_providers(self, _: str) -> None:
        try:
            from ailex_pilot.provider_registry import ProviderRegistry
            print(ProviderRegistry().status())
        except Exception as e:
            print(f"Providers: {e}")

    def _cmd_template(self, arg: str) -> None:
        try:
            from ailex_pilot.prompt_templates import PromptLibrary
            lib = PromptLibrary()
            if arg:
                tmpl = lib.get(arg)
                if tmpl:
                    print(f"Template: {tmpl.name}\n{tmpl.description}\n"
                          f"Variables: {tmpl.variables}\n\n{tmpl.template[:300]}")
                else:
                    print(f"Template '{arg}' not found.")
            else:
                print(lib.summary())
                for t in lib.list():
                    print(f"  {t.name:20s} {t.description[:50]}")
        except Exception as e:
            print(f"Templates: {e}")

    def _cmd_complexity(self, arg: str) -> None:
        try:
            from ailex_pilot.complexity import ComplexityAnalyzer
            root   = arg or self.pilot.project_dir
            report = ComplexityAnalyzer().analyze_project(root)
            from ailex_pilot.complexity import ComplexityAnalyzer as CA
            print(CA().format_project(report))
        except Exception as e:
            print(f"Complexity: {e}")

    def _cmd_security(self, _: str) -> None:
        try:
            from ailex_pilot.security import SecurityScanner
            report = SecurityScanner().scan_project(self.pilot.project_dir)
            from ailex_pilot.security import SecurityScanner as SS
            print(SS().format_report(report))
        except Exception as e:
            print(f"Security: {e}")

    def _cmd_search(self, query: str) -> None:
        if not query:
            print("Usage: /search <query>")
            return
        try:
            from ailex_pilot.code_search import SemanticCodeSearch
            cs = SemanticCodeSearch()
            cs.index_project(self.pilot.project_dir)
            results = cs.search(query, top_k=8)
            print(cs.format_results(results, query))
        except Exception as e:
            print(f"Search: {e}")

    def _cmd_save(self, arg: str) -> None:
        if self._history:
            path = arg or f"ailex_session_{int(__import__('time').time())}.txt"
            with open(path, "w") as f:
                f.write("\n".join(self._history))
            print(f"Saved to {path}")

    def _print_banner(self) -> None:
        print("\033[1;36m")
        print("  ⚡ AILEX Interactive Shell")
        print(f"  Session: {self.pilot.session.id} | "
              f"{'Real API' if self.pilot.real_api else 'Demo'}")
        print("  Type /help for commands, Tab for completion")
        print("\033[0m")
