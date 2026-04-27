"""
AILEX Pilot — dependency_graph.py
Project dependency graph: imports, circular deps, coupling metrics.
Inspired by pydeps pattern — AILEX original (no graphviz required).
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Module:
    name:      str
    path:      str
    imports:   List[str]        # modules this imports
    imported_by: List[str]      # modules that import this
    is_circular: bool = False


@dataclass
class DependencyReport:
    modules:        Dict[str, Module]
    circular:       List[Tuple[str, str]]   # circular dependency pairs
    most_depended:  List[Tuple[str, int]]   # (module, n_importers)
    most_coupled:   List[Tuple[str, int]]   # (module, n_imports)
    orphans:        List[str]               # modules nothing imports
    depth:          int                     # max dependency chain length
    mermaid:        str                     # Mermaid.js graph


class DependencyAnalyzer:
    """
    Analyses import/dependency relationships across a Python or JS/TS project.
    Detects circular dependencies, high coupling, orphaned modules.
    """

    def analyze(self, root: str) -> DependencyReport:
        modules: Dict[str, Module] = {}

        # Collect all source files
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__",
                                    "dist", "build", "venv", ".venv")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in (".py", ".ts", ".tsx", ".js", ".jsx"):
                    continue
                fpath = os.path.join(dirpath, fname)
                rel   = os.path.relpath(fpath, root)
                name  = rel.replace(os.sep, ".").rsplit(".", 1)[0]
                imports = self._extract_imports(fpath, ext)
                modules[name] = Module(
                    name=name, path=fpath,
                    imports=imports, imported_by=[],
                )

        # Build reverse: imported_by
        for name, mod in modules.items():
            for imp in mod.imports:
                if imp in modules:
                    modules[imp].imported_by.append(name)

        # Detect circular dependencies
        circular = self._find_cycles(modules)
        for a, b in circular:
            if a in modules: modules[a].is_circular = True
            if b in modules: modules[b].is_circular = True

        # Metrics
        most_depended = sorted(
            [(n, len(m.imported_by)) for n, m in modules.items()],
            key=lambda x: -x[1]
        )[:10]
        most_coupled = sorted(
            [(n, len(m.imports)) for n, m in modules.items()],
            key=lambda x: -x[1]
        )[:10]
        orphans = [n for n, m in modules.items()
                   if not m.imported_by and not n.endswith("__init__")]

        return DependencyReport(
            modules=modules,
            circular=circular,
            most_depended=most_depended,
            most_coupled=most_coupled,
            orphans=orphans[:10],
            depth=self._max_depth(modules),
            mermaid=self._to_mermaid(modules, max_nodes=30),
        )

    def _extract_imports(self, path: str, ext: str) -> List[str]:
        content = open(path, encoding="utf-8", errors="ignore").read()
        imports: List[str] = []
        if ext == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module.split(".")[0])
            except SyntaxError:
                pass
        else:
            # JS/TS: import ... from '...'
            for m in re.finditer(r"""from\s+['"]([^'"]+)['"]""", content):
                src = m.group(1)
                if src.startswith("."):
                    # Relative import — normalise
                    imports.append(src.lstrip("./").split("/")[0])
                else:
                    imports.append(src.split("/")[0])
        return list(dict.fromkeys(imports))

    def _find_cycles(self, modules: Dict[str, Module]) -> List[Tuple[str, str]]:
        cycles: List[Tuple[str, str]] = []
        visited: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            if node in path:
                idx = path.index(node)
                cycle = (path[idx], path[-1])
                if cycle not in cycles and (cycle[1], cycle[0]) not in cycles:
                    cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            mod = modules.get(node)
            if mod:
                for imp in mod.imports:
                    if imp in modules:
                        dfs(imp, path + [node])

        for name in modules:
            dfs(name, [])
        return cycles[:20]

    def _max_depth(self, modules: Dict[str, Module]) -> int:
        memo: Dict[str, int] = {}
        def depth(name: str, seen: Set[str]) -> int:
            if name in memo: return memo[name]
            if name in seen: return 0
            mod = modules.get(name)
            if not mod or not mod.imports:
                return 0
            d = 1 + max(
                (depth(i, seen | {name}) for i in mod.imports if i in modules),
                default=0
            )
            memo[name] = d
            return d
        return max((depth(n, set()) for n in modules), default=0)

    def _to_mermaid(self, modules: Dict[str, Module], max_nodes: int = 30) -> str:
        # Show only most connected nodes
        top = sorted(modules.items(),
                     key=lambda x: len(x[1].imports) + len(x[1].imported_by),
                     reverse=True)[:max_nodes]
        top_names = {n for n, _ in top}
        lines = ["graph TD"]
        for name, mod in top:
            safe = re.sub(r"[^a-zA-Z0-9]", "_", name)
            style = ":::circular" if mod.is_circular else ""
            for imp in mod.imports:
                if imp in top_names:
                    safe_imp = re.sub(r"[^a-zA-Z0-9]", "_", imp)
                    lines.append(f"    {safe} --> {safe_imp}")
        if len(lines) == 1:
            lines.append("    A[No dependencies found]")
        return "\n".join(lines)

    def format_report(self, r: DependencyReport) -> str:
        lines = [
            f"Dependency Analysis: {len(r.modules)} modules",
            f"  Circular deps:  {len(r.circular)}",
            f"  Max depth:      {r.depth}",
            f"  Orphan modules: {len(r.orphans)}",
        ]
        if r.circular:
            lines.append("\nCircular dependencies (fix these):")
            for a, b in r.circular[:5]:
                lines.append(f"  ⟳ {a} ↔ {b}")
        if r.most_depended:
            lines.append("\nMost depended on (high coupling risk):")
            for name, n in r.most_depended[:5]:
                lines.append(f"  {n:3d} importers — {name}")
        return "\n".join(lines)
