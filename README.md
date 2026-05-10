# music-auto

使用 **Playwright-first** 自動化，透過 **Chrome DevTools Protocol (CDP)** 附著到你**已用一般瀏覽器登入**的 Mureka 分頁，在 **Create Music** 頁面上自動填表、依 `DRY_RUN` 決定是否按 Generate，並輸出 JSON。預設流程不呼叫 LLM，幾乎不消耗 token；舊版 **browser-use** Agent 保留為可選備援。

本專案**不**把 Google OAuth／自動登入納入主流程：請你先在正常 Chrome 工作階段內完成登入，再讓程式接手。

## 為什麼不建議把 Google OAuth 放進自動化主流程？

- Google 常對自動化瀏覽器顯示額外驗證，流程脆弱且可能違反服務條款。
- 帳密與 OAuth 應留在**你信任的一般瀏覽器**由本人操作；程式只透過 **遠端偵錯埠**附著到**已登入**的視窗，不代填密碼、不點「Continue with Google」。

## 推薦流程

1. **關閉**所有 Chrome 後，用**遠端偵錯**重新啟動（埠號須與 `.env` 的 `BROWSER_CDP_URL` 一致），例如 Windows：
   ```text
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```
2. 在這個 Chrome 裡**手動**登入 Mureka（含 Google 帳號若需要）。
3. **手動**開到 **Create Music** 創作頁，並讓該分頁維持在前景（程式預設**不會**再導頁，避免錯誤路徑變 404）。**請在啟動程式「之前」就開好需要的 Mureka 分頁**；若先跑自動化再連開多個空白分頁，CDP 有時會先附著到錯誤分頁而像當機（程式會嘗試自動切回 URL 最像創作頁的那個分頁，仍建議少在執行中新增分頁）。
4. 在 `music-auto` 目錄執行（**正式：Notion 待生成佇列 → Mureka → 回寫同一筆**）：
   ```bash
   python app/main.py --attach-open-page --from-notion --dry-run false
   ```
   會查詢 Notion 資料庫裡 **「是否發佈」未勾選** 的列，依建立時間由舊到新逐首讀 **歌名／歌詞／Style**，填入 Mureka 並生成，再更新該列（連結、階段、勾選、時間等）。
5. 若僅本機測試、不讀 Notion，可不加 `--from-notion`（此時仍使用內建範例或 `--song-title` 等參數）。

### Notion 佇列與速度（並行生成）

預設 **一首接一首**：每首會附著 Mureka、填表、（可選）點 Generate，並 **等該首畫面穩定** 後再處理下一首，因此總時間接近各首相加。

若 Mureka 帳戶允許 **同時多首在跑**（例如最多 10 首），可在 `.env` 設定 **`NOTION_PARALLEL_MAX`**（1–10）或 CLI **`--notion-parallel-max N`**／網頁控制台選項，並 **預先開啟 N 個** 已登入的 **Create Music** 分頁（建議由左到右排列；程式依 Chrome 偵錯的 `/json/list` 順序對應第 1～N 筆 Notion 待處理列）。同一批會以 `asyncio.gather` 同時執行；**下一批**會重用同一组分頁，請確認每首完成後該分頁仍能回到可創作狀態，否則請改回 **`NOTION_PARALLEL_MAX=1`** 或分批手動跑。

並行時會啟動多個 Playwright CDP 工作連線同一 Chrome。若出現分頁搶操作或不穩，請降回並行度 1。

### 自動化引擎：Playwright vs browser-use

預設：

```env
AUTOMATION_ENGINE=playwright
BROWSER_USE_FALLBACK=false
```

| 值 | 說明 |
|----|------|
| `playwright` | 推薦。固定 selector / DOM heuristic 填表與點擊，正常情況不叫 LLM，速度最快、token 幾乎歸零。 |
| `browser_use` | 舊流程。每一步由 LLM 觀察與決策，較慢且會消耗 API 額度；適合 UI 大改版時暫時救場。 |
| `auto` | 先跑 Playwright，失敗後改用 browser-use；需設定對應 LLM 金鑰。 |

也可設 `BROWSER_USE_FALLBACK=true`，讓 `playwright` 失敗時自動改用 browser-use。這個選項會消耗 LLM token，建議只在 selector 還沒調好時短期使用。

## 專案結構（重點）

```
music-auto/
  app/
    main.py
    config.py
    prompts/mureka_tasks.py
    utils/browser_profile.py   # screenshots 路徑
    services/mureka_playwright_agent.py # Playwright-first：CDP attach、fill、submit、extract
    services/mureka_agent.py            # browser-use 備援流程
    tasks/run_song_generation.py
  web/                         # 本機網頁控制台（說明 + 執行）
    server.py
    static/
  ...
```

## 環境與安裝

- Python 3.12、`pip install -r requirements.txt`
- `python -m playwright install chromium`（`requirements.txt` 已含 `playwright` 套件；browser-use 仍依賴其瀏覽器驅動鏈）
- `.env`：至少 **`BROWSER_CDP_URL`**。預設 **`AUTOMATION_ENGINE=playwright`**，所以不需要 LLM 金鑰即可跑主流程；只有 `AUTOMATION_ENGINE=browser_use`、`AUTOMATION_ENGINE=auto` 或 `BROWSER_USE_FALLBACK=true` 才需要 **`LLM_PROVIDER`** 與對應 API key。預設 **`MUREKA_ATTACH_NAVIGATE_FIRST=false`**（附著後不強制 `navigate_to`，避免 `…/create-music` 等路徑在你環境回 404）。若要程式幫你開網址，設為 `true` 並把 **`MUREKA_CREATE_URL`** 改成瀏覽器網址列上**實際可用**的完整 URL。**`MUREKA_MODEL_MODE`**：`v9` | `o2` | **`both`**（預設：介面允許時同開 V9+O2；僅單選時 Agent 會改選 O2）。CLI／網頁可 **`--mureka-model-mode`** 覆寫。其餘：`DRY_RUN=true`、`SCREENSHOTS_DIR=screenshots`、`REQUIRE_LOGGED_IN_PAGE=true`

### LLM 供應商（Google / Groq / OpenRouter）

環境變數 **`LLM_PROVIDER`**：`google`（預設）| `groq` | `openrouter`。只有在啟用 browser-use 或 fallback 時才會使用，並依此建立 **`ChatGoogle`**、**`ChatGroq`** 或 **`ChatOpenRouter`**（見 [`app/services/llm.py`](app/services/llm.py)）。

| 值 | 必填金鑰 | `AGENT_MODEL` 預設 | 說明 |
|----|------------|-------------------|------|
| `google` | `GEMINI_API_KEY` | `gemma-4-31b-it` | 可改 `AGENT_MODEL` 為例：`gemma-4-26b-a4b-it`（約 26B）、`gemini-2.5-flash`、`gemini-2.5-pro` 等（以 AI Studio 為準）；可選 `GEMMA_API_KEY`（`gemma-*` 時優先）。 |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | 模型 id 以 [Groq](https://console.groq.com/) 為準（例：`google/gemma2-9b-it`）。 |
| `openrouter` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | 模型 slug 以 [OpenRouter Models](https://openrouter.ai/models) 為準。 |

**與 Google 並行測試／比較：** 請 **改 `.env` 後重新執行**（或開兩份專案目錄各用不同 `.env`）。本專案**未**實作執行中自動在 429 時切換供應商（需在 Agent 層攔錯並重建 LLM，維護成本高）；若要「額度用完換一家」，請 **手動**改 `LLM_PROVIDER` 與對應金鑰。

**Groq 與 OpenRouter 取捨（概觀）** 見 **[`docs/llm-providers-comparison.md`](docs/llm-providers-comparison.md)**（含速度、免費額度與 browser-use 場景備註）。

### Google API 配額（429 RESOURCE_EXHAUSTED）

若 log 出現 **`429 RESOURCE_EXHAUSTED`** 與 **`generate_content_free_tier_requests`**／**`GenerateRequestsPerDayPerProjectPerModel-FreeTier`**，代表目前 **API 金鑰所屬專案**在 **免費層** 下，**該模型**（例如 `gemma-4-31b`）的 **每日 generate 次數已用滿**（常見上限如 1500 次／日／模型）。這是 **Google 端限制**，與 Mureka、網路無關。

**可處理方式：**

- 到 [Gemini API 配額說明](https://ai.google.dev/gemini-api/docs/rate-limits) 與 [AI Studio 用量](https://ai.dev/rate-limit) 查額度；**隔日**配額重置後再跑，或 **升級付費**／使用 **另一專案與金鑰**。
- 在 `.env` 改 **`AGENT_MODEL`** 為 **其他仍有額度的模型 id**（須與 browser-use／ChatGoogle 相容，並自行查該模型的免費額度是否獨立計算）。

**為什麼會很快累積到每日上限（例如 1500）？**

- **不是「單次程式一次打 1500 下」**，而是 **當日內所有 `generate_content` 加總**（含測試、重跑、其他共用同一金鑰的程式）。
- 舊版 **browser-use** 流程：**每首歌**會跑 **多個 Agent 階段**（登入牆檢查、確認創作頁、填表、提交／dry-run、等待畫面穩定、擷取結果等），**Agent 每走一步通常就是一次 LLM 請求**；順利時也常 **數十～上百次／首**。新版預設 Playwright 流程不需要這些 LLM 步驟。
- **`NOTION_PARALLEL_MAX` > 1** 時 **同時跑多首**，請求會 **並行疊加**，當日累計更快。
- 若切回 browser-use，這屬 **Agent 架構的正常成本**，不是單一邏輯 bug；若要長期大量跑，建議維持 Playwright 主流程，或在 browser-use 模式下降並行、調低各階段 `AGENT_*_MAX_STEPS`。

**多把 API Key：** 專案僅 **`GEMINI_API_KEY`** 與可選 **`GEMMA_API_KEY`**（`gemma-*` 模型時優先），**沒有**自動「429 換下一把」；滿額請 **手動改 `.env`** 或改 **不同 GCP 專案** 的金鑰（免費桶通常依專案分開）。

**Token 與次數：** 免費層日上限相關錯誤常指向 **請求次數**；Google 仍會統計 **token** 並可能有 **RPM／TPM** 等限制，付費則常依 token 計費。

### 寫入 Notion 的營運筆記

與配額、用量累積、多 key、token／次數相關的**完整條列說明**另存於：**[`docs/notion-gemini-runbook.md`](docs/notion-gemini-runbook.md)**。

- 在 Notion：**新增頁面** → **匯入** → **Markdown** → 選取該檔；或開啟該檔 **全選複製** 貼到 Notion 頁面。
- 本專案的 Notion 整合僅用於 **歌曲資料庫**（佇列／回寫），**不會**自動把此筆記推送到你的 workspace；請依上列方式手動建立頁面。

### Windows 主控台與 UTF-8

預設 **cp950** 下，第三方函式庫若在 log 裡輸出 **emoji**，可能出現 **`UnicodeEncodeError`**（`Logging error`）。程式啟動時會嘗試將 **stdout／stderr** 設為 **UTF-8** 並 **`errors=replace`**；網頁控制台啟動的子程序也會帶 **`PYTHONIOENCODING=utf-8`**。若仍亂碼，請用 **Windows Terminal**、執行前 **`chcp 65001`**，或自行設定環境變數 **`PYTHONIOENCODING=utf-8`**。

## 網頁控制台（說明 + 執行）

在 **`music-auto` 根目錄**安裝依賴後：

```bash
pip install -r requirements.txt
python -m web
```

瀏覽器開 **http://127.0.0.1:8765**（預設）。頁面會顯示版本資訊，並可選 **正式（--from-notion）** 或 **手動測試**，以及是否覆寫 `DRY_RUN`。後端**只允許**白名單參數，不執行任意指令。

**串流輸出：** 網頁按「開始執行」會呼叫 **`POST /api/run/stream`**，以 **SSE**（`text/event-stream`）即時轉送子程序的合併 stdout/stderr。子程序使用 **`python -u`** 與環境變數 **`PYTHONUNBUFFERED=1`**，減少管線上的輸出緩衝；若第三方函式庫仍批次寫入，log 可能略呈塊狀，屬正常現象。

**整包回傳（相容）：** `POST /api/run` 仍保留，會等整段結束後一次回傳 JSON（適合腳本或舊客戶端）。

**停止執行：** 頁面 **「停止執行」** 會呼叫 **`POST /api/run/stop`**，對目前由控制台啟動的 `main.py` 子程序送出 **kill**（串流／整包共用同一追蹤）。Chrome 內瀏覽器自動化可能仍須數秒才完全停下。同一時間僅允許一個子程序；若已在跑，再次「開始執行」會回 **409**。

**執行中請勿**切換 Mureka／Create Music 所屬分頁，也**勿**在同一分頁手動點擊或輸入，以免與 CDP 自動化搶操作導致失敗。

- **若按執行出現 HTTP 404**：多半是 **8765 埠上仍在跑舊版後端**（沒有 `POST /api/run/stream`）。請關閉舊的 `python -m web` 後在 `music-auto` 根目錄重新啟動；更新後的前端會在 404 時**自動改走** `POST /api/run`（整包輸出）。

- 變更埠號：`MUSIC_AUTO_WEB_PORT=9000 python -m web`
- 僅本機時請保持 `MUSIC_AUTO_WEB_HOST=127.0.0.1`；若改綁 `0.0.0.0`，請自行承擔暴露風險。

## CLI

```bash
# 正式流程（Notion → Mureka → 更新同一筆 Notion）
python app/main.py --attach-open-page --from-notion --dry-run false

# 指定省 token 的 Playwright 主流程（預設就是這個）
python app/main.py --attach-open-page --from-notion --automation-engine playwright --dry-run false

# UI 大改版時短期救場：先 Playwright，失敗再 browser-use
python app/main.py --attach-open-page --from-notion --automation-engine auto --dry-run false

# 手動單首測試（不查 Notion；會依設定可選擇新建 Notion 列）
python app/main.py --attach-open-page --dry-run false
python app/main.py --attach-open-page --song-title "我的歌" --lyrics "..." --style-tags "pop"
python app/main.py --attach-open-page --instrumental --style-tags "ambient 120bpm" --song-title "BGM"
```

未加 `--attach-open-page` 時會結束並提示用法（避免誤以為會自動登入）。

## browser-use 與「已開啟的 Chrome」

- 程式使用 `BrowserSession(cdp_url=...)` **連線到你已啟動的 Chrome**，不在此流程建立新的持久化 profile 登入。
- 結束時呼叫 **`stop()`** 斷開 CDP，**不應**關掉你的 Chrome 程序（與本地啟動並 `kill()` 整個瀏覽器不同）。

## 一首要多久？能調「速度」嗎？

- **無法給精準秒數**：總時間 = Playwright 填表／點擊 + **Mureka 伺服端實際算歌／轉圈**。Playwright 已把「每步叫 LLM」的耗時拿掉，但無法加快 Mureka 本身生成音樂。
- **粗估**：填表與點擊通常應明顯快於 browser-use；真正等待時間主要落在 Generate 之後。多首 `--from-notion` 仍會依序或分批等待。
- **你能調的是等待策略**：
  - **`PLAYWRIGHT_ACTION_TIMEOUT_SEC`**：單次 DOM 操作等待秒數，預設 12。
  - **`PLAYWRIGHT_GENERATION_WAIT_SEC`**：點 Generate 後最多等多久確認完成／結果 URL，預設 600。設為 0 代表點擊後不等完成，適合只想快速送出、但不適合串行重用同一分頁。
  - **browser-use 相關 `AGENT_*`**：只有切到 `AUTOMATION_ENGINE=browser_use` 或 fallback 時才使用。
- **實務建議**：正式大量跑先用 `DRY_RUN=true` 測 selector 是否能填對；確認後改 `DRY_RUN=false`。若 Mureka 生成很久才出結果，可提高 `PLAYWRIGHT_GENERATION_WAIT_SEC`；若只要投遞任務、結果之後人工看，可設小一點。

## 常見錯誤

| 情況 | 說明 |
|------|------|
| 停在 **Try free now** / **Sign in** / **Continue with Google** | 代表目前畫面被判定為未登入行銷頁；請在一般 Chrome 先登入並進入 Create Music，再重跑。若已登入仍誤判，可暫設 `REQUIRE_LOGGED_IN_PAGE=false`（不建議長期關閉）。 |
| **Please log in manually in a normal browser session first.** | `REQUIRE_LOGGED_IN_PAGE=true` 且偵測到登入牆時拋出。 |
| 還沒登入 | 請完成 Google／Mureka 登入後再執行 `--attach-open-page`。 |
| 不在 **Create Music** 頁 | `verify_create_music_page()` 會要求側欄／Lyrics／Style／Generate 等弱訊號；請手動開對頁面或調整 `MUREKA_CREATE_URL`。 |
| **Could not find or click Generate** | 介面改版或按鈕文案不同；可改 `DRY_RUN=true` 先測填表，或之後調整 prompt／步數上限。 |
| 找不到 **Lyrics** 欄位 | 可能不在創作模式或版型變更；請確認 URL 與畫面為 Custom / Create Music。 |
| CDP 連不上 | 確認 Chrome 是以 `--remote-debugging-port=...` 啟動，且防火牆／URL 與 `BROWSER_CDP_URL` 一致。 |

## Notion（例如資料庫標題為「perplixity 金曲設計」）

- **`--from-notion`**：查 **「是否發佈」= 未勾選** 的列 → 用該列的 **歌名／歌詞／Style** 跑 Mureka → **只更新該 `page_id`**（不另建新列）。請設好 `NOTION_TOKEN`、`NOTION_DATABASE_ID` 與欄位對應（`.env.example`）。
- **未加 `--from-notion`**：仍為「程式指定歌曲」流程；若仍設了 Notion，會**新建一筆**再更新（舊的示範行為）。
- **`NOTION_TITLE_PROPERTY`**：須與 **Title** 欄名一致（例如 `歌名`）。
- **`創作階段` 類 Status 欄**：設 `NOTION_PROP_STATUS_KIND=status` 與 `NOTION_PROP_STATUS=創作階段`，程式會用 Notion API 的 `status` 格式寫入；`NOTION_STATUS_VALUE_*` 必須與你在 Notion 裡建立的**選項名稱**一致（預設：建立時 `編曲中`，成功 `完成`，失敗 `草稿修改`）。若你的狀態欄是 **Rich text**，改設 `NOTION_PROP_STATUS_KIND=rich_text`。
- **`NOTION_PROP_GENERATED_AT`**：對應 **Date** 欄，在**更新**時寫入當下 UTC 時間。
- **URL／錯誤／備註**：`NOTION_PROP_RESULT_URL`、`NOTION_PROP_ERROR`、`NOTION_PROP_NOTES` 僅在資料庫已有對應類型欄位時設定。
- **人聲／純音樂**：設 `NOTION_PROP_VOCAL=人聲`（Select）與 `NOTION_INSTRUMENTAL_VOCAL_LABEL=純音樂`。當該列人聲等於此標籤時，程式以**器樂模式**填表：不往 Mureka **歌詞主欄**貼可演唱歌詞；Notion「歌詞」欄可改放器樂描述（可空白）。其餘人聲選項仍走有歌詞流程，**歌詞欄必填**。
- Database id 若帶 `?v=…` 會自動截斷；JSON 會含 `notion_page_id`。
- n8n 可透過 Execute Command 觸發 `python app/main.py --attach-open-page ...`。

## 授權

依你的專案需求自行補充。
