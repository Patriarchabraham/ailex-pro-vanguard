"""
AILEX — observability.py
Centralized observability: logging + metrics + tracing + health checks.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every operation in AILEX goes through this module.
Zero-overhead when disabled. Rich when enabled.

Components:
  Tracer       — trace_id propagation across async boundaries
  EventBus     — pub/sub for pipeline events (agent.call, qa.check, cache.hit, ...)
  MetricsStore — SQLite counters for real-time dashboard
  HealthCheck  — smoke tests for all subsystems

Usage:
    from ailex_pilot.observability import observe, tracer, metrics, health

    # Decorate any function:
    @observe("agent_call", domain="code")
    def call_agent(agent, task): ...

    # Manual trace:
    with tracer.span("pipeline", domain="code") as span:
        result = run(task)
        span.set("confidence", result["confidence"])

    # Record custom metric:
    metrics.inc("cache_hits")
    metrics.timing("agent_ms", 842)

    # Health check:
    report = health.check_all()
"""

from __future__ import annotations

import functools
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

F = TypeVar("F", bound=Callable)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
METRICS_DB = BASE / "ailex_metrics.db"
LOG_DIR  = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)


# ── Span ───────────────────────────────────────────────────────────────────────

@dataclass
class Span:
    name:       str
    trace_id:   str
    start_ms:   float = field(default_factory=lambda: time.perf_counter() * 1000)
    attrs:      Dict[str, Any] = field(default_factory=dict)
    error:      Optional[str] = None
    end_ms:     float = 0.0

    @property
    def duration_ms(self) -> int:
        return int((self.end_ms or time.perf_counter() * 1000) - self.start_ms)

    def set(self, key: str, value: Any) -> "Span":
        self.attrs[key] = value
        return self

    def finish(self, error: Optional[str] = None) -> "Span":
        self.end_ms = time.perf_counter() * 1000
        self.error  = error
        return self


# ── Tracer ─────────────────────────────────────────────────────────────────────

class Tracer:
    """Lightweight trace propagation. No external deps."""

    _current_trace: Dict[int, str] = {}   # thread_id → trace_id

    def new_trace(self) -> str:
        tid = uuid.uuid4().hex[:12]
        import threading
        self._current_trace[threading.get_ident()] = tid
        return tid

    def current(self) -> str:
        import threading
        return self._current_trace.get(threading.get_ident(), "no-trace")

    @contextmanager
    def span(self, name: str, **attrs):
        """Context manager — auto-logs start/finish/error."""
        trace = self.current()
        span  = Span(name=name, trace_id=trace, attrs=attrs)
        try:
            yield span
            span.finish()
            _event_bus.emit("span.finish", span=span)
        except Exception as e:
            span.finish(error=str(e))
            _event_bus.emit("span.error", span=span)
            raise


tracer = Tracer()


# ── Event Bus ──────────────────────────────────────────────────────────────────

class EventBus:
    """In-process pub/sub for pipeline events."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, handler: Callable) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def emit(self, event: str, **data) -> None:
        for h in self._handlers.get(event, []) + self._handlers.get("*", []):
            try:
                h(event=event, **data)
            except Exception:
                pass  # never let event handlers crash the caller

    def once(self, event: str, handler: Callable) -> None:
        def wrapper(**kw):
            handler(**kw)
            self._handlers.get(event, []).remove(wrapper)
        self._handlers.setdefault(event, []).append(wrapper)


_event_bus = EventBus()


# ── Metrics Store ──────────────────────────────────────────────────────────────

class MetricsStore:
    """
    SQLite-backed metrics store.
    Counters, timings, gauges — all persistent across restarts.
    """

    def __init__(self, db: Path = METRICS_DB):
        self.conn = sqlite3.connect(str(db), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS counters (
                key   TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0,
                ts    REAL
            );
            CREATE TABLE IF NOT EXISTS timings (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                key     TEXT,
                value   REAL,
                ts      REAL
            );
            CREATE TABLE IF NOT EXISTS events (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                event    TEXT,
                data     TEXT,
                ts       REAL
            );
            CREATE INDEX IF NOT EXISTS idx_evt_ts  ON events(ts);
            CREATE INDEX IF NOT EXISTS idx_evt_key ON events(event);
            CREATE INDEX IF NOT EXISTS idx_tim_key ON timings(key);
        """)
        self.conn.commit()

    # ── Core operations ────────────────────────────────────────────────────────

    def inc(self, key: str, by: int = 1) -> None:
        self.conn.execute(
            "INSERT INTO counters(key,value,ts) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=value+?,ts=?",
            (key, by, time.time(), by, time.time())
        )
        self.conn.commit()

    def set_gauge(self, key: str, value: float) -> None:
        self.conn.execute(
            "INSERT INTO counters(key,value,ts) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=?,ts=?",
            (key, int(value), time.time(), int(value), time.time())
        )
        self.conn.commit()

    def timing(self, key: str, ms: float) -> None:
        self.conn.execute(
            "INSERT INTO timings(key,value,ts) VALUES(?,?,?)",
            (key, ms, time.time())
        )
        self.conn.commit()

    def record(self, trace_id: str, event: str, **data) -> None:
        self.conn.execute(
            "INSERT INTO events(trace_id,event,data,ts) VALUES(?,?,?,?)",
            (trace_id, event, json.dumps(data, default=str), time.time())
        )
        self.conn.commit()

    # ── Query ──────────────────────────────────────────────────────────────────

    def get_counter(self, key: str) -> int:
        r = self.conn.execute("SELECT value FROM counters WHERE key=?", (key,)).fetchone()
        return r[0] if r else 0

    def avg_timing(self, key: str, since_h: float = 24) -> float:
        r = self.conn.execute(
            "SELECT AVG(value) FROM timings WHERE key=? AND ts>?",
            (key, time.time() - since_h * 3600)
        ).fetchone()
        return round(r[0] or 0, 1)

    def recent_events(self, event: str = "", limit: int = 20) -> List[Dict]:
        where = "WHERE event=?" if event else ""
        params = [event, limit] if event else [limit]
        rows = self.conn.execute(
            f"SELECT trace_id,event,data,ts FROM events {where} ORDER BY ts DESC LIMIT ?",
            params
        ).fetchall()
        return [{"trace": r[0], "event": r[1], "data": json.loads(r[2]), "age_s": int(time.time()-r[3])} for r in rows]

    def dashboard_data(self) -> Dict[str, Any]:
        now  = time.time()
        day  = now - 86400
        hour = now - 3600

        total_calls  = self.get_counter("agent.call.total")
        calls_today  = self.conn.execute("SELECT COUNT(*) FROM events WHERE event='agent.call' AND ts>?", (day,)).fetchone()[0]
        calls_hour   = self.conn.execute("SELECT COUNT(*) FROM events WHERE event='agent.call' AND ts>?", (hour,)).fetchone()[0]
        errors       = self.conn.execute("SELECT COUNT(*) FROM events WHERE event='agent.error' AND ts>?", (day,)).fetchone()[0]
        cache_hits   = self.get_counter("cache.hit")
        cache_miss   = self.get_counter("cache.miss")
        qa_blocked   = self.get_counter("qa.blocked")
        tokens_today = self.conn.execute("SELECT SUM(CAST(json_extract(data,'$.tokens') AS INTEGER)) FROM events WHERE event='agent.call' AND ts>?", (day,)).fetchone()[0] or 0

        avg_conf = self.conn.execute(
            "SELECT AVG(CAST(json_extract(data,'$.confidence') AS REAL)) FROM events WHERE event='agent.call' AND ts>?", (day,)
        ).fetchone()[0] or 0

        avg_ms = self.avg_timing("agent_ms", 24)

        return {
            "calls_total":   total_calls,
            "calls_today":   calls_today,
            "calls_hour":    calls_hour,
            "errors_today":  errors,
            "error_rate":    f"{100*errors/max(1,calls_today):.1f}%",
            "cache_hits":    cache_hits,
            "cache_miss":    cache_miss,
            "cache_rate":    f"{100*cache_hits/max(1,cache_hits+cache_miss):.1f}%",
            "qa_blocked":    qa_blocked,
            "tokens_today":  tokens_today,
            "cost_est_usd":  f"${tokens_today * 0.000003:.4f}",
            "avg_conf":      f"{avg_conf:.3f}",
            "avg_ms":        f"{avg_ms:.0f}ms",
        }


metrics = MetricsStore()


# ── Health Check ───────────────────────────────────────────────────────────────

@dataclass
class HealthResult:
    component: str
    ok:        bool
    message:   str
    ms:        int


class HealthCheck:
    """Smoke tests for all AILEX subsystems."""

    def check_all(self, verbose: bool = True) -> List[HealthResult]:
        checks = [
            ("WebResearcher",    self._check_web_researcher),
            ("KnowledgeUpdater", self._check_knowledge_db),
            ("ContentGuard",     self._check_content_guard),
            ("HTMLQualityAssurance", self._check_html_qa),
            ("MotionSystem",     self._check_motion_system),
            ("UltraMotionSystem",self._check_ultra_motion),
            ("SmartCacheV2",     self._check_smart_cache),
            ("AgentQualityGate", self._check_agent_qa),
            ("StructuredOutput", self._check_structured_output),
            ("MultiProvider",    self._check_multi_provider),
            ("ContextCompressor",self._check_context_compressor),
            ("GenerationGuard",  self._check_generation_guard),
            ("AILEXLogger",      self._check_logger),
            ("MetricsStore",     self._check_metrics),
            ("ResearchScheduler",self._check_research_scheduler),
        ]
        results = []
        for name, fn in checks:
            t0 = time.perf_counter()
            try:
                msg = fn()
                ok  = True
            except Exception as e:
                msg = str(e)[:80]
                ok  = False
            ms = int((time.perf_counter() - t0) * 1000)
            r  = HealthResult(component=name, ok=ok, message=msg, ms=ms)
            results.append(r)
            if verbose:
                icon = "✅" if ok else "❌"
                print(f"  {icon} {name:<28} {msg[:45]:<45} {ms}ms")
        return results

    def _check_web_researcher(self) -> str:
        from .web_researcher import WebResearcher
        r = WebResearcher()
        w = r.wikipedia("Python programming language")
        assert w and w.title
        return f"Wikipedia OK: {w.title[:30]}"

    def _check_knowledge_db(self) -> str:
        from .knowledge_updater import KnowledgeUpdater
        ku = KnowledgeUpdater()
        s  = ku.stats()
        return f"{s['total']} entries, {len(s.get('by_domain', {}))} domains"

    def _check_content_guard(self) -> str:
        import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from ailex_vision.content_guard import ContentGuard
        cg  = ContentGuard()
        url = cg.pick("romantic_couple")
        assert url.startswith("https://")
        return f"pick() OK → {url[-30:]}"

    def _check_html_qa(self) -> str:
        import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from ailex_vision.html_qa import HTMLQualityAssurance
        qa = HTMLQualityAssurance()
        r  = qa.validate("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width'><title>T</title><meta name='description' content='t'><link href='https://fonts.googleapis.com/css2?family=A'></head><body><nav>Nav</nav><img src='a.jpg' alt='x' loading='lazy'><img src='b.jpg' alt='y'><img src='c.jpg' alt='z'><p>hello world this is some content for the test</p><footer>Footer</footer><script>document.querySelectorAll(\"[data-count]\")</script></body></html>")
        return f"{r.score}/100, critical={r.critical}"

    def _check_motion_system(self) -> str:
        import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from ailex_vision.motion_system import MotionSystem
        ms  = MotionSystem()
        out = ms.inject("<html><head><title>T</title></head><body></body></html>", "minimal")
        assert "lenis" in out.lower()
        return "inject() OK, Lenis present"

    def _check_ultra_motion(self) -> str:
        import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from ailex_vision.ultra_motion_system import UltraMotionSystem
        ums = UltraMotionSystem()
        out = ums.inject("<html><head><title>T</title></head><body></body></html>")
        assert "three@0.169.0" in out
        return "inject() OK, Three.js present"

    def _check_smart_cache(self) -> str:
        from .smart_cache_v2 import SmartCacheV2
        c = SmartCacheV2(":memory:")
        c.set("test", "key1", {"v": 42})
        r = c.get("test", "key1")
        assert r == {"v": 42}
        return "set/get OK"

    def _check_agent_qa(self) -> str:
        from .agent_quality_gate import AgentQualityGate
        from .structured_output import AgentOutput
        gate = AgentQualityGate()
        out  = AgentOutput(agent="DEX", model="claude-sonnet-4-6",
                           analysis="Use TypeScript strict mode to avoid runtime null errors",
                           recommendation="Add 'strict: true' to tsconfig.json",
                           confidence=0.88)
        r = gate.evaluate(out)
        return f"score={r.score:.2f}, passes={r.passes}"

    def _check_structured_output(self) -> str:
        from .structured_output import StructuredAgentCall, AGENT_TOOL_SCHEMA
        assert AGENT_TOOL_SCHEMA["name"] == "agent_response"
        return "schema OK, no API key needed"

    def _check_multi_provider(self) -> str:
        from .multi_provider import MultiProvider, PROVIDER_MODELS
        mp = MultiProvider()
        assert len(PROVIDER_MODELS) == 3
        return f"{len(mp._available_providers('fast'))} provider(s) available"

    def _check_context_compressor(self) -> str:
        from .context_compressor import ContextCompressor
        cc   = ContextCompressor()
        msgs = [{"role": "user", "content": "x"*200}] * 5
        r    = cc.compress(msgs, budget_tokens=100_000)
        assert r.messages_removed == 0
        return "compress() OK"

    def _check_generation_guard(self) -> str:
        import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from ailex_vision.generation_guard import GenerationGuard
        g = GenerationGuard()
        html, rep = g.validate_and_fix("<!DOCTYPE html><html><body></body>")
        assert "</html>" in html
        return f"{rep.bugs_fixed} auto-fixed"

    def _check_logger(self) -> str:
        from .ailex_logger import get_logger, new_trace
        log   = get_logger("health")
        trace = new_trace()
        log.info("health_check", trace=trace)
        return f"log OK, trace={trace}"

    def _check_metrics(self) -> str:
        metrics.inc("health.check")
        v = metrics.get_counter("health.check")
        assert v > 0
        return f"counter={v}"

    def _check_research_scheduler(self) -> str:
        from .research_scheduler import ResearchScheduler
        sched = ResearchScheduler(verbose=False)
        return f"scheduler OK, interval={sched.INTERVAL_HOURS}h"


health = HealthCheck()


# ── Observe decorator ──────────────────────────────────────────────────────────

def observe(operation: str, **static_attrs):
    """
    Decorator that wraps any function with:
    - Trace span (start/end/error)
    - Metrics recording (timing, counter)
    - Event emission

        @observe("agent_call", domain="code")
        def call_agent(agent, task): ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            trace = tracer.current()
            t0    = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                ms     = int((time.perf_counter() - t0) * 1000)
                metrics.inc(f"{operation}.ok")
                metrics.timing(f"{operation}_ms", ms)
                metrics.record(trace, operation, ms=ms, ok=True, **static_attrs)
                return result
            except Exception as e:
                ms = int((time.perf_counter() - t0) * 1000)
                metrics.inc(f"{operation}.error")
                metrics.record(trace, f"{operation}.error", ms=ms, error=str(e)[:100], **static_attrs)
                raise
        return wrapper  # type: ignore
    return decorator


if __name__ == "__main__":
    print("AILEX Observability — Health Check\n" + "─"*50)
    health.check_all(verbose=True)
    print("\nMetrics Dashboard:")
    d = metrics.dashboard_data()
    for k, v in d.items():
        print(f"  {k:<20} {v}")
