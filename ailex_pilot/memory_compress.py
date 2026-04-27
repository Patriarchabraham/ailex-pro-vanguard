"""
AILEX Pilot — memory_compress.py
Intelligent compression of long conversation sessions.
Summarises old messages to stay within context limits.
"""
from __future__ import annotations

import os
import time
from typing import Any, List, Optional


class MemoryCompressor:
    """
    Summarises old conversation messages to save context window.
    Keeps recent N messages verbatim, summarises everything older.
    """

    KEEP_RECENT = 10   # always keep last N messages verbatim

    def __init__(self, client: Any = None):
        self.client = client

    def compress_session(self, memory: Any, session_id: str,
                          keep_recent: int = KEEP_RECENT) -> str:
        """
        Summarise messages older than keep_recent into a single summary message.
        Returns the summary text.
        """
        session = memory.get_session(session_id)
        if not session or len(session.messages) <= keep_recent:
            return ""

        old_msgs  = session.messages[:-keep_recent]
        to_compress = "\n\n".join(
            f"[{m.role.upper()} | {m.domain or 'general'}]: {m.content[:300]}"
            for m in old_msgs
        )

        summary = self._summarise(to_compress)

        # Delete old messages and replace with summary
        memory.conn.execute(
            "DELETE FROM messages WHERE session_id=? AND id NOT IN "
            "(SELECT id FROM messages WHERE session_id=? ORDER BY ts DESC LIMIT ?)",
            (session_id, session_id, keep_recent)
        )
        # Insert summary as first message
        memory.add_message(
            session_id, "system",
            f"[COMPRESSED HISTORY — {len(old_msgs)} messages]\n{summary}",
            domain="summary",
        )
        memory.conn.commit()
        return summary

    def _summarise(self, text: str) -> str:
        if not self.client:
            # Demo: first 500 chars as "summary"
            return f"Conversation summary (demo): {text[:400]}..."
        try:
            resp = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                messages=[{"role": "user", "content":
                    f"Summarise this conversation history into 3-5 key points. "
                    f"Keep: decisions made, code written, problems solved, context needed.\n\n{text[:4000]}"}],
            )
            return resp.content[0].text
        except Exception as e:
            return f"Summary unavailable: {e}"

    def should_compress(self, session: Any, threshold: int = 20) -> bool:
        return len(session.messages) >= threshold

    def auto_compress(self, memory: Any, session_id: str) -> bool:
        """Compress if session is long enough. Returns True if compressed."""
        session = memory.get_session(session_id)
        if session and self.should_compress(session):
            self.compress_session(memory, session_id)
            return True
        return False
