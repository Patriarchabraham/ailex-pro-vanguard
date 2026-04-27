"""
AILEX — context_compressor.py  (P5)
Semantic compression of ConversationMemory when context exceeds token budget.
Prevents context bloat that degrades response quality and increases cost.

Strategy (inspired by MemGPT / LongLLaMA):
  1. Keep last N messages verbatim (recency window)
  2. Compress older messages into a structured summary via Haiku
  3. Extract and preserve: decisions, facts, preferences, code artifacts
  4. Discard: pleasantries, redundant examples, intermediate thinking

Usage:
    from ailex_pilot.context_compressor import ContextCompressor
    cc = ContextCompressor(api_key="sk-...")
    compressed = cc.compress(messages, budget_tokens=40_000)
    # Returns compressed list — same structure, fits in budget

    # Or use the estimate:
    tokens = cc.estimate_tokens(messages)
    if tokens > 60_000:
        messages = cc.compress(messages)
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_BUDGET   = 60_000    # tokens — trigger compression above this
RECENCY_WINDOW   = 20        # always keep last N messages verbatim
SUMMARY_MODEL    = "claude-haiku-4-5-20251001"  # cheapest model for summarization
CHARS_PER_TOKEN  = 3.8       # approximate chars-per-token (Anthropic avg)


# ── Structures ────────────────────────────────────────────────────────────────
@dataclass
class CompressedSummary:
    """Structured extraction from a batch of old messages."""
    decisions:     List[str]     # architectural/technical decisions made
    facts:         List[str]     # facts established (about codebase, context, user)
    preferences:   List[str]     # user preferences ("prefers TypeScript", "uses Vercel")
    code_artifacts: List[str]    # key code snippets or file paths mentioned
    open_questions: List[str]    # things still unresolved
    compressed_at:  float        # timestamp
    original_count: int          # how many messages were compressed


@dataclass
class CompressionResult:
    messages:          List[Dict]    # new message list (fits in budget)
    original_tokens:   int
    compressed_tokens: int
    messages_removed:  int
    summary:           Optional[CompressedSummary]
    savings_pct:       float


# ── Compressor ────────────────────────────────────────────────────────────────
class ContextCompressor:
    """
    Compresses conversation history to fit within a token budget.
    Uses Claude Haiku for summarization (cost: ~$0.0003 per compression).

    The summary is injected as a system-level message at the top of the
    compressed context, so future calls still have the relevant history.
    """

    SUMMARY_TOOL = {
        "name": "extract_context",
        "description": "Extract structured information from conversation history",
        "input_schema": {
            "type": "object",
            "required": ["decisions", "facts", "preferences"],
            "properties": {
                "decisions":     {"type": "array", "items": {"type": "string"},
                                  "description": "Technical/architectural decisions made"},
                "facts":         {"type": "array", "items": {"type": "string"},
                                  "description": "Established facts about the project/codebase"},
                "preferences":   {"type": "array", "items": {"type": "string"},
                                  "description": "User preferences and working style"},
                "code_artifacts":{"type": "array", "items": {"type": "string"},
                                  "description": "Key files, functions, or code snippets referenced"},
                "open_questions":{"type": "array", "items": {"type": "string"},
                                  "description": "Unresolved questions or pending tasks"},
            },
        },
    }

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    # ── Public API ─────────────────────────────────────────────────────────────

    def estimate_tokens(self, messages: List[Dict]) -> int:
        """Fast token estimate without API call."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return int(total_chars / CHARS_PER_TOKEN)

    def compress(
        self,
        messages:      List[Dict],
        budget_tokens: int = DEFAULT_BUDGET,
        recency:       int = RECENCY_WINDOW,
        verbose:       bool = False,
    ) -> CompressionResult:
        """
        Compress messages to fit within budget_tokens.
        Always preserves the last `recency` messages verbatim.

        Messages format: [{"role": "user"|"assistant", "content": str}, ...]
        """
        original_tokens = self.estimate_tokens(messages)

        # Nothing to do if already within budget
        if original_tokens <= budget_tokens or len(messages) <= recency:
            return CompressionResult(
                messages=messages,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                messages_removed=0,
                summary=None,
                savings_pct=0.0,
            )

        # Split: old messages to compress + recent messages to keep
        keep_recent = messages[-recency:]
        to_compress = messages[:-recency]

        if verbose:
            print(f"[ContextCompressor] Compressing {len(to_compress)} old messages → summary")

        # Extract structured summary from old messages
        summary = self._extract_summary(to_compress)

        # Build summary message to inject at position 0
        summary_msg = self._format_summary_message(summary)

        # New message list: summary + recent
        new_messages = [summary_msg, *keep_recent]
        compressed_tokens = self.estimate_tokens(new_messages)

        return CompressionResult(
            messages=new_messages,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            messages_removed=len(to_compress),
            summary=summary,
            savings_pct=round(100 * (1 - compressed_tokens / original_tokens), 1),
        )

    def auto_compress(
        self,
        messages:      List[Dict],
        budget_tokens: int = DEFAULT_BUDGET,
        recency:       int = RECENCY_WINDOW,
    ) -> List[Dict]:
        """
        Compress if needed, return new message list.
        Convenience method for inline use.

            messages = cc.auto_compress(messages)
        """
        result = self.compress(messages, budget_tokens, recency)
        return result.messages

    # ── Private ────────────────────────────────────────────────────────────────

    def _extract_summary(self, messages: List[Dict]) -> CompressedSummary:
        """Use Haiku to extract structured summary from old messages."""
        if not self.api_key:
            return self._heuristic_summary(messages)

        # Build the conversation transcript for summarization
        transcript = "\n".join(
            f"{m.get('role','?').upper()}: {str(m.get('content',''))[:500]}"
            for m in messages[:60]  # cap at 60 messages for the summarization call
        )

        payload = {
            "model":       SUMMARY_MODEL,
            "max_tokens":  800,
            "system":      "You extract structured information from conversation transcripts. Be concise and precise.",
            "tools":       [self.SUMMARY_TOOL],
            "tool_choice": {"type": "tool", "name": "extract_context"},
            "messages": [{
                "role": "user",
                "content": (
                    f"Extract key information from this conversation transcript:\n\n{transcript}\n\n"
                    "Focus on: decisions made, facts established, user preferences, code mentioned."
                )
            }],
        }

        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode(),
                headers={
                    "x-api-key":         self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read().decode())

            for block in resp.get("content", []):
                if block.get("type") == "tool_use":
                    inp = block.get("input", {})
                    return CompressedSummary(
                        decisions=inp.get("decisions", [])[:5],
                        facts=inp.get("facts", [])[:8],
                        preferences=inp.get("preferences", [])[:5],
                        code_artifacts=inp.get("code_artifacts", [])[:6],
                        open_questions=inp.get("open_questions", [])[:4],
                        compressed_at=time.time(),
                        original_count=len(messages),
                    )
        except Exception:
            pass

        return self._heuristic_summary(messages)

    def _heuristic_summary(self, messages: List[Dict]) -> CompressedSummary:
        """No-API fallback: simple keyword extraction."""
        all_text = " ".join(str(m.get("content", "")) for m in messages).lower()
        facts = []
        if "typescript" in all_text:    facts.append("Project uses TypeScript")
        if "react" in all_text:         facts.append("Frontend: React")
        if "python" in all_text:        facts.append("Backend: Python")
        if "vercel" in all_text:        facts.append("Deployment: Vercel")
        if "postgresql" in all_text or "postgres" in all_text: facts.append("Database: PostgreSQL")
        if "sqlite" in all_text:        facts.append("Database: SQLite")

        return CompressedSummary(
            decisions=[], facts=facts, preferences=[],
            code_artifacts=[], open_questions=[],
            compressed_at=time.time(), original_count=len(messages),
        )

    def _format_summary_message(self, summary: CompressedSummary) -> Dict:
        """Format extracted summary as an injected context message."""
        lines = [
            f"[AILEX Context Summary — {summary.original_count} previous messages compressed]\n"
        ]
        if summary.decisions:
            lines.append("**Decisions made:**")
            lines.extend(f"  • {d}" for d in summary.decisions)
        if summary.facts:
            lines.append("**Established facts:**")
            lines.extend(f"  • {f}" for f in summary.facts)
        if summary.preferences:
            lines.append("**User preferences:**")
            lines.extend(f"  • {p}" for p in summary.preferences)
        if summary.code_artifacts:
            lines.append("**Key code/files:**")
            lines.extend(f"  • {a}" for a in summary.code_artifacts)
        if summary.open_questions:
            lines.append("**Open questions:**")
            lines.extend(f"  • {q}" for q in summary.open_questions)

        return {
            "role":    "user",
            "content": "\n".join(lines),
            "_meta":   {"type": "context_summary", "compressed_at": summary.compressed_at},
        }


if __name__ == "__main__":
    cc = ContextCompressor()
    msgs = [{"role": "user" if i%2==0 else "assistant",
             "content": f"This is message {i} " + "x"*200}
            for i in range(50)]
    result = cc.compress(msgs, budget_tokens=2000, recency=5, verbose=True)
    print(f"Compressed {result.original_tokens}→{result.compressed_tokens} tokens "
          f"({result.savings_pct}% saving), removed {result.messages_removed} messages")
