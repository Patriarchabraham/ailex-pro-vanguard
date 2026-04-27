"""
AILEX Vision — tui.py
Full TUI for AILEX on tablet — Textual-based, keyboard-driven.
Inspired by Textual's reactive component model — AILEX original.
Falls back to Rich if Textual not installed.
"""
from __future__ import annotations

import os
from typing import Any, Optional

TUI_AVAILABLE = False
try:
    from textual.app        import App, ComposeResult
    from textual.widgets    import Header, Footer, Input, Log, Static, Button, Label
    from textual.containers import Horizontal, Vertical, ScrollableContainer
    from textual.binding    import Binding
    from textual.reactive   import reactive
    TUI_AVAILABLE = True
except ImportError:
    pass


if TUI_AVAILABLE:

    class AILEXApp(App):
        """Full-screen AILEX TUI. Keyboard-driven. Works on tablet via Termux."""

        CSS = """
        Screen { background: #0a0a14; }
        Header { background: #13131f; color: #d4af37; }
        Footer { background: #13131f; }
        #sidebar {
            width: 30; background: #13131f;
            border-right: solid #1e1e30;
        }
        #main { background: #0a0a14; }
        #output {
            background: #0a0a14; color: #e2e8f0;
            border: solid #1e1e30; height: 1fr;
        }
        #input-bar {
            height: 3; background: #13131f;
            border-top: solid #1e1e30;
        }
        Input {
            background: #0a0a14; color: #e2e8f0;
            border: solid #0066ff;
        }
        Input:focus { border: solid #d4af37; }
        .stat { color: #8a8aa0; padding: 0 1; }
        .stat-val { color: #d4af37; }
        Button { background: #0066ff; color: white; }
        Button:hover { background: #0052cc; }
        #status-bar { height: 1; background: #13131f; color: #8a8aa0; }
        """

        BINDINGS = [
            Binding("ctrl+q",     "quit",         "Quit"),
            Binding("ctrl+l",     "clear_output", "Clear"),
            Binding("ctrl+h",     "show_help",    "Help"),
            Binding("ctrl+k",     "show_cost",    "Cost"),
            Binding("ctrl+g",     "show_context", "Context"),
            Binding("escape",     "focus_input",  "Focus input"),
            Binding("ctrl+up",    "history_prev", "Prev"),
            Binding("ctrl+down",  "history_next", "Next"),
        ]

        domain: reactive[str] = reactive("auto")
        cost:   reactive[str] = reactive("$0.0000")

        def __init__(self, pilot: Any):
            super().__init__()
            self.pilot    = pilot
            self._history: list = []
            self._hist_idx = -1

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal():
                with Vertical(id="sidebar"):
                    yield Static("⚡ AILEX Pilot", classes="stat")
                    yield Static(f"Session: {self.pilot.session.id[:8]}", classes="stat")
                    yield Static(f"Mode: {'Real' if self.pilot.real_api else 'Demo'}", classes="stat")
                    yield Static("─" * 28, classes="stat")
                    yield Static("Domain:", classes="stat")
                    yield Static("auto", id="domain-display", classes="stat-val")
                    yield Static("─" * 28, classes="stat")
                    yield Static("Cost:", classes="stat")
                    yield Static("$0.0000", id="cost-display", classes="stat-val")
                    yield Static("─" * 28, classes="stat")
                    yield Button("Context", id="btn-context", variant="primary")
                    yield Button("Sessions", id="btn-sessions")
                    yield Button("Security", id="btn-security")
                with Vertical(id="main"):
                    yield Log(id="output", highlight=True, markup=True)
                    with Horizontal(id="input-bar"):
                        yield Input(placeholder="Ask AILEX… (@file, @git, @url, /help)", id="input")
                        yield Button("▶", id="btn-send", variant="success")
            yield Footer()

        def on_mount(self) -> None:
            self.query_one("#output", Log).write(
                "[bold cyan]AILEX Pilot TUI[/bold cyan]\n"
                "Type your request or use /help for commands.\n"
                "Shortcuts: Ctrl+H help | Ctrl+K cost | Ctrl+G context\n"
                "─" * 60
            )
            self.query_one("#input", Input).focus()

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            await self._process(event.value)

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "btn-send":
                inp = self.query_one("#input", Input)
                await self._process(inp.value)
            elif event.button.id == "btn-context":
                self._show(self.pilot.project_summary(), "Context")
            elif event.button.id == "btn-sessions":
                self._show(self.pilot.memory.summary(), "Sessions")
            elif event.button.id == "btn-security":
                from ailex_pilot.security import SecurityScanner
                r = SecurityScanner().scan_project(self.pilot.project_dir)
                self._show(SecurityScanner().format_report(r), "Security")

        async def _process(self, text: str) -> None:
            text = text.strip()
            if not text:
                return
            inp = self.query_one("#input", Input)
            inp.value = ""
            self._history.append(text)
            log = self.query_one("#output", Log)

            if text.startswith("/"):
                self._handle_command(text, log)
                return

            log.write(f"\n[bold blue]▶ {text[:80]}[/bold blue]")
            log.write("[dim]Processing…[/dim]")
            try:
                result = self.pilot.process(
                    text, run_code=False, include_context=True, fmt="concise"
                )
                report = result.get("report", result.get("error", ""))
                domain = result.get("domain", "")
                conf   = result.get("confidence", 0)
                cost_v = result.get("cost_usd", 0)
                self.query_one("#domain-display", Static).update(domain or "auto")
                total = float(self.query_one("#cost-display", Static.renderable or "$0").
                              __str__().replace("$","") or 0) + cost_v
                self.query_one("#cost-display", Static).update(f"${total:.4f}")
                log.write(f"[dim][{domain} conf={conf:.0%} ${cost_v:.4f}][/dim]")
                log.write(report)
            except Exception as e:
                log.write(f"[red]Error: {e}[/red]")

        def _handle_command(self, cmd: str, log: Log) -> None:
            c = cmd.split()[0].lower()
            if c == "/help":
                log.write("Commands: /help /cost /context /sessions /bench /clear /exit")
            elif c == "/cost":
                log.write(self.pilot.cost_report())
            elif c == "/context":
                log.write(self.pilot.project_summary())
            elif c == "/sessions":
                log.write(self.pilot.memory.summary())
            elif c == "/bench":
                log.write(self.pilot.run_benchmark(demo=True))
            elif c == "/clear":
                log.clear()
            elif c in ("/exit", "/quit"):
                self.exit()

        def _show(self, content: str, title: str) -> None:
            log = self.query_one("#output", Log)
            log.write(f"\n[bold yellow]── {title} ──[/bold yellow]")
            log.write(content)

        def action_clear_output(self) -> None:
            self.query_one("#output", Log).clear()

        def action_show_help(self) -> None:
            self._handle_command("/help", self.query_one("#output", Log))

        def action_show_cost(self) -> None:
            self._handle_command("/cost", self.query_one("#output", Log))

        def action_show_context(self) -> None:
            self._handle_command("/context", self.query_one("#output", Log))

        def action_focus_input(self) -> None:
            self.query_one("#input", Input).focus()


def run_tui(pilot: Any) -> None:
    if TUI_AVAILABLE:
        AILEXApp(pilot).run()
    else:
        print("Install Textual for TUI: pip install textual")
        print("Falling back to interactive shell…")
        from ailex_pilot.interactive_shell import AILEXShell
        AILEXShell(pilot).run()
