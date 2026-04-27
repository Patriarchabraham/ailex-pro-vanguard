"""
AILEX Pilot — scheduler.py
Advanced job scheduler for background agents.
Inspired by APScheduler/schedule patterns — AILEX original.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ScheduledJob:
    id:          str
    name:        str
    fn:          Callable
    interval_s:  Optional[int]   # recurring interval in seconds
    cron_str:    Optional[str]    # "HH:MM" daily, or "*/N" every N minutes
    next_run:    float
    last_run:    float = 0.0
    run_count:   int   = 0
    enabled:     bool  = True
    args:        list  = field(default_factory=list)
    kwargs:      dict  = field(default_factory=dict)


class JobScheduler:
    """
    Background job scheduler for AILEX agents.
    Supports: interval jobs, daily cron, one-shot delayed.
    Thread-safe. No external dependencies.
    """

    def __init__(self):
        self._jobs:    Dict[str, ScheduledJob] = {}
        self._running  = False
        self._thread:  Optional[threading.Thread] = None
        self._lock     = threading.Lock()

    # ── Job registration ──────────────────────────────────────────────────────

    def every(self, seconds: int, fn: Callable, name: str = "",
              *args, **kwargs) -> str:
        """Register a recurring job every N seconds."""
        jid = str(uuid.uuid4())[:8]
        job = ScheduledJob(
            id=jid, name=name or fn.__name__,
            fn=fn, interval_s=seconds, cron_str=None,
            next_run=time.time() + seconds,
            args=list(args), kwargs=kwargs,
        )
        with self._lock:
            self._jobs[jid] = job
        return jid

    def daily(self, time_str: str, fn: Callable, name: str = "",
              *args, **kwargs) -> str:
        """Register a daily job at HH:MM."""
        jid = str(uuid.uuid4())[:8]
        job = ScheduledJob(
            id=jid, name=name or fn.__name__,
            fn=fn, interval_s=None, cron_str=time_str,
            next_run=self._next_daily(time_str),
            args=list(args), kwargs=kwargs,
        )
        with self._lock:
            self._jobs[jid] = job
        return jid

    def once(self, delay_s: int, fn: Callable, name: str = "",
             *args, **kwargs) -> str:
        """Run once after delay_s seconds."""
        jid = str(uuid.uuid4())[:8]
        job = ScheduledJob(
            id=jid, name=name or fn.__name__,
            fn=fn, interval_s=None, cron_str=None,
            next_run=time.time() + delay_s,
            enabled=True,
            args=list(args), kwargs=kwargs,
        )
        with self._lock:
            self._jobs[jid] = job
        return jid

    def cancel(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def pause(self, job_id: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False

    def resume(self, job_id: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True

    # ── Execution ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                jobs = list(self._jobs.values())
            for job in jobs:
                if job.enabled and now >= job.next_run:
                    threading.Thread(
                        target=self._run_job, args=(job,), daemon=True
                    ).start()
            time.sleep(1.0)

    def _run_job(self, job: ScheduledJob) -> None:
        try:
            job.fn(*job.args, **job.kwargs)
        except Exception:
            pass
        finally:
            with self._lock:
                if job.id in self._jobs:
                    job.last_run  = time.time()
                    job.run_count += 1
                    if job.interval_s:
                        job.next_run = time.time() + job.interval_s
                    elif job.cron_str:
                        job.next_run = self._next_daily(job.cron_str)
                    else:
                        # One-shot — remove after running
                        self._jobs.pop(job.id, None)

    def _next_daily(self, time_str: str) -> float:
        try:
            h, m  = map(int, time_str.split(":"))
            now   = time.localtime()
            t     = time.mktime((*now[:3], h, m, 0, *now[6:]))
            if t <= time.time():
                t += 86400
            return t
        except Exception:
            return time.time() + 86400

    def status(self) -> str:
        lines = [f"Scheduler: {len(self._jobs)} jobs, running={self._running}"]
        for job in sorted(self._jobs.values(), key=lambda j: j.next_run):
            eta = max(0, job.next_run - time.time())
            lines.append(
                f"  [{job.id}] {job.name:20s} next={eta:.0f}s runs={job.run_count}"
                + ("" if job.enabled else " [paused]")
            )
        return "\n".join(lines)


def build_ailex_scheduler(pilot: Any) -> JobScheduler:
    """Pre-configured scheduler with standard AILEX background jobs."""
    sched = JobScheduler()

    # Security scan every 6 hours
    def security_job():
        from ailex_pilot.security import SecurityScanner
        r = SecurityScanner().scan_project(pilot.project_dir)
        if r.secrets:
            print(f"\n[Scheduler] ⚠ Security: {len(r.secrets)} secrets exposed!")

    # Cost report every hour
    def cost_job():
        status = pilot.cost.check_budget()
        if status.warning:
            print(f"\n[Scheduler] 💰 Budget: {status.pct_used:.0f}% used")

    sched.every(21600, security_job, "security_scan")
    sched.every(3600,  cost_job,     "cost_check")
    return sched
