"""Fast Mureka automation via Playwright CDP attach.

This engine avoids LLM/browser-use during the normal path. It attaches to the
user's already logged-in Chrome, fills Mureka with deterministic DOM heuristics,
clicks Generate when requested, and records a screenshot/result summary.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from app.config import AppSettings
from app.logger import get_logger
from app.schemas import SongInput, SongResult
from app.utils.browser_profile import get_screenshots_dir
from app.utils.cdp_targets import get_page_target_url_by_id_async

logger = get_logger(__name__)


class MurekaPlaywrightError(RuntimeError):
    """Raised when deterministic Playwright automation cannot complete."""


def _mureka_page_score(url: str) -> int:
    u = (url or "").lower()
    if "mureka" not in u:
        return 0
    if u.startswith("about:") or "newtab" in u:
        return 0
    # home/explore/pricing/library pages are NOT create-music pages
    non_create_hints = ("/home", "/explore", "/pricing", "/login", "/signup", "/settings", "/library")
    for hint in non_create_hints:
        if hint in u:
            return 1  # low score: it's Mureka but not the create page
    score = 5
    for hint in ("music-gen", "create-music", "create_music", "/create", "/tools/", "studio", "custom"):
        if hint in u:
            score += 10
    return score


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


class MurekaPlaywrightAgent:
    """Playwright-first workflow for Mureka Create Music."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        cdp_focus_target_id: str | None = None,
    ) -> None:
        self._settings = settings
        self._cdp_focus_target_id = (cdp_focus_target_id or "").strip() or None
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._page: Any | None = None
        self._clicked_generate = False
        self._result_confirmed = False

    async def aclose(self) -> None:
        """Disconnect Playwright transport without intentionally closing Chrome."""
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Playwright stop failed: %s", exc)
        self._playwright = None
        self._browser = None
        self._page = None

    async def _connect(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(
            self._settings.browser_cdp_url
        )

    def _all_pages(self) -> list[Any]:
        assert self._browser is not None
        pages: list[Any] = []
        for context in self._browser.contexts:
            pages.extend(context.pages)
        return pages

    async def _select_page(self) -> Any:
        assert self._browser is not None
        pages = self._all_pages()
        if not pages:
            if not self._browser.contexts:
                context = await self._browser.new_context()
            else:
                context = self._browser.contexts[0]
            return await context.new_page()

        # 如果指定了 cdp_focus_target_id，我們必須精確找到那個分頁
        if self._cdp_focus_target_id:
            logger.debug("Attempting to find page with specific Target ID: %s", self._cdp_focus_target_id)
            for page in pages:
                try:
                    # 透過 CDP 獲取該 Page 的 Target ID
                    client = await page.context.new_cdp_session(page)
                    target_info = await client.send("Target.getTargetInfo")
                    if target_info.get("targetInfo", {}).get("targetId") == self._cdp_focus_target_id:
                        await client.detach()
                        return page
                    await client.detach()
                except Exception:
                    continue
            logger.warning("Target ID %s not found in current pages, falling back to URL match", self._cdp_focus_target_id)

        # Fallback: 原有的 URL 評分邏輯
        best = max(pages, key=lambda p: _mureka_page_score(p.url or ""))
        if _mureka_page_score(best.url or "") > 0:
            return best
        return pages[-1]

    async def attach_to_logged_in_page(self) -> None:
        await self._connect()
        self._page = await self._select_page()
        self._page.set_default_timeout(self._settings.playwright_action_timeout_sec * 1000)
        await self._page.bring_to_front()

        current_score = _mureka_page_score(self._page.url or "")

        # Playwright CDP 經常看不到已開好的 Mureka 分頁（不同 browser context），
        # 此時 current_score == 0，需要強制將一個現有頁面導航到 Mureka。
        if current_score < 10:
            logger.info(
                "Playwright cannot see Mureka tab (current=%s, score=%s). "
                "Navigating to create URL...",
                self._page.url[:60], current_score,
            )
            try:
                await self._page.goto(
                    self._settings.mureka_create_url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                )
                logger.info("Navigated to: %s", self._page.url)
            except Exception as exc:
                if "ERR_ABORTED" in str(exc):
                    logger.warning("Navigation aborted (ERR_ABORTED), continuing...")
                else:
                    raise
            # 等待頁面完整載入
            await asyncio.sleep(2)
        else:
            logger.info("Playwright using current tab: %s", self._page.url)


        await self._dismiss_soft_overlays()
        if self._settings.require_logged_in_page and await self._looks_like_login_wall():
            raise MurekaPlaywrightError("Please log in manually in a normal browser session first.")

    async def _body_text(self) -> str:
        assert self._page is not None
        try:
            return await self._page.locator("body").inner_text(timeout=3000)
        except Exception:
            return ""

    async def _looks_like_login_wall(self) -> bool:
        text = _norm(await self._body_text())
        login_signals = (
            "try free now",
            "continue with google",
            "sign in",
            "log in",
            "login",
            "登入",
        )
        create_signals = ("generate", "lyrics", "style", "create music", "生成", "歌詞")
        return any(s in text for s in login_signals) and not any(s in text for s in create_signals)

    async def verify_create_music_page(self) -> None:
        assert self._page is not None
        text = _norm(await self._body_text())
        url_score = _mureka_page_score(self._page.url or "")
        signals = sum(
            1
            for s in (
                "generate",
                "lyrics",
                "style",
                "create music",
                "instrumental",
                "生成",
                "歌詞",
                "風格",
                "曲風",
            )
            if s in text
        )
        editable_count = await self._page.locator(
            "input:not([type=hidden]), textarea, [contenteditable=true]"
        ).count()
        if url_score <= 0 or (signals < 2 and editable_count < 2):
            raise MurekaPlaywrightError(
                "Current tab does not look like Mureka Create Music "
                f"(url={self._page.url!r}, signals={signals}, editables={editable_count})."
            )
        logger.info(
            "Playwright verified Mureka page (signals=%s, editables=%s, url=%s)",
            signals,
            editable_count,
            self._page.url,
        )

    async def _dismiss_soft_overlays(self) -> None:
        assert self._page is not None
        names = (
            "Close",
            "Got it",
            "OK",
            "Not now",
            "稍後",
            "關閉",
            "我知道了",
        )
        for name in names:
            try:
                btn = self._page.get_by_role("button", name=re.compile(name, re.I)).first()
                if await btn.count() and await btn.is_visible():
                    await btn.click(timeout=1000)
            except Exception:
                continue

    async def _click_text_if_visible(self, pattern: str) -> bool:
        assert self._page is not None
        try:
            loc = self._page.get_by_text(re.compile(pattern, re.I)).first
            if await loc.count() and await loc.is_visible():
                await loc.click(timeout=1500)
                return True
        except Exception:
            return False
        return False

    async def _select_model_mode(self) -> None:
        mode = self._settings.mureka_model_mode
        if not mode:
            return

        target_model = "V9" if mode in ("v9", "both") else "O2"
        logger.info("Playwright attempting to select model mode: %s", target_model)

        try:
            # 1. 檢查當前選中的模型
            current_model = await self._page.evaluate("""() => {
                const box = document.querySelector('.model-box');
                if (!box) return null;
                return box.innerText.trim().toUpperCase();
            }""")

            if current_model and target_model.upper() in current_model:
                logger.info("Model %s already selected", target_model)
                return

            # 2. 點擊 model-box 下拉按鈕
            model_btn = self._page.locator('.model-box .el-dropdown-link, .model-box button, .model-box [role="button"]').first
            if await model_btn.count() > 0 and await model_btn.is_visible():
                await model_btn.click(timeout=2000)
                await asyncio.sleep(1.0)

                # 3. 在下拉選單中尋找目標模型
                dropdown_item = self._page.locator(f'.el-dropdown-menu__item:has-text("{target_model}"), .el-select-dropdown__item:has-text("{target_model}")').first
                if await dropdown_item.count() > 0:
                    await dropdown_item.click(timeout=2000)
                    logger.info("Selected model %s from dropdown", target_model)
                else:
                    # Fallback: 尋找任何包含 V9/O2 的選項
                    found_any = False
                    for selector in [f'li:has-text("{target_model}")', f'div:has-text("{target_model}")']:
                        loc = self._page.locator(selector).last
                        if await loc.count() > 0 and await loc.is_visible():
                            await loc.click(timeout=1000)
                            logger.info("Selected model %s via fallback: %s", target_model, selector)
                            found_any = True
                            break
                    if not found_any:
                        logger.warning("Model %s not found in dropdown", target_model)
                        await self._page.keyboard.press("Escape")
            else:
                logger.warning("Model dropdown button not found")

        except Exception as exc:
            logger.debug("Error during model selection: %s", exc)

    async def _select_custom_mode_if_needed(self) -> None:
        """Ensure we are in 'Custom' mode (not 'Easy' or 'Soundtrack')."""
        # 先檢查是否已經在 Custom
        is_custom = await self._page.evaluate("""() => {
            const el = document.querySelector('.create-mode-tab-switch-item--active');
            if (!el) return false;
            const txt = el.innerText.trim();
            return txt.includes('Custom') || txt.includes('自訂') || txt.includes('自定義');
        }""")
        if is_custom:
            logger.info("Already on Custom tab, skipping switch")
            return

        # 使用精確的 Mureka class selector（已驗證有效）
        loc = self._page.locator('.create-mode-tab-switch-item:has-text("Custom"), .create-mode-tab-switch-item:has-text("自訂"), .create-mode-tab-switch-item:has-text("自定義")').first
        try:
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=2000)
                await asyncio.sleep(1.5)  # 等待 UI 切換和欄位載入
                logger.info("Playwright switched to Custom tab")
                return
        except Exception as exc:
            logger.debug("Custom tab click via class failed: %s", exc)

        # Fallback: 文字匹配
        for pattern in (r"Custom", r"自訂", r"自定義"):
            if await self._click_text_if_visible(pattern):
                logger.info("Playwright switched to Custom tab via text: %s", pattern)
                await asyncio.sleep(1.5)
                return
        logger.warning("Could not find Custom tab to click")

    async def _select_instrumental_if_needed(self, song_input: SongInput) -> None:
        if not song_input.instrumental:
            return
        for pattern in (r"Instrumental", r"No\s*Lyrics", r"純音樂", r"器樂", r"無歌詞"):
            if await self._click_text_if_visible(pattern):
                logger.info("Playwright selected instrumental mode via %s", pattern)
                return

    async def _fill_semantic_field(
        self,
        *,
        value: str,
        hints: list[str],
        multiline: bool,
        allow_input: bool = True,
    ) -> dict[str, Any]:
        assert self._page is not None
        script = r"""
        ({value, hints, multiline, allowInput}) => {
          const norm = (s) => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
          const visible = (el) => {
            const st = window.getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return st.visibility !== 'hidden' && st.display !== 'none' && r.width > 2 && r.height > 2;
          };
          const setNativeValue = (el, val) => {
            const proto = el instanceof HTMLTextAreaElement
              ? HTMLTextAreaElement.prototype
              : HTMLInputElement.prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) desc.set.call(el, val);
            else el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
          };
          const labelText = (el) => {
            const id = el.getAttribute('id');
            let out = '';
            if (id) {
              const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
              if (lab) out += ' ' + lab.innerText;
            }
            const parent = el.closest('label, [class], [data-testid], [role], div');
            if (parent) out += ' ' + parent.innerText;
            return out;
          };
          const nodes = Array.from(document.querySelectorAll('input, textarea, [contenteditable="true"], [contenteditable=true]'))
            .filter((el) => visible(el) && !el.disabled && el.getAttribute('aria-disabled') !== 'true')
            .filter((el) => {
              const tag = el.tagName.toLowerCase();
              const type = norm(el.getAttribute('type') || 'text');
              const placeholder = norm(el.getAttribute('placeholder') || '');
              
              // Exclude search-related fields
              if (placeholder.includes('search') || placeholder.includes('搜尋')) return false;
              if (el.closest('.search-box') || el.closest('[class*="search"]')) return false;

              if (tag === 'input') {
                if (['hidden', 'submit', 'button', 'checkbox', 'radio', 'file'].includes(type)) return false;
                if (!allowInput) return false;
              }
              if (multiline && tag === 'input') return false;
              return true;
            });
          const scored = nodes.map((el, index) => {
            const hay = norm([
              el.getAttribute('aria-label'),
              el.getAttribute('placeholder'),
              el.getAttribute('name'),
              el.getAttribute('id'),
              el.getAttribute('data-testid'),
              labelText(el),
            ].join(' '));
            let score = 0;
            for (const h0 of hints) {
              const h = norm(h0);
              if (!h) continue;
              if (hay.includes(h)) score += 30;
            }
            if (el.tagName.toLowerCase() === 'textarea') score += multiline ? 8 : 0;
            if (el.getAttribute('contenteditable')) score += 4;
            if (el.tagName.toLowerCase() === 'input') score += multiline ? -10 : 3;
            return { el, index, score, hay };
          }).sort((a, b) => b.score - a.score);
          const picked = scored[0];
          if (!picked || picked.score <= 0) {
            return { ok: false, reason: 'no semantic field match', candidates: scored.slice(0, 5).map(x => ({ score: x.score, hay: x.hay })) };
          }
          picked.el.scrollIntoView({ block: 'center', inline: 'center' });
          picked.el.focus();
          if (picked.el.getAttribute('contenteditable')) {
            picked.el.textContent = value;
            picked.el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
            picked.el.dispatchEvent(new Event('change', { bubbles: true }));
          } else {
            setNativeValue(picked.el, value);
          }
          return { ok: true, score: picked.score, hay: picked.hay, index: picked.index };
        }
        """
        return await self._page.evaluate(
            script,
            {
                "value": value,
                "hints": hints,
                "multiline": multiline,
                "allowInput": allow_input,
            },
        )

    async def _fill_field_direct(self, selector: str, value: str, *, clear_first: bool = True) -> bool:
        """Fill a field using a precise CSS selector. Returns True on success."""
        assert self._page is not None
        try:
            loc = self._page.locator(selector).first
            if await loc.count() == 0 or not await loc.is_visible():
                return False
            if clear_first:
                await loc.click()
                await loc.fill("")
            await loc.fill(value)
            logger.debug("Filled field %s with %d chars", selector, len(value))
            return True
        except Exception as exc:
            logger.debug("_fill_field_direct(%s) failed: %s", selector, exc)
            return False

    async def fill_form(self, song_input: SongInput) -> None:
        await self._dismiss_soft_overlays()
        await self._select_custom_mode_if_needed()
        await self._select_model_mode()
        await self._select_instrumental_if_needed(song_input)

        # ── 1. Lyrics / Structure (textarea) ──
        # Even for instrumental, Mureka accepts musical progression structure in the lyrics box.
        if song_input.lyrics:
            lyrics_ok = await self._fill_field_direct(
                'textarea[placeholder*="lyrics" i]', song_input.lyrics
            )
            if not lyrics_ok:
                # fallback to semantic
                res = await self._fill_semantic_field(
                    value=song_input.lyrics,
                    hints=["lyrics", "lyric", "歌詞", "structure", "progression"],
                    multiline=True, allow_input=False,
                )
                if not res.get("ok"):
                    raise MurekaPlaywrightError(f"Could not fill lyrics field: {res}")
            logger.info("Lyrics/Structure filled (%d chars)", len(song_input.lyrics))

        # ── 2. Style (textarea, placeholder contains "style") ──
        #    Mureka 2026-05: placeholder='Enter style, mood, instrument, etc...'
        style_ok = await self._fill_field_direct(
            'textarea[placeholder*="style" i]', song_input.style_tags
        )
        if not style_ok:
            res = await self._fill_semantic_field(
                value=song_input.style_tags,
                hints=["style", "tags", "genre", "prompt", "description", "風格", "曲風"],
                multiline=True,
            )
            if not res.get("ok"):
                raise MurekaPlaywrightError(f"Could not fill style field: {res}")
        logger.info("Style filled (%d chars)", len(song_input.style_tags))

        # ── 3. Song title (input, placeholder='Song title') ──
        #    CRITICAL: 不能填到右上角的搜尋框 (placeholder='Enter song title' / '輸入歌名')
        #    真正的歌名欄位 placeholder 是 'Song title'（不含 Enter）或 '歌名'
        title_ok = await self._fill_field_direct(
            'input[placeholder="Song title"]', song_input.song_title
        )
        if not title_ok:
            title_ok = await self._fill_field_direct(
                'input[placeholder="歌名"]', song_input.song_title
            )
        if not title_ok:
            # 備選：找到所有 placeholder 含 title 或 歌名 的 input，排除搜尋框
            title_ok = await self._fill_field_direct(
                'input[placeholder*="title" i]:not([placeholder*="Enter song" i])',
                song_input.song_title,
            )
        if not title_ok:
            title_ok = await self._fill_field_direct(
                'input[placeholder*="歌名" i]:not([placeholder*="輸入" i])',
                song_input.song_title,
            )
        if not title_ok:
            # 最後手段：用 JS 精確按 y 座標排除頂部搜尋框
            title_ok = await self._page.evaluate(r"""(titleVal) => {
                const inputs = Array.from(document.querySelectorAll('input'));
                const candidates = inputs.filter(el => {
                    const r = el.getBoundingClientRect();
                    const ph = (el.placeholder || '').toLowerCase();
                    // 排除搜尋框（y < 100 的都是頂部搜尋欄）
                    return r.y > 100 && r.width > 50 && (ph.includes('title') || ph.includes('歌名') || ph.includes('song'));
                });
                if (candidates.length === 0) return false;
                const el = candidates[0];
                const proto = HTMLInputElement.prototype;
                const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                if (desc && desc.set) desc.set.call(el, titleVal);
                else el.value = titleVal;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }""", song_input.song_title)
        if not title_ok:
            raise MurekaPlaywrightError("Could not fill title field (all selectors failed)")

        logger.info("Playwright filled Mureka form for title=%s", song_input.song_title)
        # 等待 Create 按鈕啟用
        await asyncio.sleep(0.5)

    async def submit_generation(self) -> None:
        if self._settings.dry_run:
            logger.info("Playwright skipped Generate click (DRY_RUN=true)")
            return

        assert self._page is not None
        await self._dismiss_soft_overlays()

        # Mureka 2026-05: 底部有一個 <button class="el-button"> 寫著 "Create"
        # 表單未填完時它是 disabled (class 含 is-disabled)
        # 等待它啟用（最多 5 秒）
        create_btn = self._page.locator('button.el-button:has-text("Create"), button.el-button:has-text("Generate"), button.el-button:has-text("生成"), button.el-button:has-text("創作")')
        try:
            await create_btn.first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        # 等待按鈕啟用
        for _ in range(10):
            try:
                btn = create_btn.first
                if await btn.count() > 0 and await btn.is_visible() and await btn.is_enabled():
                    await btn.click(timeout=3000)
                    self._clicked_generate = True
                    logger.info("Playwright clicked Create/Generate button")
                    await self._wait_for_generation_progress()
                    return
            except Exception as exc:
                logger.debug("Create button click attempt failed: %s", exc)
            await asyncio.sleep(0.5)

        # 備選方案：找頁面上任何可見且啟用的 Create/Generate 文字
        for pattern in (r"Create", r"Generate", r"生成", r"創作"):
            try:
                btn = self._page.get_by_role("button", name=re.compile(pattern, re.I)).last
                if await btn.count() > 0 and await btn.is_visible() and await btn.is_enabled():
                    await btn.click(timeout=3000)
                    self._clicked_generate = True
                    logger.info("Playwright clicked button (fallback, pattern=%s)", pattern)
                    await self._wait_for_generation_progress()
                    return
            except Exception:
                continue

        raise MurekaPlaywrightError("Could not find or click a Generate/Create control on the page.")

    async def _wait_for_generation_progress(self) -> None:
        assert self._page is not None
        max_wait = self._settings.playwright_generation_wait_sec
        if max_wait <= 0:
            return
        start_url = self._page.url
        deadline = asyncio.get_running_loop().time() + max_wait
        done_patterns = (
            "download",
            "share",
            "publish",
            "completed",
            "complete",
            "下載",
            "分享",
            "完成",
        )
        progress_patterns = ("generating", "creating", "queue", "生成中", "創作中", "排隊")
        saw_progress = False

        btn = self._page.get_by_role("button", name=re.compile(r"^\s*(Generate|Create|Create Music|生成|創作)\s*$", re.I)).first

        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(5)
            text = _norm(await self._body_text())
            
            # Check button state
            btn_disabled = False
            try:
                if await btn.count() > 0:
                    btn_disabled = not await btn.is_enabled()
            except Exception:
                pass

            if btn_disabled or any(p in text for p in progress_patterns):
                if not saw_progress:
                    logger.info("Playwright detected generation progress (button disabled or progress text found)")
                saw_progress = True
                
            if self._page.url != start_url and _mureka_page_score(self._page.url) > 0:
                self._result_confirmed = True
                return
                
            # If we saw progress, and the button becomes enabled again, or we see done patterns
            if saw_progress:
                if (not btn_disabled) or any(p in text for p in done_patterns):
                    # Make sure it's not just a quick flicker
                    await asyncio.sleep(2)
                    self._result_confirmed = True
                    logger.info("Playwright confirmed generation completion")
                    return

        logger.warning(
            "Playwright did not confirm generation completion within %s seconds; treating submit as accepted.",
            max_wait,
        )

    async def extract_result(self, *, song_input: SongInput) -> SongResult:
        assert self._page is not None
        debug_notes: list[str] = ["engine=playwright"]
        if self._settings.dry_run:
            debug_notes.append("DRY_RUN=true: filled form without clicking Generate")
        elif self._clicked_generate and not self._result_confirmed:
            debug_notes.append("Generate clicked; completion/result URL not confirmed before timeout")

        screenshot_path: str | None = None
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        shot_file = get_screenshots_dir(self._settings) / f"mureka_playwright_{ts}.png"
        try:
            await self._page.screenshot(path=str(shot_file), full_page=True)
            screenshot_path = str(shot_file)
        except Exception as exc:  # noqa: BLE001
            debug_notes.append(f"screenshot_failed:{exc}")

        status = "dry-run filled" if self._settings.dry_run else "submitted"
        if self._result_confirmed:
            status = "generation result detected"

        return SongResult(
            success=True,
            song_title=song_input.song_title,
            result_url=self._page.url,
            status=status,
            error_message=None,
            screenshot_path=screenshot_path,
            debug_notes="; ".join(debug_notes),
            used_profile_path=self._settings.browser_cdp_url,
            login_reused=True,
        )
