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
    for hint in ("music-gen", "create-music", "create_music", "/tools/", "studio", "custom"):
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

        target_url: str | None = None
        if self._cdp_focus_target_id:
            try:
                target_url = await get_page_target_url_by_id_async(
                    self._settings.browser_cdp_url,
                    self._cdp_focus_target_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not resolve CDP target url: %s", exc)

        if target_url:
            target_url_l = target_url.lower()
            for page in pages:
                if (page.url or "").lower() == target_url_l:
                    return page
            for page in pages:
                if target_url_l and target_url_l in (page.url or "").lower():
                    return page

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
        if self._settings.attach_navigate_first or current_score < 10:
            await self._page.goto(self._settings.mureka_create_url, wait_until="domcontentloaded")
            logger.info("Playwright navigated to create URL: %s", self._settings.mureka_create_url)
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
            loc = self._page.get_by_text(re.compile(pattern, re.I)).first()
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
        
        script = """
        (targetModel) => {
            const visible = (el) => {
                if (!el) return false;
                const st = window.getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return st.visibility !== 'hidden' && st.display !== 'none' && r.width > 2 && r.height > 2;
            };
            
            const knownModels = ['V9', 'O2', 'V8', 'V7.6', 'V7.5'];
            let elements = Array.from(document.querySelectorAll('button, div, span, a')).filter(el => {
                if (!visible(el) || el.childElementCount > 3) return false;
                if (el.closest('.audio-item-box') || el.closest('.song-audio-item') || el.classList.contains('audio-item-model')) return false;
                const txt = el.innerText.trim().toUpperCase();
                if (txt.length > 40) return false;
                return knownModels.some(m => txt.includes(m) || txt === m);
            });
            
            if (elements.length === 0) return null;
            elements.sort((a, b) => a.getBoundingClientRect().y - b.getBoundingClientRect().y);
            
            const targetElements = elements.filter(el => el.innerText.trim().toUpperCase().includes(targetModel.toUpperCase()));
            const otherElements = elements.filter(el => !el.innerText.trim().toUpperCase().includes(targetModel.toUpperCase()));
            
            let bestEl = null;
            let status = 'none';
            
            if (targetElements.length > 0 && otherElements.length === 0) {
                // Already selected
                return { status: 'already_selected' };
            }
            
            if (targetElements.length > 0) {
                bestEl = targetElements[0];
                status = 'clicked_target';
            } else if (otherElements.length > 0) {
                bestEl = otherElements[0];
                status = 'opened_menu';
            }
            
            if (bestEl) {
                const r = bestEl.getBoundingClientRect();
                return { 
                    status: status,
                    x: r.left + r.width / 2,
                    y: r.top + r.height / 2
                };
            }
            return null;
        }
        """
        
        try:
            res = await self._page.evaluate(script, target_model)
            if not res:
                logger.warning("Playwright could not find any model selector elements")
                return

            if res['status'] == 'already_selected':
                logger.info("Playwright confirmed %s is already selected", target_model)
                return

            # 使用 Playwright 的滑鼠點擊座標，這比 JS .click() 更強大
            logger.info("Playwright clicking at (%s, %s) to %s", res['x'], res['y'], res['status'])
            await self._page.mouse.click(res['x'], res['y'])
            
            if res['status'] == 'opened_menu':
                await asyncio.sleep(0.8) # 等待選單動畫
                res2 = await self._page.evaluate(script, target_model)
                if res2 and res2['status'] == 'clicked_target':
                    logger.info("Playwright clicking target %s at (%s, %s)", target_model, res2['x'], res2['y'])
                    await self._page.mouse.click(res2['x'], res2['y'])
                else:
                    logger.warning("Playwright opened menu but could not find target %s", target_model)
            else:
                logger.info("Playwright successfully clicked %s", target_model)

        except Exception as exc:
            logger.debug("Error during model selection: %s", exc)

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
              if (tag === 'input') {
                const type = norm(el.getAttribute('type') || 'text');
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

    async def fill_form(self, song_input: SongInput) -> None:
        await self._dismiss_soft_overlays()
        await self._select_model_mode()
        await self._select_instrumental_if_needed(song_input)

        title = await self._fill_semantic_field(
            value=song_input.song_title,
            hints=["title", "song title", "name", "標題", "歌名"],
            multiline=False,
        )
        if not title.get("ok"):
            raise MurekaPlaywrightError(f"Could not fill title field: {title}")

        if not song_input.instrumental:
            lyrics = await self._fill_semantic_field(
                value=song_input.lyrics,
                hints=["lyrics", "lyric", "歌詞"],
                multiline=True,
                allow_input=False,
            )
            if not lyrics.get("ok"):
                raise MurekaPlaywrightError(f"Could not fill lyrics field: {lyrics}")

        style = await self._fill_semantic_field(
            value=song_input.style_tags,
            hints=["style", "tags", "genre", "prompt", "description", "風格", "曲風"],
            multiline=True,
        )
        if not style.get("ok"):
            style = await self._fill_semantic_field(
                value=song_input.style_tags,
                hints=["style", "tags", "genre", "prompt", "description", "風格", "曲風"],
                multiline=False,
            )
        if not style.get("ok"):
            raise MurekaPlaywrightError(f"Could not fill style field: {style}")

        logger.info("Playwright filled Mureka form for title=%s", song_input.song_title)

    async def submit_generation(self) -> None:
        if self._settings.dry_run:
            logger.info("Playwright skipped Generate click (DRY_RUN=true)")
            return

        assert self._page is not None
        await self._dismiss_soft_overlays()
        button_patterns = (
            r"^\s*Generate\s*$",
            r"^\s*Create\s*$",
            r"^\s*Create Music\s*$",
            r"^\s*生成\s*$",
            r"^\s*創作\s*$",
        )
        for pattern in button_patterns:
            try:
                btn = self._page.get_by_role("button", name=re.compile(pattern, re.I)).first
                if await btn.count() > 0 and await btn.is_visible() and await btn.is_enabled():
                    await btn.click(timeout=self._settings.playwright_action_timeout_sec * 1000)
                    self._clicked_generate = True
                    logger.info("Playwright clicked Generate button")
                    await self._wait_for_generation_progress()
                    return
            except Exception as exc:  # noqa: BLE001
                logger.debug("Generate button pattern failed (%s): %s", pattern, exc)

        raise MurekaPlaywrightError("Could not find or click a Generate control on the page.")

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
