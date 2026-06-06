"""Pydantic models shared across tasks and services."""

from __future__ import annotations

import re
from pydantic import BaseModel, Field, model_validator


class SongInput(BaseModel):
    song_title: str = Field(..., min_length=1, description="Desired song / project title")
    lyrics: str = Field(
        default="",
        description="有歌詞模式：貼入 Mureka 歌詞區；純音樂：可為器樂描述或留空",
    )
    style_tags: str = Field(
        ...,
        min_length=1,
        description="Style / tags description for generation (e.g. energetic pop male vocal)",
    )
    vocal: str | None = Field(
        default=None,
        description="Notion「人聲」選項原文；與 instrumental 一併用於判斷模式",
    )
    instrumental: bool = Field(
        default=False,
        description="True：純音樂，不填 Mureka 歌詞主欄，可填器樂描述欄",
    )
    extra_notion_props: dict | None = Field(
        default=None,
        description="Optional custom Notion properties to be written on creation",
    )

    @model_validator(mode="after")
    def _lyrics_required_when_vocal_track(self) -> SongInput:
        if not self.instrumental and not (self.lyrics or "").strip():
            raise ValueError("非純音樂曲目需要非空歌詞")
        return self

    @model_validator(mode="after")
    def _extract_cues_to_style(self) -> SongInput:
        if not self.lyrics:
            return self
            
        extracted_cues = []
        new_lyrics_lines = []
        current_section = 'vocal_block' # Default if no tag
        
        for line in self.lyrics.split('\n'):
            line_stripped = line.strip()
            if not line_stripped:
                new_lyrics_lines.append(line)
                continue
                
            # Remove timestamp prefix like [0:00] or [00:00.00] to analyze the actual text
            text_without_ts = re.sub(r'^\[\d+:\d+(?:\.\d+)?\]\s*', '', line_stripped).strip()
            
            # Check if it's a section header like [Intro], [Verse 1]
            sec_match = re.match(r'^\[(.*?)\]$', text_without_ts)
            if sec_match:
                section_name = sec_match.group(1).lower()
                if any(k in section_name for k in ['intro', 'outro', 'instrumental', 'solo', 'interlude', 'music']):
                    current_section = 'instrumental_block'
                else:
                    current_section = 'vocal_block'
                new_lyrics_lines.append(line) # Keep the structural tag
                continue
                
            # If we are in an instrumental block, treat text as a cue
            if current_section == 'instrumental_block' and text_without_ts:
                extracted_cues.append(text_without_ts)
                continue # Do not add to new_lyrics_lines
                
            # Otherwise, keep the lyric line
            new_lyrics_lines.append(line)
            
        if extracted_cues:
            added_style = ", ".join(extracted_cues)
            self.style_tags = f"{self.style_tags}, {added_style}" if self.style_tags else added_style
            self.lyrics = '\n'.join(new_lyrics_lines)
            
        return self


class NotionPendingSong(BaseModel):
    """One database row from Notion: existing page to update after Mureka run."""

    notion_page_id: str = Field(..., min_length=1)
    song: SongInput


class SongResult(BaseModel):
    success: bool
    song_title: str | None = None
    result_url: str | None = None
    status: str | None = None
    error_message: str | None = None
    screenshot_path: str | None = None
    debug_notes: str | None = None
    used_profile_path: str | None = None
    login_reused: bool = False
    notion_page_id: str | None = None
    download_path: str | None = Field(
        default=None,
        description="Local file path when auto-download is enabled and successful",
    )
