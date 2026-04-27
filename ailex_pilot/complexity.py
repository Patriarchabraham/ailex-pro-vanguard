"""
AILEX Pilot — complexity.py
Code complexity metrics: cyclomatic, cognitive, maintainability index, LOC.
Inspired by Radon's metric pipeline — AILEX original implementation.
"""
from __future__ import annotations

import ast
import math
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FunctionMetrics:
    name:             str
    file:             str
    line:             int
    cyclomatic:       int     # McCabe complexity
    cognitive:        int     # cognitive complexity (nesting-aware)
    loc:              int     # lines of code
    lloc:             int     # logical lines of code
    params:           int     # number of parameters
    returns:          int     # number of return statements
    grade:            str     # A-F (A=simple, F=unmaintainable)


@dataclass
class FileMetrics:
    path:             str
    language:         str
    loc:              int
    lloc:             int
    blank:            int
    comment:          int
    functions:        List[FunctionMetrics]
    maintainability:  float   # 0-100 (Halstead-inspired)
    avg_complexity:   float
    max_complexity:   int
    grade:            str


@dataclass
class ProjectMetrics:
    total_loc:        int
    total_lloc:       int
    total_files:      int
    total_functions:  int
    avg_complexity:   float
    max_complexity:   int
    hotspots:         List[FunctionMetrics]   # most complex functions
    grade:            str
    by_file:          List[FileMetrics]


class ComplexityAnalyzer:
    """
    Code complexity analysis without external dependencies.
    Python: stdlib ast. JS/TS: regex-based approximation.
    """

    GRADE_THRESHOLDS = [(5, "A"), (10, "B"), (20, "C"), (30, "D"), (50, "E"), (999, "F")]

    def analyze_project(self, root: str) -> ProjectMetrics:
        file_metrics: List[FileMetrics] = []
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", ".git", "__pycache__", "dist", "build")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in (".py", ".ts", ".tsx", ".js", ".jsx"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    fm = self.analyze_file(fpath)
                    file_metrics.append(fm)
                except Exception:
                    pass

        all_funcs = [f for fm in file_metrics for f in fm.functions]
        if not all_funcs:
            return ProjectMetrics(0, 0, 0, 0, 0.0, 0, [], "A", [])

        total_loc   = sum(fm.loc for fm in file_metrics)
        total_lloc  = sum(fm.lloc for fm in file_metrics)
        complexities= [f.cyclomatic for f in all_funcs]
        avg_c       = sum(complexities) / len(complexities)
        max_c       = max(complexities)
        hotspots    = sorted(all_funcs, key=lambda f: -f.cyclomatic)[:10]

        return ProjectMetrics(
            total_loc=total_loc, total_lloc=total_lloc,
            total_files=len(file_metrics), total_functions=len(all_funcs),
            avg_complexity=round(avg_c, 2), max_complexity=max_c,
            hotspots=hotspots, grade=self._grade(avg_c),
            by_file=sorted(file_metrics, key=lambda f: -f.max_complexity),
        )

    def analyze_file(self, path: str) -> FileMetrics:
        content = open(path, encoding="utf-8", errors="ignore").read()
        ext     = os.path.splitext(path)[1].lower()
        if ext == ".py":
            return self._analyze_python(path, content)
        else:
            return self._analyze_js(path, content)

    def _analyze_python(self, path: str, content: str) -> FileMetrics:
        lines    = content.splitlines()
        loc      = len(lines)
        blank    = sum(1 for l in lines if not l.strip())
        comment  = sum(1 for l in lines if l.strip().startswith("#"))
        lloc     = loc - blank - comment
        functions: List[FunctionMetrics] = []

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cc  = self._cyclomatic_py(node)
                    cog = self._cognitive_py(node)
                    fn  = FunctionMetrics(
                        name=node.name, file=path,
                        line=node.lineno,
                        cyclomatic=cc, cognitive=cog,
                        loc=getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                        lloc=max(1, getattr(node, "end_lineno", node.lineno) - node.lineno),
                        params=len(node.args.args),
                        returns=sum(1 for n in ast.walk(node) if isinstance(n, ast.Return)),
                        grade=self._grade(cc),
                    )
                    functions.append(fn)
        except SyntaxError:
            pass

        avg_c = sum(f.cyclomatic for f in functions) / max(1, len(functions))
        mi    = self._maintainability(lloc, avg_c, len(functions))

        return FileMetrics(
            path=path, language="python",
            loc=loc, lloc=lloc, blank=blank, comment=comment,
            functions=functions,
            maintainability=mi,
            avg_complexity=round(avg_c, 2),
            max_complexity=max((f.cyclomatic for f in functions), default=0),
            grade=self._grade(avg_c),
        )

    def _analyze_js(self, path: str, content: str) -> FileMetrics:
        lines   = content.splitlines()
        loc     = len(lines)
        blank   = sum(1 for l in lines if not l.strip())
        comment = sum(1 for l in lines if l.strip().startswith("//"))
        lloc    = loc - blank - comment
        functions: List[FunctionMetrics] = []

        # Extract functions via regex
        fn_pattern = re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\())",
            re.M
        )
        for m in fn_pattern.finditer(content):
            name = m.group(1) or m.group(2)
            if not name:
                continue
            line  = content[:m.start()].count("\n") + 1
            # Approximate complexity by counting control flow keywords
            end   = min(m.start() + 2000, len(content))
            chunk = content[m.start():end]
            cc    = 1 + sum(1 for kw in
                            re.findall(r"\b(if|else if|for|while|switch|catch|&&|\|\|)\b", chunk))
            cc    = min(cc, 30)
            functions.append(FunctionMetrics(
                name=name, file=path, line=line,
                cyclomatic=cc, cognitive=cc,
                loc=chunk.count("\n"), lloc=max(1, chunk.count(";") + chunk.count("{")),
                params=chunk[:200].count(",") + 1 if "(" in chunk[:50] else 0,
                returns=chunk.count("return"),
                grade=self._grade(cc),
            ))

        avg_c = sum(f.cyclomatic for f in functions) / max(1, len(functions))
        mi    = self._maintainability(lloc, avg_c, len(functions))
        ext   = os.path.splitext(path)[1].lstrip(".")

        return FileMetrics(
            path=path, language=ext,
            loc=loc, lloc=lloc, blank=blank, comment=comment,
            functions=functions,
            maintainability=mi,
            avg_complexity=round(avg_c, 2),
            max_complexity=max((f.cyclomatic for f in functions), default=0),
            grade=self._grade(avg_c),
        )

    def _cyclomatic_py(self, node: ast.AST) -> int:
        cc = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                  ast.With, ast.Assert, ast.comprehension)):
                cc += 1
            elif isinstance(child, ast.BoolOp):
                cc += len(child.values) - 1
        return cc

    def _cognitive_py(self, node: ast.AST, depth: int = 0) -> int:
        """Cognitive complexity — nesting penalises more."""
        score = 0
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                score += 1 + depth
                score += self._cognitive_py(child, depth + 1)
            elif isinstance(child, ast.BoolOp):
                score += len(child.values) - 1
            else:
                score += self._cognitive_py(child, depth)
        return score

    def _maintainability(self, lloc: int, avg_cc: float, n_funcs: int) -> float:
        """Maintainability Index (0-100, higher = more maintainable)."""
        if lloc <= 0:
            return 100.0
        try:
            volume = lloc * math.log2(max(1, lloc))
            mi     = 171 - 5.2 * math.log(max(1, volume)) - 0.23 * avg_cc - 16.2 * math.log(max(1, lloc))
            return round(max(0.0, min(100.0, mi)), 1)
        except Exception:
            return 50.0

    def _grade(self, cc: float) -> str:
        for threshold, grade in self.GRADE_THRESHOLDS:
            if cc <= threshold:
                return grade
        return "F"

    def format_project(self, m: ProjectMetrics) -> str:
        lines = [
            f"Complexity Report: {m.total_files} files | {m.total_loc:,} LOC | "
            f"{m.total_functions} functions",
            f"Avg complexity: {m.avg_complexity:.1f} ({m.grade}) | "
            f"Max: {m.max_complexity}",
            "",
            "Hotspots (most complex):",
        ]
        for f in m.hotspots[:8]:
            rel = os.path.relpath(f.file) if os.path.exists(f.file) else f.file
            lines.append(
                f"  {f.grade} CC={f.cyclomatic:2d} {rel}:{f.line} {f.name}()"
            )
        return "\n".join(lines)
