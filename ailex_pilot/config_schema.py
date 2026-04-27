"""
AILEX Pilot — config_schema.py
YAML-driven behaviour configuration — customize AILEX without touching code.
Inspired by SWE-agent's YAML config pattern + Continue.dev's markdown config.
100% original AILEX implementation.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import yaml
    YAML_OK = True
except ImportError:
    YAML_OK = False

DEFAULT_CONFIG = """
# AILEX Configuration
# Place as .ailex.yml in your project root

ailex:
  version: "4.0"

  # Model settings
  models:
    prefer_local: false          # use Ollama when available
    session_budget: 10.0        # USD per session
    quality_mode: false          # use Flux Dev instead of Schnell for images

  # Pipeline behaviour
  pipeline:
    max_loops: 16
    act_threshold: 0.99
    use_neural_layers: true
    use_chaos_critic: true
    use_hierarchical_teams: true
    use_cache: true
    cache_similarity: 0.75       # 0.0-1.0 threshold for cache hits

  # Human-in-the-loop
  approval:
    mode: auto                   # auto | interactive | callback
    auto_approve_stages:
      - pre_agents
      - post_synthesis
    confidence_threshold: 0.85   # auto-approve above this

  # Code quality gates
  quality:
    run_after_generation: true
    tools: [syntax, pylint, tsc]
    fail_on_error: false

  # Git behaviour
  git:
    auto_commit: false
    auto_pr: false
    commit_prefix: "AILEX: "

  # Proactive monitoring
  monitor:
    enabled: false
    interval_seconds: 300
    checks: [security, dead_code, test_coverage, new_commits]

  # Notifications
  notify:
    on_task_complete: true
    on_security_issue: true
    on_regression: true

  # Agents to enable (empty = all)
  agents:
    enabled: []
    disabled: []

  # Custom agent personas (overrides defaults)
  personas: {}

  # Domain-specific overrides
  domains:
    architecture:
      min_loops: 5
      use_chaos: true
    bug:
      use_tdd: true
      max_tdd_iterations: 3
    documentation:
      model_tier: haiku
"""


@dataclass
class AILEXConfig:
    version:            str   = "4.0"
    session_budget:     float = 10.0
    quality_mode:       bool  = False
    prefer_local:       bool  = False
    max_loops:          int   = 16
    act_threshold:      float = 0.99
    use_neural_layers:  bool  = True
    use_chaos_critic:   bool  = True
    use_hierarchical:   bool  = True
    use_cache:          bool  = True
    cache_similarity:   float = 0.75
    approval_mode:      str   = "auto"
    auto_approve_stages:List[str] = field(default_factory=lambda: ["pre_agents"])
    confidence_threshold:float= 0.85
    run_quality_checks: bool  = True
    quality_tools:      List[str] = field(default_factory=lambda: ["syntax"])
    auto_commit:        bool  = False
    auto_pr:            bool  = False
    monitor_enabled:    bool  = False
    monitor_interval:   int   = 300
    notify_on_complete: bool  = True
    enabled_agents:     List[str] = field(default_factory=list)
    disabled_agents:    List[str] = field(default_factory=list)
    custom_personas:    Dict[str, str] = field(default_factory=dict)
    domain_overrides:   Dict[str, Dict] = field(default_factory=dict)
    raw:                Dict = field(default_factory=dict)


class ConfigLoader:
    """Load and validate .ailex.yml configuration."""

    SEARCH_PATHS = [".ailex.yml", ".ailex.yaml", "ailex.yml",
                    os.path.expanduser("~/.ailex.yml")]

    def load(self, project_dir: str = ".") -> AILEXConfig:
        """Search for config file and load it."""
        for fname in self.SEARCH_PATHS:
            path = fname if os.path.isabs(fname) else os.path.join(project_dir, fname)
            if os.path.exists(path):
                return self._parse(path)
        return AILEXConfig()   # defaults

    def _parse(self, path: str) -> AILEXConfig:
        if not YAML_OK:
            return AILEXConfig()
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            cfg = raw.get("ailex", {})
            models   = cfg.get("models", {})
            pipeline = cfg.get("pipeline", {})
            approval = cfg.get("approval", {})
            quality  = cfg.get("quality", {})
            git      = cfg.get("git", {})
            monitor  = cfg.get("monitor", {})
            notify   = cfg.get("notify", {})
            agents   = cfg.get("agents", {})

            return AILEXConfig(
                version=cfg.get("version", "4.0"),
                session_budget=models.get("session_budget", 10.0),
                quality_mode=models.get("quality_mode", False),
                prefer_local=models.get("prefer_local", False),
                max_loops=pipeline.get("max_loops", 16),
                act_threshold=pipeline.get("act_threshold", 0.99),
                use_neural_layers=pipeline.get("use_neural_layers", True),
                use_chaos_critic=pipeline.get("use_chaos_critic", True),
                use_hierarchical=pipeline.get("use_hierarchical_teams", True),
                use_cache=pipeline.get("use_cache", True),
                cache_similarity=pipeline.get("cache_similarity", 0.75),
                approval_mode=approval.get("mode", "auto"),
                auto_approve_stages=approval.get("auto_approve_stages", ["pre_agents"]),
                confidence_threshold=approval.get("confidence_threshold", 0.85),
                run_quality_checks=quality.get("run_after_generation", True),
                quality_tools=quality.get("tools", ["syntax"]),
                auto_commit=git.get("auto_commit", False),
                auto_pr=git.get("auto_pr", False),
                monitor_enabled=monitor.get("enabled", False),
                monitor_interval=monitor.get("interval_seconds", 300),
                notify_on_complete=notify.get("on_task_complete", True),
                enabled_agents=agents.get("enabled", []),
                disabled_agents=agents.get("disabled", []),
                custom_personas=cfg.get("personas", {}),
                domain_overrides=cfg.get("domains", {}),
                raw=raw,
            )
        except Exception:
            return AILEXConfig()

    def write_default(self, path: str = ".ailex.yml") -> None:
        with open(path, "w") as f:
            f.write(DEFAULT_CONFIG)

    def apply_to_pipeline(self, config: AILEXConfig, pipeline: Any) -> None:
        """Apply loaded config to a PilotPipeline instance."""
        try:
            from ailex_mythos_v6.config import MythosCognitiveConfig
            cfg = pipeline.cfg
            cfg.max_loop_iters       = config.max_loops
            cfg.act_threshold        = config.act_threshold
            cfg.use_neural_layers    = config.use_neural_layers
            cfg.use_constitutional   = config.use_chaos_critic
            cfg.use_hierarchical_teams = config.use_hierarchical
        except Exception:
            pass

        # Apply custom personas
        if config.custom_personas:
            try:
                from ailex_mythos_v6 import agents as agents_mod
                agents_mod.AGENT_PERSONAS.update(config.custom_personas)
            except Exception:
                pass
