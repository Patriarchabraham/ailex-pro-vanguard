"""
AILEX Pilot — retry.py
Retry/resume logic for pipeline resilience.
Exponential backoff on API failures, checkpoint after each loop.
"""
from __future__ import annotations

import asyncio
import functools
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

T = TypeVar("T")

CHECKPOINT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".ailex_checkpoints"
)


@dataclass
class RetryConfig:
    max_attempts:     int   = 3
    initial_delay_s:  float = 1.0
    backoff_factor:   float = 2.0
    max_delay_s:      float = 30.0
    retry_on:         tuple = (Exception,)    # exception types to retry


@dataclass
class CheckpointData:
    request_id:  str
    request:     str
    domain:      str
    loop_number: int
    hidden_state: Dict   # serialized HiddenState
    timestamp:   float = field(default_factory=time.time)


class RetryManager:
    """Wraps API calls with retry logic and pipeline checkpointing."""

    def __init__(self, cfg: Optional[RetryConfig] = None):
        self.cfg = cfg or RetryConfig()
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    async def with_retry_async(
        self,
        fn:       Callable,
        *args,
        operation: str = "api_call",
        **kwargs,
    ) -> Any:
        """Run async function with exponential backoff retry."""
        delay = self.cfg.initial_delay_s
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.cfg.max_attempts + 1):
            try:
                return await fn(*args, **kwargs)
            except self.cfg.retry_on as e:
                last_exc = e
                if attempt == self.cfg.max_attempts:
                    break
                actual_delay = min(delay, self.cfg.max_delay_s)
                print(f"  [retry] {operation} attempt {attempt} failed: {e}. Retrying in {actual_delay:.1f}s...")
                await asyncio.sleep(actual_delay)
                delay *= self.cfg.backoff_factor

        raise last_exc or RuntimeError(f"{operation} failed after {self.cfg.max_attempts} attempts")

    def with_retry_sync(
        self,
        fn:       Callable,
        *args,
        operation: str = "api_call",
        **kwargs,
    ) -> Any:
        """Run sync function with exponential backoff retry."""
        delay = self.cfg.initial_delay_s
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.cfg.max_attempts + 1):
            try:
                return fn(*args, **kwargs)
            except self.cfg.retry_on as e:
                last_exc = e
                if attempt == self.cfg.max_attempts:
                    break
                actual_delay = min(delay, self.cfg.max_delay_s)
                print(f"  [retry] {operation} attempt {attempt} failed: {e}. Retrying in {actual_delay:.1f}s...")
                time.sleep(actual_delay)
                delay *= self.cfg.backoff_factor

        raise last_exc or RuntimeError(f"{operation} failed after {self.cfg.max_attempts} attempts")

    # ── Checkpointing ─────────────────────────────────────────────────────────

    def save_checkpoint(self, request_id: str, request: str, domain: str,
                         loop: int, h_dict: Dict) -> str:
        """Save pipeline state after each loop."""
        data = CheckpointData(
            request_id=request_id, request=request, domain=domain,
            loop_number=loop, hidden_state=h_dict,
        )
        path = os.path.join(CHECKPOINT_DIR, f"{request_id}.json")
        with open(path, "w") as f:
            json.dump({
                "request_id":  data.request_id,
                "request":     data.request,
                "domain":      data.domain,
                "loop_number": data.loop_number,
                "hidden_state": data.hidden_state,
                "timestamp":   data.timestamp,
            }, f, indent=2, default=str)
        return path

    def load_checkpoint(self, request_id: str) -> Optional[CheckpointData]:
        """Load a saved checkpoint to resume from."""
        path = os.path.join(CHECKPOINT_DIR, f"{request_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return CheckpointData(**data)

    def list_checkpoints(self) -> List[Dict]:
        checkpoints = []
        for fname in os.listdir(CHECKPOINT_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(CHECKPOINT_DIR, fname)) as f:
                        data = json.load(f)
                    checkpoints.append(data)
                except Exception:
                    pass
        return sorted(checkpoints, key=lambda x: x.get("timestamp", 0), reverse=True)

    def clear_checkpoint(self, request_id: str) -> None:
        path = os.path.join(CHECKPOINT_DIR, f"{request_id}.json")
        if os.path.exists(path):
            os.unlink(path)

    def clear_old_checkpoints(self, max_age_hours: int = 24) -> int:
        cutoff = time.time() - max_age_hours * 3600
        removed = 0
        for fname in os.listdir(CHECKPOINT_DIR):
            path = os.path.join(CHECKPOINT_DIR, fname)
            if os.path.getmtime(path) < cutoff:
                os.unlink(path)
                removed += 1
        return removed


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for sync functions."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            mgr = RetryManager(RetryConfig(
                max_attempts=max_attempts,
                initial_delay_s=delay,
                backoff_factor=backoff,
            ))
            return mgr.with_retry_sync(fn, *args, operation=fn.__name__, **kwargs)
        return wrapper
    return decorator
