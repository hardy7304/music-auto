# music-auto：Gemini／Gemma API 用量與 429 營運筆記

> 建立目的：說明免費層配額、日誌與實際呼叫量關係。可將本檔以 Notion **匯入 → Markdown**，或全選複製到新頁面。

---

## 1. 429 RESOURCE_EXHAUSTED 代表什麼？

- Log 若出現 **`429 RESOURCE_EXHAUSTED`**，並伴隨 **`generate_content_free_tier_requests`**、**`GenerateRequestsPerDayPerProjectPerModel-FreeTier`** 等字樣，代表 **Google Generative Language API** 端判定：目前 **API 金鑰所屬專案**在 **免費層** 下，**某模型**的 **`generate_content` 請求已達當日上限**（常見例如 **1500 次／日／模型／專案**）。
- 這是 **供應商端限制**，與 Mureka、本機網路是否正常無關；**不是**本專程式邏輯「算錯」造成的假錯誤。

**可處理方向（擇一或並用）：**

- 到 [Gemini API 配額說明](https://ai.google.dev/gemini-api/docs/rate-limits) 與 [AI Studio 用量](https://ai.dev/rate-limit) 查詢；**隔日**配額重置後再跑。
- **升級付費**或建立 **另一 GCP 專案** 取得 **另一把 API 金鑰**（免費桶通常依專案分開）。
- 在 `.env` 調整 **`AGENT_MODEL`** 為 **其他仍有額度的模型 id**（須與 browser-use 相容；不同模型額度桶可能不同，需自行確認）。

---

## 2. 「1500 次」是單次執行嗎？

**不是。** 1500 指的是 **同一日曆日（通常以 Google 說明為準，多為 UTC 日）內、該專案該模型的請求數累計**，不是單次 `python app/main.py` 只發一個大包。

AI Studio 圖表上的高峰是 **整天加總**，可能來自：多首歌曲、多次測試、失敗重試、並行跑多首、或其他使用 **同一專案金鑰** 的程式。

---

## 3. 為什麼 music-auto 會吃掉很多請求？算設計錯誤嗎？

**不算實作 bug，而是 browser-use 類「瀏覽器 Agent」的正常成本。**

每首歌流程會拆成 **多個獨立的 Agent 階段**；**Agent 每決策一步**（讀畫面、決定下一步操作）通常對應 **一次** `generate_content`。典型階段包括（名稱與程式對應）：

| 階段 | 說明 |
|------|------|
| 登入牆檢查 | 確認是否被導到登入行銷頁 |
| 確認創作頁 | 確認是否像 Create Music |
| 填表 | 歌名、歌詞、Style 等 |
| 提交／Dry-run | 按 Generate 或僅驗證流程 |
| 等待穩定 | 點擊後等 UI／生成狀態穩定（非 dry-run） |
| 擷取結果 | 讀取 URL、狀態等 structured 輸出 |

各階段有 **`AGENT_*_MAX_STEPS` 上限**；失敗時程式還可能 **整段重試**（例如最多 3 次），失敗或卡住會 **額外燒步數**。

粗估：**每首順利完成也常達數十～上百次請求**（視頁面與 Agent 步數而定）。因此 **1500／日** 可能對應約 **十幾～三十幾首歌** 的量級，再加上測試與重跑。

**並行：** `.env` 的 **`NOTION_PARALLEL_MAX` > 1** 時，同時跑多首會 **線性疊加** 同一時段內的請求速率與當日累計。

---

## 4. 多把 API Key、「滿了換下一個」

- 本專案環境變數主要為 **`GEMINI_API_KEY`**，以及可選 **`GEMMA_API_KEY`**（當 `AGENT_MODEL` 為 `gemma-*` 時可優先使用）。
- **沒有**內建「偵測 429 自動換下一把 key」；額度滿了需 **手動改 `.env`** 或自行擴充程式。
- 實務上 **不同 GCP 專案** 才有獨立免費桶；同一專案多把 key **通常不會**讓免費額度加倍。

---

## 5. Gemma／Gemini：用 token 還是用「次數」算？

- **兩者 Google 都會統計與限制。**
- 你看到的 **`generate_content_free_tier_requests`**／**每日每模型** 類訊息，指的是 **`generate_content` 的請求次數**（免費層日上限常與此相關）。
- **Token**（輸入／輸出）仍會出現在用量圖表，且另有 **RPM／TPM** 等分鐘級節流；付費計費亦常與 token 掛鉤。
- AI Studio **依模型**圖表若顯示某模型（例如 Flash）用量高、另一模型（例如 Gemma）近乎為零，代表實際計費／統計歸在該模型；請以 **同一專案、同一區間** 對照 log 與 `.env` 的 **`AGENT_MODEL`** 是否一致、是否有其他服務共用金鑰。

---

## 6. 想省用量時可調什麼？

- **`NOTION_PARALLEL_MAX=1`**（除非確定要並行）。
- 適度 **下調** `AGENT_*_MAX_STEPS`（尤其 **`AGENT_SETTLE_MAX_STEPS`**），接受偶爾較早結束或失敗風險。
- 減少 **重跑與除錯次數**；長期大量跑則考慮 **付費**或 **多專案**。

---

## 7. Windows 日誌亂碼與「Logging error」

- 主因常為 **主控台 cp950** 無法輸出第三方函式庫 log 裡的 **emoji**，與 **429 無因果關係**。
- 本專案已嘗試將 **stdout／stderr** 設為 UTF-8、子程序帶 **`PYTHONIOENCODING=utf-8`**；詳見 repo 內 **`README.md`** 小節「Windows 主控台與 UTF-8」。

---

## 8. 相關檔案

- 專案說明與環境變數：**`README.md`**、**`.env.example`**
- 本筆記（給 Notion）：**`docs/notion-gemini-runbook.md`**
