import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import load_settings, AppSettings
from app.logger import setup_logging, get_logger
from generate_songs import process_single_theme_to_sheet

logger = get_logger("process_csv_ideas")

# 預設金鑰路徑
KEY_FILE = _ROOT / "google_key.json"

async def sync_with_google_sheets(settings: AppSettings, mode: str = "full"):
    """
    專業版：使用 gspread 進行雙向同步。
    1. 讀取「待生成」的主題。
    2. 呼叫 AI 生成並存入 Notion。
    3. 將結果寫回 Google Sheets。
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.error("缺少 gspread 或 google-auth 套件，請執行: pip install gspread google-auth")
        return

    if not KEY_FILE.exists():
        logger.error(f"找不到 Google API 金鑰檔案: {KEY_FILE}。請確認檔案已放在專案目錄。")
        return

    sheet_url = settings.google_sheet_url
    if not sheet_url:
        logger.error("未設定 GOOGLE_SHEET_URL，無法同步。")
        return

    try:
        # 認證
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(str(KEY_FILE), scopes=scopes)
        client = gspread.authorize(creds)
        
        # 開啟試算表
        sh = client.open_by_url(sheet_url)
        worksheet = sh.worksheets()[0] # 預設開第一個分頁
        
        # 讀取所有資料
        data = worksheet.get_all_records()
        fieldnames = worksheet.row_values(1)
        
        logger.info(f"成功連線至 Google Sheet: {sh.title}")
        
        modified_count = 0
        for i, row in enumerate(data, start=2): # 從第 2 列開始 (第 1 列是表頭)
            current_status = str(row.get("status")).strip()
            # 只要是「待生成」或是包含「失敗」字樣的，都自動列入處理
            if current_status == "待生成" or "失敗" in current_status:
                theme = row.get("theme")
                if not theme:
                    continue
                    
                logger.info(f"正在處理雲端靈感 [Row {i}]: {theme}")
                
                try:
                    # 生成 1 首歌並存入 Mureka_Queue
                    songs = await process_single_theme_to_sheet(theme, 1, settings, mode)
                    
                    if songs:
                        s = songs[0] # 我們只生成一首
                        # 準備回寫資料
                        # 假設欄位順序: theme(B), status(C), song_titles(D), generated_at(G)
                        # 我們使用標題對齊來更新，確保安全
                        try:
                            # 獲取欄位索引 (gspread 是 1-based)
                            status_idx = fieldnames.index("status") + 1
                            titles_idx = fieldnames.index("song_titles") + 1
                            gen_at_idx = fieldnames.index("generated_at") + 1
                            
                            updates = [
                                {"range": gspread.utils.rowcol_to_a1(i, status_idx), "values": [["已生成"]]},
                                {"range": gspread.utils.rowcol_to_a1(i, titles_idx), "values": [[s.song_title]]},
                                {"range": gspread.utils.rowcol_to_a1(i, gen_at_idx), "values": [[datetime.now().strftime("%Y-%m-%d %H:%M:%S")]]}
                            ]
                            worksheet.batch_update(updates)
                            logger.info(f"成功處理並同步至雲端: {theme}")
                            modified_count += 1
                        except ValueError as e:
                            logger.error(f"Google Sheet 欄位不匹配: {e}")
                    else:
                        # 標註失敗
                        status_idx = fieldnames.index("status") + 1
                        worksheet.update_cell(i, status_idx, "失敗 (AI未回傳)")
                        
                except Exception as e:
                    logger.error(f"處理靈感時發生錯誤: {theme} - {e}")
                    status_idx = fieldnames.index("status") + 1
                    worksheet.update_cell(i, status_idx, f"失敗 ({str(e)[:50]})")

        if modified_count > 0:
            logger.info(f"同步完成！共處理 {modified_count} 個項目。")
        else:
            logger.info("沒有需要處理的「待生成」靈感。")

    except Exception as e:
        logger.error(f"Google Sheets 同步過程發生崩潰: {e}")

async def async_main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="full", choices=["full", "demo", "free"])
    args = parser.parse_args()

    setup_logging()
    settings = load_settings()
    
    # 檢查是否有對應供應商的金鑰
    provider = settings.llm_provider.lower()
    if provider == "google" and not settings.gemini_api_key:
        logger.error("錯誤: 使用 Google 模式但 .env 中找不到 GEMINI_API_KEY。")
        sys.exit(1)
    elif provider == "groq" and not settings.groq_api_key:
        logger.error("錯誤: 使用 Groq 模式但 .env 中找不到 GROQ_API_KEY。")
        sys.exit(1)
        
    # 執行專業版同步
    await sync_with_google_sheets(settings, args.mode)

if __name__ == "__main__":
    asyncio.run(async_main())
