"""
AILEX — multi_provider.py  (P6)
Multi-provider LLM routing with automatic fallback.
Anthropic → OpenAI → Gemini — zero-downtime on rate limits.

Architecture:
  ProviderChain: ordered list of providers, tries each on failure
  ProviderAdapter: normalises API differences (OpenAI/Gemini → Anthropic message format)
  CostOptimiser: routes by cost when multiple providers available
  RateLimitTracker: per-provider circuit breaker (backs off for 60s after 429)

Usage:
    from ailex_pilot.multi_provider import MultiProvider
    mp = MultiProvider()
    result = mp.complete("Explain recursion", model_tier="fast")
    # Returns: {"content": str, "provider": str, "model": str, "tokens_in": int, "tokens_out": int}

    # Force a specific provider:
    result = mp.complete("...", model_tier="opus", force_provider="openai")

    # Get routing report:
    print(mp.status())
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Model tier mapping ────────────────────────────────────────────────────────
# tier → best model per provider (April 2026)
PROVIDER_MODELS: Dict[str, Dict[str, str]] = {
    "anthropic": {
        "opus":   "claude-opus-4-7",
        "sonnet": "claude-sonnet-4-6",
        "haiku":  "claude-haiku-4-5-20251001",
        "fast":   "claude-haiku-4-5-20251001",
    },
    "openai": {
        "opus":   "gpt-4o",
        "sonnet": "gpt-4o",
        "haiku":  "gpt-4o-mini",
        "fast":   "gpt-4o-mini",
    },
    "gemini": {
        "opus":   "gemini-2.5-pro-preview-03-25",
        "sonnet": "gemini-2.0-flash",
        "haiku":  "gemini-2.0-flash-lite",
        "fast":   "gemini-2.0-flash-lite",
    },
}

# Cost per 1M tokens (input/output) — April 2026
PROVIDER_COST: Dict[str, Dict[str, Tuple[float, float]]] = {
    "anthropic": {
        "opus":   (15.0,  75.0),
        "sonnet": (3.0,   15.0),
        "haiku":  (0.8,   4.0),
        "fast":   (0.8,   4.0),
    },
    "openai": {
        "opus":   (2.5,   10.0),
        "sonnet": (2.5,   10.0),
        "haiku":  (0.15,  0.6),
        "fast":   (0.15,  0.6),
    },
    "gemini": {
        "opus":   (1.25,  10.0),
        "sonnet": (0.1,   0.4),
        "haiku":  (0.075, 0.3),
        "fast":   (0.075, 0.3),
    },
}

# API endpoints
ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai":    "https://api.openai.com/v1/chat/completions",
    "gemini":    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
}


# ── Rate limit tracker ────────────────────────────────────────────────────────
@dataclass
class RateLimitTracker:
    """Circuit breaker: backs off a provider after 429."""
    backoff_until: Dict[str, float] = field(default_factory=dict)
    hit_counts:    Dict[str, int]   = field(default_factory=dict)

    def is_available(self, provider: str) -> bool:
        return time.time() > self.backoff_until.get(provider, 0.0)

    def register_429(self, provider: str) -> None:
        count = self.hit_counts.get(provider, 0) + 1
        self.hit_counts[provider] = count
        # Exponential backoff: 60s, 120s, 300s
        backoff = min(300, 60 * (2 ** (count - 1)))
        self.backoff_until[provider] = time.time() + backoff

    def register_success(self, provider: str) -> None:
        self.hit_counts[provider] = 0  # reset on success

    def status(self) -> Dict[str, Any]:
        now = time.time()
        return {
            p: {"available": now > exp, "backoff_remaining_s": max(0, int(exp - now))}
            for p, exp in self.backoff_until.items()
        }


# ── Response normalizer ───────────────────────────────────────────────────────
def _anthropic_complete(
    prompt: str, model: str, system: str, max_tokens: int,
    messages: Optional[List[Dict]], api_key: str,
) -> Dict:
    """Call Anthropic API and return normalised dict."""
    payload: Dict = {
        "model":      model,
        "max_tokens": max_tokens,
        "messages":   messages or [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    req = urllib.request.Request(
        ENDPOINTS["anthropic"],
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp  = json.loads(r.read().decode())
    return {
        "content":    resp["content"][0]["text"],
        "tokens_in":  resp["usage"]["input_tokens"],
        "tokens_out": resp["usage"]["output_tokens"],
    }


def _openai_complete(
    prompt: str, model: str, system: str, max_tokens: int,
    messages: Optional[List[Dict]], api_key: str,
) -> Dict:
    """Call OpenAI API and normalise to Anthropic format."""
    oai_messages = []
    if system:
        oai_messages.append({"role": "system", "content": system})
    if messages:
        for m in messages:
            oai_messages.append({"role": m["role"], "content": m["content"]})
    else:
        oai_messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "max_tokens": max_tokens, "messages": oai_messages}
    req = urllib.request.Request(
        ENDPOINTS["openai"],
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp  = json.loads(r.read().decode())
    usage = resp.get("usage", {})
    return {
        "content":    resp["choices"][0]["message"]["content"],
        "tokens_in":  usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
    }


def _gemini_complete(
    prompt: str, model: str, system: str, max_tokens: int,
    messages: Optional[List[Dict]], api_key: str,
) -> Dict:
    """Call Gemini API and normalise."""
    parts = []
    if system:
        parts.append({"text": f"System: {system}\n\n"})
    if messages:
        conv = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages[-10:])
        parts.append({"text": conv})
    else:
        parts.append({"text": prompt})

    payload = {
        "contents":         [{"parts": parts}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    url = ENDPOINTS["gemini"].format(model=model) + f"?key={api_key}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp  = json.loads(r.read().decode())
    cand = resp["candidates"][0]["content"]["parts"][0]["text"]
    meta = resp.get("usageMetadata", {})
    return {
        "content":    cand,
        "tokens_in":  meta.get("promptTokenCount", 0),
        "tokens_out": meta.get("candidatesTokenCount", 0),
    }


_CALLERS = {
    "anthropic": _anthropic_complete,
    "openai":    _openai_complete,
    "gemini":    _gemini_complete,
}


# ── MultiProvider ─────────────────────────────────────────────────────────────
class MultiProvider:
    """
    Tries providers in priority order. Falls back automatically on rate limit or error.

    Provider priority (default):
        1. Anthropic  (best quality, highest cost)
        2. OpenAI     (great quality, lower cost)
        3. Gemini     (competitive quality, cheapest)
    """

    def __init__(self):
        self.keys:    Dict[str, str]     = self._load_keys()
        self.rl:      RateLimitTracker   = RateLimitTracker()
        self._calls:  Dict[str, int]     = {}
        self._cost:   float              = 0.0

    def _load_keys(self) -> Dict[str, str]:
        return {
            "anthropic": os.environ.get("ANTHROPIC_API_KEY", ""),
            "openai":    os.environ.get("OPENAI_API_KEY", ""),
            "gemini":    os.environ.get("GEMINI_API_KEY", ""),
        }

    def _available_providers(self, tier: str) -> List[str]:
        """Return providers that have a key and aren't rate-limited."""
        order = ["anthropic", "openai", "gemini"]
        return [
            p for p in order
            if self.keys.get(p)
            and self.rl.is_available(p)
            and tier in PROVIDER_MODELS.get(p, {})
        ]

    def complete(
        self,
        prompt:         str,
        model_tier:     str            = "fast",
        system:         str            = "",
        max_tokens:     int            = 600,
        messages:       Optional[List] = None,
        force_provider: Optional[str]  = None,
    ) -> Dict[str, Any]:
        """
        Complete a prompt using the best available provider.
        Returns normalised dict with provider/model info added.
        """
        providers = (
            [force_provider] if force_provider and self.keys.get(force_provider)
            else self._available_providers(model_tier)
        )

        if not providers:
            return {
                "content":  "[No providers available — set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY]",
                "provider": "none", "model": "none",
                "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
            }

        last_err = None
        for provider in providers:
            model  = PROVIDER_MODELS[provider][model_tier]
            caller = _CALLERS[provider]

            try:
                result = caller(
                    prompt=prompt, model=model, system=system,
                    max_tokens=max_tokens, messages=messages,
                    api_key=self.keys[provider],
                )
                # Track
                self.rl.register_success(provider)
                self._calls[provider] = self._calls.get(provider, 0) + 1
                cost_info  = PROVIDER_COST.get(provider, {}).get(model_tier, (0, 0))
                cost_usd   = (result["tokens_in"]  * cost_info[0] / 1_000_000 +
                              result["tokens_out"] * cost_info[1] / 1_000_000)
                self._cost += cost_usd

                return {
                    **result,
                    "provider":  provider,
                    "model":     model,
                    "cost_usd":  round(cost_usd, 6),
                    "tier":      model_tier,
                }

            except urllib.error.HTTPError as e:
                last_err = e
                if e.code == 429:
                    self.rl.register_429(provider)
                    continue  # try next provider
                # Non-429 errors: stop retrying this provider
                break
            except Exception as e:
                last_err = e
                continue

        return {
            "content":  f"[All providers failed: {last_err}]",
            "provider": "failed", "model": "none",
            "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
        }

    def cheapest_for_tier(self, tier: str) -> Optional[str]:
        """Return the cheapest available provider for a tier."""
        available = self._available_providers(tier)
        if not available:
            return None
        return min(available,
                   key=lambda p: sum(PROVIDER_COST.get(p, {}).get(tier, (9999, 9999))))

    def status(self) -> str:
        lines = ["MultiProvider Status", "─" * 40]
        for provider in ["anthropic", "openai", "gemini"]:
            key     = self.keys.get(provider, "")
            has_key = "✅" if key else "❌"
            avail   = "✅" if (key and self.rl.is_available(provider)) else "⏸️ "
            calls   = self._calls.get(provider, 0)
            lines.append(f"  {has_key} {provider:<12} {avail} calls:{calls:>4}")
        lines.append(f"\nTotal cost: ${self._cost:.4f} USD")
        rl = self.rl.status()
        if rl:
            lines.append("Rate limits:")
            for p, info in rl.items():
                if not info["available"]:
                    lines.append(f"  ⏸️  {p}: back in {info['backoff_remaining_s']}s")
        return "\n".join(lines)


if __name__ == "__main__":
    mp = MultiProvider()
    print(mp.status())
    print()
    result = mp.complete("Say hello in Italian in one sentence", model_tier="fast")
    print(f"Provider: {result['provider']} | Model: {result['model']}")
    print(f"Response: {result['content']}")
    print(f"Cost: ${result['cost_usd']:.6f}")
