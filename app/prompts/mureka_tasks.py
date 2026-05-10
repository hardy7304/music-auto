"""Mureka browser-use task strings: no raw URLs (avoids Agent auto-navigate from task text)."""

from __future__ import annotations

import json

from app.config import MurekaModelMode
from app.schemas import SongInput

# Shared constraints for every agent task (CDP: page is already correct; no URL auto-open).
_PAGE_ONLY_RULES = """
Inspect the CURRENT page only.
Do NOT navigate.
Do NOT open a new tab.
Do NOT go to homepage.
""".strip()


def task_detect_login_wall() -> str:
    return f"""
{_PAGE_ONLY_RULES}

You are on the music product site (already loaded). Determine if the user is blocked by a LOGIN or
SIGN-UP funnel. Set shows_login_wall=true if the PRIMARY visible actions are clearly for unauthenticated
visitors, including (examples, match close variants):
- "Try free now"
- "Sign in" / "Log in"
- "Continue with Google"
- "Get started" when it clearly leads to authentication

Do NOT click anything. Do NOT type. Do NOT start OAuth.

If the workspace already looks like music creation (e.g. Lyrics field, Style field, Generate /
Generate Lyrics, Custom mode, sidebar entry for creating music), set shows_login_wall=false even if a
small account menu exists.

Return structured output: shows_login_wall (bool) and details (short text of what you saw).
""".strip()


def task_verify_create_music_page() -> str:
    return f"""
{_PAGE_ONLY_RULES}

Decide if this is the Create Music / Custom composition workspace for this product.

Use multiple weak signals (several should match):
- Sidebar or nav mentions creating music or equivalent
- Visible Lyrics / prompt text area for composition
- Style / tags / genre / vocal controls
- A primary "Generate", "Generate Lyrics", "Create", or similar generation button for music

Do NOT click Sign in, Try free now, Continue with Google, or any OAuth/login CTA.

Return structured output:
- is_create_music_page (bool)
- rationale (short)
- observed_signals (bullet-like text of what matched or what is missing)
""".strip()


def _model_mode_instructions(mode: MurekaModelMode) -> str:
    """Mureka 創作頁上的生成模型／版本選項（V9、O2 等）— 由 LLM 依實際 UI 操作。"""
    if mode == "v9":
        return """
2) MODEL: Find controls that choose the music generation model, engine, or version (tabs, pills,
   dropdowns, or toggles—labels may include "V9", "v9", "O2", "o2", or similar).
   Select ONLY V9 (or the closest equivalent). Do NOT enable O2 for this run.
""".strip()
    if mode == "o2":
        return """
2) MODEL: Find controls that choose the music generation model, engine, or version (tabs, pills,
   dropdowns, or toggles—labels may include "V9", "v9", "O2", "o2", or similar).
   Select ONLY O2 (or the closest equivalent). Do NOT enable V9 for this run.
""".strip()
    return """
2) MODEL: Find controls that choose the music generation model, engine, or version (tabs, pills,
   dropdowns, toggles, or checkboxes—labels may include "V9", "v9", "O2", "o2", or similar).
   Enable BOTH V9 and O2 for this single generation if the UI allows (dual toggles, multi-select,
   or an explicit combined / dual-model option).
   If the UI only allows ONE active model at a time, select O2 and proceed (one model per click).
""".strip()


def extend_system_fill_vocal() -> str:
    """Appended to Agent extend_system_message for 有歌詞填表。"""
    return (
        "TRACK MODE — VOCALS (有歌詞): You MUST paste the task's lyrics JSON into the main "
        "Lyrics / singable vocal prompt field. Do not treat this run as instrumental; do not leave "
        "that lyrics field empty unless the JSON is literally empty."
    )


def extend_system_fill_instrumental() -> str:
    """Appended to Agent extend_system_message for 純音樂填表。"""
    return (
        "TRACK MODE — INSTRUMENTAL (純音樂): Do NOT type singable song lyrics, verses, choruses, "
        "or line-by-line vocal text into any field meant for sung lyrics. Keep that lyrics-for-vocals "
        "area empty or clear it. Use only style / mood / instrumental description fields for non-vocal intent."
    )


def task_fill_form(song_input: SongInput, *, model_mode: MurekaModelMode) -> str:
    title_j = json.dumps(song_input.song_title, ensure_ascii=False)
    lyrics_j = json.dumps(song_input.lyrics, ensure_ascii=False)
    tags_j = json.dumps(song_input.style_tags, ensure_ascii=False)

    model_block = _model_mode_instructions(model_mode)
    return f"""
{_PAGE_ONLY_RULES}

You are on the music creation page in VOCAL / 有歌詞 mode (lyrics for singing).

1) Dismiss cookie banners, modals, or overlays that block inputs. Do NOT click Sign in, Try free now,
   Continue with Google, or any login/OAuth control.

2) MODE: Ensure "Custom" (or "自定義") mode is selected among the tabs (Easy, Custom, Soundtrack).
   If not selected, click it first.

{model_block}
3) If there is a song title / project name field, set it from this JSON string (paste raw text only):
{title_j}
4) Fill the main Lyrics / vocal prompt area (meant for singable lyrics) from this JSON — paste the
   full text as given, preserving line breaks:
{lyrics_j}
5) Apply Style / tags / description controls from:
{tags_j}

Do NOT use instrumental-only workflow. Do NOT skip the lyrics field if the JSON above is non-empty.

Do NOT click Generate / Create yet.

Finish when the fields show the intended content.
""".strip()


def task_fill_form_instrumental(song_input: SongInput, *, model_mode: MurekaModelMode) -> str:
    """純音樂：勿填可演唱歌詞主欄；歌詞欄位資料僅作器樂描述（可空）。"""
    title_j = json.dumps(song_input.song_title, ensure_ascii=False)
    tags_j = json.dumps(song_input.style_tags, ensure_ascii=False)
    desc_j = json.dumps(song_input.lyrics, ensure_ascii=False)

    model_block = _model_mode_instructions(model_mode)
    return f"""
{_PAGE_ONLY_RULES}

You are on the music creation page in INSTRUMENTAL / 純音樂 mode (no singable lyrics).

1) Dismiss cookie banners, modals, or overlays that block inputs. Do NOT click Sign in, Try free now,
   Continue with Google, or any login/OAuth control.

2) MODE: Ensure "Custom" (or "自定義") mode is selected among the tabs (Easy, Custom, Soundtrack).
   If not selected, click it first.

{model_block}

3) If there is a song title / project name field, set it from this JSON string (paste raw text only):
{title_j}

4) CRITICAL — No vocal lyrics: Do NOT type, paste, or generate singable verse/chorus/stanza text into
   the main "Lyrics" / singable lyric / vocal prompt area (the box meant for full songs to be sung).
   That field must stay EMPTY or be cleared. Do not fill it with the JSON in step 5 if that text
   looks like song lyrics—use only non-vocal fields (style, mood, instrumental description).

5) The following JSON is for INSTRUMENTAL mood / scene / BGM description ONLY (or leave empty). Paste it
   ONLY into a field explicitly for instrumental / mood / non-vocal description—not into the primary
   lyrics-for-singing box. If the string is empty, skip:
{desc_j}

6) Apply Style / tags / description controls from:
{tags_j}

Do NOT click Generate / Create yet.

Finish when title and style match; the singable-lyrics field must remain empty and must not contain
verse-like text.
""".strip()


def task_submit_generation_dry_run() -> str:
    return f"""
{_PAGE_ONLY_RULES}

DRY_RUN=true: the form should already be filled.

Do NOT click Generate, Create, or any control that starts generation.

You may dismiss non-login overlays only. Do NOT use Sign in / Try free now / Continue with Google.

Finish immediately.
""".strip()


def task_submit_generation_click() -> str:
    return f"""
{_PAGE_ONLY_RULES}

DRY_RUN=false: the music creation form is filled.

Click the PRIMARY control that starts music generation (prefer labels like Generate, Generate Lyrics,
Create song). If several exist, pick the one that clearly starts the full generation flow.

Do NOT click Sign in, Try free now, Continue with Google, or Log in.

If you cannot find any plausible Generate control after inspecting the visible UI, finish WITHOUT clicking
and set structured output found_and_clicked_generate=false with explanation.

If you clicked successfully, set found_and_clicked_generate=true.

Return structured JSON per schema: found_and_clicked_generate (bool), explanation (str).
""".strip()


def task_wait_generation_settle() -> str:
    return f"""
{_PAGE_ONLY_RULES}

After generation has started, wait until the UI settles: no busy spinner, or success/playback visible,
or a clear error.

Do NOT log in or use OAuth. Do not leave this view without strong reason.

Finish when status can be read from the page.
""".strip()


def task_extract_page() -> str:
    return f"""
{_PAGE_ONLY_RULES}

Return structured data:
- result_url: full URL from the address bar (read from the browser chrome only; do not type a URL)
- song_title: best visible song or project title (or empty string)
- status: concise UI state (generating, complete, dry run, error, etc.)

Do not use login/OAuth actions. Use structured output / done JSON per system rules.
""".strip()
