"""Mureka multi‑asset downloader — CDP‑attached, profile‑driven.

Supports downloading MP3, WAV, Stems/MIDI, commercial license, and video
from the Mureka library page.  Each song gets its own folder under
``downloads/`` with a ``metadata.json`` sidecar.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable, Awaitable
from typing import Any

from app.config import AppSettings
from app.logger import get_logger
from app.services.storage_manager import StorageManager

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

# Asset types in download order (mp3 first, large files last)
ASSET_MP3 = "mp3"
ASSET_WAV = "wav"
ASSET_LICENSE = "license"
ASSET_STEMS_MIDI = "stems_midi"
ASSET_VIDEO = "video"

ALL_ASSET_TYPES = (ASSET_MP3, ASSET_WAV, ASSET_LICENSE, ASSET_STEMS_MIDI, ASSET_VIDEO)

# Menu item label → asset type
MENU_LABEL_MAP: dict[str, str] = {
    # English
    "Download MP3": ASSET_MP3,
    "Download WAV": ASSET_WAV,
    "Download commercial license": ASSET_LICENSE,
    "Download Stems / MIDI": ASSET_STEMS_MIDI,
    "Download Video": ASSET_VIDEO,
    # 中文（實際畫面擷圖）
    "下載MP3": ASSET_MP3,
    "下載WAV": ASSET_WAV,
    "下載權屬證明": ASSET_LICENSE,
    "下載樂器、伴奏、MIDI分軌音訊": ASSET_STEMS_MIDI,
    "下載視頻": ASSET_VIDEO,
    # 預防其他中文介面變體
    "下載 MP3": ASSET_MP3,
    "下載 WAV": ASSET_WAV,
    "下載商業授權": ASSET_LICENSE,
    "下載 Stems / MIDI": ASSET_STEMS_MIDI,
    "下載影片": ASSET_VIDEO,
}

# Profile → set of asset types
PROFILE_MAP: dict[str, set[str]] = {
    "basic": {ASSET_MP3, ASSET_LICENSE},
    "archive": {ASSET_MP3, ASSET_WAV, ASSET_LICENSE},
    "full": {ASSET_MP3, ASSET_WAV, ASSET_STEMS_MIDI, ASSET_LICENSE},
    "video": {ASSET_MP3, ASSET_VIDEO, ASSET_LICENSE},
}

# Assets that usually produce large files (log a warning)
LARGE_ASSETS = {ASSET_WAV, ASSET_STEMS_MIDI, ASSET_VIDEO}


# ---------------------------------------------------------------------------
# data models
# ---------------------------------------------------------------------------


@dataclass
class AssetRecord:
    """One downloaded asset within a song folder."""

    asset_type: str
    filename: str
    file_path: str
    file_size: int
    file_hash: str | None
    downloaded_at: str
    status: str = "success"  # success | failed | skipped
    error: str | None = None


@dataclass
class DownloadRecord:
    """One row in download_history.json — represents a song folder."""

    song_id: str | None
    title: str
    folder: str  # relative or absolute path to the song folder
    source_url: str | None
    assets: list[AssetRecord] = ()
    downloaded_at: str = ""  # first download time
    profile: str = "basic"

    @property
    def success_count(self) -> int:
        return sum(1 for a in self.assets if a.status == "success")

    @property
    def failed_assets(self) -> list[str]:
        return [a.asset_type for a in self.assets if a.status == "failed"]


# Convert AssetRecord to dict for JSON serialization
def _asset_dict(a: AssetRecord) -> dict:
    return asdict(a)


@dataclass
class DownloadResult:
    """Return value for batch operations."""

    title: str
    song_id: str | None
    success: bool
    assets_downloaded: list[str] = ()
    assets_failed: list[str] = ()
    folder: str | None = None
    error: str | None = None
    backup_messages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _safe_name(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in name)
    cleaned = cleaned.strip().strip(".")
    return cleaned[:120] or "mureka_song"


def _sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _resolve_assets_for_profile(settings: AppSettings, profile: str, custom_assets: str | None) -> set[str]:
    """Determine which asset types to download based on profile and settings."""
    if profile in PROFILE_MAP:
        assets = set(PROFILE_MAP[profile])
    elif profile == "custom":
        if custom_assets:
            assets = set(a.strip().lower() for a in custom_assets.split(",") if a.strip().lower() in ALL_ASSET_TYPES)
        else:
            assets = {ASSET_MP3}
    else:
        assets = PROFILE_MAP["basic"]

    # Apply individual toggle overrides
    if not settings.download_commercial_license:
        assets.discard(ASSET_LICENSE)
    if not settings.download_wav:
        assets.discard(ASSET_WAV)
    if not settings.download_stems_midi:
        assets.discard(ASSET_STEMS_MIDI)
    if not settings.download_video:
        assets.discard(ASSET_VIDEO)

    # Ensure mp3 is always included as baseline
    if ASSET_MP3 not in assets:
        assets.add(ASSET_MP3)

    return assets


def _asset_sort_key(asset_type: str) -> int:
    """Return sort priority: mp3 first, then license, then wav, then large files last."""
    order = {ASSET_MP3: 0, ASSET_LICENSE: 1, ASSET_WAV: 2, ASSET_STEMS_MIDI: 3, ASSET_VIDEO: 4}
    return order.get(asset_type, 99)


# ---------------------------------------------------------------------------
# MurekaDownloader
# ---------------------------------------------------------------------------


class MurekaDownloader:
    """Download multiple asset types from Mureka library.

    Usage::

        dl = MurekaDownloader(settings, profile="basic")
        await dl.connect()
        results, new_count = await dl.download_from_library()
        await dl.close()
    """

    def __init__(
        self,
        settings: AppSettings,
        *,
        profile: str | None = None,
        custom_assets: str | None = None,
        download_dir: str | Path | None = None,
    ) -> None:
        self._settings = settings

        # Resolve profile
        self._profile = profile or settings.download_profile
        self._asset_types = _resolve_assets_for_profile(settings, self._profile, custom_assets)
        self._max_file_size_mb = settings.download_max_file_size_mb

        logger.info(
            "Downloader initialised — profile=%s assets=%s max_size_mb=%s",
            self._profile,
            sorted(self._asset_types, key=_asset_sort_key),
            self._max_file_size_mb,
        )

        # Download directory
        if download_dir:
            self._download_dir = Path(download_dir).expanduser().resolve()
        else:
            repo_root = Path(__file__).resolve().parents[2]
            self._download_dir = (repo_root / ".." / "downloads").resolve()
        self._download_dir.mkdir(parents=True, exist_ok=True)

        # History
        self._history_path = self._download_dir / "download_history.json"

        # Playwright handles
        self._playwright: Any | None = None
        self._browser: Any | None = None

        # Runtime state
        self._history: list[DownloadRecord] = []
        self._downloaded_ids: set[str] = set()
        
        # Dual Backup Manager
        self._storage_manager = StorageManager(settings)
        
        # D1 Database Manager
        from app.services.d1_manager import D1Manager
        self._d1_manager = D1Manager(settings)

    # ── connection lifecycle ──────────────────────────────────────────

    async def connect(self) -> None:
        from playwright.async_api import async_playwright

        cdp_url = self._settings.browser_cdp_url
        logger.info("MurekaDownloader connecting to CDP: %s", cdp_url)

        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
        except Exception:
            await self._playwright.stop()
            self._playwright = None
            raise

        await self._load_history()
        logger.info("Connected — history: %s songs", len(self._history))

    async def close(self) -> None:
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Playwright stop error (ignored): %s", exc)
        self._playwright = None
        self._browser = None

    # ── history ───────────────────────────────────────────────────────

    async def _load_history(self) -> None:
        if not self._history_path.exists():
            self._history = []
            self._downloaded_ids = set()
            return

        try:
            raw = json.loads(self._history_path.read_text(encoding="utf-8"))
            self._history = []
            for item in raw:
                # ── backward compat: old format had file_path instead of folder/assets ──
                if "file_path" in item and "folder" not in item:
                    old_path = Path(item.get("file_path", ""))
                    song_id = item.get("song_id")
                    title = item.get("title", old_path.stem)
                    folder = str(old_path.parent) if old_path.parent != self._download_dir else str(self._download_dir / (song_id or title))
                    asset = AssetRecord(
                        asset_type="mp3",
                        filename=old_path.name if old_path.name else f"{title}.mp3",
                        file_path=str(old_path),
                        file_size=item.get("file_size", 0),
                        file_hash=item.get("file_hash"),
                        downloaded_at=item.get("downloaded_at", ""),
                        status=item.get("status", "success"),
                        error=item.get("error"),
                    )
                    rec = DownloadRecord(
                        song_id=song_id,
                        title=title,
                        folder=folder,
                        source_url=item.get("source_url"),
                        assets=[asset],
                        downloaded_at=item.get("downloaded_at", ""),
                        profile="basic",
                    )
                    self._history.append(rec)
                    continue

                assets_raw = item.pop("assets", [])
                assets = [AssetRecord(**a) for a in assets_raw]
                rec = DownloadRecord(assets=assets, **item)
                self._history.append(rec)
        except Exception as exc:
            logger.warning("Failed to parse download_history.json, starting fresh: %s", exc)
            self._history = []

        self._downloaded_ids = set()
        required_assets = set(self._asset_types)
        assets_by_id: dict[str, set[str]] = {}
        
        for rec in self._history:
            if not rec.song_id:
                continue
            if rec.song_id not in assets_by_id:
                assets_by_id[rec.song_id] = set()
            for a in rec.assets:
                if a.status == "success":
                    assets_by_id[rec.song_id].add(a.asset_type)
                    
        for s_id, success_assets in assets_by_id.items():
            if required_assets.issubset(success_assets):
                self._downloaded_ids.add(s_id)

    async def _save_history(self) -> None:
        data = []
        for rec in self._history:
            d = asdict(rec)
            d["assets"] = [_asset_dict(a) for a in rec.assets]
            data.append(d)
        self._history_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_downloaded(self, song_id: str | None = None) -> bool:
        if song_id and song_id in self._downloaded_ids:
            return True
        return False

    # ── page helpers ──────────────────────────────────────────────────

    def _all_pages(self) -> list[Any]:
        assert self._browser is not None
        pages: list[Any] = []
        for ctx in self._browser.contexts:
            pages.extend(ctx.pages)
        return pages

    async def _find_mureka_page(self, *, url_substring: str = "mureka.ai") -> Any | None:
        pages = self._all_pages()
        candidates = [p for p in pages if url_substring in (p.url or "")]
        if not candidates:
            return None
        for p in candidates:
            u = (p.url or "").lower()
            if any(k in u for k in ("library", "my-works", "mine", "my_songs")):
                return p
        # Do not return a non-library Mureka page (e.g. /create), to prevent hijacking the generation tab.
        return None

    # ── public API ────────────────────────────────────────────────────

    async def download_from_library(
        self,
        *,
        library_url: str | None = None,
        max_idle_rounds: int = 15,
        scroll_px: int = 1000,
        progress_callback: Callable[[dict], Awaitable[None]] | None = None,
    ) -> tuple[list[DownloadResult], int]:
        """Scan Mureka library and download all non‑duplicate songs."""
        if self._browser is None:
            raise RuntimeError("Not connected. Call connect() first.")

        async def _emit_event(msg_dict: dict) -> None:
            if progress_callback:
                await progress_callback(msg_dict)

        async def _emit(t: str, s: str) -> None:
            await _emit_event({"t": t, "s": s})

        page = await self._find_mureka_page()
        if page is None:
            target = library_url or self._settings.mureka_base_url.rstrip("/") + "/library"
            logger.info("Opening library: %s", target)
            await _emit("out", f"開啟作品庫頁面：{target}\n")
            ctx = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
            page = await ctx.new_page()
            await page.goto(target, wait_until="domcontentloaded", timeout=30000)
        else:
            await page.bring_to_front()
            current = (page.url or "").lower()
            if "library" not in current and "my-works" not in current and "mine" not in current:
                target = library_url or self._settings.mureka_base_url.rstrip("/") + "/library"
                logger.info("Navigating to library: %s", target)
                await _emit("out", f"導航到作品庫：{target}\n")
                await page.goto(target, wait_until="domcontentloaded", timeout=30000)

        await asyncio.sleep(3)
        logger.info("Library page ready: %s", page.url)
        await _emit("out", f"頁面就緒：{page.url}\n")

        results: list[DownloadResult] = []
        consecutive_idle = 0
        total_failures = 0

        while consecutive_idle < max_idle_rounds:
            cur_url = page.url or ""
            if "song-detail" in cur_url and "library" not in cur_url:
                logger.warning("Landed on song-detail — going back")
                await page.go_back()
                await asyncio.sleep(3)
                continue

            items = await page.query_selector_all(".song-audio-item")
            found_any = False
            processed_this_round: set[str] = set()

            if items:
                await _emit("out", f"本輪找到 {len(items)} 首歌曲...\n")

            for item in items:
                try:
                    html = await item.inner_html()
                    match = re.search(r"skm/image/[0-9]+/([^.?]+)", html)
                    song_id = match.group(1) if match else None

                    if not song_id or song_id in self._downloaded_ids or song_id in processed_this_round:
                        continue
                    processed_this_round.add(song_id)

                    title_el = await item.query_selector(".audio-item-title")
                    title = (await title_el.inner_text()).strip() if title_el else "Unknown"

                    img_el = await item.query_selector("img")
                    img_url = await img_el.get_attribute("src") if img_el else None
                    found_any = True

                    await _emit("out", f"⬇️ {title}\n")
                    logger.info("[%s] Downloading: %s", self._profile.upper(), title)

                    result = await self._download_song_assets(page, item, title, song_id)
                    results.append(result)

                    if result.success:
                        self._downloaded_ids.add(song_id)
                        await _emit("out", f"   ✅ 成功 — {', '.join(result.assets_downloaded)}\n")
                        
                        cover_url = img_url
                        if img_url and result.folder:
                            try:
                                import urllib.request
                                cover_path = Path(result.folder) / "cover.jpg"
                                def _download_cover():
                                    req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                                    with urllib.request.urlopen(req) as response, open(cover_path, 'wb') as out_file:
                                        out_file.write(response.read())
                                await asyncio.to_thread(_download_cover)
                                await _emit("out", f"   🖼️ 已儲存專輯封面 (cover.jpg)\n")
                            except Exception as e:
                                logger.warning("Failed to download cover for %s: %s", title, e)

                        if img_url:
                            await _emit_event({"t": "song_cover", "title": title, "url": img_url})
                            
                        # Backup to NAS & R2
                        if result.folder:
                            folder_path = Path(result.folder)
                            backup_messages = await self._storage_manager.sync_all(folder_path)
                            for msg in backup_messages:
                                await _emit("out", f"   {msg}\n")
                            
                            # Write to D1 Database
                            category_path = self._storage_manager._get_category_path(folder_path.name)
                            author = folder_path.name.split("_")[1] if "_" in folder_path.name else "Unknown"
                            d1_success = await self._d1_manager.upsert_song(
                                song_id=song_id,
                                title=title,
                                author=author,
                                folder_name=folder_path.name,
                                r2_category_path=category_path,
                                cover_url=cover_url
                            )
                            if d1_success:
                                await _emit("out", f"   💾 已寫入 Cloudflare D1 資料庫\n")
                                
                        for msg in result.backup_messages:
                            await _emit("out", f"   {msg}\n")
                    else:
                        total_failures += 1
                        await _emit("out", f"   ⚠️ 部分失敗 — {', '.join(result.assets_failed) if result.assets_failed else result.error}\n")

                    await self._random_delay(2, 5)

                except Exception as exc:
                    total_failures += 1
                    await _emit("out", f"   ❌ 錯誤：{exc}\n")
                    continue

            if total_failures >= 10:
                await _emit("out", "\n🔄 累積失敗達 10 首，觸發防呆重置！正在捲動回最頂端重新檢查...\n")
                logger.info("Total failures reached 10, resetting to top.")
                try:
                    await page.evaluate("window.scrollTo(0, 0)")
                except Exception:
                    pass
                total_failures = 0
                consecutive_idle = 0
                await asyncio.sleep(5)
                continue

            logger.debug("Scrolling for more items…")
            await page.mouse.move(1200, 400)
            await page.mouse.wheel(0, scroll_px)
            await asyncio.sleep(4)

            if not found_any:
                consecutive_idle += 1
                await _emit("out", f"無新歌曲，閒置 {consecutive_idle}/{max_idle_rounds}...\n")
            else:
                consecutive_idle = 0

        new_count = sum(1 for r in results if r.success)
        logger.info("Library download complete — %s new / %s total", new_count, len(results))
        return results, new_count

    # ── per‑song multi‑asset download ─────────────────────────────────

    async def _open_menu(self, page: Any, item: Any) -> bool:
        """Open the dropdown menu for one song card. Returns True if successful."""
        selectors = [
            ".audio-item-more-box",
            ".audio-item-more-btn-download",
            ".audio-item-more-btn",
            "[class*='more-btn']",
            "[class*='more-actions']",
            "[class*='more']",
            "button[aria-label*='more']",
            "button",
        ]
        trigger = None
        for sel in selectors:
            trigger = await item.query_selector(sel)
            if trigger:
                break
        if trigger is None:
            return False

        await trigger.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await trigger.hover()
        await trigger.click()
        
        try:
            # Wait for any dropdown menu to become visible
            await page.wait_for_selector(".el-popper:visible, .el-dropdown-menu:visible", timeout=3000)
            await asyncio.sleep(0.5)
            return True
        except Exception:
            return False

    async def _try_click_menu_label(self, page: Any, label: str) -> bool:
        """Try to click a dropdown menu item by text. Returns True if clicked."""
        js = """(text) => {
            // Look for elements whose trimmed innerText is an exact match or starts with the text
            const all = Array.from(document.querySelectorAll('div, span, li, button, a, p'));
            const exact = all.find(el => {
                const t = (el.innerText || '').trim();
                return t === text || t.startsWith(text + '\\n') || t.startsWith(text + ' ');
            });
            if (exact) { exact.click(); return true; }
            const fuzzy = all.find(el => (el.innerText || '').trim().includes(text));
            if (fuzzy) { fuzzy.click(); return true; }
            return false;
        }"""
        try:
            return await page.evaluate(js, label)
        except Exception:
            return False

    async def _download_song_assets(
        self,
        page: Any,
        item: Any,
        title: str,
        song_id: str,
    ) -> DownloadResult:
        """Download multiple assets based on the selected profile."""
        safe_title = _safe_name(title)
        short_id = song_id[:8] if song_id else "unknown"
        song_folder = self._download_dir / f"{safe_title}_{short_id}"
        song_folder.mkdir(parents=True, exist_ok=True)

        asset_records: list[AssetRecord] = []
        downloaded_types: list[str] = []
        failed_types: list[str] = []

        # Ensure the menu is open first
        menu_open = await self._open_menu(page, item)
        if not menu_open:
            return DownloadResult(title=title, song_id=song_id, success=False, error="No more button found to open menu")

        # Sort requested asset types by priority (MP3 -> License -> WAV -> Stems -> Video)
        ordered_assets = sorted(self._asset_types, key=_asset_sort_key)

        for i, asset_type in enumerate(ordered_assets):
            # 1. Check if already downloaded and in history
            existing_record = await self._check_already_downloaded(song_folder, title, asset_type)
            if existing_record:
                asset_records.append(existing_record)
                downloaded_types.append(asset_type)
                continue

            # 2. Re-open menu if it closed from previous download
            if i > 0:
                await self._reopen_menu(page, item)

            # 3. Find the correct labels for this asset_type
            matching_labels = [lbl for lbl, a_type in MENU_LABEL_MAP.items() if a_type == asset_type]
            if not matching_labels:
                matching_labels = [f"Download {asset_type.upper()}"]
            
            logger.info("[%s] Attempting %s via labels: %s", title, asset_type, matching_labels)

            # 4. Download based on type
            if asset_type == "license":
                record = await self._download_license(page, song_folder, title, matching_labels, asset_type, safe_title, short_id)
            else:
                record = await self._download_via_event(page, song_folder, title, matching_labels, asset_type, safe_title, short_id)

            asset_records.append(record)
            if record.status == "success":
                downloaded_types.append(asset_type)
            else:
                failed_types.append(asset_type)

        # 5. Write metadata and history
        await self._write_metadata(song_folder, title, song_id, asset_records)

        history_rec = DownloadRecord(
            song_id=song_id, title=title, folder=str(song_folder), source_url=page.url,
            assets=asset_records,
            downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            profile=self._profile,
        )
        self._history.append(history_rec)
        await self._save_history()

        # 6. Run Dual Backup (NAS / Cloudflare R2)
        if len(failed_types) == 0:
            backup_messages = await self._storage_manager.sync_all(song_folder)
            for msg in backup_messages:
                logger.info("[%s] %s", title, msg)
                # Output to UI log if possible (we don't have _emit here, but it's fine as the upper loop handles it)

        return DownloadResult(
            title=title, song_id=song_id,
            success=len(failed_types) == 0,
            assets_downloaded=downloaded_types,
            assets_failed=failed_types,
            folder=str(song_folder),
            backup_messages=backup_messages if len(failed_types) == 0 else []
        )

    async def _click_visible_text(self, page: Any, labels: list[str]) -> bool:
        """Find the first visible element matching any of the labels and click it natively."""
        for label in labels:
            locs = page.get_by_text(label)
            count = await locs.count()
            for i in range(count):
                loc = locs.nth(i)
                try:
                    if await loc.is_visible():
                        # Use native click without force to ensure it's actually actionable
                        await loc.click()
                        return True
                except Exception:
                    pass
        return False

    async def _download_via_event(
        self, page: Any, song_folder: Path, title: str, labels: list[str], asset_type: str, safe_title: str, short_id: str
    ) -> AssetRecord:
        """Download via browser download event (MP3, WAV, Stems, Video)."""
        try:
            ok = False
            async with page.expect_download(timeout=90000) as dl_info:
                ok = await self._click_visible_text(page, labels)
                if not ok:
                    raise RuntimeError(f"Menu item '{labels}' not found or not visible")

            download = await dl_info.value
            suggested = download.suggested_filename or f"{safe_title}_{asset_type}{_asset_ext(asset_type)}"
            final_name = f"{_safe_name(Path(suggested).stem)}_{short_id}{Path(suggested).suffix}"
            final_path = song_folder / final_name
            await download.save_as(final_path)

            file_size = final_path.stat().st_size
            fhash = _sha256_file(final_path)
            logger.info("[%s] ✅ %s downloaded (%s KB)", title, asset_type, file_size // 1024)
            
            # We don't close dialogs here, MP3/WAV/Video don't open dialogs
            await asyncio.sleep(1)
            
            return AssetRecord(
                asset_type=asset_type, filename=final_name, file_path=str(final_path),
                file_size=file_size, file_hash=fhash,
                downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                status="success",
            )

        except Exception as exc:
            err_msg = str(exc)[:150]
            logger.warning("[%s] ❌ %s failed: %s", title, asset_type, err_msg)
            return AssetRecord(
                asset_type=asset_type, filename="", file_path="", file_size=0, file_hash=None,
                downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                status="failed", error=err_msg,
            )

    async def _download_license(
        self, page: Any, song_folder: Path, title: str, labels: list[str], asset_type: str, safe_title: str, short_id: str
    ) -> AssetRecord:
        """Download commercial license (which opens a dialog)."""
        ok = await self._click_visible_text(page, labels)
        if not ok:
            return AssetRecord(
                asset_type=asset_type, filename="", file_path="", file_size=0, file_hash=None,
                downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                status="failed", error=f"Menu item '{labels}' not found or not visible",
            )
            
        try:
            dialog = await page.query_selector(".download-copyright")
            if not dialog:
                await asyncio.sleep(2)
                dialog = await page.query_selector(".download-copyright")
            
            if dialog:
                inputs = await dialog.query_selector_all("input")
                if len(inputs) >= 2:
                    await inputs[0].fill("User")
                    await inputs[1].fill("user@example.com")
                
                btns = await dialog.query_selector_all("button")
                if btns:
                    # Give Vue time to enable the button after filling inputs
                    await asyncio.sleep(1)
                    async with page.expect_download(timeout=90000) as dl_info:
                        await btns[-1].click()
                        download = await dl_info.value
                        
                    suggested = download.suggested_filename or f"{safe_title}_{asset_type}{_asset_ext(asset_type)}"
                    final_name = f"{_safe_name(Path(suggested).stem)}_{short_id}{Path(suggested).suffix}"
                    final_path = song_folder / final_name
                    await download.save_as(final_path)

                    file_size = final_path.stat().st_size
                    fhash = _sha256_file(final_path)
                    logger.info("[%s] ✅ license downloaded (%s KB)", title, file_size // 1024)
                    
                    try:
                        close_btn = await page.query_selector(".dialog-close")
                        if close_btn:
                            await close_btn.click()
                    except:
                        pass
                    
                    return AssetRecord(
                        asset_type=asset_type, filename=final_name, file_path=str(final_path),
                        file_size=file_size, file_hash=fhash,
                        downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        status="success",
                    )
            
            return AssetRecord(
                asset_type=asset_type, filename="", file_path="", file_size=0, file_hash=None,
                downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                status="failed", error="License dialog not found or download failed",
            )
        except Exception as exc:
            try:
                close_btn = await page.query_selector(".dialog-close")
                if close_btn:
                    await close_btn.click()
            except:
                pass
            return AssetRecord(
                asset_type=asset_type, filename="", file_path="", file_size=0, file_hash=None,
                downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                status="failed", error=str(exc)[:150],
            )

    async def _check_already_downloaded(self, song_folder: Path, title: str, asset_type: str) -> AssetRecord | None:
        """Return an AssetRecord if the file already exists on disk with matching hash in history, else None."""
        existing = list(song_folder.glob(f"*{_asset_ext(asset_type)}"))
        if not existing:
            return None
        for fp in existing:
            if fp.name.startswith("."):
                continue
            fhash = _sha256_file(fp)
            for rec in self._history:
                for a in rec.assets:
                    if a.file_hash == fhash and a.status == "success":
                        logger.info("[%s] %s already downloaded — skipping", title, asset_type)
                        return AssetRecord(
                            asset_type=asset_type, filename=fp.name, file_path=str(fp),
                            file_size=fp.stat().st_size, file_hash=fhash,
                            downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            status="skipped",
                        )
        return None

    async def _reopen_menu(self, page: Any, item: Any) -> None:
        """Re‑open the dropdown menu after the previous click closed it."""
        try:
            await page.mouse.click(0, 0)
        except Exception:
            pass
        await asyncio.sleep(1)
        await self._open_menu(page, item)

    async def _get_menu_labels(self, page: Any) -> set[str]:
        """Extract visible menu item text from the currently open dropdown."""
        js = """() => {
            const all = Array.from(document.querySelectorAll('*'));
            const keywords = ['Download MP3', 'Download WAV', 'Download commercial license', 'Download Stems', 'Download Video'];
            return all
                .filter(el => el.innerText && keywords.some(k => el.innerText.trim().includes(k)))
                .map(el => el.innerText.trim())
                .filter((v, i, arr) => arr.indexOf(v) === i);
        }"""
        try:
            labels = await page.evaluate(js)
            return set(labels)
        except Exception:
            return set()

    async def _write_metadata(self, folder: Path, title: str, song_id: str | None, assets: list[AssetRecord]) -> None:
        meta = {
            "title": title,
            "song_id": song_id,
            "profile": self._profile,
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "assets": [
                {
                    "type": a.asset_type,
                    "filename": a.filename,
                    "file_path": a.file_path,
                    "file_size": a.file_size,
                    "file_hash": a.file_hash,
                    "status": a.status,
                    "error": a.error,
                }
                for a in assets
            ],
        }
        meta_path = folder / "metadata.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── utilities ─────────────────────────────────────────────────────

    @staticmethod
    async def _random_delay(min_sec: float = 2.0, max_sec: float = 5.0) -> None:
        await asyncio.sleep(random.uniform(min_sec, max_sec))


def _asset_ext(asset_type: str) -> str:
    """Return typical file extension for an asset type."""
    ext_map = {
        ASSET_MP3: ".mp3",
        ASSET_WAV: ".wav",
        ASSET_LICENSE: ".pdf",
        ASSET_STEMS_MIDI: ".zip",
        ASSET_VIDEO: ".mp4",
    }
    return ext_map.get(asset_type, ".bin")