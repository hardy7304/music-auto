"""Schema validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import SongInput, SongResult


def test_song_input_valid() -> None:
    data = SongInput(
        song_title="T",
        lyrics="L",
        style_tags="pop",
    )
    assert data.song_title == "T"


def test_song_input_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        SongInput(song_title="", lyrics="x", style_tags="y")


def test_song_result_optional_fields() -> None:
    r = SongResult(success=False, error_message="boom")
    assert r.result_url is None
    assert r.screenshot_path is None
    assert r.login_reused is False
    assert r.model_dump()["success"] is False
