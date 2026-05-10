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
from app.services.notion_service import create_page_async
from app.services import sheet_service
from app.logger import setup_logging, get_logger

logger = get_logger("generate_songs")

def generate_songs_with_llm(settings: AppSettings, theme: str, count: int, mode: str = "full") -> list[SongInput]:
    provider = settings.llm_provider.lower()
    model_name = settings.agent_model
    
    # 定義結構模式
    structures = {
        "full": "[Intro] -> [Verse 1] -> [Pre-Chorus] -> [Chorus] -> [Verse 2] -> [Pre-Chorus] -> [Chorus] -> [Bridge] -> [Final Chorus] -> [Outro]",
        "demo": "[Verse 1] -> [Chorus] -> [Bridge] -> [Final Chorus] -> [Outro]",
        "free": "AI determined creative structure"
    }
    target_structure = structures.get(mode, structures["full"])
    
    import datetime
    current_month = datetime.datetime.now().strftime("%Y-%m")

    prompt = f"""
    You are a Grammy-winning music producer and a celebrated poet-lyricist known for
    evocative, imagery-rich songwriting in Traditional Chinese (繁體中文).

    Generate EXACTLY {count} unique, professional-grade song concepts for the theme: "{theme}"
    If {count} is greater than 1, make sure each concept explores a DIFFERENT angle or mood of the theme.

    Target lyric structure: {target_structure}

    ═══ LANGUAGE RULE ═══
    NEVER use Simplified Chinese (簡體中文). Verify every character.
    NEVER output English, Arabic, or any non-Chinese characters in the lyrics (except style_tags).
    If I see a single English word in the lyrics, you fail.

    ═══ SONG TITLE GUIDELINES ═══
    The title is the SOUL of a song. Follow these rules strictly:
    • Use literary devices: metaphor (暗喻), synesthesia (通感), personification (擬人), or oxymoron (矛盾修辭法).
    • Evoke a vivid mental image or emotional scene — the listener should "see" the song before hearing it.
    • Draw inspiration from the poetic naming styles of: 周杰倫 (Jay Chou), 五月天 (Mayday), 陳綺貞 (Cheer Chen), 林俊傑 (JJ Lin).
    • Examples of GOOD titles: 「把回憶拗成月光」「呼吸裡的鯨魚」「時差裡的擁抱」「星塵做的繭」「日落販賣機」
    • Examples of BAD titles (too generic): 「健身之歌」「愛情故事」「夏天的風」「快樂生活」
    • Length: 3–8 characters preferred. Absolutely NO generic, literal, or dictionary-definition titles.
    • Each title in the batch must feel like it belongs on a professional album tracklist.

    ═══ LYRICS GUIDELINES ═══
    • The lyrics MUST be profoundly poetic, using heavy symbolism, metaphors, and sensory details (sight, sound, touch).
    • AVOID literal or blunt storytelling. Use the "Show, Don't Tell" principle.
    • For example: Instead of saying "I am sad", write "眼淚在眼眶裡溺水" (Tears are drowning in the eye sockets).
    • For example: Instead of saying "I lost my way in the fog", write "指南針被回憶磁化，白雪覆蓋了回程" (The compass was magnetized by memories, white snow covered the return path).
    • Ensure natural rhythm and singable phrasing. You MUST maintain consistent rhyming schemes (押韻) at the end of lines within the same section (e.g., AABB or ABAB).
    • Each song MUST have a distinct emotional arc, building tension from the Verse to an explosive or deeply emotional Chorus.

    ═══ OUTPUT FORMAT ═══
    Because you are in JSON object mode, you MUST return a single JSON object.
    The JSON object MUST have EXACTLY two keys:
    1. "thought": A string containing your brief brainstorming of metaphors, imagery, and poetic concepts in Chinese.
    2. "songs": A JSON array containing EXACTLY {count} song objects.

    Each song object in the "songs" array MUST have:
    - song_title: Poetic, imagery-rich title in 繁體中文 (follow guidelines above).
    - lyrics: Full lyrics in 繁體中文 with tags [Intro], [Verse 1], [Pre-Chorus], etc. MUST use actual newlines (\n) between each line and tag! DO NOT write it as a single continuous sentence.
    - style_tags: High-detail ENGLISH music production metadata. MUST follow this rich format:
      "Genre/Era • Sub-genre/Influence • Specific Instrumentation • Vocal Style/Texture • Aesthetic/Mood • Production details".
      Example: "Jay-Z-inspired • Boom-Bap meets Modern Trap • Piano riff + hard-knock drums • Confident vocal delivery • Orchestral horns • New York grit aesthetic • Production: Blueprint-era meets 2026 stadium rap".
      NEVER just provide 1-2 words. Be extremely descriptive for the music engine.
    - vocal: One of ["男聲", "女聲", "男女對唱", "合音", "團體", "饒舌", "純音樂"].
    - usage_scenario: JSON array of 繁體中文 strings describing usage.
    - energy_level: One of "高能量", "低沉", "舒緩", "爆發力".
    - bpm: Integer.
    - key: e.g. "C Major".
    - release_date: Must be "{current_month}".
    """

    text = ""
    
    if provider == "google":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.gemini_api_key)
        clean_model_name = model_name.split("/")[-1]
        logger.info(f"正在透過 Google 呼叫 {clean_model_name}...")
        try:
            response = client.models.generate_content(
                model=clean_model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            text = response.text.strip()
        except Exception as e:
            logger.error(f"Google API 失敗: {e}")
            return []

    elif provider == "groq":
        import requests
        logger.info(f"正在透過 Groq 呼叫 {model_name}...")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json"
        }
        # 強化 Prompt，要求完整結構
        enhanced_prompt = prompt + "\nIMPORTANT: Ensure the lyrics include [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Chorus], and [Outro] for a complete professional structure."
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": enhanced_prompt}],
            "response_format": {"type": "json_object"}
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            res_json = resp.json()
            text = res_json["choices"][0]["message"]["content"]
            logger.debug(f"Groq 原始回傳: {text}")
        except Exception as e:
            logger.error(f"Groq API 失敗: {e}")
            return []

    elif provider == "openrouter":
        import requests
        logger.info(f"正在透過 OpenRouter 呼叫 {model_name}...")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://mureka-auto.internal", # Required by OpenRouter
            "X-Title": "Mureka Auto"
        }
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "top_p": 0.9
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            res_json = resp.json()
            text = res_json["choices"][0]["message"]["content"]
            logger.debug(f"OpenRouter 原始回傳: {text}")
        except Exception as e:
            logger.error(f"OpenRouter API 失敗: {e}")
            return []
            
    elif provider == "deepseek":
        import requests
        logger.info(f"正在透過 DeepSeek 官方呼叫 {model_name}...")
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            res_json = resp.json()
            text = res_json["choices"][0]["message"]["content"]
            logger.debug(f"DeepSeek 原始回傳: {text}")
        except Exception as e:
            logger.error(f"DeepSeek API 失敗: {e}")
            return []
            
    elif provider == "nvidia":
        import requests
        logger.info(f"正在透過 NVIDIA NIM 呼叫 {model_name}...")
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "top_p": 0.7,
            "max_tokens": 4096
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            res_json = resp.json()
            text = res_json["choices"][0]["message"]["content"]
            logger.debug(f"NVIDIA 原始回傳: {text}")
        except Exception as e:
            logger.error(f"NVIDIA API 失敗: {e}")
            return []
            
    else:
        logger.error(f"不支援的供應商: {provider}")
        return []

    try:
        from app.services.notion_service import _date_now_utc_value
        
        # 清理可能存在的 Markdown 代碼塊標記
        clean_text = text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            # 找第一個區塊
            clean_text = clean_text.split("```")[1].strip()
            # 如果裡面還有結束標記，再切一次
            if "```" in clean_text:
                clean_text = clean_text.split("```")[0].strip()
            
        data = json.loads(clean_text)
        song_list = []
        
        # 使用遞迴尋找所有包含 song_title 和 lyrics 的物件
        def extract_songs_from_data(obj, collected):
            if isinstance(obj, dict):
                if ("song_title" in obj or "title" in obj) and "lyrics" in obj:
                    collected.append(obj)
                else:
                    for val in obj.values():
                        extract_songs_from_data(val, collected)
            elif isinstance(obj, list):
                for item in obj:
                    extract_songs_from_data(item, collected)

        extract_songs_from_data(data, song_list)

        if not song_list:
            logger.error(f"JSON 結構中找不到任何完整的歌曲資料。原始資料預覽: {str(data)[:200]}")
            return []

        songs = []
        for item in song_list:
            if not isinstance(item, dict): continue
            
            # 確保獲取到內容
            title = item.get("song_title") or item.get("title") or "Untitled"
            lyrics = item.get("lyrics") or ""
            if not lyrics:
                continue # Skip empty items
            styles = item.get("style_tags") or "Pop"
            vocal_type = item.get("vocal") or "女聲"
            
            usage_list = item.get("usage_scenario", [])
            if isinstance(usage_list, str): usage_list = [usage_list]
            
            # 根據 BPM 數字轉換為 Notion 的選擇標籤 (Select)
            bpm_val = int(item.get("bpm", 120))
            if bpm_val < 90:
                rhythm_label = "慢速 (Slow)"
            elif bpm_val > 125:
                rhythm_label = "快速 (Fast)"
            else:
                rhythm_label = "中幕 (Medium)"

            extra_props = {
                "製作人": {"people": [
                    {"object": "user", "id": "112d872b-594c-810b-aff9-0002b7a2c78c"},
                    {"object": "user", "id": "20dd872b-594c-81a9-8781-0002c9c77ee9"}
                ]},
                "用途場景": {"multi_select": [{"name": s} for s in usage_list if s]},
                "能量": {"select": {"name": item.get("energy_level", "中")}},
                "節奏": {"select": {"name": rhythm_label}},
                "曲調": {"select": {"name": item.get("key", "C Major")}},
                "發布月份": {"date": {"start": item.get("release_date", "2026-05-01")}},
                "創作工具": {"select": {"name": "Mureka"}},
                "創作日期": _date_now_utc_value()
            }
            
            # 自動加上日期與姓名詞綴 (YYYYMMDD 張嘉豪)
            import datetime
            prefix = datetime.datetime.now().strftime("%Y%m%d") + " 張嘉豪 "
            final_title = prefix + title
            
            songs.append(SongInput(
                song_title=final_title,
                lyrics=lyrics,
                style_tags=styles,
                vocal=vocal_type,
                instrumental=True if vocal_type == "純音樂" else False,
                extra_notion_props=extra_props
            ))
        
        if not songs:
            logger.warning(f"未能從解析出的資料中提取到任何歌曲。原始文字: {text[:200]}...")
            
        return songs
    except Exception as e:
        logger.error(f"解析產出失敗: {e}\n原文: {text}")
        return []

async def process_single_theme_to_notion(theme: str, count: int, settings: AppSettings, mode: str = "full") -> list[SongInput]:
    """LLM 生成後寫入 Notion（原有流程）。"""
    songs = generate_songs_with_llm(settings, theme, count, mode)
    if not songs: return []

    logger.info(f"成功生成 {len(songs)} 首歌！開始寫入 Notion...")
    for i, song in enumerate(songs, 1):
        try:
            page_id = await create_page_async(settings, song)
            logger.info(f"[{i}/{len(songs)}] 寫入成功: {song.song_title}")
        except Exception as e:
            logger.warning(f"寫入失敗 '{song.song_title}': {e}")
    return songs


async def process_single_theme_to_sheet(theme: str, count: int, settings: AppSettings, mode: str = "full") -> list[SongInput]:
    """LLM 生成後寫入 Google Sheet（新流程，取代 Notion）。"""
    songs = generate_songs_with_llm(settings, theme, count, mode)
    if not songs: return []

    if not sheet_service.sheet_sync_enabled(settings):
        logger.error("Google Sheet 未設定！請在 .env 填入 GOOGLE_SHEET_URL 並確認 google_key.json 存在。")
        return songs

    logger.info(f"成功生成 {len(songs)} 首歌！開始寫入 Google Sheet...")
    try:
        await sheet_service.write_songs_to_sheet_async(settings, songs)
        logger.info(f"✅ 已將 {len(songs)} 首歌寫入 Sheet！")
    except Exception as e:
        logger.error(f"寫入 Sheet 失敗: {e}")
    return songs


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="LLM 生成歌曲並寫入 Notion 或 Google Sheet")
    parser.add_argument("--theme", type=str, required=True, help="歌曲主題（例如：城市愛情、失戀、勵志）")
    parser.add_argument("--count", type=int, default=3, help="要生成幾首歌（預設 3）")
    parser.add_argument("--mode", type=str, default="full", choices=["full", "demo", "free"], help="歌曲結構模式")
    parser.add_argument(
        "--target",
        type=str,
        default="sheet",
        choices=["notion", "sheet"],
        help="寫入目標：sheet（Google Sheet，預設）或 notion",
    )
    args = parser.parse_args()
    setup_logging()
    settings = load_settings()

    if args.target == "sheet":
        await process_single_theme_to_sheet(args.theme, args.count, settings, args.mode)
    else:
        await process_single_theme_to_notion(args.theme, args.count, settings, args.mode)


if __name__ == "__main__":
    asyncio.run(async_main())
