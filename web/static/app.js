(function () {
  const versionPill = document.getElementById("versionPill");
  const logOut = document.getElementById("logOut");
  const runForm = document.getElementById("runForm");
  const runBtn = document.getElementById("runBtn");
  const stopBtn = document.getElementById("stopBtn");
  const runStatus = document.getElementById("runStatus");

  // ── 下載中心元素 ──
  const dlLog = document.getElementById("dlLog");
  const dlRunBtn = document.getElementById("dlRunBtn");
  const dlStopBtn = document.getElementById("dlStopBtn");
  const dlStatus = document.getElementById("dlStatus");
  const dlStats = document.getElementById("dlStats");
  const dlNewCount = document.getElementById("dlNewCount");
  const dlTotalCount = document.getElementById("dlTotalCount");

  let runStreamSupported = false;
  let runAbort = null;
  let dlAbort = null;

  // ═══════════════════════════════════════════════════
  // SSE 解析通用函式
  // ═══════════════════════════════════════════════════
  function parseSseBlock(block) {
    const lines = block.split("\n");
    const dataLines = [];
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith("data:")) {
        dataLines.push(lines[i].slice(5).trimStart());
      }
    }
    if (dataLines.length === 0) return null;
    try {
      return JSON.parse(dataLines.join("\n"));
    } catch (e) {
      return { t: "parse_err", raw: dataLines.join("\n") };
    }
  }

  function formatHttpError(status, data) {
    let detail = data.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((e) => e.msg || JSON.stringify(e)).join("\n");
    } else if (detail && typeof detail === "object") {
      detail = JSON.stringify(detail, null, 2);
    }
    return "HTTP " + status + "\n" + (detail || "(無詳情)");
  }

  // ═══════════════════════════════════════════════════
  // Meta
  // ═══════════════════════════════════════════════════
  async function loadMeta() {
    try {
      const r = await fetch("/api/meta");
      if (!r.ok) throw new Error(r.statusText);
      const d = await r.json();
      runStreamSupported = d.run_stream_supported === true;
      versionPill.textContent = "v" + d.app_version + " · Py " + d.python_version;
    } catch (e) {
      versionPill.textContent = "無法載入版本資訊";
    }
  }

  // ═══════════════════════════════════════════════════
  // Helper: 取得 radio 值
  // ═══════════════════════════════════════════════════
  function getRadioValue(name) {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : null;
  }

  function dryRunBody() {
    const v = getRadioValue("dry");
    if (v === "true") return true;
    if (v === "false") return false;
    return null;
  }

  function songModeBody() {
    const v = getRadioValue("song_mode");
    if (v === "full" || v === "demo" || v === "free") return v;
    return "full";
  }

  // ═══════════════════════════════════════════════════
  // 歌曲生成 — Stream
  // ═══════════════════════════════════════════════════
  async function requestStop() {
    try {
      const r = await fetch("/api/run/stop", { method: "POST" });
      const j = await r.json().catch(() => ({}));
      if (runAbort) runAbort.abort();
      if (j && j.message) runStatus.textContent = String(j.message);
    } catch (e) { console.error(e); }
  }

  if (stopBtn) stopBtn.addEventListener("click", requestStop);

  // Toggle UI based on preset
  runForm.addEventListener("change", (ev) => {
    if (ev.target.name === "preset") {
      const preset = ev.target.value;
      const batchSettings = document.getElementById("batchSettings");
      if (batchSettings) {
        batchSettings.style.display = preset === "generate_batch" ? "block" : "none";
      }
    }
  });

  runForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const preset = getRadioValue("preset");
    if (!preset) return;

    const body = {
      preset,
      dry_run: dryRunBody(),
      mureka_model_mode: getRadioValue("mmm") === "env" ? null : getRadioValue("mmm"),
      notion_parallel_max: getRadioValue("npm") === "env" ? null : parseInt(getRadioValue("npm"), 10),
      notion_limit: parseInt(document.getElementById("notionLimitInput").value, 10) || null,
      automation_engine: getRadioValue("engine") === "env" ? null : getRadioValue("engine"),
      song_mode: songModeBody(),
      env_file: document.getElementById("envFileInput").value.trim() || null,
      theme: document.getElementById("themeInput") ? document.getElementById("themeInput").value.trim() : null,
      count: document.getElementById("countInput") ? parseInt(document.getElementById("countInput").value, 10) : 1,
    };

    runAbort = new AbortController();
    runBtn.disabled = true;
    if (stopBtn) stopBtn.disabled = false;
    runStatus.hidden = false;
    runStatus.textContent = "發送請求中...";
    logOut.textContent = "發送請求中...\n";

    const t0 = Date.now();
    const timer = setInterval(() => {
      const sec = Math.floor((Date.now() - t0) / 1000);
      runStatus.textContent = `執行中 · 已 ${sec} 秒 — 請勿切換或手動操作 Create Music 分頁。`;
    }, 1000);

    let header = "", output = "", exitCode = null, streamError = null;

    try {
      if (!runStreamSupported) {
        logOut.textContent = "（整包模式）子程序執行中...\n";
        const res = await runViaBatch(body, t0, runAbort.signal);
        logOut.textContent = res;
        return;
      }

      let r = await fetch("/api/run/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: runAbort.signal,
      });

      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        logOut.textContent = formatHttpError(r.status, data);
        return;
      }

      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let sep;
        while ((sep = buf.indexOf("\n\n")) >= 0) {
          const block = buf.slice(0, sep);
          buf = buf.slice(sep + 2);
          const msg = parseSseBlock(block);
          if (!msg || !msg.t) continue;
          if (msg.t === "meta") {
            header = "$ " + msg.cmd.join(" ") + "\n\n--- 串流輸出 ---\n";
            logOut.textContent = header + output;
          } else if (msg.t === "out") {
            output += msg.s;
            logOut.textContent = header + output;
            logOut.scrollTop = logOut.scrollHeight;
          } else if (msg.t === "done") {
            exitCode = msg.code;
          } else if (msg.t === "error") {
            streamError = msg.msg;
          }
        }
      }

      const elapsed = Math.round((Date.now() - t0) / 1000);
      logOut.textContent += `\n--- 結束 ---\n總耗時約 ${elapsed} 秒\nexit code: ${exitCode}`;
      if (streamError) logOut.textContent += `\n錯誤：${streamError}`;
    } catch (e) {
      logOut.textContent += `\n請求失敗：${e}`;
    } finally {
      clearInterval(timer);
      runBtn.disabled = false;
      if (stopBtn) stopBtn.disabled = true;
      runStatus.hidden = true;
    }
  });

  async function runViaBatch(body, t0, signal) {
    const r = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: signal,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return formatHttpError(r.status, data);
    const elapsed = Math.round((Date.now() - t0) / 1000);
    return [
      "（整包模式：總耗時約 " + elapsed + " 秒）",
      "$ " + (data.command || []).join(" "),
      "--- stdout ---",
      data.stdout || "(空)",
      "--- exit " + data.exit_code + " ---",
    ].join("\n");
  }

  // ═══════════════════════════════════════════════════
  // 下載中心 — 獨立邏輯（不影響歌曲生成）
  // ═══════════════════════════════════════════════════
  async function downloadStop() {
    try {
      await fetch("/api/download/stop", { method: "POST" });
      if (dlAbort) dlAbort.abort();
    } catch (e) { console.error(e); }
  }

  if (dlStopBtn) dlStopBtn.addEventListener("click", downloadStop);
  if (dlRunBtn) dlRunBtn.addEventListener("click", startDownload);

  async function startDownload() {
    dlAbort = new AbortController();
    dlRunBtn.disabled = true;
    dlStopBtn.disabled = false;
    dlStatus.hidden = false;
    dlStatus.className = "dl-status running";
    dlStatus.textContent = "⬇️ 下載中... 正在連接 Chrome";
    dlLog.textContent = "發送請求中...\n";
    dlStats.hidden = true;

    const t0 = Date.now();
    const timer = setInterval(() => {
      const sec = Math.floor((Date.now() - t0) / 1000);
      dlStatus.textContent = `⬇️ 下載中 · 已 ${sec} 秒`;
    }, 1000);

    let header = "", output = "";

    try {
      const selectedProfile = getRadioValue("dl_profile") || "basic";
      const r = await fetch("/api/download/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ library_url: null, profile: selectedProfile }),
        signal: dlAbort.signal,
      });

      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        dlLog.textContent = formatHttpError(r.status, data);
        return;
      }

      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let sep;
        while ((sep = buf.indexOf("\n\n")) >= 0) {
          const block = buf.slice(0, sep);
          buf = buf.slice(sep + 2);
          const msg = parseSseBlock(block);
          if (!msg || !msg.t) continue;

          if (msg.t === "meta") {
            header = "$ " + msg.cmd.join(" ") + "\n\n--- 即時輸出 ---\n";
            dlLog.textContent = header + output;
          } else if (msg.t === "out") {
            output += msg.s;
            dlLog.textContent = header + output;
            dlLog.scrollTop = dlLog.scrollHeight;
          } else if (msg.t === "dl_stats") {
            dlStats.hidden = false;
            dlNewCount.textContent = msg.new;
            dlTotalCount.textContent = msg.total;
          } else if (msg.t === "done") {
            const elapsed = Math.round((Date.now() - t0) / 1000);
            dlLog.textContent += `\n--- 下載結束 ---\n總耗時約 ${elapsed} 秒\n`;
            dlStatus.className = "dl-status";
            dlStatus.textContent = "✅ 下載完成";
          } else if (msg.t === "error") {
            dlLog.textContent += `\n❌ 錯誤：${msg.msg}\n`;
            dlStatus.className = "dl-status";
            dlStatus.textContent = "❌ 下載失敗";
          }
        }
      }
    } catch (e) {
      if (e.name === "AbortError") {
        dlLog.textContent += "\n⏹️ 下載已被使用者停止。\n";
        dlStatus.textContent = "⏹️ 已停止";
      } else {
        dlLog.textContent += `\n請求失敗：${e}\n`;
        dlStatus.textContent = "❌ 連線失敗";
      }
    } finally {
      clearInterval(timer);
      dlRunBtn.disabled = false;
      dlStopBtn.disabled = true;
      dlStatus.className = "dl-status";
    }
  }

  // ═══════════════════════════════════════════════════
  // 啟動
  // ═══════════════════════════════════════════════════
  loadMeta();
})();