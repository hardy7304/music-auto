

# 🎵 Sonora — 音樂串流 + 探索 App

原創品牌的音樂 App，結合「唱片公司藝人展示」與「串流播放器」。
技術：**React 18 + TypeScript + Tailwind CSS + Framer Motion**（純前端，無後端）。

---

## 功能總覽

- 🏠 **首頁探索**：精選 Hero、新發行、為你推薦、特色藝人、熱門排行
- 🔎 **搜尋**：依曲風瀏覽 + 即時搜尋歌曲 / 藝人
- 📚 **音樂庫**：歌單清單
- 👤 **藝人專頁**：大頭圖、簡介、追蹤數、該藝人歌曲清單
- ▶️ **真實播放器**：用 `<audio>` 播放真實音訊（播放/暫停、進度條 seek、音量）
- 🎤 **同步歌詞**：卡拉OK 式逐句高亮，點句可跳轉
- 📻 **電台自動播放**：播完自動接歌、上一首/下一首、隨機、循環
- 📱 **響應式**：手機版側欄收合為底部導覽列

---

## 🚀 在 Antigravity / Cline / 任何 IDE 啟動（保母級步驟）

### 步驟 1：建立一個 Vite + React + TS 專案

```bash
npm create vite@latest sonora -- --template react-ts
cd sonora
```

### 步驟 2：放入這些檔案

把本專案的以下檔案 / 資料夾複製到新專案的 `src/` 裡：

```
src/
├── App.tsx              ← 用「App.clean.tsx」改名而來（見步驟 3）
├── index.css
├── data/music.ts
├── context/PlayerContext.tsx
├── components/   （Sidebar, TopBar, PlayerBar, Hero, Carousel,
│                  TrackCard, ArtistCard, PlaylistCard,
│                  MobileNav, LyricsView）
└── pages/        （HomeView, SearchView, LibraryView, ArtistView）
```

### 步驟 3：用乾淨版的 App

- 把 **`App.clean.tsx` 改名為 `App.tsx`**（覆蓋原本的）。
- **刪除** `canvas.manifest.js` 和 `useScreenInit.js`（這兩個只給 Magic Patterns 預覽用，外部不需要）。

> `App.clean.tsx` 已經移除所有 Magic Patterns 專屬相依，可直接執行。

### 步驟 4：安裝套件

```bash
npm install
npm install lucide-react framer-motion react-router-dom tailwind-merge date-fns
```

### 步驟 5：設定 Tailwind CSS

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

`tailwind.config.js`：
```js
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

確認 `src/index.css` 最上面有 Tailwind 的三行 import（本專案的 `index.css` 已包含，直接沿用即可）。

### 步驟 6：確認進入點

`src/main.tsx`（Vite 預設）：
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```
> 注意：本專案用「具名匯出」`export function App`，所以是 `import { App }`（有大括號）。

### 步驟 7：啟動

```bash
npm run dev
```
打開瀏覽器看到的網址（通常 http://localhost:5173）即可。

---

## 🎧 換成你自己的歌曲（Mureka → NAS / Cloudflare R2）

目前用的是公開示範 mp3。換成你的歌：

1. 用 **Mureka** 生成歌曲 → 下載到電腦 → 上傳到 **Cloudflare R2**（或 NAS）。
2. 取得每首歌的公開網址。
3. 打開 `src/data/music.ts`，把每首歌的 `audioUrl` 換成你的網址：

```ts
{
  id: 't1',
  title: 'Neon Tide',
  artist: 'Aurelia Quinn',
  album: 'Glass Horizons',
  cover: 'https://你的圖片網址.jpg',
  duration: 214,
  audioUrl: 'https://你的-r2-網域.com/songs/neon-tide.mp3', // ← 換這裡
}
```

**重要設定**：
- R2 / NAS 必須用 **HTTPS**（http 會被前端擋）。
- 設定 **CORS**，允許你的前端網域存取音訊檔。

### 換歌詞
在 `src/data/music.ts` 的 `LYRICS` 物件，用歌曲 id 當 key，填入 `{ time, text }`（`time` 是該句開始的秒數）：
```ts
const LYRICS = {
  t1: [
    { time: 0, text: '第一句歌詞' },
    { time: 8, text: '第二句歌詞' },
  ],
}
```

---

## 🤖 給 Antigravity / Cline 的提示範例

把整個資料夾打開後，可以這樣下指令：

> 「這是一個 React + TypeScript + Tailwind 的音樂串流 App（Sonora）。
> 結構：`components/`（UI 元件）、`pages/`（頁面）、`context/PlayerContext.tsx`（播放器全域狀態）、`data/music.ts`（歌曲資料）。
> 請幫我加上 ______ 功能。」

可以接著請 AI 做的擴充：
- 使用者帳號 / 登入
- 把歌曲資料改從後端 API 讀取
- 建立歌單 CRUD（新增 / 刪除歌曲）
- 串接 Mureka API 自動生成歌曲（需後端保護 API key）
- 深色 / 淺色主題切換

---

## 📁 專案結構

```
src/
├── App.tsx                    主框架（側欄 + 內容 + 播放器）
├── index.css                  全域樣式 + 字體 + 進度條樣式
├── context/
│   └── PlayerContext.tsx       播放器狀態（播放/佇列/電台/歌詞開關）
├── data/
│   └── music.ts                歌曲、藝人、歌單、歌詞資料 + 輔助函式
├── components/
│   ├── Sidebar.tsx             左側導覽 + 歌單
│   ├── TopBar.tsx              頂部搜尋 + 帳號
│   ├── PlayerBar.tsx           底部播放器（含歌詞鈕）
│   ├── LyricsView.tsx          全螢幕同步歌詞
│   ├── Hero.tsx                首頁精選橫幅
│   ├── Carousel.tsx            橫向滑動區塊
│   ├── TrackCard.tsx           歌曲卡片
│   ├── ArtistCard.tsx          藝人卡片
│   ├── PlaylistCard.tsx        歌單卡片
│   └── MobileNav.tsx           手機底部導覽
└── pages/
    ├── HomeView.tsx            首頁探索
    ├── SearchView.tsx          搜尋
    ├── LibraryView.tsx         音樂庫
    └── ArtistView.tsx          藝人專頁
```

---

製作於 Magic Patterns。所有藝人、專輯、封面皆為虛構 / 示意，未使用任何真實品牌商標。

