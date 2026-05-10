"""CLI entrypoint: sample run with JSON output."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.logger import get_logger, reconfigure_stdio_utf8, setup_logging

reconfigure_stdio_utf8()

import argparse
import asyncio
import json
from typing import cast

from app.config import (
    AppSettings,
    AutomationEngine,
    ConfigurationError,
    MurekaModelMode,
    load_settings,
)
from app.schemas import NotionPendingSong, SongInput
from app.services import notion_service
from app.services import sheet_service
from app.tasks.run_song_generation import run_song_generation

logger = get_logger(__name__)


def _default_song_input() -> SongInput:
    """僅供手動測試（未使用 --from-notion 時）。"""
    return SongInput(
        song_title="Test Song",
        lyrics="This is a test lyric...\nLine two for the demo.",
        style_tags="energetic pop male vocal",
    )


def _cli_mureka_model_mode(value: str) -> MurekaModelMode:
    v = value.strip().lower()
    if v in ("v9", "o2", "both"):
        return cast(MurekaModelMode, v)
    raise argparse.ArgumentTypeError("expected v9, o2, or both")


def _cli_notion_parallel_max(value: str) -> int:
    try:
        n = int(value.strip(), 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected integer 1-10, got {value!r}") from exc
    if 1 <= n <= 10:
        return n
    raise argparse.ArgumentTypeError("notion parallel max must be between 1 and 10")


def _cli_non_negative_int(value: str) -> int:
    try:
        n = int(value.strip(), 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected non-negative integer, got {value!r}") from exc
    if n < 0:
        raise argparse.ArgumentTypeError("expected non-negative integer")
    return n


def _cli_bool(value: str) -> bool:
    v = value.strip().lower()
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {value!r}")


def _cli_automation_engine(value: str) -> AutomationEngine:
    v = value.strip().lower()
    if v in ("playwright", "browser_use", "auto"):
        return cast(AutomationEngine, v)
    raise argparse.ArgumentTypeError("expected playwright, browser_use, or auto")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mureka auto-generation via Playwright/browser-use")
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Optional path to a .env file",
    )
    parser.add_argument(
        "--attach-open-page",
        action="store_true",
        help="Attach via CDP to your open Chrome; run fill/generate on Mureka Create Music page",
    )
    parser.add_argument(
        "--from-notion",
        action="store_true",
        help="讀取 Notion「是否發佈」未勾選的列，依序帶入 Mureka 並回寫同一筆（推薦正式流程）",
    )
    parser.add_argument(
        "--from-sheet",
        action="store_true",
        help="讀取 Google Sheet「是否發佈=FALSE」的列，依序帶入 Mureka 並回寫結果（Notion 已滿時使用）",
    )
    parser.add_argument(
        "--dry-run",
        type=_cli_bool,
        default=None,
        metavar="BOOL",
        help="Override DRY_RUN from .env (true or false)",
    )
    parser.add_argument("--song-title", type=str, default=None)
    parser.add_argument("--lyrics", type=str, default=None)
    parser.add_argument("--style-tags", type=str, default=None)
    parser.add_argument(
        "--instrumental",
        action="store_true",
        help="純音樂模式：不填 Mureka 可演唱歌詞主欄；可搭配 --lyrics 作器樂／氛圍描述",
    )
    parser.add_argument(
        "--mureka-model-mode",
        type=_cli_mureka_model_mode,
        default=None,
        metavar="MODE",
        help="覆寫 MUREKA_MODEL_MODE：v9 | o2 | both（both=介面允許時同開 V9+O2）",
    )
    parser.add_argument(
        "--notion-parallel-max",
        type=_cli_notion_parallel_max,
        default=None,
        metavar="N",
        help="覆寫 NOTION_PARALLEL_MAX（1–10）：>1 時需多個 Mureka 分頁同時併跑",
    )
    parser.add_argument(
        "--notion-limit",
        type=_cli_non_negative_int,
        default=None,
        metavar="N",
        help="只處理前 N 筆 Notion 待生成列；0 或未指定代表不限制。建議測試先用 1。",
    )
    parser.add_argument(
        "--automation-engine",
        type=_cli_automation_engine,
        default=None,
        metavar="ENGINE",
        help="覆寫 AUTOMATION_ENGINE：playwright | browser_use | auto",
    )
    parser.add_argument(
        "--browser-use-fallback",
        type=_cli_bool,
        default=None,
        metavar="BOOL",
        help="Playwright 失敗時是否改用 browser-use（會消耗 LLM token）",
    )
    return parser.parse_args()


def _apply_settings_overrides(settings: AppSettings, args: argparse.Namespace) -> AppSettings:
    s = settings
    if args.dry_run is not None:
        s = replace(s, dry_run=args.dry_run)
    if args.mureka_model_mode is not None:
        s = replace(s, mureka_model_mode=args.mureka_model_mode)
    if args.notion_parallel_max is not None:
        s = replace(s, notion_parallel_max=args.notion_parallel_max)
    if args.notion_limit is not None:
        s = replace(s, notion_run_limit=args.notion_limit)
    if args.automation_engine is not None:
        s = replace(s, automation_engine=args.automation_engine)
    if args.browser_use_fallback is not None:
        s = replace(s, browser_use_fallback=args.browser_use_fallback)
    return s


def _validate_runtime_settings(settings: AppSettings) -> str | None:
    needs_llm = settings.automation_engine in ("browser_use", "auto") or settings.browser_use_fallback
    if not needs_llm:
        return None
    if settings.llm_provider == "google" and not settings.gemini_api_key:
        return "GEMINI_API_KEY is required when browser-use or fallback is enabled."
    if settings.llm_provider == "groq" and not settings.groq_api_key:
        return "GROQ_API_KEY is required when browser-use or fallback is enabled with LLM_PROVIDER=groq."
    if settings.llm_provider == "openrouter" and not settings.openrouter_api_key:
        return "OPENROUTER_API_KEY is required when browser-use or fallback is enabled with LLM_PROVIDER=openrouter."
    if settings.llm_provider == "nvidia" and not settings.nvidia_api_key:
        return "NVIDIA_API_KEY is required when browser-use or fallback is enabled with LLM_PROVIDER=nvidia."
    if settings.llm_provider == "deepseek" and not settings.deepseek_api_key:
        return "DEEPSEEK_API_KEY is required when browser-use or fallback is enabled with LLM_PROVIDER=deepseek."
    if settings.llm_provider == "auto" and (
        not settings.groq_api_key or not settings.openrouter_api_key
    ):
        return "GROQ_API_KEY and OPENROUTER_API_KEY are required when browser-use/fallback uses LLM_PROVIDER=auto."
    return None


async def _auto_launch_chrome(settings: AppSettings) -> bool:
    """Kill existing Chrome and start with --remote-debugging-port using a dedicated profile."""
    import subprocess
    import os

    exe = settings.chrome_exe_path
    if not os.path.isfile(exe):
        logger.error("Chrome 不存在：%s。請設定 CHROME_EXE_PATH。", exe)
        return False

    logger.info("自動啟動 Chrome（關閉現有程序）...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                   capture_output=True, timeout=10)
    await asyncio.sleep(3)

    user_data_dir = settings.chrome_user_data_dir
    args = [
        exe,
        f"--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--restore-last-session",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    logger.info("啟動 Chrome：%s", " ".join(args[:3]))
    subprocess.Popen(args, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    await asyncio.sleep(5)

    from app.utils.cdp_targets import check_chrome_debugger_async
    try:
        info = await check_chrome_debugger_async(settings.browser_cdp_url, timeout_sec=5)
        logger.info(
            "Chrome 自動啟動成功：%s（profile=%s）",
            info.get("Browser", "?"),
            user_data_dir,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Chrome 自動啟動後仍無法連線：%s", exc)
        return False


async def _preflight_cdp(settings: AppSettings) -> bool:
    from app.utils.cdp_targets import check_chrome_debugger_async

    try:
        info = await check_chrome_debugger_async(settings.browser_cdp_url)
    except Exception:  # noqa: BLE001
        if settings.auto_launch_chrome:
            logger.warning(
                "Chrome CDP 連線失敗，嘗試自動啟動 Chrome（AUTO_LAUNCH_CHROME=true）..."
            )
            return await _auto_launch_chrome(settings)
        logger.error(
            "Chrome CDP 連線失敗。請先用 --remote-debugging-port=9222 啟動 Chrome，"
            "並確認 BROWSER_CDP_URL=%s。"
            "\n提示：執行 start_chrome_debug.bat 或設定 AUTO_LAUNCH_CHROME=true 讓程式自動啟動。",
            settings.browser_cdp_url,
        )
        return False
    logger.info(
        "Chrome CDP ready: %s",
        info.get("Browser") or info.get("User-Agent") or settings.browser_cdp_url,
    )
    return True


async def _run_notion_queue_sequential(
    settings: AppSettings,
    pending: list[NotionPendingSong],
) -> tuple[list[dict], bool]:
    results: list[dict] = []
    all_ok = True
    for i, row in enumerate(pending, start=1):
        logger.info(
            "[%s/%s] Notion → Mureka：%r (page=%s, instrumental=%s)",
            i,
            len(pending),
            row.song.song_title,
            row.notion_page_id,
            row.song.instrumental,
        )
        result = await run_song_generation(
            settings,
            row.song,
            attach_open_page=True,
            existing_notion_page_id=row.notion_page_id,
        )
        results.append(result.model_dump(mode="json"))
        if not result.success:
            all_ok = False

        # Fast Queueing Mode Burst Limit (8 songs)
        if i % 8 == 0 and i < len(pending):
            logger.info("已連續送出 8 首，為避免排隊塞車，暫停 3 分鐘讓伺服器消化...")
            await asyncio.sleep(180)

    return results, all_ok


async def _run_sheet_queue_sequential(
    settings: AppSettings,
    pending: list,
) -> tuple[list[dict], bool]:
    """從 Google Sheet 讀取列 → Mureka 生成 → 回寫 Sheet 結果（不碰 Notion）。"""
    from app.services.sheet_service import update_song_result_in_sheet

    results: list[dict] = []
    all_ok = True
    for i, row in enumerate(pending, start=1):
        logger.info(
            "[%s/%s] Sheet 第 %s 列 → Mureka：%r (instrumental=%s)",
            i,
            len(pending),
            row.row_index,
            row.song.song_title,
            row.song.instrumental,
        )
        # existing_notion_page_id=None, skip_notion=True → 完全不碰 Notion
        result = await run_song_generation(
            settings,
            row.song,
            attach_open_page=True,
            existing_notion_page_id=None,
            skip_notion=True,
        )
        # 回寫 Sheet
        try:
            await update_song_result_in_sheet(settings, row.row_index, result)
        except Exception as exc:
            logger.warning("Sheet 回寫失敗（第 %s 列）：%s", row.row_index, exc)

        results.append(result.model_dump(mode="json"))
        if not result.success:
            all_ok = False

        # Burst limit
        if i % 8 == 0 and i < len(pending):
            logger.info("已連續送出 8 首，暫停 3 分鐘...")
            await asyncio.sleep(180)

    return results, all_ok


async def _run_notion_queue(
    settings: AppSettings,
    pending: list[NotionPendingSong],
) -> tuple[list[dict], bool]:
    from app.utils.cdp_targets import list_page_target_ids_matching_url_async

    want = max(1, min(settings.notion_parallel_max, 10))
    if want <= 1 or len(pending) <= 1:
        return await _run_notion_queue_sequential(settings, pending)

    try:
        target_ids = await list_page_target_ids_matching_url_async(
            settings.browser_cdp_url,
            url_substrings=("mureka",),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("列舉 Chrome 分頁失敗（改為串行）：%s", exc)
        return await _run_notion_queue_sequential(settings, pending)

    eff = min(want, len(target_ids), len(pending))
    if eff < want:
        logger.warning(
            "NOTION_PARALLEL_MAX=%s 但偵測到 %s 個 URL 含 mureka 的分頁，本輪並行度調整為 %s",
            settings.notion_parallel_max,
            len(target_ids),
            eff,
        )
    if eff < 2:
        if want >= 2 and not target_ids:
            logger.warning(
                "未偵測到 Mureka 分頁：請預先開啟多個 Create Music 分頁，或將 NOTION_PARALLEL_MAX 設為 1"
            )
        return await _run_notion_queue_sequential(settings, pending)

    results: list[dict] = []
    all_ok = True
    for batch_start in range(0, len(pending), eff):
        batch = pending[batch_start : batch_start + eff]
        tids = target_ids[: len(batch)]
        logger.info(
            "Notion 佇列並行：第 %s–%s 筆，使用 %s 個分頁",
            batch_start + 1,
            batch_start + len(batch),
            len(tids),
        )
        coros = [
            run_song_generation(
                settings,
                row.song,
                attach_open_page=True,
                existing_notion_page_id=row.notion_page_id,
                cdp_focus_target_id=tid,
            )
            for row, tid in zip(batch, tids, strict=True)
        ]
        batch_results = await asyncio.gather(*coros)
        for r in batch_results:
            results.append(r.model_dump(mode="json"))
            if not r.success:
                all_ok = False
    return results, all_ok


async def _async_main() -> int:
    args = _parse_args()
    setup_logging()
    try:
        settings = load_settings(env_path=args.env_file) if args.env_file else load_settings()
    except ConfigurationError as exc:
        logger.error("%s", exc)
        return 2

    settings = _apply_settings_overrides(settings, args)
    runtime_error = _validate_runtime_settings(settings)
    if runtime_error:
        logger.error("%s", runtime_error)
        return 2

    if not args.attach_open_page:
        logger.error(
            "請加上 --attach-open-page。請先用一般 Chrome 登入 Mureka 並開啟 Create Music，"
            "再以遠端偵錯連線執行本程式（見 README 的 BROWSER_CDP_URL）。"
        )
        return 2

    if not await _preflight_cdp(settings):
        return 2

    if args.from_notion:
        try:
            pending = await notion_service.fetch_unpublished_songs(settings)
        except ValueError as exc:
            logger.error("%s", exc)
            return 2
        except Exception as exc:  # noqa: BLE001
            logger.error("讀取 Notion 失敗: %s", exc)
            return 2

        if not pending:
            logger.info("沒有「是否發佈」未勾選的列，結束。")
            print(json.dumps([], ensure_ascii=False, indent=2))
            return 0

        if settings.notion_run_limit > 0:
            original_len = len(pending)
            pending = pending[: settings.notion_run_limit]
            logger.warning(
                "NOTION_RUN_LIMIT=%s：本次只處理前 %s/%s 筆。",
                settings.notion_run_limit,
                len(pending),
                original_len,
            )

        results, all_ok = await _run_notion_queue(settings, pending)

        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0 if all_ok else 1

    if args.from_sheet:
        if not sheet_service.sheet_sync_enabled(settings):
            logger.error(
                "Google Sheet 未設定：請在 .env 填入 GOOGLE_SHEET_URL，"
                "並確認 google_key.json 存在於專案根目錄。"
            )
            return 2
        try:
            pending_sheet = await sheet_service.fetch_unpublished_songs_from_sheet_async(settings)
        except Exception as exc:
            logger.error("讀取 Google Sheet 失敗: %s", exc)
            return 2

        if not pending_sheet:
            logger.info("Google Sheet 沒有待生成的列（是否發佈=FALSE 且音樂連結空白），結束。")
            print(json.dumps([], ensure_ascii=False, indent=2))
            return 0

        if settings.notion_run_limit > 0:
            original_len = len(pending_sheet)
            pending_sheet = pending_sheet[: settings.notion_run_limit]
            logger.warning(
                "NOTION_RUN_LIMIT=%s：本次只處理前 %s/%s 筆 Sheet 列。",
                settings.notion_run_limit,
                len(pending_sheet),
                original_len,
            )

        results, all_ok = await _run_sheet_queue_sequential(settings, pending_sheet)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0 if all_ok else 1

    song = _default_song_input()
    if args.song_title:
        song = song.model_copy(update={"song_title": args.song_title})
    if args.lyrics is not None:
        song = song.model_copy(update={"lyrics": args.lyrics})
    if args.style_tags:
        song = song.model_copy(update={"style_tags": args.style_tags})
    if args.instrumental:
        inst_upd: dict = {
            "instrumental": True,
            "vocal": settings.notion_instrumental_vocal_label,
        }
        if args.lyrics is None:
            inst_upd["lyrics"] = ""
        song = song.model_copy(update=inst_upd)

    logger.info("手動測試模式：%r（若要正式流程請加 --from-notion）", song.song_title)
    result = await run_song_generation(settings, song, attach_open_page=True)

    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if result.success else 1


def main() -> None:
    raise SystemExit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
