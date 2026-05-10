"""
Groq → OpenRouter（隨機）→（可選）Ollama 的 browser-use LLM 自動輪替。

僅在 LLM_PROVIDER=auto 時由 create_browser_llm 使用；Groq 用量平衡為行程內記憶體計數。

說明：Playwright 只做瀏覽器自動化；推論請用雲端 API（Groq／OpenRouter 等）。
本機 Ollama 預設不啟用（見 LLM_AUTO_USE_OLLAMA）。
"""

from __future__ import annotations

import asyncio
import os
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, TypeVar, overload

from pydantic import BaseModel

from app.config import AppSettings
from app.logger import get_logger
from app.services.llm import LLMFactoryError
from browser_use.llm.base import BaseChatModel
from browser_use.llm.exceptions import ModelError, ModelProviderError
from browser_use.llm.messages import BaseMessage
from browser_use.llm.views import ChatInvokeCompletion

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# 依常見 RPD 比例做負載平衡（僅供排序；實際額度以 Groq 為準）
_GROQ_POOL: tuple[dict[str, int | str], ...] = (
    {"model": "google/gemma2-9b-it", "rpd": 14400},
    {"model": "mixtral-8x7b-32768", "rpd": 14400},
    {"model": "llama-3.3-70b-versatile", "rpd": 1000},
)

_OPENROUTER_MODELS: tuple[str, ...] = (
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "deepseek/deepseek-chat",
    "google/gemma-2-9b-it",
)

_groq_usage: defaultdict[str, int] = defaultdict(int)


def _sorted_groq_entries() -> list[dict[str, int | str]]:
    return sorted(
        _GROQ_POOL,
        key=lambda x: _groq_usage[str(x["model"])] / max(int(x["rpd"]), 1),
    )


def _sleep_backoff(attempt: int) -> float:
    return float(min(2**attempt, 32.0))


def _env_truthy(name: str, *, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


@dataclass
class FailoverChatModel(BaseChatModel):
    """依序嘗試 Groq（多模型）→ OpenRouter（每次重試可換隨機模型）→ 可選 Ollama。"""

    groq_api_key: str
    openrouter_api_key: str
    ollama_model: str
    ollama_host: str | None
    use_ollama: bool
    timeout: float | None
    max_retries_per_backend: int = 3
    model: str = "auto-failover"
    _verified_api_keys: bool = True

    @property
    def provider(self) -> str:
        return "auto"

    @property
    def name(self) -> str:
        return str(self.model)

    @overload
    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: None = None,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[str]: ...

    @overload
    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: type[T],
        **kwargs: Any,
    ) -> ChatInvokeCompletion[T]: ...

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: type[T] | None = None,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        from browser_use.llm.groq.chat import ChatGroq
        from browser_use.llm.openrouter.chat import ChatOpenRouter

        last_err: BaseException | None = None

        for entry in _sorted_groq_entries():
            mid = str(entry["model"])
            gkw: dict[str, Any] = {
                "model": mid,
                "api_key": self.groq_api_key,
                "max_retries": 1,
            }
            if self.timeout is not None:
                gkw["timeout"] = float(self.timeout)
            groq_llm = ChatGroq(**gkw)
            for attempt in range(self.max_retries_per_backend):
                try:
                    out = await groq_llm.ainvoke(
                        messages, output_format, **kwargs
                    )
                    _groq_usage[mid] += 1
                    return out
                except ModelError as exc:
                    last_err = exc
                    logger.warning(
                        "Groq model=%s attempt=%s failed: %s",
                        mid,
                        attempt + 1,
                        exc,
                    )
                    await asyncio.sleep(_sleep_backoff(attempt))
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    logger.warning(
                        "Groq model=%s attempt=%s unexpected: %s",
                        mid,
                        attempt + 1,
                        exc,
                    )
                    await asyncio.sleep(_sleep_backoff(attempt))

        for attempt in range(self.max_retries_per_backend):
            or_model = random.choice(_OPENROUTER_MODELS)
            okw: dict[str, Any] = {
                "model": or_model,
                "api_key": self.openrouter_api_key,
                "max_retries": 1,
            }
            if self.timeout is not None:
                okw["timeout"] = float(self.timeout)
            or_llm = ChatOpenRouter(**okw)
            try:
                return await or_llm.ainvoke(messages, output_format, **kwargs)
            except ModelError as exc:
                last_err = exc
                logger.warning(
                    "OpenRouter model=%s attempt=%s failed: %s",
                    or_model,
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(_sleep_backoff(attempt))
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning(
                    "OpenRouter model=%s attempt=%s unexpected: %s",
                    or_model,
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(_sleep_backoff(attempt))

        if self.use_ollama:
            from browser_use.llm.ollama.chat import ChatOllama

            olkw: dict[str, Any] = {"model": self.ollama_model}
            if self.ollama_host:
                olkw["host"] = self.ollama_host
            if self.timeout is not None:
                olkw["timeout"] = float(self.timeout)
            ollama_llm = ChatOllama(**olkw)
            for attempt in range(self.max_retries_per_backend):
                try:
                    return await ollama_llm.ainvoke(messages, output_format, **kwargs)
                except ModelError as exc:
                    last_err = exc
                    logger.warning(
                        "Ollama model=%s attempt=%s failed: %s",
                        self.ollama_model,
                        attempt + 1,
                        exc,
                    )
                    await asyncio.sleep(_sleep_backoff(attempt))
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    logger.warning(
                        "Ollama model=%s attempt=%s unexpected: %s",
                        self.ollama_model,
                        attempt + 1,
                        exc,
                    )
                    await asyncio.sleep(_sleep_backoff(attempt))

        tail = "groq → openrouter → ollama" if self.use_ollama else "groq → openrouter (cloud only)"
        raise ModelProviderError(
            message=(f"Failover LLM exhausted ({tail}). Last error: {last_err!r}"),
            status_code=502,
            model=self.name,
        ) from last_err


def create_failover_browser_llm(settings: AppSettings) -> FailoverChatModel:
    if not settings.groq_api_key or not settings.openrouter_api_key:
        raise LLMFactoryError(
            "LLM_PROVIDER=auto requires GROQ_API_KEY and OPENROUTER_API_KEY."
        )
    ollama_model = (os.getenv("OLLAMA_MODEL") or "llama3.2").strip()
    ollama_host_raw = (os.getenv("OLLAMA_HOST") or "").strip()
    use_ollama = _env_truthy("LLM_AUTO_USE_OLLAMA", default=False)
    to = float(settings.agent_llm_timeout) if settings.agent_llm_timeout else None
    retries_raw = (os.getenv("LLM_FAILOVER_MAX_RETRIES") or "3").strip()
    try:
        max_retries = max(1, int(retries_raw))
    except ValueError:
        max_retries = 3
    return FailoverChatModel(
        groq_api_key=settings.groq_api_key,
        openrouter_api_key=settings.openrouter_api_key,
        ollama_model=ollama_model,
        ollama_host=ollama_host_raw or None,
        use_ollama=use_ollama,
        timeout=to,
        max_retries_per_backend=max_retries,
        model=settings.agent_model.strip() or "auto-failover",
    )
