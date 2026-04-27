"""
AILEX Pilot — file_watcher.py
File system watcher — auto-trigger AILEX analysis on code changes.
Inspired by Watchdog's event model — AILEX original implementation.
Uses stdlib only (no watchdog dependency).
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class FileEvent:
    kind:      str    # "modified" | "created" | "deleted" | "moved"
    path:      str
    ts:        float = field(default_factory=time.time)
    old_path:  str = ""   # for "moved" events


EventHandler = Callable[[FileEvent], None]

WATCH_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs",
    ".go", ".rs", ".java", ".kt", ".swift",
    ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".sql", ".sh",
}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build",
    ".next", "out", ".cache", "venv", ".venv", ".turbo",
}


class FileWatcher:
    """
    Watches a directory for file changes using polling (no external deps).
    Fires handlers on create/modify/delete. Debounces rapid changes.
    Runs in a background thread.
    """

    def __init__(
        self,
        root:          str,
        handlers:      List[EventHandler] = [],
        interval_s:    float = 1.5,
        debounce_s:    float = 0.5,
        extensions:    Set[str] = WATCH_EXTENSIONS,
    ):
        self.root       = os.path.abspath(root)
        self.handlers   = list(handlers)
        self.interval   = interval_s
        self.debounce   = debounce_s
        self.extensions = extensions
        self._running   = False
        self._thread:   Optional[threading.Thread] = None
        self._snapshot: Dict[str, float] = {}   # path → mtime
        self._pending:  Dict[str, FileEvent] = {}
        self._lock      = threading.Lock()

    def on(self, handler: EventHandler) -> "FileWatcher":
        self.handlers.append(handler)
        return self

    def start(self) -> None:
        self._snapshot = self._scan()
        self._running  = True
        self._thread   = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        last_fire = 0.0
        while self._running:
            try:
                current = self._scan()
                events  = self._diff(self._snapshot, current)
                if events:
                    with self._lock:
                        for e in events:
                            self._pending[e.path] = e
                self._snapshot = current
                # Fire debounced events
                now = time.time()
                if self._pending and (now - last_fire) >= self.debounce:
                    with self._lock:
                        batch = list(self._pending.values())
                        self._pending.clear()
                    for event in batch:
                        for handler in self.handlers:
                            try:
                                handler(event)
                            except Exception:
                                pass
                    last_fire = now
            except Exception:
                pass
            time.sleep(self.interval)

    def _scan(self) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for dirpath, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS
                       and not d.startswith(".")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.extensions:
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    result[fpath] = os.path.getmtime(fpath)
                except OSError:
                    pass
        return result

    def _diff(
        self,
        old: Dict[str, float],
        new: Dict[str, float],
    ) -> List[FileEvent]:
        events: List[FileEvent] = []
        for path, mtime in new.items():
            if path not in old:
                events.append(FileEvent("created", path))
            elif old[path] != mtime:
                events.append(FileEvent("modified", path))
        for path in old:
            if path not in new:
                events.append(FileEvent("deleted", path))
        return events

    @property
    def is_running(self) -> bool:
        return self._running


class AILEXFileWatcher:
    """
    High-level watcher: auto-runs AILEX analysis when files change.
    Debounces rapid saves. Respects .gitignore-style ignore patterns.
    """

    def __init__(self, pilot: Any, root: str = ".", cooldown_s: float = 5.0):
        self.pilot     = pilot
        self.root      = root
        self.cooldown  = cooldown_s
        self._last_run = 0.0
        self._watcher  = FileWatcher(root)
        self._watcher.on(self._on_change)

    def start(self) -> None:
        self._watcher.start()
        print(f"[AILEX Watcher] Watching {self.root} — auto-analysis on change")

    def stop(self) -> None:
        self._watcher.stop()

    def _on_change(self, event: FileEvent) -> None:
        now = time.time()
        if now - self._last_run < self.cooldown:
            return
        self._last_run = now
        rel = os.path.relpath(event.path, self.root)
        print(f"\n[AILEX Watcher] {event.kind}: {rel}")
        try:
            result = self.pilot.process(
                f"A file was {event.kind}: {rel}. "
                f"Briefly analyse if this change needs attention (bugs, security, tests).",
                include_context=False,
                run_code=False,
                fmt="concise",
            )
            report = result.get("report", "")
            if report and "no critical" not in report.lower():
                print(f"  AILEX: {report[:200]}")
        except Exception:
            pass
