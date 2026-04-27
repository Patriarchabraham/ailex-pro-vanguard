"""
AILEX Pilot — notify.py
Push notifications: alert user when autonomous tasks complete.
Supports: Telegram, Slack, desktop (notify-send), terminal bell.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Optional


class Notifier:
    """Send push notifications when AILEX tasks finish."""

    def __init__(self):
        self.telegram_token  = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat   = os.getenv("TELEGRAM_CHAT_ID", "")
        self.slack_webhook   = os.getenv("SLACK_WEBHOOK_URL", "")

    def notify(self, title: str, body: str, level: str = "info") -> None:
        """Send notification via all available channels."""
        sent = False
        if self.telegram_token and self.telegram_chat:
            sent = self._telegram(title, body) or sent
        if self.slack_webhook:
            sent = self._slack(title, body, level) or sent
        if not sent:
            self._terminal(title, body)

    def task_done(self, task_title: str, result: str, success: bool = True) -> None:
        icon  = "✅" if success else "❌"
        title = f"{icon} AILEX: {task_title}"
        body  = result[:300] if result else ("Completed" if success else "Failed")
        self.notify(title, body, "success" if success else "error")

    def _telegram(self, title: str, body: str) -> bool:
        try:
            import urllib.request, json
            text = f"*{title}*\n{body[:400]}"
            data = json.dumps({"chat_id": self.telegram_chat,
                               "text": text, "parse_mode": "Markdown"}).encode()
            req  = urllib.request.Request(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                data=data, headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False

    def _slack(self, title: str, body: str, level: str) -> bool:
        try:
            import urllib.request, json
            color = {"success": "#36a64f", "error": "#e01e5a",
                     "warning": "#ff9900", "info": "#0066ff"}.get(level, "#0066ff")
            payload = {"attachments": [{"color": color, "title": title,
                                         "text": body[:400], "footer": "AILEX Pilot"}]}
            data = json.dumps(payload).encode()
            req  = urllib.request.Request(
                self.slack_webhook, data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False

    def _terminal(self, title: str, body: str) -> None:
        # Desktop notification
        for cmd in [
            ["notify-send", title, body[:200]],
            ["osascript", "-e", f'display notification "{body[:100]}" with title "{title}"'],
        ]:
            try:
                subprocess.run(cmd, capture_output=True, timeout=3)
                return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        # Terminal bell + print
        print(f"\a[AILEX] {title}: {body[:100]}")

    @property
    def channels(self) -> dict:
        return {
            "telegram": bool(self.telegram_token and self.telegram_chat),
            "slack":    bool(self.slack_webhook),
        }
