import os
import librosa
import numpy as np
from openai import OpenAI
from pathlib import Path
import sys

# --- 設定 ---
# 優先讀取 .env 中的 API Key，如果沒有則從環境變數讀取
def get_client():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到 NVIDIA_API_KEY。請在 .env 檔案中設定或 export。")
        sys.exit(1)
    
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

CLIENT = get_client()
MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")

def get_audio_info(mp3_path):
    """
    使用 librosa 分析音訊能量，找出活躍區間。
    """
    try:
        # sr=None 保持原始採樣率
        y, sr = librosa.load(str(mp3_path), sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # 找出非靜音區間 (top_db 越高越靈敏，25-30 是人聲經驗值)
        intervals = librosa.effects.split(y, top_db=28) 
        
        active_segments = []
        for start, end in intervals:
            active_segments.append({
                "start": round(start / sr, 2),
                "end": round(end / sr, 2)
            })
        return duration, active_segments
    except Exception as e:
        print(f"❌ 音訊分析失敗: {e}")
        return 0, []

def align_lyrics_with_ai(lyrics, duration, segments):
    """
    請求 NVIDIA NIM API 進行智能對齊分配。
    """
    # 簡化 segments 以節省 Token
    summary_segments = segments[:50] # 限制前 50 個區間
    
    prompt = f"""
你是一位專業的音樂歌詞同步專家。
我有一首歌曲，長度為 {duration:.1f} 秒。
經過音訊分析，這首歌中「有聲音（歌聲）」的時間區間大概如下（單位：秒）：
{summary_segments}

請將以下歌詞，根據這些聲音區間進行合理的分配。
每一句歌詞都需要一個 [mm:ss.xx] 的時間戳記。

歌詞內容：
{lyrics}

任務要求：
1. 輸出標準 LRC 格式，每一行都是 [mm:ss.xx] 歌詞內容。
2. 時間戳記必須與我提供的聲音區間（Active Segments）吻合。
3. 考慮每一句歌詞的長度，給予合理的間隔。
4. 只輸出 LRC 內容，不要有任何前言或結語。
"""

    try:
        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是一個精準的音樂歌詞同步專家，只輸出標準 LRC 內容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ API 請求失敗: {e}")
        return ""

def main(song_name):
    # 路徑定位
    project_root = Path(__file__).resolve().parent.parent
    web_player_dir = project_root / "web_player"
    
    mp3_path = web_player_dir / "music" / f"{song_name}.mp3"
    txt_path = web_player_dir / "lyrics" / f"{song_name}.txt"
    lrc_path = web_player_dir / "lyrics" / f"{song_name}.lrc"

    if not mp3_path.exists():
        # 嘗試找看看目錄下唯一的 mp3
        music_files = list((web_player_dir / "music").glob("*.mp3"))
        if music_files:
            mp3_path = music_files[0]
            print(f"⚠️ 找不到指定檔名，自動使用：{mp3_path.name}")
        else:
            print(f"❌ 找不到音訊檔案：{mp3_path}")
            return

    if not txt_path.exists():
        print(f"❌ 找不到歌詞文字檔：{txt_path}")
        print("💡 請先將歌詞存為 .txt 檔案放在 lyrics 目錄下。")
        return

    print(f"🎵 正在處理：{mp3_path.name}")
    print("⏳ 正在分析音訊特徵 (這可能需要 10-30 秒)...")
    duration, segments = get_audio_info(mp3_path)
    
    if not segments:
        print("❌ 無法偵測到音訊內容。")
        return

    print(f"📄 讀取歌詞文字...")
    with open(txt_path, "r", encoding="utf-8") as f:
        lyrics = f.read()

    print(f"🤖 正在請求 NVIDIA AI 進行智能對齊...")
    lrc_result = align_lyrics_with_ai(lyrics, duration, segments)

    if lrc_result and "[" in lrc_result:
        with open(lrc_path, "w", encoding="utf-8") as f:
            f.write(lrc_result)
        print(f"✅ 成功！LRC 已儲存至：{lrc_path.name}")
    else:
        print("❌ 無法生成有效的 LRC 內容。")

if __name__ == "__main__":
    # 使用方式：python scripts/auto_align_lrc.py [歌曲名稱]
    # 如果不帶參數，預設處理目錄下的第一個 mp3
    arg_name = sys.argv[1] if len(sys.argv) > 1 else ""
    # 去除副檔名
    arg_name = Path(arg_name).stem if arg_name else ""
    main(arg_name)
