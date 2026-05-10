"""List Chrome page target ids via DevTools HTTP API (no browser_use session required)."""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

import httpx


def _cdp_list_url(browser_cdp_url: str) -> str:
    raw = (browser_cdp_url or "").strip()
    if not raw:
        raise ValueError("BROWSER_CDP_URL is empty")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = "http://" + raw.lstrip("/")
    p = urlparse(raw)
    host = p.hostname or "127.0.0.1"
    port = p.port or 9222
    return f"http://{host}:{port}/json/list"


def _cdp_version_url(browser_cdp_url: str) -> str:
    raw = (browser_cdp_url or "").strip()
    if not raw:
        raise ValueError("BROWSER_CDP_URL is empty")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = "http://" + raw.lstrip("/")
    p = urlparse(raw)
    host = p.hostname or "127.0.0.1"
    port = p.port or 9222
    return f"http://{host}:{port}/json/version"


def check_chrome_debugger(
    browser_cdp_url: str,
    *,
    timeout_sec: float = 3.0,
) -> dict:
    """Return Chrome DevTools /json/version response, or raise with the connection error."""
    url = _cdp_version_url(browser_cdp_url)
    with httpx.Client(timeout=timeout_sec) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected CDP /json/version response from {url}")
    return data


async def check_chrome_debugger_async(
    browser_cdp_url: str,
    *,
    timeout_sec: float = 3.0,
) -> dict:
    """Async variant for preflight checks before touching Notion rows."""
    return await asyncio.to_thread(
        check_chrome_debugger,
        browser_cdp_url,
        timeout_sec=timeout_sec,
    )


def list_page_target_ids_matching_url(
    browser_cdp_url: str,
    *,
    url_substrings: tuple[str, ...] = ("mureka",),
    timeout_sec: float = 10.0,
) -> list[str]:
    """
    Return target ``id`` values for ``type==page`` whose URL contains any substring (case-insensitive).

    Tab order follows Chrome's ``/json/list`` response (typically left-to-right).
    """
    url = _cdp_list_url(browser_cdp_url)
    subs_l = tuple(s.lower() for s in url_substrings if s)
    with httpx.Client(timeout=timeout_sec) as client:
        r = client.get(url)
        r.raise_for_status()
        items = r.json()
    out: list[str] = []
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("type") != "page":
            continue
        u = (it.get("url") or "").lower()
        if subs_l and not any(s in u for s in subs_l):
            continue
        tid = it.get("id")
        if tid:
            out.append(str(tid))
    return out


def get_page_target_url_by_id(
    browser_cdp_url: str,
    target_id: str,
    *,
    timeout_sec: float = 10.0,
) -> str | None:
    """Return the current URL for a Chrome DevTools page target id."""
    wanted = (target_id or "").strip()
    if not wanted:
        return None
    url = _cdp_list_url(browser_cdp_url)
    with httpx.Client(timeout=timeout_sec) as client:
        r = client.get(url)
        r.raise_for_status()
        items = r.json()
    if not isinstance(items, list):
        return None
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("type") == "page" and str(it.get("id") or "") == wanted:
            return str(it.get("url") or "")
    return None


async def list_page_target_ids_matching_url_async(
    browser_cdp_url: str,
    *,
    url_substrings: tuple[str, ...] = ("mureka",),
    timeout_sec: float = 10.0,
) -> list[str]:
    """Async variant for use from ``async_main`` without blocking the event loop."""
    return await asyncio.to_thread(
        list_page_target_ids_matching_url,
        browser_cdp_url,
        url_substrings=url_substrings,
        timeout_sec=timeout_sec,
    )


async def get_page_target_url_by_id_async(
    browser_cdp_url: str,
    target_id: str,
    *,
    timeout_sec: float = 10.0,
) -> str | None:
    """Async variant for resolving a Chrome DevTools target id to its URL."""
    return await asyncio.to_thread(
        get_page_target_url_by_id,
        browser_cdp_url,
        target_id,
        timeout_sec=timeout_sec,
    )
