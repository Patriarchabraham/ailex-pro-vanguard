"""
AILEX Pilot — finetune_export.py
Export session history as fine-tuning datasets (Anthropic, OpenAI JSONL formats).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class FineTuneDataset:
    format:    str       # "anthropic" | "openai" | "alpaca"
    examples:  List[dict]
    count:     int
    saved_path: Optional[str]


class FineTuneExporter:
    """
    Export high-quality AILEX sessions as fine-tuning data.
    Only exports sessions with confidence >= threshold.
    """

    def __init__(self, min_confidence: float = 0.92, min_quality: float = 0.65):
        self.min_confidence = min_confidence
        self.min_quality    = min_quality

    def export(self, memory: Any, feedback: Any = None,
               fmt: str = "anthropic", output_path: str = "") -> FineTuneDataset:
        """Export sessions as JSONL fine-tuning data."""
        examples = self._collect_examples(memory, feedback)
        formatted = [self._format(e, fmt) for e in examples if e]
        formatted = [f for f in formatted if f]

        if not output_path:
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                f"ailex_finetune_{fmt}_{int(time.time())}.jsonl"
            )
        with open(output_path, "w") as f:
            for ex in formatted:
                f.write(json.dumps(ex) + "\n")

        return FineTuneDataset(
            format=fmt, examples=formatted,
            count=len(formatted), saved_path=output_path,
        )

    def _collect_examples(self, memory: Any, feedback: Any) -> list:
        examples = []
        try:
            # Get high-confidence sessions from memory
            rows = memory.conn.execute(
                "SELECT m1.content as user_msg, m2.content as assistant_msg, "
                "m2.domain, m2.confidence, m2.loops_run "
                "FROM messages m1 JOIN messages m2 ON m1.session_id=m2.session_id "
                "WHERE m1.role='user' AND m2.role='assistant' "
                "AND m2.confidence >= ? AND m1.ts < m2.ts "
                "ORDER BY m2.ts DESC LIMIT 500",
                (self.min_confidence,)
            ).fetchall()

            for r in rows:
                if r["user_msg"] and r["assistant_msg"] and len(r["assistant_msg"]) > 50:
                    examples.append({
                        "user":      r["user_msg"][:500],
                        "assistant": r["assistant_msg"][:2000],
                        "domain":    r["domain"],
                        "confidence": r["confidence"],
                    })

            # Boost examples with positive feedback
            if feedback:
                pos_rows = feedback.conn.execute(
                    "SELECT request, domain FROM feedback WHERE rating=1 LIMIT 100"
                ).fetchall()
                for r in pos_rows:
                    examples.append({
                        "user":      r["request"],
                        "assistant": f"[High-rated response for {r['domain']}]",
                        "domain":    r["domain"],
                        "confidence": 1.0,
                    })
        except Exception:
            pass
        return examples

    def _format(self, ex: dict, fmt: str) -> Optional[dict]:
        if fmt == "anthropic":
            return {
                "messages": [
                    {"role": "user",      "content": ex["user"]},
                    {"role": "assistant", "content": ex["assistant"]},
                ]
            }
        elif fmt == "openai":
            return {
                "messages": [
                    {"role": "system",    "content": f"You are AILEX, expert {ex['domain']} specialist."},
                    {"role": "user",      "content": ex["user"]},
                    {"role": "assistant", "content": ex["assistant"]},
                ]
            }
        elif fmt == "alpaca":
            return {
                "instruction": ex["user"],
                "input":       "",
                "output":      ex["assistant"],
            }
        return None

    def stats(self, dataset: FineTuneDataset) -> str:
        return (
            f"Fine-tune export: {dataset.count} examples ({dataset.format})\n"
            f"Saved: {dataset.saved_path}"
        )
