import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from datetime import datetime

# 設定金鑰與路徑
_ROOT = Path(__file__).resolve().parent
KEY_FILE = _ROOT.parent / "google_key.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gH2qooBwXr96goZtPom8aoURNRLz9OmcSBx1KIwzvKI/edit"

def update_full_history():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(str(KEY_FILE), scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_url(SHEET_URL)

    history_name = "開發歷程紀錄"
    try:
        hist_sheet = sh.worksheet(history_name)
    except:
        hist_sheet = sh.add_worksheet(title=history_name, rows="100", cols="5")
    
    # 整理完整歷史 (包含今天以前)
    full_history = [
        ["時間點", "版本里程碑", "核心變動", "備註"],
        ["早期階段", "Legacy Agent", "使用 browser-use 框架", "依賴 LLM 決策，每一步都消耗 Token，速度較慢。"],
        ["中期階段", "Playwright-first", "核心引擎重構", "改用 Playwright CDP 附著技術，達成零 Token 消耗、秒級填表。"],
        ["近期階段", "Notion Queue", "任務自動化流程", "整合 Notion API，建立正式的生產任務佇列 (Queue)。"],
        ["2026-05-08 14:27", "v0.3.0", "Web UI 整合", "由 AI Antigravity 介入，建立黑金風格網頁控制台，取代 bat 檔。"],
        ["2026-05-08 15:30", "v0.5.0", "Google Sheet 讀取", "新增從雲端表格同步靈感的功能。"],
        ["2026-05-08 16:40", "v0.7.0", "雙向 API 同步", "透過 Google Service Account 達成雲端狀態自動回寫。"],
        ["2026-05-08 17:00", "v0.8.0", "系統全自動美化", "系統達成『自動讀取、自動生成、自動回寫、自動美化』的完全體狀態。"]
    ]
    
    hist_sheet.clear()
    hist_sheet.update("A1", full_history)
    hist_sheet.format("A1:D1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1}, "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}}})

    print("完整開發歷史已更新至雲端！")

if __name__ == "__main__":
    update_full_history()
