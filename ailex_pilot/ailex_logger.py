"""
AILEX — ailex_logger.py  (P4)
Structured JSON logging with trace IDs per pipeline run.
Every agent call, every pipeline, every error — traceable.

Usage:
    from ailex_pilot.ailex_logger import get_logger, new_trace
    log = get_logger("pipeline")
    trace = new_trace()
    log.info("pipeline_start", trace=trace, domain="code", task_len=42)
    log.agent("DEX", trace=trace, duration_ms=850, confidence=0.92, tokens=280)
    log.error("api_error", trace=trace, error="RateLimitError", retry=1)
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
LOG_DIR  = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "logs"
LOG_DIR.mkdir(exist_ok=True)


def new_trace() -> str:
    """Generate a unique trace ID for one pipeline run."""
    return uuid.uuid4().hex[:12]


# ── JSON formatter ─────────────────────────────────────────────────────────────
class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts":      datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if hasattr(record, "extra"):
            base.update(record.extra)
        return json.dumps(base, default=str, ensure_ascii=False)


# ── AILEX Logger ───────────────────────────────────────────────────────────────
class AILEXLogger:
    """
    Structured logger for AILEX pipeline operations.
    Writes JSON lines to logs/ailex-YYYY-MM-DD.jsonl
    Also outputs human-readable to stderr at INFO level.
    """

    def __init__(self, name: str):
        self.name = name
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"ailex-{today}.jsonl"

        self._raw = logging.getLogger(f"ailex.{name}")
        self._raw.setLevel(logging.DEBUG)

        if not self._raw.handlers:
            # File handler — JSON
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(_JSONFormatter())
            self._raw.addHandler(fh)

            # Console handler — human readable
            ch = logging.StreamHandler()
            ch.setLevel(logging.WARNING)
            fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s",
                                    datefmt="%H:%M:%S")
            ch.setFormatter(fmt)
            self._raw.addHandler(ch)

        self._raw.propagate = False

    def _emit(self, level: str, event: str, **kw) -> None:
        record = logging.LogRecord(
            name=self._raw.name, level=getattr(logging, level),
            pathname="", lineno=0,
            msg=event, args=(), exc_info=None,
        )
        record.extra = {"event": event, **kw}
        self._raw.handle(record)

    # ── Public API ─────────────────────────────────────────────────────────────

    def info(self, event: str, **kw)  -> None: self._emit("INFO",  event, **kw)
    def debug(self, event: str, **kw) -> None: self._emit("DEBUG", event, **kw)
    def warn(self, event: str, **kw)  -> None: self._emit("WARNING", event, **kw)
    def error(self, event: str, **kw) -> None: self._emit("ERROR", event, **kw)

    def agent(self, agent_name: str, trace: str, duration_ms: int,
              confidence: float, tokens: int, **kw) -> None:
        """Log one agent call with timing and quality metrics."""
        self._emit("INFO", "agent_call",
                   trace=trace, agent=agent_name,
                   duration_ms=duration_ms, confidence=round(confidence, 3),
                   tokens=tokens, **kw)

    def pipeline(self, event: str, trace: str, domain: str,
                 loops: int = 0, total_ms: int = 0, **kw) -> None:
        """Log pipeline lifecycle events."""
        self._emit("INFO", f"pipeline_{event}",
                   trace=trace, domain=domain,
                   loops=loops, total_ms=total_ms, **kw)

    def cost(self, trace: str, usd: float, tokens_in: int,
             tokens_out: int, model: str) -> None:
        """Log cost for one API call."""
        self._emit("INFO", "cost",
                   trace=trace, usd=round(usd, 6),
                   tokens_in=tokens_in, tokens_out=tokens_out, model=model)

    def qa(self, trace: str, check: str, passed: bool, score: float, **kw) -> None:
        """Log quality gate check result."""
        self._emit("INFO" if passed else "WARNING", "qa_check",
                   trace=trace, check=check, passed=passed,
                   score=round(score, 3), **kw)


# ── Registry ───────────────────────────────────────────────────────────────────
_loggers: dict[str, AILEXLogger] = {}

def get_logger(name: str = "ailex") -> AILEXLogger:
    """Get or create a named logger. Thread-safe."""
    if name not in _loggers:
        _loggers[name] = AILEXLogger(name)
    return _loggers[name]


# ── Context manager for tracing a block ───────────────────────────────────────
class Trace:
    """
    Context manager that auto-logs start/end with duration.

        with Trace("pipeline", domain="code") as t:
            result = pipeline.run(task)
        # logs: pipeline_start + pipeline_end with total_ms
    """
    def __init__(self, name: str, logger: Optional[AILEXLogger] = None, **meta):
        self.name    = name
        self.log     = logger or get_logger(name)
        self.meta    = meta
        self.trace   = new_trace()
        self._t0     = 0.0

    def __enter__(self) -> "Trace":
        self._t0 = time.perf_counter()
        self.log.info(f"{self.name}_start", trace=self.trace, **self.meta)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        ms = int((time.perf_counter() - self._t0) * 1000)
        if exc_type:
            self.log.error(f"{self.name}_error", trace=self.trace,
                           error=str(exc_val), duration_ms=ms, **self.meta)
        else:
            self.log.info(f"{self.name}_done", trace=self.trace,
                          duration_ms=ms, **self.meta)

    def child(self, name: str, **meta) -> "Trace":
        """Create a child trace that inherits the parent trace ID."""
        t = Trace(name, self.log, **{**self.meta, **meta})
        t.trace = self.trace  # same trace ID, different name
        return t


# ── Tail logs (CLI utility) ────────────────────────────────────────────────────
def tail_logs(n: int = 20, level: str = "INFO") -> list[dict]:
    """Return last N log entries. Useful for CLI and tests."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    path  = LOG_DIR / f"ailex-{today}.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in reversed(lines[-200:]):
        try:
            e = json.loads(line)
            if e.get("level", "INFO") >= level:
                entries.append(e)
                if len(entries) >= n:
                    break
        except Exception:
            pass
    return list(reversed(entries))


if __name__ == "__main__":
    log   = get_logger("demo")
    trace = new_trace()
    log.info("demo_start", trace=trace, msg="AILEX Logger working")
    log.agent("DEX", trace=trace, duration_ms=842, confidence=0.91, tokens=280)
    log.cost(trace=trace, usd=0.00042, tokens_in=120, tokens_out=280, model="claude-sonnet-4-6")
    log.pipeline("complete", trace=trace, domain="code", loops=4, total_ms=3200)
    print(f"Log written to: {LOG_DIR}")
    recent = tail_logs(5)
    for e in recent:
        print(json.dumps(e, ensure_ascii=False))
