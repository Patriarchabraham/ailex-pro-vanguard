"""
AILEX Pilot — telemetry.py
OpenTelemetry traces + Prometheus metrics for production observability.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional


class AILEXTelemetry:
    """
    Observability for AILEX Pilot.
    Traces every pipeline call with OpenTelemetry.
    Exposes Prometheus metrics on /metrics.
    Falls back to no-op if packages not installed.
    """

    def __init__(self, service_name: str = "ailex-pilot"):
        self.service_name = service_name
        self._tracer      = None
        self._meter       = None
        self._counters: Dict[str, Any] = {}
        self._histograms: Dict[str, Any] = {}
        self._init_otel()
        self._init_prometheus()

    def _init_otel(self) -> None:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor, ConsoleSpanExporter
            )
            provider = TracerProvider()
            # Console exporter by default; swap for OTLP in production
            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
            if endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
                except ImportError:
                    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            else:
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
        except ImportError:
            pass

    def _init_prometheus(self) -> None:
        try:
            from prometheus_client import Counter, Histogram, start_http_server
            self._counters["requests"] = Counter(
                "ailex_requests_total", "Total AILEX requests",
                ["domain", "status"]
            )
            self._histograms["duration"] = Histogram(
                "ailex_request_duration_seconds", "Request duration",
                ["domain"]
            )
            self._histograms["loops"] = Histogram(
                "ailex_loops_total", "Loops per request",
                ["domain"], buckets=[1,2,4,6,8,10,12,16]
            )
            port = int(os.getenv("AILEX_METRICS_PORT", "9090"))
            start_http_server(port)
        except ImportError:
            pass

    @contextmanager
    def trace_request(self, request: str, domain: str = "unknown"):
        """Context manager that traces a pipeline call."""
        start = time.time()
        span  = None
        if self._tracer:
            span = self._tracer.start_span(f"ailex.process.{domain}")
            span.set_attribute("request", request[:100])
            span.set_attribute("domain", domain)
        try:
            yield span
            duration = time.time() - start
            self._record("requests", {"domain": domain, "status": "success"})
            self._record_hist("duration", duration, {"domain": domain})
            if span:
                span.set_attribute("duration_s", round(duration, 2))
                span.set_status(__import__("opentelemetry.trace", fromlist=["StatusCode"]).StatusCode.OK)
        except Exception as e:
            self._record("requests", {"domain": domain, "status": "error"})
            if span:
                span.record_exception(e)
            raise
        finally:
            if span:
                span.end()

    def record_loops(self, domain: str, loops: int) -> None:
        self._record_hist("loops", loops, {"domain": domain})

    def record_cost(self, cost: float, model: str) -> None:
        if "cost" not in self._counters:
            return
        self._counters["cost"].labels(model=model).inc(cost)

    def _record(self, name: str, labels: Dict) -> None:
        c = self._counters.get(name)
        if c:
            try:
                c.labels(**labels).inc()
            except Exception:
                pass

    def _record_hist(self, name: str, value: float, labels: Dict) -> None:
        h = self._histograms.get(name)
        if h:
            try:
                h.labels(**labels).observe(value)
            except Exception:
                pass

    @property
    def available(self) -> Dict[str, bool]:
        return {
            "opentelemetry": self._tracer is not None,
            "prometheus":    bool(self._counters),
        }
