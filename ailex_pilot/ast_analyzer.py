"""
AILEX Pilot — ast_analyzer.py
Structural code analysis: call graphs, imports, dead code, complexity.
Supports Python (ast stdlib) and JS/TS (regex-based).
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CodeSymbol:
    name:       str
    kind:       str        # function | class | import | variable
    file:       str
    line:       int
    calls:      List[str] = field(default_factory=list)
    called_by:  List[str] = field(default_factory=list)
    is_used:    bool = True


@dataclass
class ASTReport:
    file:          str
    language:      str
    symbols:       List[CodeSymbol]
    imports:       List[str]
    dead_code:     List[str]       # symbols defined but never called
    complexity:    Dict[str, int]  # function → cyclomatic complexity
    lines:         int
    issues:        List[str]


class ASTAnalyzer:
    """
    Structural code analysis without running the code.
    Python: uses stdlib ast. JS/TS: regex-based extraction.
    """

    def analyze_file(self, path: str) -> ASTReport:
        if not os.path.exists(path):
            return ASTReport(path, "unknown", [], [], [], {}, 0, [f"File not found: {path}"])
        content = open(path, encoding="utf-8", errors="ignore").read()
        ext     = os.path.splitext(path)[1].lower()
        if ext == ".py":
            return self._analyze_python(path, content)
        elif ext in (".ts", ".tsx", ".js", ".jsx", ".mjs"):
            return self._analyze_js(path, content)
        return ASTReport(path, ext.lstrip("."), [], [], [], {}, content.count("\n"), [])

    def analyze_project(self, root: str) -> Dict[str, ASTReport]:
        reports: Dict[str, ASTReport] = {}
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in
                       ("node_modules", ".git", "__pycache__", "dist", "build", ".venv")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".py", ".ts", ".tsx", ".js", ".jsx"):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        reports[os.path.relpath(fpath, root)] = self.analyze_file(fpath)
                    except Exception:
                        pass
        return reports

    def find_dead_code(self, reports: Dict[str, ASTReport]) -> List[Tuple[str, str]]:
        """Cross-file dead code: defined in one file, never referenced in any."""
        all_defined: Dict[str, str] = {}
        all_called:  Set[str]       = set()
        for path, r in reports.items():
            for sym in r.symbols:
                if sym.kind in ("function", "class"):
                    all_defined[sym.name] = path
            all_called.update(c for sym in r.symbols for c in sym.calls)

        return [(name, path) for name, path in all_defined.items()
                if name not in all_called and not name.startswith("_")]

    def _analyze_python(self, path: str, content: str) -> ASTReport:
        symbols:    List[CodeSymbol] = []
        imports:    List[str]        = []
        complexity: Dict[str, int]   = {}
        issues:     List[str]        = []

        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError as e:
            return ASTReport(path, "python", [], [], [], {}, content.count("\n"),
                             [f"SyntaxError: {e}"])

        # Collect definitions and calls
        defined_names: Set[str] = set()
        called_names:  Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined_names.add(node.name)
                calls = [n.func.id if isinstance(n.func, ast.Name) else ""
                         for n in ast.walk(node) if isinstance(n, ast.Call)]
                calls = [c for c in calls if c]
                called_names.update(calls)
                complexity[node.name] = self._cyclomatic(node)
                symbols.append(CodeSymbol(
                    name=node.name, kind="function", file=path,
                    line=node.lineno, calls=calls[:10],
                ))

            elif isinstance(node, ast.ClassDef):
                defined_names.add(node.name)
                symbols.append(CodeSymbol(
                    name=node.name, kind="class", file=path, line=node.lineno,
                ))

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                else:
                    imports.append(node.module or "")

        dead = [s.name for s in symbols
                if s.kind == "function" and s.name not in called_names
                and not s.name.startswith("_") and s.name not in
                ("main", "test", "setup", "teardown")]

        # High complexity warning
        for fname, comp in complexity.items():
            if comp > 10:
                issues.append(f"High complexity ({comp}): {fname}")

        return ASTReport(path=path, language="python", symbols=symbols,
                         imports=list(set(imports)), dead_code=dead,
                         complexity=complexity, lines=content.count("\n"), issues=issues)

    def _analyze_js(self, path: str, content: str) -> ASTReport:
        symbols: List[CodeSymbol] = []
        imports: List[str]        = []

        # Functions
        for m in re.finditer(
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
            content
        ):
            name = m.group(1) or m.group(2)
            if name:
                line = content[:m.start()].count("\n") + 1
                symbols.append(CodeSymbol(name=name, kind="function", file=path, line=line))

        # Classes
        for m in re.finditer(r"(?:export\s+)?class\s+(\w+)", content):
            line = content[:m.start()].count("\n") + 1
            symbols.append(CodeSymbol(name=m.group(1), kind="class", file=path, line=line))

        # Imports
        for m in re.finditer(r"import\s+.+?\s+from\s+['\"](.+?)['\"]", content):
            imports.append(m.group(1))

        # Dead code (basic: defined but never called in same file)
        defined = {s.name for s in symbols}
        called  = set(re.findall(r"(\w+)\s*\(", content))
        dead    = [n for n in defined if n not in called and not n[0].isupper()]

        return ASTReport(path=path, language="typescript", symbols=symbols,
                         imports=list(set(imports)), dead_code=dead,
                         complexity={}, lines=content.count("\n"), issues=[])

    def _cyclomatic(self, node: ast.AST) -> int:
        """Cyclomatic complexity = 1 + branches."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                  ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def format_report(self, report: ASTReport) -> str:
        lines = [
            f"AST Analysis: {report.file} ({report.language}, {report.lines} lines)",
            f"  Symbols:    {len(report.symbols)} ({sum(1 for s in report.symbols if s.kind=='function')} functions)",
            f"  Imports:    {len(report.imports)}",
            f"  Dead code:  {len(report.dead_code)}",
        ]
        if report.dead_code:
            lines.append(f"  Unused:     {', '.join(report.dead_code[:8])}")
        if report.issues:
            lines.append("  Issues:")
            for i in report.issues[:5]:
                lines.append(f"    ⚠ {i}")
        return "\n".join(lines)
