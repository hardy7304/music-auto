import os
import json
import sys

# 強制編碼
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 設定路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "downloads"))
PLAYLIST_FILE = os.path.join(BASE_DIR, "web_player", "playlist.json")

def sync():
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"[Error] Not found: {DOWNLOAD_DIR}")
        return

    files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.mp3')]
    playlist = []
    
    # 排序
    files_with_time = [(f, os.path.getmtime(os.path.join(DOWNLOAD_DIR, f))) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)

    for f, _ in files_with_time:
        display_title = f
        if '_' in f:
            parts = f.rsplit('_', 2)
            if len(parts) >= 3 and parts[1].isdigit():
                display_title = parts[0]
        
        display_title = display_title.replace('.mp3', '').strip()

        # 使用 /downloads/ 開頭的絕對路徑，配合根目錄伺服器
        playlist.append({
            "title": display_title,
            "filename": f,
            "audioPath": f"/downloads/{f}", 
            "cover": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=2070&auto=format&fit=crop"
        })

    with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(playlist, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 同步成功！")

if __name__ == "__main__":
    sync()
