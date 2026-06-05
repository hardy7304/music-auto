import os
import json
import sys
import re

# 強制輸出編碼
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 路徑設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DOWNLOAD_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "downloads"))
PLAYLIST_FILE = os.path.join(PROJECT_ROOT, "web_player", "playlist.json")

# 關鍵字分類規則
GENRE_RULES = {
    "Wellness (整復按摩)": ["整復", "按摩", "筋絡", "撥筋", "理療", "推拿", "舒壓", "健康"],
    "Lifestyle (生活美食)": ["湯", "台南", "牛肉", "早晨", "清晨", "美食", "夜晚", "時光", "生活", "日常"],
    "Meditation (冥想禪修)": ["冥想", "禪", "心靈", "靜心", "靈性", "能量", "心經", "佛"],
    "Energetic (活力節奏)": ["健身", "暴走", "運動", "戰鬥", "節奏", "活力", "搖滾", "蹦迪"],
    "Emotional (深情思念)": ["寂寞", "思念", "憂傷", "織夢", "星空", "海洋", "深情", "回憶"],
    "System (測試與Demo)": ["test", "測試", "demo", "err", "試聽", "未命名"]
}

def clean_title(filename):
    # 移除擴展名
    t = filename.replace('.mp3', '')
    # 移除開頭日期 (8位數)
    t = re.sub(r'^\d{8}', '', t)
    # 移除作者名
    t = t.replace('張嘉豪', '').replace('Hao', '').replace('_', ' ').strip()
    return t if t else filename.replace('.mp3', '')

def get_genre(title, filename):
    combined = (title + filename).lower()
    for genre, keywords in GENRE_RULES.items():
        for kw in keywords:
            if kw.lower() in combined:
                return genre
    return "General (一般)"

def sync():
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Error: {DOWNLOAD_DIR} not found")
        return

    files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.mp3')]
    
    # 按檔案修改時間排序 (新歌在前)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x)), reverse=True)

    playlist = []
    for f in files:
        title = clean_title(f)
        genre = get_genre(title, f)
        
        # 核心：確保 filename 與 title 是一一對應的
        playlist.append({
            "id": f,
            "title": title,
            "filename": f,
            "genre": genre,
            "audioPath": f"/downloads/{f}",
            "cover": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=2070&auto=format&fit=crop"
        })

    # 強制覆寫 JSON
    with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(playlist, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully synced {len(playlist)} songs to {PLAYLIST_FILE}")

if __name__ == "__main__":
    sync()
