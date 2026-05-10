# OpenRouter 與 Groq（概觀）：搭配 browser-use / music-auto

本檔供與 **[`README.md`](../README.md)**「LLM 供應商」一併閱讀。實際免費額度、模型清單與價格以 **Groq Console**、**OpenRouter** 與各供應商最新文件為準。

---

## 定位差異

| | **OpenRouter** | **Groq** |
|--|----------------|----------|
| **本質** | 多模型聚合（類似「模型超市」） | 自有推理服務，強調低延遲 |
| **模型數量** | 非常多（各家 slug 並列） | 以平台列出的為主，相對少 |
| **速度** | 依模型與路由而異 | 常見情境下延遲較低（實測因模型／地區而異） |
| **設定** | `OPENROUTER_API_KEY` + OpenRouter 模型 id | `GROQ_API_KEY` + Groq 模型 id |

在 **music-auto** 中：設定 **`LLM_PROVIDER=openrouter`** 或 **`groq`**，並設定 **`AGENT_MODEL`** 為對應平台支援的 model id，即可與 **browser-use** 的 Agent 一併使用（見專案 [`app/services/llm.py`](../app/services/llm.py)）。

---

## 對 browser-use（操作 Mureka）的意義

這類流程需要：

- 讀懂頁面結構與指令、產生下一步操作；
- 多步反覆呼叫 LLM（每步通常一次請求）。

因此 **推論延遲** 會直接影響「等 AI 想好再動」的體感時間；**免費額度／RPD／RPM** 則決定每日能跑多少首或測試多少次。若 **Google 免費層**已滿，可改用 **Groq／OpenRouter** 上仍有額度的模型做對照實驗（**改 `.env` 後重跑**即可；本專案不內建自動輪替）。

---

## 使用建議（實務）

1. **主力實驗**：在 Groq 或 OpenRouter 選一個 **穩定、延遲可接受** 的模型，跑通 `--attach-open-page` 全流程。
2. **對照 Google**：`LLM_PROVIDER=google` 與其他供應商 **分開測**，比較成功率與總耗時（同時注意各平台額度不同，無法單純橫向比「誰比較省錢」而不看官方計費）。
3. **額度**：免費層常改；若出現 **429／rate limit**，請查該平台儀表板或改 **其他模型 slug**／**付費方案**。

---

## 一句話

- **Groq**：延遲常為賣點；模型選擇以平台為準。  
- **OpenRouter**：單一 API 串多種模型；速度與價格依所選模型而異。  
- **兩者都可在本專案用 `LLM_PROVIDER` 切換**，與 **Google（`ChatGoogle`）** 分開設定即可比較。
