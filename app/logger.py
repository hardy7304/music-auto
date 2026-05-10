"""Centralized logging for the music-auto application."""

from __future__ import annotations

import logging
import sys


def reconfigure_stdio_utf8() -> None:
    """Avoid UnicodeEncodeError on Windows (e.g. cp950) when logs contain emoji."""
    for stream in (sys.stdout, sys.stderr):
        try:
            reconfigure = getattr(stream, "reconfigure", None)
            if callable(reconfigure):
                reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging once (idempotent safe to call multiple times)."""
    reconfigure_stdio_utf8()
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger (call setup_logging early in main)."""
    return logging.getLogger(name)
