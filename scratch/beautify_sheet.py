import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from datetime import datetime

# 設定金鑰與路徑
_ROOT = Path(__file__).resolve().parent
KEY_FILE = _ROOT.parent / "google_key.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gH2qooBwXr96goZtPom8aoURNRLz9OmcSBx1KIwzvKI/edit"

def beautify_and_record():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(str(KEY_FILE), scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_url(SHEET_URL)

    # --- 1. 紀錄開發歷程 ---
    history_name = "開發歷程紀錄"
    try:
        hist_sheet = sh.add_worksheet(title=history_name, rows="100", cols="5")
    except:
        hist_sheet = sh.worksheet(history_name)
    
    history_data = [
        ["時間戳", "版本", "里程碑事件", "技術細節"],
        ["2026-05-08 14:20", "v0.1.0", "系統啟動與批次檔時期", "最初使用 .bat 腳本進行單純的 CLI 執行。"],
        ["2026-05-08 14:27", "v0.3.0", "Web UI 控制台轉型", "棄用 bat 檔，建立 FastAPI 網頁介面，引入 SSE 實時日誌串流。"],
        ["2026-05-08 15:30", "v0.5.0", "CSV 與雲端連線整合", "成功串接 Google Sheet (CSV) 讀取模式，大幅降低資料輸入難度。"],
        ["2026-05-08 16:20", "v0.6.0", "Gemini 套件與模型升級", "更換為 google-genai 最新套件，並改用 gemini-1.5-flash，解決穩定性問題。"],
        ["2026-05-08 16:40", "v0.7.0", "專業版雙向 API 同步", "建立 Service Account 授權，達成 Google Sheets 自動讀取與回寫。"],
        ["2026-05-08 17:00", "v0.8.0", "系統美化與歷程封裝", "完成自動美化腳本與開發歷程存檔，系統進入完全體。"]
    ]
    hist_sheet.clear()
    hist_sheet.update("A1", history_data)
    hist_sheet.format("A1:D1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})

    # --- 2. 自動美化工作表1 ---
    main_sheet = sh.worksheets()[0] # 獲取第一個分頁
    
    # 設置標題顏色與加粗
    main_sheet.format("A1:G1", {
        "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1},
        "textFormat": {"foregroundColor": {"red": 1.0, "green": 0.84, "blue": 0.0}, "bold": True}, # 黑底金字
        "horizontalAlignment": "CENTER"
    })
    
    # 凍結第一列
    main_sheet.freeze(rows=1)
    
    # 設置狀態欄位 (C欄) 的條件格式
    # 備註：gspread 的條件格式化需要使用 batch_update，這裡我們做一些簡單的顏色填充
    data = main_sheet.get_all_values()
    for i, row in enumerate(data, start=1):
        if i == 1: continue
        status = row[2] # 假設 status 在 C 欄
        if status == "已生成":
            main_sheet.format(f"C{i}", {"backgroundColor": {"red": 0.8, "green": 1.0, "blue": 0.8}})
        elif status == "待生成":
            main_sheet.format(f"C{i}", {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.8}})
            
    print("開發歷程已更新，且工作表美化完成！")

if __name__ == "__main__":
    beautify_and_record()
