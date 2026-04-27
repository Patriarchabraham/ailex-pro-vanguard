"""
AILEX Pilot — webhooks.py
HTTP trigger server — receive webhooks from GitHub, Slack, CI/CD.
AILEX processes the event and responds.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse, parse_qs


@dataclass
class WebhookEvent:
    source:    str          # "github", "slack", "custom"
    event:     str          # "push", "pr", "mention", etc.
    payload:   Dict
    raw:       bytes
    headers:   Dict
    timestamp: float = field(default_factory=lambda: __import__("time").time())


WebhookHandler = Callable[[WebhookEvent], Optional[str]]


class WebhookServer:
    """
    Minimal HTTP server that receives webhooks and routes to AILEX.
    Run in a background thread — doesn't block the main process.
    """

    def __init__(
        self,
        port:           int   = 8765,
        secret:         str   = "",
        github_secret:  str   = "",
    ):
        self.port          = port
        self.secret        = secret or os.getenv("WEBHOOK_SECRET", "")
        self.github_secret = github_secret or os.getenv("GITHUB_WEBHOOK_SECRET", "")
        self._handlers: Dict[str, List[WebhookHandler]] = {}
        self._server:   Optional[HTTPServer] = None
        self._thread:   Optional[threading.Thread] = None
        self._events:   List[WebhookEvent] = []

    def on(self, event: str, handler: WebhookHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event, []).append(handler)

    def on_any(self, handler: WebhookHandler) -> None:
        """Register a catch-all handler."""
        self._handlers.setdefault("*", []).append(handler)

    def start(self) -> None:
        """Start webhook server in background thread."""
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    length  = int(self.headers.get("Content-Length", 0))
                    body    = self.rfile.read(length)
                    headers = {k.lower(): v for k, v in self.headers.items()}
                    event   = server._route(self.path, headers, body)
                    if event:
                        server._events.append(event)
                        responses = server._dispatch(event)
                        reply     = "\n".join(r for r in responses if r) or "ok"
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "ok", "response": reply}).encode())
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error":"unroutable"}')
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())

            def log_message(self, *args):
                pass  # suppress default logging

        self._server = HTTPServer(("0.0.0.0", self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"  [webhook] Listening on port {self.port}")

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

    def _route(self, path: str, headers: Dict, body: bytes) -> Optional[WebhookEvent]:
        """Parse incoming request into WebhookEvent."""
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw": body.decode(errors="ignore")}

        # GitHub webhook
        if "x-github-event" in headers:
            if self.github_secret:
                sig = headers.get("x-hub-signature-256", "")
                if not self._verify_github(body, sig):
                    return None
            return WebhookEvent(
                source="github",
                event=headers["x-github-event"],
                payload=payload, raw=body, headers=headers,
            )

        # Slack webhook
        if "x-slack-signature" in headers:
            return WebhookEvent(
                source="slack",
                event=payload.get("type", "event"),
                payload=payload, raw=body, headers=headers,
            )

        # Custom webhook
        event_type = urlparse(path).path.strip("/") or "custom"
        return WebhookEvent(
            source="custom", event=event_type,
            payload=payload, raw=body, headers=headers,
        )

    def _verify_github(self, body: bytes, signature: str) -> bool:
        if not self.github_secret:
            return True
        expected = "sha256=" + hmac.new(
            self.github_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _dispatch(self, event: WebhookEvent) -> List[str]:
        responses: List[str] = []
        for h in self._handlers.get(event.event, []):
            try:
                r = h(event)
                if r: responses.append(r)
            except Exception as e:
                responses.append(f"handler error: {e}")
        for h in self._handlers.get("*", []):
            try:
                r = h(event)
                if r: responses.append(r)
            except Exception as e:
                responses.append(f"handler error: {e}")
        return responses

    def recent_events(self, n: int = 10) -> List[WebhookEvent]:
        return self._events[-n:]

    def format_event(self, e: WebhookEvent) -> str:
        ts = __import__("time").strftime("%H:%M:%S", __import__("time").localtime(e.timestamp))
        summary = ""
        if e.source == "github":
            repo   = e.payload.get("repository", {}).get("full_name", "")
            pusher = e.payload.get("pusher", {}).get("name", "")
            summary = f"repo={repo} pusher={pusher}"
        elif e.source == "slack":
            summary = e.payload.get("text", "")[:60]
        return f"[{ts}] {e.source}/{e.event} {summary}"


# ── Preset handlers ───────────────────────────────────────────────────────────

def make_github_pr_handler(pipeline) -> WebhookHandler:
    """Auto-process GitHub PR events with AILEX."""
    def handler(event: WebhookEvent) -> Optional[str]:
        if event.event != "pull_request":
            return None
        action = event.payload.get("action", "")
        if action not in ("opened", "synchronize"):
            return None
        pr      = event.payload.get("pull_request", {})
        title   = pr.get("title", "")
        body    = pr.get("body", "")
        request = f"Review PR: '{title}'\n\nDescription: {body[:500]}"
        try:
            p, h, coda = pipeline.process(request, override_domain="code")
            return pipeline.report(p, h, coda, fmt="concise")
        except Exception as e:
            return f"AILEX error: {e}"
    return handler


def make_push_handler(pipeline) -> WebhookHandler:
    """Auto-analyze pushed commits with AILEX."""
    def handler(event: WebhookEvent) -> Optional[str]:
        if event.event != "push":
            return None
        commits  = event.payload.get("commits", [])
        messages = [c.get("message", "")[:100] for c in commits[:5]]
        if not messages:
            return None
        request = f"Analyze these commits: {'; '.join(messages)}"
        try:
            p, h, coda = pipeline.process(request, override_domain="code")
            return pipeline.report(p, h, coda, fmt="concise")
        except Exception as e:
            return f"AILEX error: {e}"
    return handler
