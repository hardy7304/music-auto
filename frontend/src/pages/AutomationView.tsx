import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Download, Terminal, Database, Cloud } from 'lucide-react';

interface Stats {
  local: number;
  r2: number;
}

export function AutomationView() {
  const [stats, setStats] = useState<Stats>({ local: 0, r2: 0 });
  const [activeTab, setActiveTab] = useState<'generate' | 'download'>('generate');
  
  // Generator form states
  const [preset, setPreset] = useState('from_sheet');
  const [theme, setTheme] = useState('');
  const [count, setCount] = useState(3);
  const [engine, setEngine] = useState('env');
  const [dryRun, setDryRun] = useState('env');
  const [modelMode, setModelMode] = useState('env');
  const [parallelMax, setParallelMax] = useState('env');
  const [songMode, setSongMode] = useState('full');
  const [notionLimit, setNotionLimit] = useState('');
  const [envFile, setEnvFile] = useState('');
  
  // Downloader form states
  const [dlProfile, setDlProfile] = useState('basic');
  const [dlLibraryUrl, setDlLibraryUrl] = useState('');

  // Runner state
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [downloadStats, setDownloadStats] = useState({ new: 0, total: 0 });
  const [downloadProgress, setDownloadProgress] = useState(0);

  const consoleEndRef = useRef<HTMLDivElement | null>(null);

  // Fetch initial stats
  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  };

  useEffect(() => {
    fetchStats();
    // Poll stats every 10 seconds
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const addLog = (text: string) => {
    setLogs((prev) => [...prev, text]);
  };

  const handleStopGenerator = async () => {
    try {
      const res = await fetch('/api/run/stop', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        addLog(`\n🛑 [系統主控] ${data.message || '已送出停止信號'}`);
      }
    } catch (e: any) {
      addLog(`\n❌ 停止失敗: ${e.message}`);
    }
  };

  const handleStopDownloader = async () => {
    try {
      const res = await fetch('/api/download/stop', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        addLog(`\n🛑 [系統主控] ${data.message || '已送出停止下載信號'}`);
      }
    } catch (e: any) {
      addLog(`\n❌ 停止下載失敗: ${e.message}`);
    }
  };

  const readStream = async (url: string, payload: any, onDone: () => void) => {
    setLogs([]);
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.body) {
        addLog("❌ 無法建立資料串流。");
        onDone();
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              
              if (data.t === 'meta') {
                addLog(`🚀 啟動指令: ${data.cmd?.join(' ')}\n`);
              } else if (data.t === 'out') {
                addLog(data.s);
              } else if (data.t === 'error') {
                addLog(`\n❌ 錯誤: ${data.msg}\n`);
              } else if (data.t === 'done') {
                addLog(`\n🏁 執行結束 (狀態碼: ${data.code})\n`);
                fetchStats();
              } else if (data.t === 'dash_stats') {
                setStats({ local: data.local, r2: data.r2 });
              } else if (data.t === 'dl_stats') {
                setDownloadStats({ new: data.new, total: data.total });
              } else if (data.t === 'song_cover') {
                addLog(`🖼️ 偵測到新封面：${data.title}\n`);
              }
            } catch (err) {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (err: any) {
      addLog(`\n❌ 連線發生異常: ${err.message}\n`);
    } finally {
      onDone();
    }
  };

  const handleStartGenerator = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating || isDownloading) return;
    setIsGenerating(true);
    addLog("⏳ 正在初始化自動化生產流程...\n");

    const payload = {
      preset,
      theme: theme || undefined,
      count: count || undefined,
      dry_run: dryRun === 'env' ? null : dryRun === 'true',
      mureka_model_mode: modelMode === 'env' ? null : modelMode,
      notion_parallel_max: parallelMax === 'env' ? null : parseInt(parallelMax),
      notion_limit: notionLimit ? parseInt(notionLimit) : null,
      automation_engine: engine === 'env' ? null : engine,
      song_mode: songMode,
      env_file: envFile || null,
    };

    await readStream('/api/run/stream', payload, () => {
      setIsGenerating(false);
    });
  };

  const handleStartDownloader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating || isDownloading) return;
    setIsDownloading(true);
    setDownloadProgress(0);
    setDownloadStats({ new: 0, total: 0 });
    addLog("⏳ 正在連線 Chrome 並啟動批量下載器...\n");

    const payload = {
      library_url: dlLibraryUrl || null,
      profile: dlProfile,
    };

    await readStream('/api/download/stream', payload, () => {
      setIsDownloading(false);
    });
  };

  return (
    <div className="space-y-6">
      {/* Dashboard Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-center gap-4 rounded-xl bg-neutral-900/60 p-5 border border-neutral-800/40 backdrop-blur-md">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-violet-500/20 text-violet-400">
            <Database className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-neutral-400">本機曲庫總數 (D1)</p>
            <p className="text-2xl font-bold text-white">{stats.local}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 rounded-xl bg-neutral-900/60 p-5 border border-neutral-800/40 backdrop-blur-md">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-violet-500/20 text-violet-400">
            <Cloud className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-neutral-400">R2 雲端同步數</p>
            <p className="text-2xl font-bold text-white">{stats.r2}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-neutral-800">
        <button
          onClick={() => setActiveTab('generate')}
          className={`px-6 py-3 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'generate' ? 'border-violet-500 text-white' : 'border-transparent text-neutral-400 hover:text-white'}`}
        >
          🎛️ 歌曲生成控制台
        </button>
        <button
          onClick={() => setActiveTab('download')}
          className={`px-6 py-3 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'download' ? 'border-violet-500 text-white' : 'border-transparent text-neutral-400 hover:text-white'}`}
        >
          ⬇️ 下載中心
        </button>
      </div>

      {/* Form Area */}
      <div className="rounded-xl bg-neutral-900/40 p-6 border border-neutral-800/40 backdrop-blur-md">
        {activeTab === 'generate' ? (
          <form onSubmit={handleStartGenerator} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Presets */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-neutral-300">執行模式 (Preset)</label>
                <select
                  value={preset}
                  onChange={(e) => setPreset(e.target.value)}
                  className="w-full rounded-lg bg-neutral-800 px-4 py-2.5 text-sm text-white border border-neutral-700 outline-none focus:border-violet-500"
                >
                  <option value="generate_batch">✨ AI 靈感大爆發 (Agent)</option>
                  <option value="process_csv">1. 處理靈感主題 (CSV → Queue)</option>
                  <option value="from_sheet">2. 正式生產 (Google Sheet Queue)</option>
                  <option value="from_notion">舊版生產 (Notion Queue)</option>
                  <option value="manual">單曲測試 (Manual Test)</option>
                </select>
              </div>

              {/* Song Mode */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-neutral-300">歌曲結構模式</label>
                <select
                  value={songMode}
                  onChange={(e) => setSongMode(e.target.value)}
                  className="w-full rounded-lg bg-neutral-800 px-4 py-2.5 text-sm text-white border border-neutral-700 outline-none focus:border-violet-500"
                >
                  <option value="full">正式完整 (Full) - 含主副歌/橋段/結尾</option>
                  <option value="demo">精簡短片 (Demo) - 結構緊湊適合影音</option>
                  <option value="free">自由發揮 (Free) - 由 AI 靈感決定</option>
                </select>
              </div>
            </div>

            {/* Batch generation settings */}
            {preset === 'generate_batch' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4 rounded-lg bg-violet-500/5 border border-violet-500/10">
                <div className="md:col-span-2 space-y-2">
                  <label className="text-sm font-semibold text-neutral-300">音樂種類 / 主題</label>
                  <input
                    type="text"
                    value={theme}
                    onChange={(e) => setTheme(e.target.value)}
                    placeholder="例如：健身、放鬆身心靈、世界流行金曲"
                    className="w-full rounded-lg bg-neutral-800 px-4 py-2 text-sm text-white border border-neutral-700 outline-none focus:border-violet-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-neutral-300">生成數量</label>
                  <input
                    type="number"
                    value={count}
                    onChange={(e) => setCount(parseInt(e.target.value))}
                    min={1}
                    max={20}
                    className="w-full rounded-lg bg-neutral-800 px-4 py-2 text-sm text-white border border-neutral-700 outline-none focus:border-violet-500"
                  />
                </div>
              </div>
            )}

            {/* Advanced configurations toggler */}
            <details className="group border-t border-neutral-800 pt-4">
              <summary className="text-xs font-semibold text-neutral-400 cursor-pointer list-none flex items-center gap-2 select-none">
                <span>⚙️ 展開進階設定 (自動化引擎、模型、限制)</span>
              </summary>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 mt-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-neutral-400">自動化引擎 (Engine)</label>
                  <select
                    value={engine}
                    onChange={(e) => setEngine(e.target.value)}
                    className="w-full rounded-lg bg-neutral-800 px-3 py-2 text-xs text-white border border-neutral-700 outline-none"
                  >
                    <option value="env">沿用 .env 配置</option>
                    <option value="playwright">Playwright (推薦)</option>
                    <option value="auto">Auto (失敗自動切換)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-neutral-400">Dry Run 模式</label>
                  <select
                    value={dryRun}
                    onChange={(e) => setDryRun(e.target.value)}
                    className="w-full rounded-lg bg-neutral-800 px-3 py-2 text-xs text-white border border-neutral-700 outline-none"
                  >
                    <option value="env">沿用 .env 配置</option>
                    <option value="true">開啟 (只跑不點 Generate)</option>
                    <option value="false">關閉 (會點擊 Generate 扣點數)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-neutral-400">生成模型 (Model)</label>
                  <select
                    value={modelMode}
                    onChange={(e) => setModelMode(e.target.value)}
                    className="w-full rounded-lg bg-neutral-800 px-3 py-2 text-xs text-white border border-neutral-700 outline-none"
                  >
                    <option value="env">沿用 .env 配置</option>
                    <option value="v9">僅 V9 模型</option>
                    <option value="o2">僅 O2 模型</option>
                    <option value="both">V9 + O2 雙模型並行</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-neutral-400">並行設定 (Parallel)</label>
                  <select
                    value={parallelMax}
                    onChange={(e) => setParallelMax(e.target.value)}
                    className="w-full rounded-lg bg-neutral-800 px-3 py-2 text-xs text-white border border-neutral-700 outline-none"
                  >
                    <option value="env">沿用 .env 配置</option>
                    <option value="1">單線程 (1)</option>
                    <option value="3">輕量並行 (3)</option>
                    <option value="5">高速並行 (5)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-neutral-400">處理數量限制</label>
                  <input
                    type="number"
                    value={notionLimit}
                    onChange={(e) => setNotionLimit(e.target.value)}
                    placeholder="0 = 無限制"
                    className="w-full rounded-lg bg-neutral-800 px-3 py-2 text-xs text-white border border-neutral-700 outline-none"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-neutral-400">設定檔路徑 (.env)</label>
                  <input
                    type="text"
                    value={envFile}
                    onChange={(e) => setEnvFile(e.target.value)}
                    placeholder="預設 .env"
                    className="w-full rounded-lg bg-neutral-800 px-3 py-2 text-xs text-white border border-neutral-700 outline-none"
                  />
                </div>
              </div>
            </details>

            {/* Run Actions */}
            <div className="flex gap-4 border-t border-neutral-800 pt-4">
              <button
                type="submit"
                disabled={isGenerating || isDownloading}
                className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-violet-700 disabled:bg-neutral-800 disabled:text-neutral-500"
              >
                <Play className="h-4 w-4 fill-current" />
                <span>開始自動化流程</span>
              </button>
              <button
                type="button"
                onClick={handleStopGenerator}
                disabled={!isGenerating}
                className="flex items-center gap-2 rounded-lg border border-neutral-700 px-5 py-2.5 text-sm font-semibold text-neutral-300 transition-colors hover:bg-neutral-800 disabled:border-neutral-800 disabled:text-neutral-600"
              >
                <Square className="h-4 w-4 fill-current" />
                <span>停止執行</span>
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleStartDownloader} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Profile */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-neutral-300">下載模式 (Profile)</label>
                <select
                  value={dlProfile}
                  onChange={(e) => setDlProfile(e.target.value)}
                  className="w-full rounded-lg bg-neutral-800 px-4 py-2.5 text-sm text-white border border-neutral-700 outline-none focus:border-violet-500"
                >
                  <option value="basic">基本 (Basic) - MP3 + 授權書</option>
                  <option value="archive">存檔 (Archive) - MP3 + WAV + 授權書</option>
                  <option value="full">完整 (Full) - MP3 + WAV + 伴奏/MIDI + 授權書</option>
                  <option value="video">影片 (Video) - MP3 + 影片檔 + 授權書</option>
                </select>
              </div>

              {/* Custom library url override */}
              <div className="md:col-span-2 space-y-2">
                <label className="text-sm font-semibold text-neutral-300">覆寫 Mureka 作品庫連結 (選填)</label>
                <input
                  type="text"
                  value={dlLibraryUrl}
                  onChange={(e) => setDlLibraryUrl(e.target.value)}
                  placeholder="留空則預設開啟「我的作品」頁面"
                  className="w-full rounded-lg bg-neutral-800 px-4 py-2.5 text-sm text-white border border-neutral-700 outline-none focus:border-violet-500"
                />
              </div>
            </div>

            {/* Run Actions */}
            <div className="flex gap-4 border-t border-neutral-800 pt-4">
              <button
                type="submit"
                disabled={isGenerating || isDownloading}
                className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-violet-700 disabled:bg-neutral-800 disabled:text-neutral-500"
              >
                <Download className="h-4 w-4" />
                <span>🚀 開始批量下載</span>
              </button>
              <button
                type="button"
                onClick={handleStopDownloader}
                disabled={!isDownloading}
                className="flex items-center gap-2 rounded-lg border border-neutral-700 px-5 py-2.5 text-sm font-semibold text-neutral-300 transition-colors hover:bg-neutral-800 disabled:border-neutral-800 disabled:text-neutral-600"
              >
                <Square className="h-4 w-4 fill-current" />
                <span>停止下載</span>
              </button>
            </div>
            
            {/* Stats info */}
            {isDownloading && (downloadStats.total > 0) && (
              <div className="flex items-center gap-4 text-sm text-neutral-400 mt-2">
                <span>📦 新下載：<strong className="text-white">{downloadStats.new}</strong> 首</span>
                <span>📋 總掃描：<strong className="text-white">{downloadStats.total}</strong> 首</span>
              </div>
            )}
          </form>
        )}
      </div>

      {/* Logger Window */}
      <div className="rounded-xl border border-neutral-800 bg-black p-4 shadow-2xl flex flex-col min-h-[300px]">
        <div className="flex items-center gap-2 text-xs font-semibold text-neutral-500 border-b border-neutral-900 pb-2 mb-3">
          <Terminal className="h-4 w-4 text-violet-400" />
          <span>📜 即時執行日誌 (Live Console Logs)</span>
          {(isGenerating || isDownloading) && (
            <span className="flex h-2 w-2 rounded-full bg-violet-400 animate-ping ml-auto" />
          )}
        </div>
        
        <div className="flex-1 overflow-y-auto max-h-[350px] font-mono text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap select-text">
          {logs.length > 0 ? (
            logs.map((log, index) => (
              <span key={index}>{log}</span>
            ))
          ) : (
            <span className="text-neutral-600">（等待執行中...）</span>
          )}
          <div ref={consoleEndRef} />
        </div>
      </div>
    </div>
  );
}
