"""
AILEX Pilot — provider_registry.py
Unified LLM provider registry — swap between Anthropic, Ollama, OpenAI.
Inspired by Simon Willison's llm-cli provider pattern — AILEX original.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Provider:
    name:       str
    priority:   int          # lower = preferred
    available:  bool
    models:     Dict[str, str]   # tier → model_id
    client:     Any = None


class ProviderRegistry:
    """
    Auto-detects and manages LLM providers.
    Tier routing: opus/sonnet/haiku map to best available model per provider.
    """

    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._active: Optional[str] = None
        self._detect()

    def _detect(self) -> None:
        # 1. Anthropic (highest priority)
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                client = anthropic.Anthropic()
                self._providers["anthropic"] = Provider(
                    name="anthropic", priority=1, available=True,
                    client=client,
                    models={
                        "opus":   "claude-opus-4-7",
                        "sonnet": "claude-sonnet-4-6",
                        "haiku":  "claude-haiku-4-5-20251001",
                    }
                )
            except ImportError:
                pass

        # 2. Ollama (local, free)
        try:
            from ailex_mythos_v6.ollama_backend import OllamaClient
            ol = OllamaClient()
            if ol.available:
                models = ol.list_models()
                tier_map = self._map_ollama_tiers(models)
                self._providers["ollama"] = Provider(
                    name="ollama", priority=2, available=True,
                    client=ol, models=tier_map,
                )
        except Exception:
            pass

        # 3. OpenAI (optional)
        if os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                client = openai.OpenAI()
                self._providers["openai"] = Provider(
                    name="openai", priority=3, available=True,
                    client=client,
                    models={
                        "opus":   "gpt-4o",
                        "sonnet": "gpt-4o-mini",
                        "haiku":  "gpt-4o-mini",
                    }
                )
            except ImportError:
                pass

        # Set active provider
        if self._providers:
            best = min(self._providers.values(), key=lambda p: p.priority)
            self._active = best.name

    def _map_ollama_tiers(self, models: List[str]) -> Dict[str, str]:
        tier_map: Dict[str, str] = {}
        # Map by model size
        for m in models:
            ml = m.lower()
            if any(x in ml for x in ("70b", "72b", "65b")):
                tier_map.setdefault("opus", m)
            elif any(x in ml for x in ("13b", "14b", "8b", "7b")):
                tier_map.setdefault("sonnet", m)
            elif any(x in ml for x in ("3b", "1b", "mini", "small")):
                tier_map.setdefault("haiku", m)
        # Fallback: use first available for all tiers
        first = models[0] if models else "llama3"
        for tier in ("opus", "sonnet", "haiku"):
            tier_map.setdefault(tier, first)
        return tier_map

    def get_client(self, provider: Optional[str] = None) -> Optional[Any]:
        name = provider or self._active
        p    = self._providers.get(name or "")
        return p.client if p else None

    def get_model(self, tier: str = "sonnet",
                  provider: Optional[str] = None) -> str:
        name = provider or self._active
        p    = self._providers.get(name or "")
        if p:
            return p.models.get(tier, p.models.get("sonnet", ""))
        return "claude-sonnet-4-6"

    def switch(self, provider: str) -> bool:
        if provider in self._providers:
            self._active = provider
            return True
        return False

    def status(self) -> str:
        lines = [f"Provider Registry — active: {self._active or 'none'}"]
        for name, p in sorted(self._providers.items(), key=lambda x: x[1].priority):
            mark = "→ " if name == self._active else "  "
            models_str = " | ".join(f"{t}={m}" for t, m in p.models.items())
            lines.append(f"{mark}[{name}] {models_str}")
        if not self._providers:
            lines.append("  No providers available. Set ANTHROPIC_API_KEY or start Ollama.")
        return "\n".join(lines)

    @property
    def active(self) -> Optional[str]:
        return self._active

    @property
    def providers(self) -> List[str]:
        return list(self._providers)
