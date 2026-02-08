"""Structured logger that can output to console and/or a GUI callback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

LogCallback = Callable[[str], None]


@dataclass
class Logger:
    """Simple logger used across GUI + automation.

    The callback is designed to be thread-safe *by design of the caller*:
    GUI should pass a callback that enqueues messages and drains them on the UI thread.
    """

    callback: Optional[LogCallback] = None
    to_console: bool = True

    def _emit(self, level: str, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        if self.to_console:
            print(line, flush=True)
        if self.callback:
            self.callback(line)

    def info(self, message: str) -> None:
        self._emit("INFO", message)

    def warn(self, message: str) -> None:
        self._emit("WARN", message)

    def error(self, message: str) -> None:
        self._emit("ERROR", message)
