"""Project-root paths (e.g. screenshots directory)."""

from __future__ import annotations

from pathlib import Path

from app.config import AppSettings

# music-auto/ (parent of app/)
MUSIC_AUTO_ROOT = Path(__file__).resolve().parents[2]


def get_screenshots_dir(settings: AppSettings) -> Path:
    """Directory for run screenshots (created if missing), resolved under project root when relative."""
    raw = (settings.screenshots_dir or "screenshots").strip()
    p = Path(raw)
    if not p.is_absolute():
        p = MUSIC_AUTO_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()
