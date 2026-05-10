"""Auto-generate Mureka style tags from song title, lyrics, and vocal type.

Zero LLM token cost — uses keyword analysis of Chinese/English content
to produce genre + mood + vocal style tags suitable for Mureka's Style field.
"""

from __future__ import annotations

import re
from typing import Sequence

from app.logger import get_logger

logger = get_logger(__name__)

# ─── Genre detection rules ────────────────────────────────────────
# Each rule: (keywords_in_title_or_lyrics, genre_tags)

_GENRE_RULES: list[tuple[Sequence[str], list[str]]] = [
    # Chinese traditional / ancient
    (("古", "禪", "琴", "茶", "墨", "詩", "劍", "武", "俠", "朝", "宮", "皇"),
     ["Chinese Traditional", "Cinematic"]),
    # City / urban / neon
    (("城市", "都市", "霓虹", "街道", "咖啡", "計程車", "地鐵", "公寓", "巷弄"),
     ["City Pop", "Urban"]),
    # Electronic / dance / party
    (("電", "跳", "舞", "嗨", "DJ", "節拍", "脈動", "引擎", "迴路", "數位", "循環"),
     ["Electronic", "Dance"]),
    # Rock / metal / intense
    (("戰", "火", "怒", "暴", "狂", "雷", "鐵", "鋼", "崩", "裂", "烈", "衝", "燃", "焰"),
     ["Rock", "Intense"]),
    # Hip-hop / rap
    (("饒舌", "嘻哈", "說唱", "flow", "beat", "押韻", "街頭"),
     ["Hip-Hop", "Rap"]),
    # R&B / soul
    (("靈魂", "節奏", "藍調", "soul", "groove"),
     ["R&B", "Soul"]),
    # Jazz
    (("爵士", "jazz", "即興", "薩克斯", "鋼琴曲"),
     ["Jazz", "Smooth"]),
    # Folk / nature / acoustic
    (("海", "山", "河", "田", "風", "花", "草", "森林", "鄉", "原野", "土地", "故鄉"),
     ["Folk", "Acoustic"]),
    # Ballad / love
    (("愛", "心", "情", "吻", "擁抱", "思念", "懷念", "離別", "淚", "傷"),
     ["Ballad", "Emotional"]),
    # Dream / ambient / chill
    (("夢", "星", "月", "雲", "霧", "靜", "冥想", "沉", "浮", "飄", "幻"),
     ["Dream Pop", "Ambient"]),
    # Cinematic / epic
    (("史詩", "壯", "英雄", "傳說", "征途", "命運", "榮耀", "戰線", "未來"),
     ["Cinematic", "Epic"]),
    # Pop (general — lower priority)
    (("快樂", "陽光", "笑", "青春", "校園", "朋友", "夏天", "旅行"),
     ["Pop", "Upbeat"]),
]

# ─── Mood detection ───────────────────────────────────────────────

_MOOD_RULES: list[tuple[Sequence[str], str]] = [
    (("快", "嗨", "衝", "跳", "燃", "熱", "狂", "爆", "炸"), "Energetic"),
    (("慢", "靜", "柔", "輕", "緩", "幽", "淡", "沉"), "Mellow"),
    (("悲", "傷", "哭", "淚", "痛", "寒", "冷", "孤", "寂"), "Melancholic"),
    (("怒", "暴", "戰", "烈", "狠", "崩"), "Aggressive"),
    (("浪漫", "溫", "暖", "甜", "蜜", "愛", "擁"), "Romantic"),
    (("神秘", "暗", "影", "謎", "迷", "幻", "深"), "Mysterious"),
    (("希望", "光", "明", "亮", "升", "翔", "飛"), "Uplifting"),
    (("懷舊", "復古", "老", "回憶", "從前", "昔"), "Nostalgic"),
]

# ─── Vocal type mapping ──────────────────────────────────────────

_VOCAL_MAP: dict[str, str] = {
    "男聲": "Male Vocal",
    "女聲": "Female Vocal",
    "合音": "Harmony Vocals",
    "團體": "Group Vocals",
    "饒舌": "Rap Vocal",
    "男女對唱": "Male-Female Duet",
    "純音樂": "",  # No vocal tag for instrumental
}


def generate_style_tags(
    *,
    title: str,
    lyrics: str = "",
    vocal: str | None = None,
    instrumental: bool = False,
) -> str:
    """Analyze title + lyrics and return a Mureka-compatible style string.

    Returns something like: "City Pop, Ballad, Mellow, Female Vocal"
    """
    hay = f"{title} {lyrics}".lower()

    # Detect genres (collect unique, max 3)
    genres: list[str] = []
    for keywords, tags in _GENRE_RULES:
        if any(k.lower() in hay for k in keywords):
            for t in tags:
                if t not in genres:
                    genres.append(t)
            if len(genres) >= 3:
                break

    # Default genre if nothing matched
    if not genres:
        if instrumental:
            genres = ["Cinematic", "Ambient"]
        else:
            genres = ["Mandopop"]

    # Detect mood (max 2)
    moods: list[str] = []
    for keywords, mood in _MOOD_RULES:
        if any(k.lower() in hay for k in keywords):
            if mood not in moods and mood not in genres:
                moods.append(mood)
            if len(moods) >= 2:
                break

    # Default mood if nothing matched
    if not moods:
        # Guess from genre
        if any(g in ("Rock", "Electronic", "Hip-Hop") for g in genres):
            moods = ["Energetic"]
        elif any(g in ("Ballad", "Dream Pop", "Ambient") for g in genres):
            moods = ["Mellow"]
        else:
            moods = ["Emotional"]

    # Vocal tag
    vocal_tag = ""
    if vocal and not instrumental:
        vocal_tag = _VOCAL_MAP.get(vocal.strip(), "")

    # Instrumental tag
    if instrumental:
        genres = [g for g in genres if g not in ("Pop", "Mandopop")]
        if not genres:
            genres = ["Cinematic"]
        genres.insert(0, "Instrumental")

    # Combine
    parts = genres[:3] + moods[:2]
    if vocal_tag:
        parts.append(vocal_tag)

    result = ", ".join(parts)
    logger.info("Auto-generated style for '%s': %s", title, result)
    return result


def maybe_generate_style(
    *,
    existing_style: str,
    title: str,
    lyrics: str = "",
    vocal: str | None = None,
    instrumental: bool = False,
) -> str:
    """Return existing_style if it looks valid, otherwise auto-generate."""
    s = (existing_style or "").strip()
    # Skip generation if there's already a meaningful style
    if s and s not in ("（未指定風格）", "未指定", "", "none", "null"):
        return s
    return generate_style_tags(
        title=title,
        lyrics=lyrics,
        vocal=vocal,
        instrumental=instrumental,
    )
