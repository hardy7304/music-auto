"""
Mureka automation via CDP attach to your already-open, logged-in Chrome session.

Does not perform Google OAuth, bootstrap login, or click Sign in / Try free now / Continue with Google.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.config import AppSettings
from app.logger import get_logger
from app.prompts import mureka_tasks
from app.schemas import SongInput, SongResult
from app.services.llm import create_browser_llm
from app.utils.browser_profile import get_screenshots_dir

logger = get_logger(__name__)

_MAX_AGENT_RETRIES = 2
_RETRY_BACKOFF_SEC = 4.0

_LOGIN_WALL_ERROR = "Please log in manually in a normal browser session first."


def _mureka_tab_score(url: str) -> int:
    """Higher = more likely Mureka Create Music workspace (multi-tab / new-tab safe)."""
    u = (url or "").lower()
    if "mureka" not in u:
        return 0
    score = 10
    for hint in ("music-gen", "create-music", "create_music", "/tools/", "studio", "custom"):
        if hint in u:
            score += 3
    if u.startswith("about:") or "newtab" in u or u in ("chrome://newtab/",):
        return 0
    return score


class LoginWallDetected(BaseModel):
    shows_login_wall: bool
    details: str = ""


class CreateMusicPageOk(BaseModel):
    is_create_music_page: bool
    rationale: str = ""
    observed_signals: str = ""


class GenerateClickResult(BaseModel):
    found_and_clicked_generate: bool
    explanation: str = ""


class MurekaExtractedPage(BaseModel):
    result_url: str = Field(..., description="Current URL")
    song_title: str = Field(..., description="Visible title or empty string")
    status: str = Field(..., description="Visible UI status summary")


class MurekaAgentError(RuntimeError):
    """Raised when the browser agent cannot complete a step."""


class MurekaSongAgent:
    """Attach to existing browser (CDP), then verify Create Music page, fill, submit, extract."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        cdp_focus_target_id: str | None = None,
    ) -> None:
        self._settings = settings
        self._cdp_focus_target_id = (cdp_focus_target_id or "").strip() or None
        self._llm = create_browser_llm(settings)
        self._browser_session = self._build_browser_session(settings)
        self._closed = False

    @staticmethod
    def _build_browser_session(settings: AppSettings) -> Any:
        from browser_use import BrowserSession

        return BrowserSession(
            cdp_url=settings.browser_cdp_url,
            keep_alive=True,
        )

    async def ensure_browser_started(self) -> None:
        await self._browser_session.start()

    async def aclose(self) -> None:
        """Disconnect CDP without killing the user's Chrome process."""
        if self._closed:
            return
        self._closed = True
        try:
            await self._browser_session.stop()
        except Exception as exc:  # noqa: BLE001
            logger.error("Error while stopping browser session: %s", exc)

    def _agent_common_kwargs(self, *, extend_system_append: str | None = None) -> dict[str, Any]:
        base = (
            "Never click Try free now, Sign in, Log in, Continue with Google, or any OAuth/login CTA. "
            "Never type passwords or automate Google account login. "
            "Stay on the current tab: do not navigate, open new tabs, or go to the homepage unless the "
            "user explicitly asked; these tasks assume the page is already correct. "
            "If other empty or unrelated tabs exist, ignore them and never switch to about:blank/new tab."
        )
        if extend_system_append:
            base = f"{base} {extend_system_append}"
        kwargs: dict[str, Any] = {
            "llm": self._llm,
            "browser_session": self._browser_session,
            "flash_mode": True,
            # False: browser-use scans the task string for URLs/domains and injects an initial navigate
            # ("Found URL in task..."). We navigate only via BrowserSession.navigate_to in code.
            "directly_open_url": False,
            "step_timeout": self._settings.agent_step_timeout,
            "max_failures": 5,
            "extend_system_message": base,
        }
        if self._settings.agent_llm_timeout is not None:
            kwargs["llm_timeout"] = self._settings.agent_llm_timeout
        return kwargs

    async def _focus_preferred_mureka_tab_if_needed(self) -> None:
        """
        After CDP connect, browser-use may focus the first page in Chrome's list (often left-most).
        If the user opened new tabs first or order changed, focus can land on about:blank — then agents hang.
        When no explicit parallel target_id, switch to the best-scoring Mureka URL among open tabs.
        """
        sess = self._browser_session
        sm = getattr(sess, "session_manager", None)
        if sm is None:
            return

        await asyncio.sleep(0.35)

        page_targets = sm.get_all_page_targets()
        current_id = sess.agent_focus_target_id

        if current_id:
            cur = sm.get_target(current_id)
            if cur is not None and _mureka_tab_score(cur.url) >= 10:
                logger.info(
                    "CDP 已在 Mureka 分頁（…%s），略過自動切換",
                    str(current_id)[-8:],
                )
                return

        best_id: str | None = None
        best_s = 0
        for t in page_targets:
            s = _mureka_tab_score(t.url)
            if s > best_s:
                best_s = s
                best_id = t.target_id

        if best_id and best_s >= 10 and best_id != current_id:
            from browser_use.browser.events import SwitchTabEvent

            await sess.event_bus.dispatch(SwitchTabEvent(target_id=best_id))
            logger.info(
                "已自動切換至 URL 分數最高的 Mureka 分頁（…%s）",
                str(best_id)[-8:],
            )
        elif best_s < 10:
            logger.warning(
                "未偵測到含 mureka 的已開分頁（目前共 %s 個）。請先開 Create Music 再執行；"
                "執行中請勿新增空白分頁以免 CDP 誤附著在非創作頁。",
                len(page_targets),
            )

    async def _run_agent_with_retries(
        self,
        *,
        task: str,
        max_steps: int,
        extend_system_append: str | None = None,
        **extra: Any,
    ) -> Any:
        from browser_use import Agent

        last_exc: Exception | None = None
        total_attempts = _MAX_AGENT_RETRIES + 1
        for attempt in range(1, total_attempts + 1):
            agent = Agent(
                task,
                max_steps=max_steps,
                **self._agent_common_kwargs(extend_system_append=extend_system_append),
                **extra,
            )
            try:
                return await agent.run()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.error("Agent run failed (attempt %s/%s): %s", attempt, total_attempts, exc)
                if attempt < total_attempts:
                    await asyncio.sleep(_RETRY_BACKOFF_SEC * attempt)
        raise MurekaAgentError(f"Agent failed after {total_attempts} attempts: {last_exc!r}") from last_exc

    async def _run_structured(
        self,
        *,
        task: str,
        schema: type[BaseModel],
        max_steps: int,
    ) -> BaseModel:
        history = await self._run_agent_with_retries(
            task=task,
            max_steps=max_steps,
            output_model_schema=schema,
        )
        structured = history.structured_output
        if structured is None:
            parsed = history.get_structured_output(schema)
            if parsed is not None:
                structured = parsed
        if structured is None:
            raise MurekaAgentError("Structured agent output missing.")
        return structured

    async def attach_to_logged_in_page(self) -> None:
        """
        Connect via CDP. Optionally navigate to MUREKA_CREATE_URL when
        MUREKA_ATTACH_NAVIGATE_FIRST is true; otherwise keep the current tab URL.

        No login automation. If a login funnel is detected (when REQUIRE_LOGGED_IN_PAGE), fail fast.
        """
        await self.ensure_browser_started()
        if self._cdp_focus_target_id:
            from browser_use.browser.events import SwitchTabEvent

            await self._browser_session.event_bus.dispatch(
                SwitchTabEvent(target_id=self._cdp_focus_target_id)
            )
            logger.info(
                "CDP focus switched to target …%s for parallel slot",
                self._cdp_focus_target_id[-6:],
            )
        elif not self._settings.attach_navigate_first:
            await self._focus_preferred_mureka_tab_if_needed()

        if self._settings.attach_navigate_first:
            await self._browser_session.navigate_to(self._settings.mureka_create_url)
            logger.info("Navigated to create URL: %s", self._settings.mureka_create_url)
        else:
            logger.info(
                "Skipping navigate_to (MUREKA_ATTACH_NAVIGATE_FIRST=false); using current browser tab"
            )

        if not self._settings.require_logged_in_page:
            return

        wall = await self._run_structured(
            task=mureka_tasks.task_detect_login_wall(),
            schema=LoginWallDetected,
            max_steps=self._settings.wall_check_max_steps,
        )
        if wall.shows_login_wall:
            logger.error("Login wall detected: %s", wall.details)
            raise MurekaAgentError(_LOGIN_WALL_ERROR)
        logger.info("No login wall detected (details=%s)", (wall.details or "")[:120])

    async def verify_create_music_page(self) -> None:
        """Confirm weak signals for Create Music / Custom workspace."""
        ok = await self._run_structured(
            task=mureka_tasks.task_verify_create_music_page(),
            schema=CreateMusicPageOk,
            max_steps=self._settings.verify_create_max_steps,
        )
        if not ok.is_create_music_page:
            msg = (
                f"目前頁面不像 Mureka Create Music 創作區：{ok.rationale or 'unknown'}. "
                f"觀察：{ok.observed_signals or 'n/a'}"
            )
            raise MurekaAgentError(msg)
        logger.info("Create Music page verified: %s", (ok.rationale or "")[:160])

    async def fill_form(self, song_input: SongInput) -> None:
        """Fill title, lyrics (or instrumental path), style tags; dismiss non-login overlays only."""
        mm = self._settings.mureka_model_mode
        if song_input.instrumental:
            task = mureka_tasks.task_fill_form_instrumental(song_input, model_mode=mm)
            sys_append = mureka_tasks.extend_system_fill_instrumental()
            logger.info("fill_form() instrumental mode (title=%s)", song_input.song_title)
        else:
            task = mureka_tasks.task_fill_form(song_input, model_mode=mm)
            sys_append = mureka_tasks.extend_system_fill_vocal()
        await self._run_agent_with_retries(
            task=task,
            max_steps=self._settings.fill_form_max_steps,
            extend_system_append=sys_append,
        )
        logger.info("fill_form() done for title=%s", song_input.song_title)

    async def submit_generation(self) -> None:
        """DRY_RUN=false: click Generate; otherwise skip. Never perform login actions."""
        if self._settings.dry_run:
            await self._run_agent_with_retries(
                task=mureka_tasks.task_submit_generation_dry_run(),
                max_steps=self._settings.submit_max_steps,
            )
            logger.info("submit_generation() skipped click (DRY_RUN=true)")
            return

        out = await self._run_structured(
            task=mureka_tasks.task_submit_generation_click(),
            schema=GenerateClickResult,
            max_steps=self._settings.submit_max_steps,
        )
        if not out.found_and_clicked_generate:
            raise MurekaAgentError(
                out.explanation.strip()
                if (out.explanation and out.explanation.strip())
                else "Could not find or click a Generate control on the page."
            )

        await self._run_agent_with_retries(
            task=mureka_tasks.task_wait_generation_settle(),
            max_steps=self._settings.settle_max_steps,
        )
        logger.info("submit_generation() clicked Generate and waited for settle")

    async def extract_result(self, *, song_input: SongInput) -> SongResult:
        """Screenshot + structured fields -> SongResult."""
        debug_notes: list[str] = []
        if self._settings.dry_run:
            debug_notes.append("DRY_RUN=true：未執行 Generate 點擊（若設定正確）。")

        screenshot_path: str | None = None
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        shot_file = get_screenshots_dir(self._settings) / f"mureka_{ts}.png"
        cdp_ref = self._settings.browser_cdp_url

        try:
            extracted = await self._run_structured(
                task=mureka_tasks.task_extract_page(),
                schema=MurekaExtractedPage,
                max_steps=self._settings.extract_max_steps,
            )
        except Exception as exc:  # noqa: BLE001
            try:
                await self._browser_session.take_screenshot(path=str(shot_file))
                screenshot_path = str(shot_file)
            except Exception as shot_exc:  # noqa: BLE001
                debug_notes.append(f"screenshot_after_extract_fail:{shot_exc}")
            return SongResult(
                success=False,
                song_title=song_input.song_title,
                result_url=None,
                status=None,
                error_message=str(exc),
                screenshot_path=screenshot_path,
                debug_notes="; ".join(debug_notes) if debug_notes else None,
                used_profile_path=cdp_ref,
                login_reused=False,
            )

        try:
            await self._browser_session.take_screenshot(path=str(shot_file))
            screenshot_path = str(shot_file)
        except Exception as exc:  # noqa: BLE001
            debug_notes.append(f"screenshot_failed:{exc}")

        return SongResult(
            success=True,
            song_title=extracted.song_title or song_input.song_title,
            result_url=extracted.result_url,
            status=extracted.status,
            error_message=None,
            screenshot_path=screenshot_path,
            debug_notes="; ".join(debug_notes) if debug_notes else None,
            used_profile_path=cdp_ref,
            login_reused=False,
        )
