"""
AILEX Pilot — plugins.py
Plugin system: add custom agents without touching core code.
Drop a .py file in ~/.aiox-core/plugins/ and AILEX loads it automatically.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "plugins"
)


@dataclass
class PluginAgent:
    name:        str
    tier:        str           # "opus" | "sonnet" | "haiku"
    persona:     str           # system prompt
    domains:     List[str]     # domain affinity
    handler:     Optional[Callable] = None   # custom async handler


@dataclass
class Plugin:
    name:        str
    version:     str
    author:      str
    agents:      List[PluginAgent] = field(default_factory=list)
    hooks:       Dict[str, Callable] = field(default_factory=dict)
    loaded:      bool = False
    error:       Optional[str] = None


class PluginManager:
    """
    Discovers, loads, and registers AILEX plugins.
    Plugin format: a Python file with a `register(manager)` function.
    """

    def __init__(self, plugin_dir: str = PLUGIN_DIR):
        self.plugin_dir = plugin_dir
        self.plugins:   Dict[str, Plugin] = {}
        self.agents:    Dict[str, PluginAgent] = {}
        self.hooks:     Dict[str, List[Callable]] = {}
        os.makedirs(plugin_dir, exist_ok=True)

    def discover_and_load(self) -> List[Plugin]:
        """Scan plugin dir and load all .py files."""
        loaded = []
        for fname in os.listdir(self.plugin_dir):
            if fname.endswith(".py") and not fname.startswith("_"):
                plugin = self._load_file(os.path.join(self.plugin_dir, fname))
                if plugin:
                    loaded.append(plugin)
        return loaded

    def _load_file(self, path: str) -> Optional[Plugin]:
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            spec   = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(module)  # type: ignore

            plugin = Plugin(
                name=getattr(module, "__plugin_name__", name),
                version=getattr(module, "__version__", "0.0.1"),
                author=getattr(module, "__author__", "unknown"),
            )
            if hasattr(module, "register"):
                module.register(self, plugin)
            plugin.loaded = True
            self.plugins[plugin.name] = plugin
            return plugin
        except Exception as e:
            err_plugin = Plugin(name=name, version="0", author="", error=str(e))
            self.plugins[name] = err_plugin
            return err_plugin

    def register_agent(self, plugin: Plugin, agent: PluginAgent) -> None:
        """Register a custom agent from a plugin."""
        plugin.agents.append(agent)
        self.agents[agent.name] = agent
        # Inject into v6 agents module if available
        try:
            from ailex_mythos_v6 import agents as agents_mod
            from ailex_mythos_v6.config import AGENT_MODEL_TIER
            agents_mod.AGENT_PERSONAS[agent.name] = agent.persona
            model_map = {"opus": "claude-opus-4-7", "sonnet": "claude-sonnet-4-6",
                         "haiku": "claude-haiku-4-5-20251001"}
            AGENT_MODEL_TIER[agent.name] = model_map.get(agent.tier, "claude-sonnet-4-6")
            for domain in agent.domains:
                if domain in agents_mod.DOMAIN_AFFINITY:
                    if agent.name not in agents_mod.DOMAIN_AFFINITY[domain]:
                        agents_mod.DOMAIN_AFFINITY[domain].append(agent.name)
        except Exception:
            pass

    def register_hook(self, plugin: Plugin, event: str, fn: Callable) -> None:
        """Register a hook for pipeline events: pre_process, post_process, on_commit."""
        plugin.hooks[event] = fn
        self.hooks.setdefault(event, []).append(fn)

    def fire_hook(self, event: str, *args, **kwargs) -> None:
        for fn in self.hooks.get(event, []):
            try:
                fn(*args, **kwargs)
            except Exception:
                pass

    def status(self) -> str:
        lines = [f"Plugins ({len(self.plugins)} loaded, {len(self.agents)} agents):"]
        for name, p in self.plugins.items():
            status = "✓" if p.loaded else f"✗ {p.error}"
            agents = ", ".join(a.name for a in p.agents) if p.agents else "no agents"
            lines.append(f"  [{status}] {name} v{p.version} — {agents}")
        return "\n".join(lines)

    def create_example_plugin(self) -> str:
        """Write an example plugin to the plugin directory."""
        path = os.path.join(self.plugin_dir, "example_agent.py")
        content = '''"""
Example AILEX plugin — adds a custom ZEUS agent.
Place in ~/.aiox-core/plugins/ to activate automatically.
"""

__plugin_name__ = "zeus-agent"
__version__     = "1.0.0"
__author__      = "your-name"


def register(manager, plugin):
    from ailex_pilot.plugins import PluginAgent
    manager.register_agent(plugin, PluginAgent(
        name    = "ZEUS",
        tier    = "sonnet",
        persona = (
            "You are ZEUS, omniscient technical advisor.\\n"
            "Focus: holistic view, cross-cutting concerns, big picture decisions.\\n"
            "End with: CONFIDENCE: 0.X"
        ),
        domains = ["architecture", "strategy", "vague"],
    ))
    manager.register_hook(plugin, "post_process", lambda result: (
        print(f"[ZEUS hook] domain={result.get('domain')} conf={result.get('confidence',0):.2f}")
        if result else None
    ))
'''
        with open(path, "w") as f:
            f.write(content)
        return path
