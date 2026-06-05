"""Load and validate environment-driven configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when required settings are missing or invalid."""


MurekaModelMode = Literal["v9", "o2", "both"]
LlmProvider = Literal["google", "groq", "openrouter", "nvidia", "deepseek", "auto"]
AutomationEngine = Literal["playwright", "browser_use", "auto"]


def _require(name: str, value: str | None) -> str:
    if value is None or not str(value).strip():
        raise ConfigurationError(
            f"Missing or empty required environment variable: {name}. "
            f"Copy .env.example to .env and set a non-empty value."
        )
    return str(value).strip()


def _bool_env(raw: str | None, *, default: bool) -> bool:
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _strip_opt(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _normalize_notion_database_id(raw: str) -> str:
    """Accept raw id or pasted Notion URL fragment (strip ?view=…)."""
    s = raw.strip()
    if not s:
        return s
    if "?" in s:
        s = s.split("?", 1)[0].strip()
    return s


@dataclass(frozen=True, slots=True)
class NotionFieldMap:
    """
    Notion database property names — must match columns exactly.
    """

    title_property: str
    lyrics_property: str | None
    style_property: str | None
    result_url_property: str | None
    status_property: str | None
    error_property: str | None
    notes_property: str | None
    success_property: str | None
    generated_at_property: str | None
    vocal_property: str | None


@dataclass(frozen=True, slots=True)
class NotionStatusOptions:
    """How NOTION_PROP_STATUS is written: Notion「狀態」欄位 vs plain rich_text."""

    use_notion_status_type: bool
    value_running: str
    value_done: str
    value_failed: str


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Application settings sourced from the environment."""

    llm_provider: LlmProvider
    gemini_api_key: str
    gemma_api_key: str | None
    groq_api_key: str | None
    openrouter_api_key: str | None
    nvidia_api_key: str | None
    deepseek_api_key: str | None
    agent_model: str
    notion_token: str | None
    notion_database_id: str | None
    notion_fields: NotionFieldMap
    notion_status: NotionStatusOptions
    notion_instrumental_vocal_label: str
    browser_cdp_url: str
    headless: bool
    dry_run: bool
    mureka_base_url: str
    mureka_create_url: str
    attach_navigate_first: bool
    require_logged_in_page: bool
    agent_step_timeout: int
    agent_llm_timeout: int | None
    agent_max_steps: int
    wall_check_max_steps: int
    verify_create_max_steps: int
    fill_form_max_steps: int
    submit_max_steps: int
    settle_max_steps: int
    extract_max_steps: int
    screenshots_dir: str
    mureka_model_mode: MurekaModelMode
    notion_parallel_max: int
    notion_run_limit: int
    automation_engine: AutomationEngine
    browser_use_fallback: bool
    playwright_action_timeout_sec: int
    playwright_generation_wait_sec: int
    auto_launch_chrome: bool
    chrome_exe_path: str
    chrome_user_data_dir: str
    google_sheet_url: str
    download_dir: str
    download_max_parallel: int
    download_retry_count: int
    auto_download_after_generate: bool
    download_profile: str
    download_commercial_license: bool
    download_wav: bool
    download_stems_midi: bool
    download_video: bool
    download_max_file_size_mb: int
    nas_sync_path: str | None
    r2_account_id: str | None
    r2_access_key_id: str | None
    r2_secret_access_key: str | None
    r2_bucket_name: str | None
    cloudflare_account_id: str | None
    cloudflare_api_token: str | None
    cloudflare_d1_database_id: str | None
    r2_public_url: str | None


def google_api_key_for_browser_llm(settings: AppSettings) -> str:
    """
    Same Google AI Studio key works for both Gemini and Gemma on the Generative Language API.
    """
    model_l = settings.agent_model.strip().lower()
    if model_l.startswith("gemma") and settings.gemma_api_key:
        return settings.gemma_api_key
    return settings.gemini_api_key


def load_settings(*, env_path: str | None = None) -> AppSettings:
    """Load `.env` and build AppSettings."""
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    engine_raw = (os.getenv("AUTOMATION_ENGINE") or "playwright").strip().lower()
    if engine_raw not in ("playwright", "browser_use", "auto"):
        engine_raw = "playwright"
    automation_engine: AutomationEngine = engine_raw  # type: ignore[assignment]
    browser_use_fallback = _bool_env(os.getenv("BROWSER_USE_FALLBACK"), default=False)
    needs_llm = automation_engine in ("browser_use", "auto") or browser_use_fallback

    prov_raw = (os.getenv("LLM_PROVIDER") or "google").strip().lower()
    if prov_raw not in ("google", "groq", "openrouter", "nvidia", "deepseek", "auto"):
        prov_raw = "google"
    llm_provider: LlmProvider = prov_raw  # type: ignore[assignment]

    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    nvidia_api_key: str | None = None
    deepseek_api_key: str | None = None
    gemini = ""

    if llm_provider == "google" and needs_llm:
        gemini = _require("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    elif llm_provider == "google":
        gemini = os.getenv("GEMINI_API_KEY", "").strip()
    elif llm_provider == "groq" and needs_llm:
        groq_api_key = _require("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    elif llm_provider == "groq":
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip() or None
    elif llm_provider == "auto" and needs_llm:
        groq_api_key = _require("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
        openrouter_api_key = _require("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY"))
        gemini = os.getenv("GEMINI_API_KEY", "").strip()
    elif llm_provider == "auto":
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip() or None
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "").strip() or None
        gemini = os.getenv("GEMINI_API_KEY", "").strip()
    elif llm_provider == "nvidia":
        nvidia_api_key = _require("NVIDIA_API_KEY", os.getenv("NVIDIA_API_KEY"))
    elif llm_provider == "deepseek":
        deepseek_api_key = _require("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY"))
    elif needs_llm:
        openrouter_api_key = _require("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY"))
    else:
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "").strip() or None

    gemma_raw = os.getenv("GEMMA_API_KEY", "").strip()
    gemma_api_key = gemma_raw or None

    if llm_provider == "google":
        agent_model = os.getenv("AGENT_MODEL", "gemma-4-31b-it").strip()
    elif llm_provider == "groq":
        agent_model = os.getenv("AGENT_MODEL", "llama-3.3-70b-versatile").strip()
    elif llm_provider == "auto":
        agent_model = os.getenv("AGENT_MODEL", "auto-failover").strip()
    elif llm_provider == "nvidia":
        agent_model = os.getenv("AGENT_MODEL", "deepseek-ai/deepseek-v3").strip()
    elif llm_provider == "deepseek":
        agent_model = os.getenv("AGENT_MODEL", "deepseek-chat").strip()
    else:
        agent_model = os.getenv("AGENT_MODEL", "meta-llama/llama-3.3-70b-instruct").strip()

    n_token = os.getenv("NOTION_TOKEN", "").strip() or None
    n_db_raw = os.getenv("NOTION_DATABASE_ID", "").strip()
    n_db = _normalize_notion_database_id(n_db_raw) if n_db_raw else None

    notion_fields = NotionFieldMap(
        title_property=os.getenv("NOTION_TITLE_PROPERTY", "Name").strip() or "Name",
        lyrics_property=_strip_opt(os.getenv("NOTION_PROP_LYRICS")),
        style_property=_strip_opt(os.getenv("NOTION_PROP_STYLE")),
        result_url_property=_strip_opt(os.getenv("NOTION_PROP_RESULT_URL")),
        status_property=_strip_opt(os.getenv("NOTION_PROP_STATUS")),
        error_property=_strip_opt(os.getenv("NOTION_PROP_ERROR")),
        notes_property=_strip_opt(os.getenv("NOTION_PROP_NOTES")),
        success_property=_strip_opt(os.getenv("NOTION_PROP_SUCCESS")),
        generated_at_property=_strip_opt(os.getenv("NOTION_PROP_GENERATED_AT")),
        vocal_property=_strip_opt(os.getenv("NOTION_PROP_VOCAL")),
    )

    notion_instrumental_vocal_label = (
        os.getenv("NOTION_INSTRUMENTAL_VOCAL_LABEL", "純音樂") or "純音樂"
    ).strip()

    _sk = (os.getenv("NOTION_PROP_STATUS_KIND", "status") or "status").strip().lower()
    notion_status = NotionStatusOptions(
        use_notion_status_type=_sk in ("status", "native", "notion"),
        value_running=(os.getenv("NOTION_STATUS_VALUE_RUNNING", "編曲中") or "編曲中").strip(),
        value_done=(os.getenv("NOTION_STATUS_VALUE_DONE", "完成") or "完成").strip(),
        value_failed=(os.getenv("NOTION_STATUS_VALUE_FAILED", "草稿修改") or "草稿修改").strip(),
    )

    browser_cdp_url = os.getenv("BROWSER_CDP_URL", "http://127.0.0.1:9222").strip()
    headless = _bool_env(os.getenv("BROWSER_HEADLESS"), default=False)
    dry_run = _bool_env(os.getenv("DRY_RUN"), default=True)

    mureka_base_url = os.getenv("MUREKA_BASE_URL", "https://www.mureka.ai").strip()
    mureka_create_url = os.getenv("MUREKA_CREATE_URL", "https://www.mureka.ai/create").strip()

    attach_navigate_first = _bool_env(os.getenv("MUREKA_ATTACH_NAVIGATE_FIRST"), default=False)
    require_logged_in_page = _bool_env(os.getenv("REQUIRE_LOGGED_IN_PAGE"), default=True)

    step_timeout = int(os.getenv("AGENT_STEP_TIMEOUT", "240"))
    llm_timeout_raw = os.getenv("AGENT_LLM_TIMEOUT", "").strip()
    llm_timeout: int | None = int(llm_timeout_raw) if llm_timeout_raw else None

    max_steps = int(os.getenv("AGENT_MAX_STEPS", "120"))
    wall_check_max_steps = int(os.getenv("AGENT_WALL_CHECK_MAX_STEPS", "10"))
    verify_create_max_steps = int(os.getenv("AGENT_VERIFY_CREATE_MAX_STEPS", "15"))
    fill_form_max_steps = int(os.getenv("AGENT_FILL_MAX_STEPS", "45"))
    submit_max_steps = int(os.getenv("AGENT_SUBMIT_MAX_STEPS", "25"))
    settle_max_steps = int(os.getenv("AGENT_SETTLE_MAX_STEPS", "80"))
    extract_max_steps = int(os.getenv("AGENT_EXTRACT_MAX_STEPS", "25"))

    screenshots_dir = os.getenv("SCREENSHOTS_DIR", "screenshots").strip()

    _mmm = (os.getenv("MUREKA_MODEL_MODE", "both") or "both").strip().lower()
    mureka_model_mode: MurekaModelMode = _mmm if _mmm in ("v9", "o2", "both") else "both"

    notion_parallel_max = int(os.getenv("NOTION_PARALLEL_MAX", "1") or "1")
    notion_parallel_max = max(1, min(10, notion_parallel_max))
    notion_run_limit = int(os.getenv("NOTION_RUN_LIMIT", "0") or "0")
    notion_run_limit = max(0, notion_run_limit)

    playwright_action_timeout_sec = int(os.getenv("PLAYWRIGHT_ACTION_TIMEOUT_SEC", "12"))
    playwright_generation_wait_sec = int(os.getenv("PLAYWRIGHT_GENERATION_WAIT_SEC", "10"))

    auto_launch_chrome = _bool_env(os.getenv("AUTO_LAUNCH_CHROME"), default=True)
    chrome_exe_path = os.getenv("CHROME_EXE_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe").strip()
    chrome_user_data_dir = os.getenv("CHROME_USER_DATA_DIR", "").strip()

    google_sheet_url = os.getenv("GOOGLE_SHEET_URL", "").strip()

    download_dir = os.getenv("DOWNLOAD_DIR", "../downloads").strip()
    download_max_parallel = max(1, min(10, int(os.getenv("DOWNLOAD_MAX_PARALLEL", "3") or "3")))
    download_retry_count = max(0, min(5, int(os.getenv("DOWNLOAD_RETRY_COUNT", "3") or "3")))
    auto_download_after_generate = _bool_env(os.getenv("AUTO_DOWNLOAD_AFTER_GENERATE"), default=False)

    _dp = (os.getenv("DOWNLOAD_PROFILE", "basic") or "basic").strip().lower()
    download_profile = _dp if _dp in ("basic", "archive", "full", "video", "custom") else "basic"
    download_commercial_license = _bool_env(os.getenv("DOWNLOAD_COMMERCIAL_LICENSE"), default=True)
    download_wav = _bool_env(os.getenv("DOWNLOAD_WAV"), default=False)
    download_stems_midi = _bool_env(os.getenv("DOWNLOAD_STEMS_MIDI"), default=False)
    download_video = _bool_env(os.getenv("DOWNLOAD_VIDEO"), default=False)
    download_max_file_size_mb = int(os.getenv("DOWNLOAD_MAX_FILE_SIZE_MB", "300") or "300")

    nas_sync_path = os.getenv("NAS_SYNC_PATH", "").strip() or None
    r2_account_id = _strip_opt(os.getenv("R2_ACCOUNT_ID"))
    r2_access_key_id = _strip_opt(os.getenv("R2_ACCESS_KEY_ID"))
    r2_secret_access_key = _strip_opt(os.getenv("R2_SECRET_ACCESS_KEY"))
    r2_bucket_name = _strip_opt(os.getenv("R2_BUCKET_NAME"))
    cloudflare_account_id = _strip_opt(os.getenv("CLOUDFLARE_ACCOUNT_ID"))
    cloudflare_api_token = _strip_opt(os.getenv("CLOUDFLARE_API_TOKEN"))
    cloudflare_d1_database_id = _strip_opt(os.getenv("CLOUDFLARE_D1_DATABASE_ID"))

    return AppSettings(
        llm_provider=llm_provider,
        gemini_api_key=gemini,
        gemma_api_key=gemma_api_key,
        groq_api_key=groq_api_key,
        openrouter_api_key=openrouter_api_key,
        nvidia_api_key=nvidia_api_key,
        deepseek_api_key=deepseek_api_key,
        agent_model=agent_model,
        notion_token=n_token,
        notion_database_id=n_db,
        notion_fields=notion_fields,
        notion_status=notion_status,
        notion_instrumental_vocal_label=notion_instrumental_vocal_label,
        browser_cdp_url=browser_cdp_url,
        headless=headless,
        dry_run=dry_run,
        mureka_base_url=mureka_base_url,
        mureka_create_url=mureka_create_url,
        attach_navigate_first=attach_navigate_first,
        require_logged_in_page=require_logged_in_page,
        agent_step_timeout=step_timeout,
        agent_llm_timeout=llm_timeout,
        agent_max_steps=max_steps,
        wall_check_max_steps=wall_check_max_steps,
        verify_create_max_steps=verify_create_max_steps,
        fill_form_max_steps=fill_form_max_steps,
        submit_max_steps=submit_max_steps,
        settle_max_steps=settle_max_steps,
        extract_max_steps=extract_max_steps,
        screenshots_dir=screenshots_dir,
        mureka_model_mode=mureka_model_mode,
        notion_parallel_max=notion_parallel_max,
        notion_run_limit=notion_run_limit,
        automation_engine=automation_engine,
        browser_use_fallback=browser_use_fallback,
        playwright_action_timeout_sec=playwright_action_timeout_sec,
        playwright_generation_wait_sec=playwright_generation_wait_sec,
        auto_launch_chrome=auto_launch_chrome,
        chrome_exe_path=chrome_exe_path,
        chrome_user_data_dir=chrome_user_data_dir,
        google_sheet_url=google_sheet_url,
        download_dir=download_dir,
        download_max_parallel=download_max_parallel,
        download_retry_count=download_retry_count,
        auto_download_after_generate=auto_download_after_generate,
        download_profile=download_profile,
        download_commercial_license=download_commercial_license,
        download_wav=download_wav,
        download_stems_midi=download_stems_midi,
        download_video=download_video,
        download_max_file_size_mb=download_max_file_size_mb,
        nas_sync_path=nas_sync_path,
        r2_account_id=r2_account_id,
        r2_access_key_id=r2_access_key_id,
        r2_secret_access_key=r2_secret_access_key,
        r2_bucket_name=r2_bucket_name,
        cloudflare_account_id=cloudflare_account_id,
        cloudflare_api_token=cloudflare_api_token,
        cloudflare_d1_database_id=cloudflare_d1_database_id,
        r2_public_url=_strip_opt(os.getenv("R2_PUBLIC_URL")),
    )
