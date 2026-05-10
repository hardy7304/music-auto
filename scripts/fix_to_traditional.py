import os
from openai import OpenAI
from pathlib import Path
import sys

# 從環境變數讀取 NVIDIA API Key
# 腳本會優先檢查專案根目錄的 .env
def get_config():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        # 嘗試手動讀取 .env
        try:
            env_path = Path(__file__).resolve().parent.parent / ".env"
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("NVIDIA_API_KEY="):
                            return line.split("=")[1].strip()
        except:
            pass
    return api_key

NVIDIA_API_KEY = get_config()

if not NVIDIA_API_KEY:
    print("❌ 錯誤：找不到 NVIDIA_API_KEY。請在 .env 中設定。")
    sys.exit(1)

CLIENT = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY)

def fix_lyrics_with_ai(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            print(f"⚠️ 檔案是空的：{file_path.name}")
            return

        print(f"🤖 正在調用 NVIDIA LLM 進行精準繁體轉換：{file_path.name}...")
        
        prompt = f"""
你是一個專業的繁簡轉換專家。請將以下歌詞內容完整轉換為「繁體中文（台灣標準）」。
要求：
1. 嚴格保持原本的格式（LRC 或 SRT 的時間戳記）不可變動。
2. 將所有簡體字改為繁體，並修正語法（例如：裡面、頭髮、聯繫）。
3. 只輸出轉換後的文字內容，不要有任何多餘的解釋或對話。

待轉換內容：
{content}
"""

        response = CLIENT.chat.completions.create(
            model="meta/llama-3.3-70b-instruct",
            messages=[
                {"role": "system", "content": "你是一個專業的繁簡轉換工具，只輸出轉換後的結果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        translated_content = response.choices[0].message.content.strip()
        
        # 移除 AI 可能誤加的 Markdown 標籤
        if translated_content.startswith("```"):
            translated_content = "\n".join(translated_content.split("\n")[1:-1])

        # 覆蓋寫入原檔案
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(translated_content)
            
        print(f"✅ 成功！{file_path.name} 已經轉換為完美的繁體中文。")
        
    except Exception as e:
        print(f"❌ 轉換失敗: {e}")

def main(name):
    # 路徑定位
    project_root = Path(__file__).resolve().parent.parent
    lyrics_dir = project_root / "web_player" / "lyrics"
    
    # 支援傳入完整路徑或僅檔名
    song_stem = Path(name).stem
    
    target_files = []
    for ext in [".srt", ".lrc"]:
        p = lyrics_dir / f"{song_stem}{ext}"
        if p.exists():
            target_files.append(p)
            
    if not target_files:
        print(f"❌ 找不到對應的歌詞檔案：{song_stem}")
        print(f"搜尋路徑：{lyrics_dir}")
        return

    for f in target_files:
        fix_lyrics_with_ai(f)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        # 預設處理目錄下的所有 srt/lrc
        print("💡 提示：您可以指定檔名，例如 python scripts/fix_to_traditional.py aurora-song")
        main("aurora-song")
