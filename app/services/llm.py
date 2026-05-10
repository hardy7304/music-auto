"""Factory for browser-use LLM backends (Google Gemini/Gemma, Groq, OpenRouter)."""

from __future__ import annotations

from app.config import AppSettings, google_api_key_for_browser_llm
from app.logger import get_logger

logger = get_logger(__name__)

# Tried after the preferred AGENT_MODEL if ChatGoogle init fails (wrong id, quota, region, etc.).
# Order: Gemma 26B/31B first, then Gemini flash/pro/lite (ids 以 Google AI Studio / genai 為準).
_FALLBACK_MODELS: tuple[str, ...] = (
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-flash-latest",
    "gemini-2.0-flash",
)


class LLMFactoryError(RuntimeError):
    """Raised when no compatible browser-use LLM could be constructed."""


def create_gemini_browser_llm(api_key: str, *, model: str) -> object:
    """
    Build a browser-use ``ChatGoogle`` instance.

    Uses ``model`` first (e.g. ``gemma-4-31b-it``, ``gemma-4-26b-a4b-it``, ``gemini-2.5-flash``), then fallbacks.
    Same API key as ``GEMINI_API_KEY`` (or ``GEMMA_API_KEY`` when configured in settings).
    """
    last_error: Exception | None = None

    try:
        from browser_use import ChatGoogle
    except ImportError as exc:  # pragma: no cover - environment specific
        raise LLMFactoryError(
            "browser_use is not installed or failed to import. "
            "Install dependencies from requirements.txt."
        ) from exc

    preferred = model.strip()
    candidates = [preferred] + [m for m in _FALLBACK_MODELS if m != preferred]

    for model_name in candidates:
        try:
            llm = ChatGoogle(model=model_name, api_key=api_key)
            logger.info("Initialized ChatGoogle with model=%s", model_name)
            return llm
        except Exception as exc:  # noqa: BLE001 - aggregate attempts
            logger.warning("Failed to init ChatGoogle model=%s: %s", model_name, exc)
            last_error = exc

    raise LLMFactoryError(
        f"Could not initialize ChatGoogle after trying: {', '.join(candidates)}. "
        f"Last error: {last_error!r}"
    )


def create_browser_llm(settings: AppSettings) -> object:
    """
    Build the browser-use LLM for ``MurekaSongAgent`` from ``LLM_PROVIDER``.

    - ``google``: ChatGoogle (Gemini / Gemma via Generative Language API).
    - ``groq``: ChatGroq (see Groq model ids).
    - ``openrouter``: ChatOpenRouter (OpenRouter model slug, e.g. ``meta-llama/...``).
    - ``auto``: Groq → OpenRouter → Ollama failover (see ``llm_manager``).
    """
    provider = settings.llm_provider
    model = settings.agent_model.strip()
    to = settings.agent_llm_timeout

    if provider == "auto":
        from app.services.llm_manager import create_failover_browser_llm

        return create_failover_browser_llm(settings)

    if provider == "google":
        return create_gemini_browser_llm(
            google_api_key_for_browser_llm(settings),
            model=model,
        )

    if provider == "groq":
        if not settings.groq_api_key:
            raise LLMFactoryError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")
        from browser_use.llm.groq.chat import ChatGroq

        kwargs: dict = {"model": model, "api_key": settings.groq_api_key}
        if to is not None:
            kwargs["timeout"] = float(to)
        llm = ChatGroq(**kwargs)
        logger.info("Initialized ChatGroq with model=%s", model)
        return llm

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMFactoryError(
                "OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter."
            )
        from browser_use.llm.openrouter.chat import ChatOpenRouter

        kwargs: dict = {"model": model, "api_key": settings.openrouter_api_key}
        if to is not None:
            kwargs["timeout"] = float(to)
        llm = ChatOpenRouter(**kwargs)
        logger.info("Initialized ChatOpenRouter with model=%s", model)
        return llm

    if provider == "nvidia":
        if not settings.nvidia_api_key:
            raise LLMFactoryError("NVIDIA_API_KEY is required when LLM_PROVIDER=nvidia.")
        from browser_use import ChatOpenAI

        kwargs: dict = {
            "model": model,
            "api_key": settings.nvidia_api_key,
            "base_url": "https://integrate.api.nvidia.com/v1",
        }
        if to is not None:
            kwargs["timeout"] = float(to)
        llm = ChatOpenAI(**kwargs)
        logger.info("Initialized NVIDIA ChatOpenAI with model=%s", model)
        return llm

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise LLMFactoryError("DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek.")
        from browser_use import ChatOpenAI

        kwargs: dict = {
            "model": model,
            "api_key": settings.deepseek_api_key,
            "base_url": "https://api.deepseek.com",
        }
        if to is not None:
            kwargs["timeout"] = float(to)
        llm = ChatOpenAI(**kwargs)
        logger.info("Initialized DeepSeek ChatOpenAI with model=%s", model)
        return llm

    raise LLMFactoryError(f"Unsupported LLM_PROVIDER: {provider!r}")
