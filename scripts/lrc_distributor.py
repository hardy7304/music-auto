import os
from pathlib import Path
from pydub import AudioSegment
import sys

def format_lrc_time(seconds):
    """將秒數轉為 [mm:ss.xx] 格式"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    # 格式化為兩位整數秒 + 兩位小數毫秒
    return f"[{minutes:02d}:{secs:05.2f}]"

def distribute_lrc(song_name="aurora-song"):
    # 設定路徑 (基於專案根目錄)
    project_root = Path(__file__).resolve().parent.parent
    web_player_dir = project_root / "web_player"
    
    mp3_path = web_player_dir / "music" / f"{song_name}.mp3"
    txt_path = web_player_dir / "lyrics" / f"{song_name}.txt"
    lrc_path = web_player_dir / "lyrics" / f"{song_name}.lrc"

    # 1. 檢查檔案是否存在
    if not mp3_path.exists():
        # 嘗試找看看目錄下唯一的 mp3
        music_files = list((web_player_dir / "music").glob("*.mp3"))
        if music_files:
            mp3_path = music_files[0]
            print(f"⚠️ 找不到指定 mp3，改用：{mp3_path.name}")
        else:
            print(f"❌ 錯誤：找不到音訊檔案於 {mp3_path}")
            return

    if not txt_path.exists():
        print(f"❌ 錯誤：找不到歌詞文字檔 {txt_path}")
        print("💡 請確認該路徑下有對應的 .txt 檔案（純文字歌詞，一行一句）。")
        return

    # 2. 獲取音樂總長度
    try:
        print(f"正在分析音樂長度：{mp3_path.name}")
        audio = AudioSegment.from_file(str(mp3_path))
        total_seconds = len(audio) / 1000.0
        print(f"音樂總長度：{total_seconds:.2f} 秒")
    except Exception as e:
        print(f"❌ 讀取音樂失敗: {e}")
        print("💡 請確保已安裝 ffmpeg (sudo apt install ffmpeg)")
        return

    # 3. 讀取歌詞內容
    with open(txt_path, "r", encoding="utf-8") as f:
        # 只保留有內容的行
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not lines:
        print("❌ 錯誤：歌詞檔案內容為空。")
        return

    # 4. 平均分配時間
    # 保留起始 5 秒（通常是前奏），結束留 3 秒
    start_padding = 5.0
    end_padding = 3.0
    
    if total_seconds <= (start_padding + end_padding):
        # 歌太短的話，縮短 padding
        start_padding = total_seconds * 0.1
        end_padding = total_seconds * 0.1

    usable_time = total_seconds - start_padding - end_padding
    interval = usable_time / len(lines)
    
    lrc_content = []
    print(f"正在將 {len(lines)} 句歌詞分配到時間軸上...")
    
    for i, lyric in enumerate(lines):
        current_time = start_padding + (i * interval)
        lrc_line = f"{format_lrc_time(current_time)}{lyric}"
        lrc_content.append(lrc_line)

    # 5. 輸出 LRC 檔案
    with open(lrc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lrc_content))

    print(f"✅ 成功！LRC 檔案已儲存：{lrc_path.name}")
    print("-" * 30)
    print("生成內容預覽 (前 5 句)：")
    for line in lrc_content[:5]:
        print(line)

if __name__ == "__main__":
    # 支援手動輸入檔名，預設為 aurora-song
    name = sys.argv[1] if len(sys.argv) > 1 else "aurora-song"
    # 去除副檔名
    name = Path(name).stem
    distribute_lrc(name)
