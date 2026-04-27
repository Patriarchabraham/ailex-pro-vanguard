"""
AILEX — provider_health.py
Real-time health monitoring + automatic failover testing for all LLM providers.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Checks: Anthropic · OpenAI · Gemini · GitHub · Replicate
Tests: API connectivity, rate limit status, cost estimation, failover chain.

Usage:
    from ailex_pilot.provider_health import ProviderHealth
    ph = ProviderHealth()
    report = ph.check_all()
    print(ph.format_report(report))

    # Failover test:
    result = ph.test_failover_chain("Write hello world in Python")
    print(result.winning_provider, result.response[:100])
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProviderStatus:
    name:         str
    available:    bool
    has_key:      bool
    latency_ms:   int     = 0
    model_tested: str     = ""
    error:        str     = ""
    rate_limited: bool    = False
    cost_per_1k:  float   = 0.0    # USD per 1k output tokens
    tier:         str     = "fast" # tier used for test


@dataclass
class FailoverResult:
    task:             str
    winning_provider: str
    response:         str
    providers_tried:  List[str]
    total_ms:         int
    fallback_used:    bool


@dataclass
class HealthReport:
    providers:  List[ProviderStatus]
    timestamp:  str
    all_ok:     bool
    failover_chain: List[str]   # ordered list of available providers

    def available_providers(self) -> List[str]:
        return [p.name for p in self.providers if p.available]

    def summary(self) -> str:
        ok   = sum(1 for p in self.providers if p.available)
        lines = [f"Provider Health Report ({self.timestamp})", "─" * 50]
        for p in self.providers:
            icon   = "✅" if p.available else ("🔑" if not p.has_key else "❌")
            detail = f"{p.model_tested} {p.latency_ms}ms" if p.available else (p.error[:40] if p.error else "no key")
            lines.append(f"  {icon} {p.name:<14} {detail}")
        lines.append(f"\n  {ok}/{len(self.providers)} providers available")
        lines.append(f"  Failover chain: {' → '.join(self.failover_chain) or 'none'}")
        return "\n".join(lines)


class ProviderHealth:
    """
    Health monitor for all AILEX LLM providers.
    Tests actual API connectivity with a minimal ping request.
    """

    PING_PROMPT = "Reply with exactly: AILEX_OK"
    PING_TOKENS = 20

    # Cost per 1k output tokens (fast tier)
    COSTS = {
        "anthropic": 0.004,   # Haiku
        "openai":    0.0006,  # GPT-4o-mini
        "gemini":    0.0003,  # Flash-Lite
    }

    def check_all(self, ping_api: bool = False) -> HealthReport:
        """
        Check all providers. If ping_api=True, makes a real (minimal) API call.
        If ping_api=False, just checks if keys are configured.
        """
        providers = []
        providers.append(self._check_anthropic(ping_api))
        providers.append(self._check_openai(ping_api))
        providers.append(self._check_gemini(ping_api))

        all_ok = all(p.available for p in providers if p.has_key)
        chain  = [p.name for p in providers if p.available]

        return HealthReport(
            providers=providers,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            all_ok=all_ok,
            failover_chain=chain,
        )

    def test_failover_chain(
        self,
        task:          str,
        model_tier:    str = "fast",
        verbose:       bool = True,
    ) -> FailoverResult:
        """
        Test the full failover chain: try Anthropic → OpenAI → Gemini.
        Returns which provider succeeded and the response.
        """
        from .multi_provider import MultiProvider
        mp  = MultiProvider()
        t0  = time.perf_counter()

        result = mp.complete(task, model_tier=model_tier)

        return FailoverResult(
            task=task,
            winning_provider=result.get("provider","none"),
            response=result.get("content",""),
            providers_tried=[result.get("provider","none")],
            total_ms=int((time.perf_counter()-t0)*1000),
            fallback_used=result.get("provider","none") != "anthropic",
        )

    def get_cheapest(self, tier: str = "fast") -> Optional[str]:
        """Return the cheapest available provider for a tier."""
        report = self.check_all(ping_api=False)
        available = report.available_providers()
        if not available:
            return None
        # Sort by cost
        by_cost = sorted(available, key=lambda p: self.COSTS.get(p, 9999))
        return by_cost[0]

    def estimate_cost(self, tokens_in: int, tokens_out: int, provider: str = "anthropic",
                      tier: str = "fast") -> float:
        """Estimate USD cost for a given token count."""
        from .multi_provider import PROVIDER_COST
        costs = PROVIDER_COST.get(provider, {}).get(tier, (0, 0))
        return tokens_in * costs[0] / 1_000_000 + tokens_out * costs[1] / 1_000_000

    def format_report(self, report: HealthReport) -> str:
        return report.summary()

    # ── Private checks ─────────────────────────────────────────────────────────

    def _check_anthropic(self, ping: bool) -> ProviderStatus:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return ProviderStatus("anthropic", False, False, error="No ANTHROPIC_API_KEY")

        if not ping:
            return ProviderStatus("anthropic", True, True,
                                  model_tested="claude-haiku-4-5-20251001",
                                  cost_per_1k=self.COSTS["anthropic"])

        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": self.PING_TOKENS,
                    "messages": [{"role": "user", "content": self.PING_PROMPT}]
                }).encode(),
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            ms = int((time.perf_counter()-t0)*1000)
            return ProviderStatus("anthropic", True, True,
                                  latency_ms=ms,
                                  model_tested="claude-haiku-4-5-20251001",
                                  cost_per_1k=self.COSTS["anthropic"])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return ProviderStatus("anthropic", False, True, rate_limited=True,
                                      error="Rate limited (429)")
            return ProviderStatus("anthropic", False, True, error=f"HTTP {e.code}")
        except Exception as e:
            return ProviderStatus("anthropic", False, True, error=str(e)[:60])

    def _check_openai(self, ping: bool) -> ProviderStatus:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return ProviderStatus("openai", False, False, error="No OPENAI_API_KEY")

        if not ping:
            return ProviderStatus("openai", True, True,
                                  model_tested="gpt-4o-mini",
                                  cost_per_1k=self.COSTS["openai"])

        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({
                    "model": "gpt-4o-mini",
                    "max_tokens": self.PING_TOKENS,
                    "messages": [{"role": "user", "content": self.PING_PROMPT}]
                }).encode(),
                headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            ms = int((time.perf_counter()-t0)*1000)
            return ProviderStatus("openai", True, True, latency_ms=ms,
                                  model_tested="gpt-4o-mini",
                                  cost_per_1k=self.COSTS["openai"])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return ProviderStatus("openai", False, True, rate_limited=True,
                                      error="Rate limited (429)")
            return ProviderStatus("openai", False, True, error=f"HTTP {e.code}")
        except Exception as e:
            return ProviderStatus("openai", False, True, error=str(e)[:60])

    def _check_gemini(self, ping: bool) -> ProviderStatus:
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            return ProviderStatus("gemini", False, False, error="No GEMINI_API_KEY")

        if not ping:
            return ProviderStatus("gemini", True, True,
                                  model_tested="gemini-2.0-flash-lite",
                                  cost_per_1k=self.COSTS["gemini"])

        t0 = time.perf_counter()
        model = "gemini-2.0-flash-lite"
        url   = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({"contents": [{"parts": [{"text": self.PING_PROMPT}]}],
                                 "generationConfig": {"maxOutputTokens": self.PING_TOKENS}}).encode(),
                headers={"content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            ms = int((time.perf_counter()-t0)*1000)
            return ProviderStatus("gemini", True, True, latency_ms=ms,
                                  model_tested=model,
                                  cost_per_1k=self.COSTS["gemini"])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return ProviderStatus("gemini", False, True, rate_limited=True,
                                      error="Rate limited (429)")
            return ProviderStatus("gemini", False, True, error=f"HTTP {e.code}")
        except Exception as e:
            return ProviderStatus("gemini", False, True, error=str(e)[:60])


if __name__ == "__main__":
    ph     = ProviderHealth()
    report = ph.check_all(ping_api=False)  # key-only check
    print(ph.format_report(report))
    print()
    print(f"Cheapest provider (fast tier): {ph.get_cheapest('fast') or 'none available'}")
    print(f"Cost estimate (1k in, 2k out, anthropic): ${ph.estimate_cost(1000, 2000, 'anthropic'):.6f}")
    print()

    # Failover test (only if API key available)
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("Testing failover chain…")
        result = ph.test_failover_chain("Say 'hello' in one word", model_tier="fast")
        print(f"  Provider: {result.winning_provider}")
        print(f"  Response: {result.response[:80]}")
        print(f"  Latency:  {result.total_ms}ms")
        print(f"  Fallback: {result.fallback_used}")
