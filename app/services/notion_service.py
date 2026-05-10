"""
Notion database sync for Mureka runs (e.g. database titled 「perplixity 金曲設計」 in Notion).

Property names come from env and must match the database schema exactly.
Supports Notion native Status columns (NOTION_PROP_STATUS_KIND=status) and date / URL / checkbox / rich_text.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from notion_client import APIResponseError, Client

from app.config import AppSettings
from app.logger import get_logger
from app.schemas import NotionPendingSong, SongInput, SongResult

logger = get_logger(__name__)

_NOTION_TEXT_MAX = 2000


def notion_sync_enabled(settings: AppSettings) -> bool:
    return bool(settings.notion_token and settings.notion_database_id)


def _clip(text: str) -> str:
    if len(text) <= _NOTION_TEXT_MAX:
        return text
    return text[: _NOTION_TEXT_MAX - 1] + "…"


def _title_value(content: str) -> dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": _clip(content or "")}}]}


def _rich_text_value(content: str) -> dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": _clip(content or "")}}]}


def _url_value(url: str | None) -> dict[str, Any]:
    return {"url": url if (url and url.strip()) else None}


def _checkbox_value(value: bool) -> dict[str, Any]:
    return {"checkbox": bool(value)}


def _notion_status_value(option_name: str) -> dict[str, Any]:
    """Notion API Status property (must match an existing option name in the database)."""
    return {"status": {"name": option_name}}


def _date_now_utc_value() -> dict[str, Any]:
    dt = datetime.now(timezone.utc)
    start = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"date": {"start": start}}


def _build_create_properties(settings: AppSettings, song_input: SongInput) -> dict[str, Any]:
    f = settings.notion_fields
    ns = settings.notion_status
    props: dict[str, Any] = {f.title_property: _title_value(song_input.song_title)}
    if f.lyrics_property:
        props[f.lyrics_property] = _rich_text_value(song_input.lyrics)
    if f.style_property:
        props[f.style_property] = _rich_text_value(song_input.style_tags)
    if f.status_property:
        if ns.use_notion_status_type:
            props[f.status_property] = _notion_status_value(ns.value_running)
        else:
            props[f.status_property] = _rich_text_value("進行中")
    if f.vocal_property and song_input.vocal:
        props[f.vocal_property] = {"select": {"name": song_input.vocal}}
    if f.generated_at_property:
        props[f.generated_at_property] = _date_now_utc_value()
        
    if song_input.extra_notion_props:
        props.update(song_input.extra_notion_props)
        
    return props


async def create_page_async(settings: AppSettings, song_input: SongInput) -> str:
    """Create a new row in Notion and return its page_id."""
    import asyncio
    return await asyncio.to_thread(_create_page_sync, settings, song_input)


def _build_update_properties(settings: AppSettings, result: SongResult) -> dict[str, Any]:
    f = settings.notion_fields
    ns = settings.notion_status

    if settings.dry_run:
        props: dict[str, Any] = {}
        if f.error_property and result.error_message:
            props[f.error_property] = _rich_text_value(result.error_message)
        if f.notes_property and result.debug_notes:
            props[f.notes_property] = _rich_text_value(result.debug_notes)
        return props

    props: dict[str, Any] = {}
    if f.result_url_property:
        props[f.result_url_property] = _url_value(result.result_url)
    if f.status_property:
        if ns.use_notion_status_type:
            name = ns.value_done if result.success else ns.value_failed
            props[f.status_property] = _notion_status_value(name)
        else:
            text = result.status or ("完成" if result.success else "失敗")
            props[f.status_property] = _rich_text_value(text)
    if f.error_property and result.error_message:
        props[f.error_property] = _rich_text_value(result.error_message)
    if f.notes_property and result.debug_notes:
        props[f.notes_property] = _rich_text_value(result.debug_notes)
    if f.success_property:
        props[f.success_property] = _checkbox_value(result.success)
    if f.generated_at_property:
        props[f.generated_at_property] = _date_now_utc_value()
    return props


def _create_page_sync(settings: AppSettings, song_input: SongInput) -> str:
    assert settings.notion_token and settings.notion_database_id
    client = Client(auth=settings.notion_token, notion_version="2022-06-28")
    body = client.pages.create(
        parent={"database_id": settings.notion_database_id},
        properties=_build_create_properties(settings, song_input),
    )
    page_id = str(body.get("id", ""))
    if not page_id:
        raise RuntimeError("Notion create returned no page id")
    logger.info("Notion page created: %s", page_id)
    return page_id


def _update_page_sync(settings: AppSettings, page_id: str, result: SongResult) -> None:
    assert settings.notion_token
    client = Client(auth=settings.notion_token, notion_version="2022-06-28")
    props = _build_update_properties(settings, result)
    if not props:
        logger.info("Notion update skipped (no NOTION_PROP_* mapped for result fields)")
        return
    client.pages.update(page_id, properties=props)
    logger.info("Notion page updated: %s", page_id)

def _update_page_properties_sync(settings: AppSettings, page_id: str, props: dict[str, Any]) -> None:
    assert settings.notion_token
    from notion_client import Client
    client = Client(auth=settings.notion_token, notion_version="2022-06-28")
    client.pages.update(page_id, properties=props)
    logger.info("Notion page properties updated: %s", page_id)

async def update_page_properties_async(settings: AppSettings, page_id: str, props: dict[str, Any]) -> None:
    """Update arbitrary properties on an existing Notion page."""
    import asyncio
    await asyncio.to_thread(_update_page_properties_sync, settings, page_id, props)


def _extract_select_name(props: dict[str, Any], prop_name: str | None) -> str | None:
    if not prop_name:
        return None
    block = props.get(prop_name) or {}
    sel = block.get("select")
    if not sel or not isinstance(sel, dict):
        return None
    name = sel.get("name")
    return str(name).strip() if name is not None else None


def _join_plain_segments(segments: list[dict[str, Any]] | None) -> str:
    if not segments:
        return ""
    parts: list[str] = []
    for seg in segments:
        if seg.get("type") == "text":
            t = seg.get("text") or {}
            parts.append(str(t.get("content", "") or ""))
        else:
            parts.append(str(seg.get("plain_text", "") or ""))
    return "".join(parts).strip()


def _parse_page_to_pending(settings: AppSettings, page: dict[str, Any]) -> NotionPendingSong | None:
    pid = page.get("id")
    if not pid:
        return None
    props = page.get("properties") or {}
    f = settings.notion_fields
    title_prop = props.get(f.title_property) or {}
    song_title = _join_plain_segments(title_prop.get("title"))
    vocal_name = _extract_select_name(props, f.vocal_property)
    label = settings.notion_instrumental_vocal_label
    instrumental = (vocal_name or "").strip() == label.strip()
    lyrics = ""
    if f.lyrics_property:
        rp = props.get(f.lyrics_property) or {}
        lyrics = _join_plain_segments(rp.get("rich_text"))
    style = ""
    if f.style_property:
        sp = props.get(f.style_property) or {}
        style = _join_plain_segments(sp.get("rich_text"))
    if not song_title:
        logger.warning("略過 Notion 列 %s：歌名空白", pid)
        return None
    if not instrumental and not lyrics:
        logger.warning(
            "略過 Notion 列 %s（%s）：有歌詞曲目但「歌詞」欄空白（人聲=%s）",
            pid,
            song_title,
            vocal_name or "（未設定 NOTION_PROP_VOCAL）",
        )
        return None
    if not style:
        from app.services.style_generator import generate_style_tags

        style = generate_style_tags(
            title=song_title,
            lyrics=lyrics,
            vocal=vocal_name,
            instrumental=instrumental,
        )
        
    # 幫 Mureka 標題加上日期與名字：例如 "20260506 張嘉豪 城市的光"
    from datetime import datetime
    today_str = datetime.now().strftime("%Y%m%d")
    mureka_title = song_title
    if "張嘉豪" not in mureka_title:
        mureka_title = f"{today_str} 張嘉豪 {song_title}"

    try:
        return NotionPendingSong(
            notion_page_id=str(pid),
            song=SongInput(
                song_title=mureka_title,
                lyrics=lyrics,
                style_tags=style,
                vocal=vocal_name,
                instrumental=instrumental,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("略過 Notion 列 %s：欄位無法組成 SongInput（%s）", pid, exc)
        return None


def _first_data_source_id(database: dict[str, Any]) -> str | None:
    for item in database.get("data_sources") or []:
        if isinstance(item, dict) and item.get("id"):
            return str(item["id"])
        if isinstance(item, str):
            return item
    return None


def _query_unpublished_sync(settings: AppSettings) -> list[NotionPendingSong]:
    assert settings.notion_token and settings.notion_database_id
    chk = settings.notion_fields.success_property
    if not chk:
        raise ValueError(
            "從 Notion 讀取待生成列需要設定 NOTION_PROP_SUCCESS（例如：是否發佈）"
        )
    client = Client(auth=settings.notion_token, notion_version="2022-06-28")
    db_meta = client.databases.retrieve(settings.notion_database_id)
    data_source_id = _first_data_source_id(db_meta)

    out: list[NotionPendingSong] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {
            "filter": {"property": chk, "checkbox": {"equals": False}},
            "sorts": [{"timestamp": "created_time", "direction": "ascending"}],
            "page_size": 100,
        }
        if cursor:
            body["start_cursor"] = cursor

        if data_source_id:
            resp = client.data_sources.query(data_source_id, **body)
        else:
            resp = client.request(
                path=f"databases/{settings.notion_database_id}/query",
                method="POST",
                body=body,
            )
        for page in resp.get("results", []):
            parsed = _parse_page_to_pending(settings, page)
            if parsed:
                out.append(parsed)
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return out


async def fetch_unpublished_songs(settings: AppSettings) -> list[NotionPendingSong]:
    if not notion_sync_enabled(settings):
        raise ValueError("需要 NOTION_TOKEN 與 NOTION_DATABASE_ID 才能使用 Notion 待生成佇列")
    try:
        return await asyncio.to_thread(_query_unpublished_sync, settings)
    except APIResponseError as exc:
        logger.error("Notion 查詢失敗: %s", exc)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Notion 查詢失敗: %s", exc)
        raise


async def create_song_record(settings: AppSettings, song_input: SongInput) -> str | None:
    if not notion_sync_enabled(settings):
        return None
    try:
        return await asyncio.to_thread(_create_page_sync, settings, song_input)
    except APIResponseError as exc:
        logger.warning("Notion API error on create: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notion create failed: %s", exc)
        return None


async def update_song_result(
    settings: AppSettings,
    notion_page_id: str | None,
    result: SongResult,
) -> None:
    if not notion_page_id or not settings.notion_token:
        return
    try:
        await asyncio.to_thread(_update_page_sync, settings, notion_page_id, result)
    except APIResponseError as exc:
        logger.warning("Notion API error on update: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notion update failed: %s", exc)
