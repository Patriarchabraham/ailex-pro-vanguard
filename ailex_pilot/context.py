"""
AILEX Pilot — context.py
Reads and indexes any codebase for injection into agent prompts.
The most critical missing piece: AILEX now sees the actual project.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


IGNORE_DIRS: Set[str] = {
    "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    "coverage", ".cache", "venv", ".venv", "env", ".env", "vendor",
    ".turbo", ".vercel", "out", ".expo", "eggs", "*.egg-info",
}

IGNORE_FILES: Set[str] = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "*.min.js", "*.min.css", "*.map", "*.pyc", "*.pyo",
    ".DS_Store", "Thumbs.db",
}

CODE_EXTENSIONS: Dict[str, str] = {
    ".py":    "python",   ".ts": "typescript", ".tsx":  "typescript",
    ".js":    "javascript",".jsx":"javascript", ".mjs":  "javascript",
    ".rs":    "rust",     ".go": "go",         ".java": "java",
    ".rb":    "ruby",     ".php":"php",         ".swift":"swift",
    ".kt":    "kotlin",   ".cs": "csharp",      ".cpp":  "cpp",
    ".c":     "c",        ".sh": "bash",         ".md":   "markdown",
    ".sql":   "sql",      ".html":"html",        ".css":  "css",
    ".scss":  "scss",     ".yaml":"yaml",        ".yml":  "yaml",
    ".json":  "json",     ".toml":"toml",        ".env":  "env",
    ".tf":    "terraform",".dockerfile":"docker",
}

MAX_FILE_BYTES   = 50_000   # skip files larger than this
MAX_TOTAL_CHARS  = 200_000  # total context budget
MAX_FILES        = 100


@dataclass
class CodeFile:
    path:       str          # relative to root
    language:   str
    content:    str
    size:       int
    lines:      int
    symbols:    List[str]    # functions, classes, exports detected


@dataclass
class ProjectContext:
    root:         str
    name:         str
    language:     str         # dominant language
    tech_stack:   List[str]
    files:        List[CodeFile]
    structure:    str         # ascii tree
    key_files:    List[str]   # package.json, main.py, etc.
    total_lines:  int
    total_files:  int
    summary:      str


class ProjectReader:
    """Reads and indexes a codebase for AI agent context."""

    def __init__(self, max_files: int = MAX_FILES,
                 max_total: int = MAX_TOTAL_CHARS):
        self.max_files = max_files
        self.max_total = max_total

    def read(self, root: str = ".") -> ProjectContext:
        root = os.path.abspath(root)
        name = os.path.basename(root)

        files: List[CodeFile] = []
        total_chars = 0

        # Prioritise key files first
        candidates = self._collect_candidates(root)
        for path in candidates:
            if len(files) >= self.max_files:
                break
            if total_chars >= self.max_total:
                break
            try:
                rel  = os.path.relpath(path, root)
                size = os.path.getsize(path)
                if size > MAX_FILE_BYTES:
                    continue
                content = open(path, encoding="utf-8", errors="ignore").read()
                if total_chars + len(content) > self.max_total:
                    content = content[:self.max_total - total_chars]
                ext  = Path(path).suffix.lower()
                lang = CODE_EXTENSIONS.get(ext, "text")
                cf   = CodeFile(
                    path=rel, language=lang, content=content,
                    size=size, lines=content.count("\n"),
                    symbols=self._extract_symbols(content, lang),
                )
                files.append(cf)
                total_chars += len(content)
            except (OSError, PermissionError):
                continue

        tech        = self._detect_tech(root, files)
        dominant    = self._dominant_language(files)
        key_files   = self._key_files(root)
        structure   = self._tree(root, max_depth=4)
        total_lines = sum(f.lines for f in files)

        ctx = ProjectContext(
            root=root, name=name, language=dominant,
            tech_stack=tech, files=files,
            structure=structure, key_files=key_files,
            total_lines=total_lines, total_files=len(files),
            summary="",
        )
        ctx.summary = self._summarize(ctx)
        return ctx

    def _collect_candidates(self, root: str) -> List[str]:
        """Walk tree, prioritising key files."""
        priority: List[str] = []
        regular:  List[str] = []

        KEY_NAMES = {
            "package.json", "pyproject.toml", "setup.py", "Cargo.toml",
            "go.mod", "pom.xml", "build.gradle", "Makefile", "Dockerfile",
            "docker-compose.yml", "README.md", "CLAUDE.md", ".env.example",
            "tsconfig.json", "vite.config.ts", "next.config.js",
            "tailwind.config.js", "prisma/schema.prisma",
        }

        for dirpath, dirs, files_list in os.walk(root):
            dirs[:] = [d for d in dirs
                       if d not in IGNORE_DIRS and not d.startswith(".")]
            rel_dir = os.path.relpath(dirpath, root)
            depth   = rel_dir.count(os.sep) if rel_dir != "." else 0
            if depth > 6:
                dirs.clear()
                continue
            for fname in files_list:
                if any(fname.endswith(ig.lstrip("*")) for ig in IGNORE_FILES):
                    continue
                fpath = os.path.join(dirpath, fname)
                ext   = Path(fpath).suffix.lower()
                if ext not in CODE_EXTENSIONS and fname not in KEY_NAMES:
                    continue
                if fname in KEY_NAMES or os.path.relpath(fpath, root) in KEY_NAMES:
                    priority.append(fpath)
                else:
                    regular.append(fpath)

        # Sort regular files: shorter paths (closer to root) first
        regular.sort(key=lambda p: (p.count(os.sep), p))
        return priority + regular

    def _extract_symbols(self, content: str, lang: str) -> List[str]:
        patterns = {
            "python":     [r"^(?:def|class|async def)\s+(\w+)", r"^(\w+)\s*=\s*(?:lambda|def)"],
            "typescript": [r"(?:export\s+)?(?:function|class|const|interface|type|enum)\s+(\w+)",
                           r"(?:export\s+default\s+)?(?:function|class)\s+(\w+)"],
            "javascript": [r"(?:function|class|const|let|var)\s+(\w+)",
                           r"module\.exports\s*=\s*\{([^}]+)\}"],
            "go":         [r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)"],
            "rust":       [r"^(?:pub\s+)?(?:fn|struct|enum|trait|impl)\s+(\w+)"],
        }
        syms: List[str] = []
        for pattern in patterns.get(lang, []):
            for m in re.finditer(pattern, content, re.MULTILINE):
                sym = m.group(1).strip()
                if sym and len(sym) > 1:
                    syms.append(sym)
        return list(dict.fromkeys(syms))[:20]

    def _detect_tech(self, root: str, files: List[CodeFile]) -> List[str]:
        tech: List[str] = []
        has = lambda name: any(name in f.path for f in files)
        content_has = lambda kw: any(kw in f.content for f in files)

        if has("package.json"):      tech.append("Node.js")
        if has("next.config"):        tech.append("Next.js")
        if has("vite.config"):        tech.append("Vite")
        if has("tailwind.config"):    tech.append("Tailwind CSS")
        if has("prisma"):             tech.append("Prisma")
        if has("requirements.txt") or has("pyproject.toml"): tech.append("Python")
        if has("Cargo.toml"):         tech.append("Rust")
        if has("go.mod"):             tech.append("Go")
        if has("Dockerfile"):         tech.append("Docker")
        if content_has("from anthropic"): tech.append("Anthropic SDK")
        if content_has("from openai"):    tech.append("OpenAI SDK")
        if content_has("useState"):       tech.append("React")
        if content_has("from fastapi"):   tech.append("FastAPI")
        if content_has("from django"):    tech.append("Django")
        if content_has("express()"):      tech.append("Express")
        return tech

    def _dominant_language(self, files: List[CodeFile]) -> str:
        counts: Dict[str, int] = {}
        for f in files:
            counts[f.language] = counts.get(f.language, 0) + f.lines
        if not counts:
            return "unknown"
        return max(counts, key=lambda k: counts[k])

    def _key_files(self, root: str) -> List[str]:
        candidates = [
            "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
            "README.md", "CLAUDE.md", ".env.example", "Dockerfile",
            "src/index.ts", "src/main.ts", "src/app.py", "main.py",
            "src/index.js", "app.js", "server.py", "server.ts",
        ]
        return [c for c in candidates if os.path.exists(os.path.join(root, c))]

    def _tree(self, root: str, max_depth: int = 4) -> str:
        lines: List[str] = [os.path.basename(root) + "/"]
        self._tree_walk(root, root, "", lines, 0, max_depth)
        return "\n".join(lines[:80])  # cap at 80 lines

    def _tree_walk(self, root: str, current: str, prefix: str,
                   lines: List[str], depth: int, max_depth: int) -> None:
        if depth >= max_depth:
            return
        try:
            entries = sorted(os.listdir(current))
        except PermissionError:
            return
        entries = [e for e in entries
                   if e not in IGNORE_DIRS and not e.startswith(".")
                   or e in (".env.example",)]
        for i, entry in enumerate(entries[:25]):
            is_last  = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            path      = os.path.join(current, entry)
            lines.append(prefix + connector + entry + ("/" if os.path.isdir(path) else ""))
            if os.path.isdir(path):
                extension = "    " if is_last else "│   "
                self._tree_walk(root, path, prefix + extension, lines, depth + 1, max_depth)

    def _summarize(self, ctx: ProjectContext) -> str:
        parts = [
            f"Project: {ctx.name} ({ctx.language}, {ctx.total_files} files, {ctx.total_lines:,} lines)",
            f"Tech: {', '.join(ctx.tech_stack) or 'unknown'}",
            f"Key files: {', '.join(ctx.key_files[:6]) or 'none'}",
        ]
        # Key symbols per file
        for f in ctx.files[:5]:
            if f.symbols:
                parts.append(f"  {f.path}: {', '.join(f.symbols[:6])}")
        return "\n".join(parts)

    def to_prompt(self, ctx: ProjectContext, max_files: int = 20) -> str:
        """Format project context for injection into agent prompts."""
        sections = [
            "=== PROJECT CONTEXT ===",
            ctx.summary,
            "",
            "=== DIRECTORY STRUCTURE ===",
            ctx.structure,
        ]
        shown = 0
        for f in ctx.files:
            if shown >= max_files:
                sections.append(f"... ({ctx.total_files - shown} more files not shown)")
                break
            sections += [
                f"\n--- {f.path} ({f.language}, {f.lines} lines) ---",
                f"Symbols: {', '.join(f.symbols[:8])}" if f.symbols else "",
                f"```{f.language}",
                f.content[:3000] + ("..." if len(f.content) > 3000 else ""),
                "```",
            ]
            shown += 1
        sections.append("=== END PROJECT CONTEXT ===")
        return "\n".join(s for s in sections if s is not None)
