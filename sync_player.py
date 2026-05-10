import os
import asyncio
import re
from pathlib import Path
from app.services.nvidia_lyrics_service import NvidiaLyricsService

async def main():
    # 使用絕對路徑確保一定能找到檔案
    root = Path(__file__).resolve().parent
    html_path = root / "web_player" / "index.html"
    
    if not html_path.exists():
        print(f"找不到網頁檔案: {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 簡單提取歌曲資訊 (這是一個示範，針對您目前的 index.html 結構)
    # 我們找第一個歌曲的標題和歌詞
    title_match = re.search(r'title: "(.*?)",', content)
    lyrics_match = re.search(r'lyrics: `(.*?)`', content, re.DOTALL)

    if title_match and lyrics_match:
        title = title_match.group(1)
        lyrics_raw = lyrics_match.group(1).strip()
        
        print(f"正在使用 NVIDIA_MODEL={os.getenv('NVIDIA_MODEL', 'meta/llama-3.3-70b-instruct')} 為《{title}》同步歌詞...")
        
        service = NvidiaLyricsService()
        new_lrc = await service.generate_lrc(title, lyrics_raw)
        
        if "[" in new_lrc:
            # 使用正則表達式精確替換 lyrics: `...` 之間的內容，避免重複
            new_content = re.sub(r'lyrics: `.*?`', f'lyrics: `{new_lrc}`', content, flags=re.DOTALL)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("✅ 歌詞同步完成！請重新整理網頁看看效果。")
        else:
            print("❌ AI 產出格式不正確，請檢查 API Key 設定。")
    else:
        print("未能在 index.html 中找到待處理的歌詞。")

if __name__ == "__main__":
    asyncio.run(main())
