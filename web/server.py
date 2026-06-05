"""
本機網頁控制台：說明 + 受控執行 main.py（僅允許白名單參數，預設 127.0.0.1）。
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
# music-auto 專案根目錄（含 app/）
PROJECT_ROOT = WEB_DIR.parent
MAIN_SCRIPT = PROJECT_ROOT / "app" / "main.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from app.logger import get_logger, reconfigure_stdio_utf8

reconfigure_stdio_utf8()
logger = get_logger(__name__)

APP_VERSION = "0.6.0"

# 同一時間僅允許一個子程序（串流或整包），供「停止執行」終止。
_run_state_lock = asyncio.Lock()
_run_busy = False
_child_proc: asyncio.subprocess.Process | None = None


class RunRequest(BaseModel):
    """僅允許預設流程，避免任意指令注入。"""

    preset: Literal["from_notion", "from_sheet", "manual", "process_csv", "generate_batch", "download_library"]
    dry_run: bool | None = Field(
        default=None,
        description="覆寫 DRY_RUN：True=不點 Generate；False=會點；None=沿用 .env",
    )
    mureka_model_mode: Literal["v9", "o2", "both"] | None = Field(
        default=None,
        description="覆寫 MUREKA_MODEL_MODE；None=沿用 .env",
    )
    notion_parallel_max: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="覆寫 NOTION_PARALLEL_MAX；None=沿用 .env",
    )
    notion_limit: int | None = Field(
        default=None,
        ge=0,
        description="只處理前 N 筆 Notion 待生成列；None=沿用 .env，0=不限制",
    )
    automation_engine: Literal["playwright", "browser_use", "auto"] | None = Field(
        default=None,
        description="覆寫 AUTOMATION_ENGINE；playwright=省 token，browser_use=舊版 Agent，auto=失敗時備援",
    )
    browser_use_fallback: bool | None = Field(
        default=None,
        description="Playwright 失敗時是否改用 browser-use（會消耗 LLM token）；None=沿用 .env",
    )
    song_mode: Literal["full", "demo", "free"] | None = Field(
        default=None,
        description="歌曲結構模式：full=正式完整, demo=精簡版, free=自由發揮",
    )
    env_file: str | None = Field(
        default=None,
        description=(
            "選填：相對於專案根目錄的設定檔路徑（如 .env.cloud），會以 "
            "`python app/main.py ... --env-file <path>` 載入；用於與預設 `.env` 分開的雲端 LLM 等設定"
        ),
    )
    theme: str | None = Field(
        default="流行金曲",
        description="用於 generate_batch 模式的主題",
    )
    count: int | None = Field(
        default=1,
        description="用於 generate_batch 模式的生成數量",
    )


class RunResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    command: list[str]


def _resolve_env_file_for_cli(raw: str | None) -> str | None:
    """只允許專案根目錄下的現有檔案，避免路徑穿越。"""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    p = Path(s)
    if p.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="env_file 請使用相對於專案根目錄的路徑（勿用絕對路徑）",
        )
    if ".." in p.parts:
        raise HTTPException(status_code=400, detail="env_file 不可包含 ..")
    root = PROJECT_ROOT.resolve()
    candidate = (root / p).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="env_file 必須位於專案根目錄之下",
        ) from None
    if not candidate.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"找不到設定檔：{candidate}",
        )
    return str(candidate)


def _build_command(req: RunRequest) -> list[str]:
    if req.preset == "process_csv":
        cmd = [sys.executable, str(PROJECT_ROOT / "process_csv_ideas.py")]
        if req.song_mode:
            cmd.extend(["--mode", req.song_mode])
        return cmd

    if req.preset == "download_library":
        cmd = [sys.executable, str(MAIN_SCRIPT), "--attach-open-page", "--download-from-library"]
        if req.dry_run is not None:
            cmd.extend(["--dry-run", "true" if req.dry_run else "false"])
        return cmd

    if req.preset == "generate_batch":
        cmd = [sys.executable, str(PROJECT_ROOT / "generate_songs.py")]
        if req.theme:
            cmd.extend(["--theme", req.theme])
        if req.count is not None:
            cmd.extend(["--count", str(req.count)])
        if req.song_mode:
            cmd.extend(["--mode", req.song_mode])
        # 強制寫入 sheet
        cmd.extend(["--target", "sheet"])
        return cmd

    cmd: list[str] = [sys.executable, str(MAIN_SCRIPT), "--attach-open-page"]
    env_path = _resolve_env_file_for_cli(req.env_file)
    if env_path is not None:
        cmd.extend(["--env-file", env_path])
    if req.preset == "from_notion":
        cmd.append("--from-notion")
    elif req.preset == "from_sheet":
        cmd.append("--from-sheet")
    if req.dry_run is not None:
        cmd.extend(["--dry-run", "true" if req.dry_run else "false"])
    if req.mureka_model_mode is not None:
        cmd.extend(["--mureka-model-mode", req.mureka_model_mode])
    if req.notion_parallel_max is not None:
        cmd.extend(["--notion-parallel-max", str(req.notion_parallel_max)])
    if req.notion_limit is not None:
        cmd.extend(["--notion-limit", str(req.notion_limit)])
    if req.automation_engine is not None:
        cmd.extend(["--automation-engine", req.automation_engine])
    if req.browser_use_fallback is not None:
        cmd.extend(["--browser-use-fallback", "true" if req.browser_use_fallback else "false"])
    return cmd


def _build_command_unbuffered(req: RunRequest) -> list[str]:
    """在解譯器後插入 -u，降低管線 stdout 區塊緩衝。"""
    base = _build_command(req)
    # python -u ...
    return [base[0], "-u", *base[1:]]


async def _collect_results(gen: AsyncIterator[str]) -> list[str]:
    """Collect all items from an async generator into a list."""
    results = []
    async for item in gen:
        results.append(item)
    return results


def _sse_data(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


async def _try_acquire_run() -> None:
    global _run_busy
    async with _run_state_lock:
        if _run_busy:
            raise HTTPException(
                status_code=409,
                detail="已有執行中的工作，請先按「停止執行」或待其結束。",
            )
        _run_busy = True


async def _release_run(proc: asyncio.subprocess.Process | None) -> None:
    global _run_busy, _child_proc
    async with _run_state_lock:
        _run_busy = False
        if proc is not None and _child_proc is proc:
            _child_proc = None


async def _bind_child_proc(proc: asyncio.subprocess.Process) -> None:
    global _child_proc
    async with _run_state_lock:
        _child_proc = proc


async def _stream_subprocess(req: RunRequest) -> AsyncIterator[str]:
    try:
        await _try_acquire_run()
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "busy"
        yield _sse_data({"t": "error", "msg": detail})
        yield _sse_data({"t": "done", "code": 409})
        return

    cmd = _build_command_unbuffered(req)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc: asyncio.subprocess.Process | None = None
    try:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except Exception as exc:  # noqa: BLE001
            await _release_run(None)
            yield _sse_data({"t": "error", "msg": str(exc)})
            yield _sse_data({"t": "done", "code": -1})
            return

        await _bind_child_proc(proc)
        yield _sse_data({"t": "meta", "cmd": cmd})

        if proc.stdout:
            while True:
                chunk = await proc.stdout.read(4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                yield _sse_data({"t": "out", "s": text})
        return_code = await proc.wait()
        yield _sse_data({"t": "done", "code": return_code})
    except Exception as exc:  # noqa: BLE001
        yield _sse_data({"t": "error", "msg": str(exc)})
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
    finally:
        await _release_run(proc)


app = FastAPI(title="music-auto 控制台", version=APP_VERSION)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=500, detail="static/index.html 缺失")
    return FileResponse(index_path)


@app.get("/library")
async def library_page() -> FileResponse:
    lib_path = STATIC_DIR / "library.html"
    if not lib_path.is_file():
        raise HTTPException(status_code=500, detail="static/library.html 缺失")
    return FileResponse(lib_path)


@app.get("/api/stats")
async def get_stats():
    # downloader uses (repo_root / ".." / "downloads" / "download_history.json").resolve()
    # where repo_root is music-auto
    history_file = (PROJECT_ROOT / ".." / "downloads" / "download_history.json").resolve()
    local_count = 0
    if history_file.exists():
        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
            local_count = len(data)
        except Exception:
            pass
    return {"local": local_count, "r2": local_count}


@app.get("/api/meta")
async def api_meta() -> dict:
    return {
        "app_version": APP_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "project_root": str(PROJECT_ROOT),
        "main_script": str(MAIN_SCRIPT),
        "main_script_exists": MAIN_SCRIPT.is_file(),
        "run_stream_supported": True,
        "run_stop_supported": True,
        "post_endpoints": ["/api/run", "/api/run/stream", "/api/run/stop"],
        "hint": "若 POST /api/run/stream 回 404，請關掉舊的 python -m web 後在 music-auto 目錄重啟。",
    }


@app.get("/api/songs")
async def api_songs(limit: int = 50, offset: int = 0, genre: str | None = None) -> list[dict]:
    """從 D1 資料庫抓取最新下載的歌曲，並解析 R2 公開 URL 或本地串流路徑"""
    from app.config import load_settings
    from app.services.d1_manager import D1Manager
    
    settings = load_settings()
    d1 = D1Manager(settings)
    from app.services.storage_manager import StorageManager
    sm = StorageManager(settings)
    
    if not d1.enabled:
        return []
    songs = await d1.get_recent_songs(limit=limit, offset=offset, genre=genre)
    
    # 優先提供 NAS 本地串流，因為 R2 可能尚未上傳完成
    for song in songs:
        song["fallback_url"] = f"/api/songs/{song['song_id']}/play"
        r2_url = None
        
        # 使用 boto3 產生 presigned URL，這樣就不需要公開 Bucket (也就不需要 r2.dev)
        if sm._r2_client and settings.r2_bucket_name and song.get("r2_category_path") and song.get("folder_name"):
            filename = f"{song['folder_name']}.mp3"
            category_key = song["r2_category_path"].replace("\\", "/")
            s3_key = f"{category_key}/{filename}"
            try:
                r2_url = sm._r2_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.r2_bucket_name,
                        'Key': s3_key
                    },
                    ExpiresIn=3600 * 24 # 網址 24 小時有效
                )
            except Exception:
                pass
            
        song["audio_url"] = r2_url if r2_url else song["fallback_url"]
        
        # Ensure genre is at least returned (fallback to Uncategorized if None)
        if "genre" not in song or not song["genre"]:
            song["genre"] = "Uncategorized"
            
    return songs

class GenreUpdateRequest(BaseModel):
    genre: str

@app.put("/api/songs/{song_id}/genre")
async def api_update_song_genre(song_id: str, req: GenreUpdateRequest):
    from app.config import load_settings
    from app.services.d1_manager import D1Manager
    settings = load_settings()
    d1 = D1Manager(settings)
    success = await d1.update_song_genre(song_id, req.genre)
    if not success:
        return JSONResponse({"error": "Failed to update genre"}, status_code=500)
    return {"status": "success", "genre": req.genre}


@app.get("/api/songs/{song_id}/play")
async def api_song_play(song_id: str):
    """取得歌曲的 MP3 音訊串流"""
    from app.config import load_settings
    from app.services.d1_manager import D1Manager
    from fastapi.responses import FileResponse
    import glob
    
    settings = load_settings()
    d1 = D1Manager(settings)
    if not d1.enabled:
        raise HTTPException(status_code=404, detail="D1 is not enabled")
        
    songs = await d1.get_recent_songs(limit=500) # Fetch more to find the ID
    song = next((s for s in songs if s["song_id"] == song_id), None)
    
    if not song or not song.get("folder_name"):
        raise HTTPException(status_code=404, detail="Song not found in database")
        
    # 如果有 R2 設定，也可以在此將請求 redirect 到 R2（選項）
    # 但為了相容性，這裡保持返回本地檔案，若本地找不到則報錯
    folder_path = Path(settings.download_dir) / song["folder_name"]
    mp3_files = list(folder_path.glob("*.mp3")) if folder_path.exists() else []
    
    if not mp3_files:
        # Fallback to predicting filename if it's there but glob fails? No, if it doesn't exist locally, we can't serve it.
        # Check if we can redirect to R2
        if settings.r2_bucket_name and settings.r2_public_url and song.get("r2_category_path"):
            from fastapi.responses import RedirectResponse
            import urllib.parse
            filename = urllib.parse.quote(f"{song['folder_name']}.mp3")
            category_key = urllib.parse.quote(song["r2_category_path"].replace("\\", "/"), safe="/")
            r2_url = f"{settings.r2_public_url.rstrip('/')}/{category_key}/{filename}"
            return RedirectResponse(url=r2_url)
            
        raise HTTPException(status_code=404, detail="MP3 file not found in directory")
        
    return FileResponse(path=mp3_files[0], media_type="audio/mpeg")


@app.post("/api/run/stop")
async def api_run_stop() -> dict[str, bool | str]:
    """終止目前由本控制台啟動的子程序。"""
    async with _run_state_lock:
        proc = _child_proc
    if proc is None:
        return {"stopped": False, "message": "目前沒有執行中的子程序"}
    if proc.returncode is not None:
        return {"stopped": False, "message": "程序已結束"}
    try:
        proc.kill()
    except ProcessLookupError:
        pass
    return {"stopped": True, "message": "已送出終止信號（Chrome 內自動化可能仍須數秒才停下）"}


# ═══════════════════════════════════════════════════════════════
# 下載中心獨立端點（內部直接呼叫 MurekaDownloader，不走 main.py CLI）
# ═══════════════════════════════════════════════════════════════

_dl_lock = asyncio.Lock()
_dl_busy = False
_dl_task: asyncio.Task | None = None


class DlRunRequest(BaseModel):
    library_url: str | None = Field(
        default=None,
        description="可選：覆寫 Mureka 作品庫頁面 URL",
    )
    profile: str | None = Field(
        default=None,
        description="下載模式：basic, archive, full, video, custom",
    )


@app.post("/api/download/stream")
async def api_download_stream(req: DlRunRequest) -> StreamingResponse:
    """獨立下載 SSE 串流：使用 asyncio.Queue 實現即時進度回報。"""
    from app.services.mureka_downloader import MurekaDownloader
    from app.config import load_settings

    async def _stream():
        global _dl_busy, _dl_task

        async with _dl_lock:
            if _dl_busy:
                yield _sse_data({"t": "error", "msg": "下載已在進行中，請稍候或按停止。"})
                yield _sse_data({"t": "done", "code": 409})
                return
            _dl_busy = True

        settings = load_settings()
        downloader = MurekaDownloader(settings, profile=req.profile)
        queue: asyncio.Queue[dict] = asyncio.Queue()

        async def progress(msg: dict):
            await queue.put(msg)

        async def run_download():
            try:
                yield _sse_data({"t": "meta", "cmd": ["MurekaDownloader.download_from_library"]})
                yield _sse_data({"t": "out", "s": "正在連接 Chrome CDP...\n"})

                await downloader.connect()

                yield _sse_data({"t": "out", "s": "✅ 已連接。開始掃描作品庫...\n"})
                yield _sse_data({"t": "dash_stats", "local": len(downloader._history), "r2": len(downloader._history)})
                yield _sse_data({"t": "out", "s": f"下載目錄：{downloader._download_dir}\n"})
                yield _sse_data({"t": "out", "s": f"歷史記錄：{len(downloader._history)} 筆\n\n"})

                results, new_count = await downloader.download_from_library(
                    library_url=req.library_url,
                    progress_callback=progress,
                )

                yield _sse_data({"t": "out", "s": f"\n--- 下載完成 ---\n"})
                yield _sse_data({"t": "out", "s": f"新下載：{new_count} 首\n"})
                yield _sse_data({"t": "out", "s": f"總處理：{len(results)} 首\n"})
                yield _sse_data({"t": "dl_stats", "new": new_count, "total": len(results)})
                yield _sse_data({"t": "done", "code": 0})

            except Exception as exc:
                logger.exception("Download stream failed")
                yield _sse_data({"t": "error", "msg": str(exc)})
                yield _sse_data({"t": "done", "code": 1})
            finally:
                await downloader.close()
                async with _dl_lock:
                    _dl_busy = False
                    _dl_task = None

        global _dl_task
        # 背景執行下載，同時從 queue 讀取進度
        _dl_task = asyncio.ensure_future(_collect_results(run_download()))
        download_task = _dl_task

        # 先送出 meta
        yield _sse_data({"t": "meta", "cmd": ["MurekaDownloader.download_from_library"]})

        while not download_task.done() or not queue.empty():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield _sse_data(msg)
            except asyncio.TimeoutError:
                if download_task.done():
                    # drain remaining
                    while not queue.empty():
                        msg = queue.get_nowait()
                        yield _sse_data(msg)
                    break

        # 送出下載器產生的最終結果
        final_results = await download_task
        for item in final_results:
            yield item

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/download/stop")
async def api_download_stop() -> dict[str, bool | str]:
    """停止正在進行的下載（目前僅標記，待下一輪 idle 檢測退出）。"""
    global _dl_busy, _dl_task
    async with _dl_lock:
        if not _dl_busy:
            return {"stopped": False, "message": "目前沒有執行中的下載"}
        
        # Cancel the task if it exists
        if _dl_task and not _dl_task.done():
            _dl_task.cancel()
            
        _dl_busy = False
        _dl_task = None
        
    return {"stopped": True, "message": "已送出停止信號，下載任務已取消。"}


@app.post("/api/run", response_model=RunResponse)
async def api_run(req: RunRequest) -> RunResponse:
    if req.preset != "process_csv" and not MAIN_SCRIPT.is_file():
        raise HTTPException(status_code=500, detail="找不到 app/main.py")
    await _try_acquire_run()
    cmd = _build_command_unbuffered(req)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc: asyncio.subprocess.Process | None = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await _bind_child_proc(proc)
        stdout_b, stderr_b = await proc.communicate()
        out = (stdout_b or b"").decode("utf-8", errors="replace")
        err = (stderr_b or b"").decode("utf-8", errors="replace")
        cmd_display = _build_command(req)
        return RunResponse(
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=out,
            stderr=err,
            command=cmd_display,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await _release_run(proc)


@app.post("/api/run/stream")
async def api_run_stream(req: RunRequest) -> StreamingResponse:
    """以 SSE 串流子程序合併 stdout/stderr。"""
    if req.preset != "process_csv" and not MAIN_SCRIPT.is_file():
        raise HTTPException(status_code=500, detail="找不到 app/main.py")

    return StreamingResponse(
        _stream_subprocess(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
