import argparse
import asyncio
import json
import os
import sys
import re
from pathlib import Path

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import load_settings, AppSettings
from app.schemas import SongInput
from app.services import notion_service
from app.logger import setup_logging, get_logger

logger = get_logger("fill_missing_songs")

def generate_missing_song_details(api_key: str, model_name: str, title: str) -> dict | None:
    import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    You are an expert music producer and lyricist.
    I have a song title: "{title}"
    But the lyrics and tags are missing. Please generate the creative contents for this song.
    
    Provide:
    1. lyrics: Full lyrics including [Verse], [Chorus], [Bridge], etc. The lyrics should be profound and match the title.
    2. style_tags: A comma-separated list of musical styles, genres, and moods in English (e.g., "Pop, Acoustic, Melancholy, Female Vocal").
    3. vocal: The type of vocal. MUST be one of the following exact strings: "男聲", "女聲", "男女對唱", "合音", "團體", "饒舌", "純音樂".
    4. usage_scenario: A JSON array of short strings describing the best use cases or scenarios for this song (e.g. ["深夜讀書", "長途開車"]).
    5. energy_level: A short string describing the energy of the song (e.g. "高能量", "低沉", "舒緩", "爆發力").
    6. bpm: An integer representing the Beats Per Minute (e.g. 120, 85, 140).
    7. key: A short string representing the musical key (e.g. "C Major", "A Minor", "G Major").
    8. release_date: A string representing the suitable release date in "YYYY-MM-DD" format (e.g. "2026-05-01").
    
    Return the result strictly as a valid JSON object (NOT an array). Do NOT include Markdown formatting like ```json.
    Example:
    {{
      "lyrics": "[Verse 1]\\n...",
      "style_tags": "Pop, Chill",
      "vocal": "女聲",
      "usage_scenario": ["開車", "放鬆"],
      "energy_level": "舒緩",
      "bpm": 85,
      "key": "C Major",
      "release_date": "2026-05-01"
    }}
    """
    
    logger.info(f"正在呼叫 Gemini 模型補齊歌曲「{title}」...")
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API 呼叫失敗: {e}")
        return None
    
    matches = re.findall(r"\{\s*\".*?\}\s*", text, re.DOTALL)
    if matches:
        text = matches[-1]
    
    try:
        data = json.loads(text.strip())
        return data
    except json.JSONDecodeError as e:
        logger.error(f"解析 JSON 失敗: {e}\n模型輸出: {text}")
        return None

async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Auto backfill missing lyrics in Notion.")
    parser.add_argument("--limit", type=int, default=5, help="一次最多處理幾首歌")
    args = parser.parse_args()

    setup_logging()
    settings = load_settings()
    
    if not settings.gemini_api_key:
        logger.error("錯誤: .env 中找不到 GEMINI_API_KEY。")
        sys.exit(1)
        
    try:
        pending = await notion_service.fetch_unpublished_songs(settings)
    except Exception as e:
        logger.error(f"無法讀取 Notion: {e}")
        sys.exit(1)
        
    # Filter songs that have no lyrics
    missing_songs = [row for row in pending if not (row.song.lyrics or "").strip()]
    
    if not missing_songs:
        logger.info("恭喜！沒有找到需要補齊歌詞的歌曲。")
        sys.exit(0)
        
    logger.info(f"找到 {len(missing_songs)} 首沒有歌詞的歌曲，將處理前 {args.limit} 首。")
    
    for i, row in enumerate(missing_songs[:args.limit], 1):
        title = row.song.song_title
        logger.info(f"[{i}/{min(len(missing_songs), args.limit)}] 準備補齊: {title}")
        
        data = generate_missing_song_details(settings.gemini_api_key, settings.agent_model, title)
        if not data:
            logger.warning(f"跳過 {title} (生成失敗)")
            continue
            
        usage_list = data.get("usage_scenario", [])
        if isinstance(usage_list, str):
            usage_list = [usage_list]
            
        extra_props = {
            "製作人": {"people": [
                {"object": "user", "id": "112d872b-594c-810b-aff9-0002b7a2c78c"},
                {"object": "user", "id": "20dd872b-594c-81a9-8781-0002c9c77ee9"}
            ]},
            "用途場景": {"multi_select": [{"name": s} for s in usage_list if s]},
            "能量": {"select": {"name": data.get("energy_level", "中")}},
            "BPM": {"number": int(data.get("bpm", 120))},
            "曲調": {"select": {"name": data.get("key", "C Major")}},
            "發布月份": {"date": {"start": data.get("release_date", "2026-05-01")}},
            "創作工具": {"select": {"name": "Mureka"}},
            "創作日期": notion_service._date_now_utc_value()
        }
        
        # Build SongInput
        updated_song = SongInput(
            song_title=title,
            lyrics=data.get("lyrics", ""),
            style_tags=data.get("style_tags", ""),
            vocal=data.get("vocal", "女聲"),
            instrumental=True if data.get("vocal") == "純音樂" else False,
            extra_notion_props=extra_props
        )
        
        # Build props for Notion
        props = notion_service._build_create_properties(settings, updated_song)
        # We don't want to change the title if it already exists, but overwriting it with the same is fine.
        
        try:
            await notion_service.update_page_properties_async(settings, row.notion_page_id, props)
            logger.info(f"成功回填 Notion: {title}")
        except Exception as e:
            logger.error(f"回填 Notion 失敗 '{title}': {e}")
            
    logger.info("補齊作業完成！您可以再次執行 main.py 讓 Mureka 開始製作這些音樂！")

if __name__ == "__main__":
    asyncio.run(async_main())
