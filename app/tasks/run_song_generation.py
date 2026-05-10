"""Orchestrates one end-to-end song generation run (CDP attach to open browser)."""

from __future__ import annotations

from app.config import AppSettings
from app.logger import get_logger
from app.schemas import SongInput, SongResult
from app.services.mureka_agent import MurekaAgentError, MurekaSongAgent
from app.services.mureka_playwright_agent import (
    MurekaPlaywrightAgent,
    MurekaPlaywrightError,
)
from app.services import notion_service

logger = get_logger(__name__)


def _failure_result(
    settings: AppSettings,
    song_input: SongInput,
    *,
    message: str,
    notion_page_id: str | None = None,
) -> SongResult:
    return SongResult(
        success=False,
        song_title=song_input.song_title,
        result_url=None,
        status=None,
        error_message=message,
        screenshot_path=None,
        debug_notes=None,
        used_profile_path=settings.browser_cdp_url,
        login_reused=False,
        notion_page_id=notion_page_id,
    )


async def _run_browser_use_agent(
    settings: AppSettings,
    song_input: SongInput,
    *,
    notion_page_id: str | None,
    cdp_focus_target_id: str | None,
) -> SongResult:
    agent = MurekaSongAgent(settings, cdp_focus_target_id=cdp_focus_target_id)
    try:
        await agent.attach_to_logged_in_page()
        await agent.verify_create_music_page()
        await agent.fill_form(song_input)
        await agent.submit_generation()
        return await agent.extract_result(song_input=song_input)
    except MurekaAgentError as exc:
        logger.error("Mureka browser-use agent error: %s", exc)
        return _failure_result(
            settings, song_input, message=str(exc), notion_page_id=notion_page_id
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected browser-use error during song generation")
        return _failure_result(
            settings, song_input, message=str(exc), notion_page_id=notion_page_id
        )
    finally:
        await agent.aclose()


async def _run_playwright_agent(
    settings: AppSettings,
    song_input: SongInput,
    *,
    notion_page_id: str | None,
    cdp_focus_target_id: str | None,
) -> SongResult:
    agent = MurekaPlaywrightAgent(settings, cdp_focus_target_id=cdp_focus_target_id)
    try:
        await agent.attach_to_logged_in_page()
        await agent.verify_create_music_page()
        await agent.fill_form(song_input)
        await agent.submit_generation()
        return await agent.extract_result(song_input=song_input)
    except MurekaPlaywrightError as exc:
        logger.error("Mureka Playwright agent error: %s", exc)
        return _failure_result(
            settings, song_input, message=str(exc), notion_page_id=notion_page_id
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected Playwright error during song generation")
        return _failure_result(
            settings, song_input, message=str(exc), notion_page_id=notion_page_id
        )
    finally:
        await agent.aclose()


async def run_song_generation(
    settings: AppSettings,
    song_input: SongInput,
    *,
    attach_open_page: bool,
    existing_notion_page_id: str | None = None,
    cdp_focus_target_id: str | None = None,
    skip_notion: bool = False,
) -> SongResult:
    """
    Requires ``attach_open_page=True``: connect to Chrome via ``BROWSER_CDP_URL``, open
    ``MUREKA_CREATE_URL``, verify Create Music page, fill form, optionally generate, extract.

    If ``existing_notion_page_id`` is set (Notion → Mureka 流程），不會新建資料庫列，只會在結束時更新該頁。

    ``skip_notion=True``：完全跨過 Notion（用於 Sheet 流程）。

    ``cdp_focus_target_id``：Chrome DevTools 目標 id（``/json/list`` 的 ``id``），用於多分頁並行時切到指定分頁。
    """
    if not attach_open_page:
        return _failure_result(
            settings,
            song_input,
            message="This workflow requires --attach-open-page and a Chrome instance with remote debugging.",
        )

    if existing_notion_page_id:
        notion_page_id = existing_notion_page_id
        logger.info("使用既有 Notion 列 %s（不新建）", notion_page_id)
    elif skip_notion:
        notion_page_id = None
        logger.debug("skip_notion=True：跨過 Notion 創建。")
    else:
        notion_page_id = await notion_service.create_song_record(settings, song_input)
        if notion_service.notion_sync_enabled(settings) and not notion_page_id:
            logger.warning(
                "Notion 已設定 token/database，但建立列失敗；請檢查權限與 NOTION_TITLE_PROPERTY 是否與資料庫欄位名稱一致。"
            )

    logger.info("Automation engine: %s", settings.automation_engine)
    if settings.automation_engine == "browser_use":
        result = await _run_browser_use_agent(
            settings,
            song_input,
            notion_page_id=notion_page_id,
            cdp_focus_target_id=cdp_focus_target_id,
        )
    else:
        result = await _run_playwright_agent(
            settings,
            song_input,
            notion_page_id=notion_page_id,
            cdp_focus_target_id=cdp_focus_target_id,
        )
        should_fallback = (
            not result.success
            and (settings.automation_engine == "auto" or settings.browser_use_fallback)
        )
        if should_fallback:
            logger.warning(
                "Playwright failed; falling back to browser-use. This will consume LLM tokens."
            )
            result = await _run_browser_use_agent(
                settings,
                song_input,
                notion_page_id=notion_page_id,
                cdp_focus_target_id=cdp_focus_target_id,
            )

    # 只在非 Sheet 流程時更新 Notion
    notion_update_id = notion_page_id if not skip_notion else None
    await notion_service.update_song_result(settings, notion_update_id, result)
    if notion_page_id:
        result = result.model_copy(update={"notion_page_id": notion_page_id})
    return result
