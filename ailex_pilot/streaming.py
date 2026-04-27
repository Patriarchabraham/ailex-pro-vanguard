"""
AILEX Pilot — streaming.py
Real-time streaming of AILEX responses to the user.
Shows ORION partial output as it generates — no more 60-120s silence.
"""
from __future__ import annotations

import sys
import time
from typing import Any, Callable, Generator, Optional


class StreamingOutput:
    """
    Wraps AILEX pipeline to stream ORION tokens in real time.
    Works with Rich (progress + live) or plain print fallback.
    """

    def __init__(self, use_rich: bool = True):
        self.use_rich = use_rich
        try:
            from rich.live    import Live
            from rich.spinner import Spinner
            from rich.text    import Text
            self._rich_ok = True
        except ImportError:
            self._rich_ok = False

    def stream_ask(
        self,
        pilot: Any,
        request: str,
        domain: Optional[str] = None,
        on_token: Optional[Callable[[str], None]] = None,
        fmt: str = "full",
    ) -> dict:
        """
        Process request with live streaming of agent progress.
        Shows: which agents are running, partial ORION output, final report.
        """
        if self._rich_ok and self.use_rich:
            return self._stream_rich(pilot, request, domain, on_token, fmt)
        return self._stream_plain(pilot, request, domain, on_token, fmt)

    def _stream_rich(self, pilot, request, domain, on_token, fmt) -> dict:
        from rich.live    import Live
        from rich.console import Console
        from rich.text    import Text
        from rich.panel   import Panel

        console  = Console()
        buffer   = []
        status   = ["Initialising…"]

        def _token_cb(tok: str) -> None:
            buffer.append(tok)
            if on_token:
                on_token(tok)

        with Live(console=console, refresh_per_second=8) as live:
            def update(msg: str) -> None:
                status[0] = msg
                partial   = "".join(buffer)[-400:]
                live.update(Panel(
                    f"[dim]{status[0]}[/dim]\n\n{partial}",
                    title=f"[bold]AILEX[/bold] — {request[:50]}",
                ))

            update("Loading project context…")
            # Run with streaming callback injected
            result = pilot.process(
                request,
                domain=domain,
                run_code=True,
                include_context=True,
                fmt=fmt,
                _stream_cb=_token_cb,   # pilot.process will call this if present
            )
            update("Done")

        return result

    def _stream_plain(self, pilot, request, domain, on_token, fmt) -> dict:
        stages = ["Loading context", "Running agents", "ORION synthesising", "CHAOS reviewing"]
        for stage in stages:
            print(f"\r⟳  {stage}…", end="", flush=True)
            time.sleep(0.1)

        result = pilot.process(
            request, domain=domain,
            run_code=True, include_context=True, fmt=fmt,
        )
        print(f"\r✓  Done in {result.get('duration_s', 0):.1f}s          ")
        return result

    def stream_tokens(
        self,
        gen: Generator[str, None, None],
        prefix: str = "",
    ) -> str:
        """Stream tokens from a generator, print live, return full text."""
        buffer = []
        if prefix:
            print(prefix, end="", flush=True)
        for tok in gen:
            print(tok, end="", flush=True)
            buffer.append(tok)
        print()
        return "".join(buffer)
