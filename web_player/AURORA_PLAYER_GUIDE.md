# AURORA Professional Web Player - 最終維護與雲端佈署指南

這份文件紀錄了 AURORA 播放器的最終版本功能、雲端架構以及手機版優化細節。

## 核心成果總結
- **雲端混合架構**：前端託管於 **Cloudflare Pages**，音樂與歌詞資產託管於 **Cloudflare R2**。
- **手機版深度適配**：全螢幕橫向佈局、歌詞置中、隱藏次要資訊，提供類似 Spotify 的流暢體驗。
- **極速同步校準**：內建 `syncOffset: 0.45s`，補償行動裝置音訊延遲。
- **抗當機解析器**：採用高效能 DocumentFragment 渲染與暴力容錯解析，確保大檔案不卡死。
- **個人品牌整合**：製作人標記「張嘉豪 | 柔手運動按摩 & 柔手傳統整復推拿」。

## 雲端佈署關鍵步驟

### 1. Cloudflare R2 (資產中心)
- **Bucket 名稱**：`mureka-playlist`
- **目錄結構**：
  - `music/aurora-song.mp3`
  - `lyrics/aurora-song.srt`
- **CORS 設定 (必做)**：請在 R2 設定中貼入以下 JSON，否則歌詞無法顯示：
  ```json
  [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["Range"],
      "ExposeHeaders": ["Content-Range", "Content-Length", "Accept-Ranges"],
      "MaxAgeSeconds": 3000
    }
  ]
  ```

### 2. Cloudflare Pages (網頁中心)
- **上傳檔案**：`index.html`, `index.js`, `index.css`。
- **注意事項**：若修改了 `index.js` 裡的 `r2_base_url`，必須重新部署一次 Pages。

## 維護指令
- **本地預覽**：點擊 `啟動播放器.bat`。
- **AI 繁體化**：將 SRT 放入 `lyrics/` 後點擊 `一鍵繁體化.bat`。

---
**專案紀錄日期：2026-05-12**  
**開發者：Antigravity AI & 張嘉豪**
