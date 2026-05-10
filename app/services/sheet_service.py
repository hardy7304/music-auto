"""
Google Sheets 資料庫服務 — 對應 notion_service.py 的 Sheet 版本。

欄位定義（第 1 列為標題，資料從第 2 列起）：
  A  歌名        B  歌詞         C  Style / Tags  D  人聲
  E  用途場景    F  能量         G  節奏           H  曲調
  I  發布月份    J  創作工具     K  創作日期       L  創作階段
  M  音樂連結    N  是否發佈     O  AI生成時間     P  錯誤訊息
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import AppSettings
from app.logger import get_logger
from app.schemas import SongInput, SongResult

logger = get_logger(__name__)

# ── 欄位順序定義（與 Sheet 完全對應）────────────────────────────────────
SHEET_HEADERS = [
    "歌名",          # A  col 1
    "歌詞",          # B  col 2
    "Style / Tags",  # C  col 3
    "人聲",          # D  col 4
    "用途場景",      # E  col 5
    "能量",          # F  col 6
    "節奏",          # G  col 7
    "曲調",          # H  col 8
    "發布月份",      # I  col 9
    "創作工具",      # J  col 10
    "創作日期",      # K  col 11
    "創作階段",      # L  col 12
    "音樂連結",      # M  col 13
    "是否發佈",      # N  col 14
    "AI生成時間",    # O  col 15
    "錯誤訊息",      # P  col 16
]

# 欄位名稱 → 1-indexed 欄號（方便取用）
COL: dict[str, int] = {h: i + 1 for i, h in enumerate(SHEET_HEADERS)}

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# google_key.json 位於專案根目錄
_KEY_FILE = Path(__file__).resolve().parents[2] / "google_key.json"


# ── 輔助型別 ────────────────────────────────────────────────────────────
class SheetPendingSong:
    """一列待生成的 Sheet 資料。"""

    def __init__(self, row_index: int, song: SongInput) -> None:
        self.row_index = row_index  # 1-indexed Sheet 列號
        self.song = song

    def __repr__(self) -> str:
        return f"SheetPendingSong(row={self.row_index}, title={self.song.song_title!r})"


# ── 工具函式 ─────────────────────────────────────────────────────────────
def _col_letter(col: int) -> str:
    """將 1-indexed 欄號轉為字母（1→A, 26→Z, 27→AA …）。"""
    s = ""
    while col > 0:
        col, r = divmod(col - 1, 26)
        s = chr(65 + r) + s
    return s


def _a1(row: int, col: int) -> str:
    """建立 A1 格式的儲存格位置，例如 _a1(5, 12) → 'L5'。"""
    return f"{_col_letter(col)}{row}"


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ── 連線 ─────────────────────────────────────────────────────────────────
def _get_client():  # type: ignore[return]
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(str(_KEY_FILE), scopes=_SCOPES)
    return gspread.authorize(creds)


def _get_worksheet(settings: AppSettings):  # type: ignore[return]
    """取得專用的 Mureka_Queue 工作表，並在需要時自動建立標題列。"""
    client = _get_client()
    sh = client.open_by_url(settings.google_sheet_url)
    
    try:
        ws = sh.worksheet("Mureka_Queue")
    except Exception:
        # 如果 Mureka_Queue 不存在，就建立它
        ws = sh.add_worksheet(title="Mureka_Queue", rows="1000", cols="20")

    # 確保標題列存在
    existing = ws.row_values(1)
    if not existing or existing[0] != SHEET_HEADERS[0]:
        ws.insert_row(SHEET_HEADERS, 1)
        ws.freeze(rows=1)
        # 標題列黑底金字美化
        ws.format(
            f"A1:{_col_letter(len(SHEET_HEADERS))}1",
            {
                "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1},
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 0.84, "blue": 0.0},
                    "bold": True,
                },
                "horizontalAlignment": "CENTER",
            },
        )
        logger.info("Sheet 標題列已自動建立並美化")
    return ws


def sheet_sync_enabled(settings: AppSettings) -> bool:
    """判斷 Sheet 功能是否已設定（有 URL 且金鑰檔案存在）。"""
    return bool(settings.google_sheet_url and _KEY_FILE.exists())


# ── 寫入新歌曲 ──────────────────────────────────────────────────────────
def write_songs_to_sheet(settings: AppSettings, songs: list[SongInput]) -> None:
    """將 LLM 生成的歌曲批量寫入 Sheet（每首一列）。"""
    ws = _get_worksheet(settings)
    now = _now_str()
    rows_to_append: list[list[str]] = []

    for song in songs:
        extra: dict[str, Any] = song.extra_notion_props or {}

        # 解析 extra_notion_props 中的各欄位
        usage_raw = extra.get("用途場景", {})
        if isinstance(usage_raw, dict):
            usage_str = ", ".join(
                m.get("name", "") for m in usage_raw.get("multi_select", []) if m.get("name")
            )
        else:
            usage_str = str(usage_raw)

        energy = _safe_select(extra, "能量")
        rhythm = _safe_select(extra, "節奏")
        key    = _safe_select(extra, "曲調")
        tool   = _safe_select(extra, "創作工具") or "Mureka"
        release = extra.get("發布月份", {}).get("date", {}).get("start", "") \
                  if isinstance(extra.get("發布月份"), dict) else ""

        row: list[str] = [""] * len(SHEET_HEADERS)
        row[COL["歌名"]        - 1] = song.song_title
        row[COL["歌詞"]        - 1] = song.lyrics
        row[COL["Style / Tags"]- 1] = song.style_tags
        row[COL["人聲"]        - 1] = song.vocal or ""
        row[COL["用途場景"]    - 1] = usage_str
        row[COL["能量"]        - 1] = energy
        row[COL["節奏"]        - 1] = rhythm
        row[COL["曲調"]        - 1] = key
        row[COL["發布月份"]    - 1] = release
        row[COL["創作工具"]    - 1] = tool
        row[COL["創作日期"]    - 1] = now
        row[COL["創作階段"]    - 1] = "草稿"
        row[COL["音樂連結"]    - 1] = ""
        row[COL["是否發佈"]    - 1] = "FALSE"
        row[COL["AI生成時間"]  - 1] = ""
        row[COL["錯誤訊息"]    - 1] = ""
        rows_to_append.append(row)

    ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
    
    # 強制全表靠上對齊並自動換行，避免排版跑掉
    try:
        req = {
            "repeatCell": {
                "range": {"sheetId": ws.id},
                "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"
            }
        }
        ws.spreadsheet.batch_update({"requests": [req]})
    except Exception as exc:
        logger.warning("自動排版設定失敗：%s", exc)

    logger.info("已寫入 %s 首歌曲到 Sheet，並完成排版", len(songs))


async def write_songs_to_sheet_async(settings: AppSettings, songs: list[SongInput]) -> None:
    await asyncio.to_thread(write_songs_to_sheet, settings, songs)


def _safe_select(extra: dict[str, Any], key: str) -> str:
    val = extra.get(key, {})
    if isinstance(val, dict):
        return val.get("select", {}).get("name", "") or ""
    return ""


# ── 讀取待生成列 ────────────────────────────────────────────────────────
def fetch_unpublished_songs_from_sheet(settings: AppSettings) -> list[SheetPendingSong]:
    """讀取「是否發佈=FALSE」且「音樂連結」空白的列，回傳待處理清單。"""
    ws = _get_worksheet(settings)
    all_rows = ws.get_all_values()
    if not all_rows or len(all_rows) < 2:
        return []

    def _get(row: list[str], col_name: str) -> str:
        idx = COL.get(col_name, 0) - 1
        if idx < 0 or idx >= len(row):
            return ""
        return str(row[idx]).strip()

    pending: list[SheetPendingSong] = []
    # all_rows[0] = 標題列（跳過），資料從 index 1 = Sheet 第 2 列起
    for i, row in enumerate(all_rows[1:], start=2):
        published  = _get(row, "是否發佈").upper()
        result_url = _get(row, "音樂連結")

        # 已完成或已有連結 → 跳過
        if published == "TRUE" or result_url:
            continue

        song_title = _get(row, "歌名")
        if not song_title:
            continue

        lyrics      = _get(row, "歌詞")
        style       = _get(row, "Style / Tags")
        vocal       = _get(row, "人聲") or None
        instrumental = (vocal or "").strip() == "純音樂"

        if not instrumental and not lyrics:
            logger.warning("略過 Sheet 第 %s 列（%s）：有聲曲目但歌詞空白", i, song_title)
            continue

        if not style:
            from app.services.style_generator import generate_style_tags
            style = generate_style_tags(
                title=song_title,
                lyrics=lyrics,
                vocal=vocal,
                instrumental=instrumental,
            )

        # 幫 Mureka 標題加日期與名字
        today_str = datetime.now().strftime("%Y%m%d")
        mureka_title = song_title
        if "張嘉豪" not in mureka_title:
            mureka_title = f"{today_str} 張嘉豪 {song_title}"

        try:
            song_input = SongInput(
                song_title=mureka_title,
                lyrics=lyrics,
                style_tags=style,
                vocal=vocal,
                instrumental=instrumental,
            )
            pending.append(SheetPendingSong(row_index=i, song=song_input))
        except Exception as exc:
            logger.warning("略過 Sheet 第 %s 列（%s）：%s", i, song_title, exc)

    return pending


async def fetch_unpublished_songs_from_sheet_async(
    settings: AppSettings,
) -> list[SheetPendingSong]:
    return await asyncio.to_thread(fetch_unpublished_songs_from_sheet, settings)


# ── 回寫生成結果 ────────────────────────────────────────────────────────
def update_song_result_in_sheet_sync(
    settings: AppSettings, row_index: int, result: SongResult
) -> None:
    """將 Mureka 生成結果回寫到 Sheet 指定列。"""
    ws = _get_worksheet(settings)
    now = _now_str()

    status    = "完成" if result.success else "草稿修改"
    published = "TRUE" if result.success else "FALSE"

    batch = [
        {"range": _a1(row_index, COL["創作階段"]),   "values": [[status]]},
        {"range": _a1(row_index, COL["音樂連結"]),   "values": [[result.result_url or ""]]},
        {"range": _a1(row_index, COL["是否發佈"]),   "values": [[published]]},
        {"range": _a1(row_index, COL["AI生成時間"]), "values": [[now]]},
        {"range": _a1(row_index, COL["錯誤訊息"]),   "values": [[result.error_message or ""]]},
    ]
    ws.batch_update(batch, value_input_option="USER_ENTERED")
    logger.info("Sheet 第 %s 列已回寫結果（成功=%s）", row_index, result.success)


async def update_song_result_in_sheet(
    settings: AppSettings, row_index: int, result: SongResult
) -> None:
    await asyncio.to_thread(update_song_result_in_sheet_sync, settings, row_index, result)
