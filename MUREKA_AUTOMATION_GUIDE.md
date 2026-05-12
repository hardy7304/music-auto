# Mureka 批量下載自動化維護手冊

## 🚀 快速啟動流程
1. **啟動 Chrome 偵錯模式**：
   執行 `music-auto/start_chrome_debug.bat`。
2. **登入並就位**：
   在開啟的 Chrome 中登入 Mureka，進入 **Create Music** 頁面，確保右側作品列表已顯示。
3. **啟動下載器**：
   在終端機執行：
   ```powershell
   & ".\music-auto\.venv\Scripts\python.exe" ".\music-auto\scripts\mureka_batch_downloader.py"
   ```

## 🛠️ 技術邏輯說明 (供未來維護參考)
為了應對 Mureka 複雜的網頁結構，我們採用了以下方案：
- **CDP (Chrome DevTools Protocol)**：透過 Port 9222 接管已登入的瀏覽器，解決自動化登入困難的問題。
- **JS 穿透點擊 (Penetration Click)**：
  - Mureka 的歌曲方塊本身是個大型超連結，直接點擊容易導致頁面跳轉。
  - 我們使用 `element.evaluate("el => el.click()")` 直接在瀏覽器內部觸發按鈕，避開外層連結。
- **智能防重複系統**：
  - 腳本會從歌曲封面網址擷取唯一 ID 並存入 `download_history.txt`。
  - **即使 MP3 檔案被搬移到 NAS**，只要紀錄檔還在，就不會重複下載。
- **高精準檔名**：
  - 格式：`歌名_YYYYMMDD_HHMMSS.mp3`。
  - 加入「秒」級時間戳記，解決同分鐘內下載多首歌曲導致的覆蓋問題。
- **獨立容器捲動**：
  - 針對右側 `div.flex-1.overflow-y-auto` 執行滑鼠滾輪模擬 (`page.mouse.wheel`)。

## 📂 檔案管理與 NAS 建議
- **本地路徑**：`music-auto/downloads`。
- **搬移建議**：
  - 下載完畢後，可將 MP3 剪下並貼上到您的 **NAS (SMB)**。
  - **切記**：請保留 `music-auto/download_history.txt`，這是腳本的記憶中心。
- **存儲空間**：若筆電空間不足，建議定期執行搬移。

## ⚠️ 常見異常排除
- **腳本跑進「歌曲詳情頁」**：腳本內建「導航守衛」，會自動按「上一頁」返回。若頻繁發生，請檢查網路延遲並增加點擊後的 sleep 時間。
- **辨識出 0 首歌曲**：通常是 Chrome 連線中斷或網頁尚未完全載入，請重新執行腳本。

---
*上次更新日期：2024-05-12*
