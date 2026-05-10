"""
環境自检：請在 music-auto 目錄執行
  .venv\\Scripts\\python scripts\\self_check.py

或（專案根目錄）
  python scripts\\self_check.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    print("music-auto 環境檢查")
    print(f"專案根目錄: {_ROOT}")
    ok = True

    if not (_ROOT / "app" / "main.py").is_file():
        print("[FAIL] 找不到 app/main.py（請在 music-auto 目錄執行此腳本）")
        return 1

    venv_py = _ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_py.is_file():
        print("[WARN] 未找到 .venv（建議: python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt）")
    else:
        try:
            proc = subprocess.run(
                [str(venv_py), "--version"],
                cwd=str(_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode == 0:
                version = (proc.stdout or proc.stderr or "").strip()
                print(f"[OK] 虛擬環境: {venv_py} ({version})")
            else:
                msg = (proc.stderr or proc.stdout or "").strip()
                print(f"[FAIL] .venv\\Scripts\\python.exe 存在但無法執行: {msg}")
                ok = False
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] .venv\\Scripts\\python.exe 存在但無法執行: {exc}")
            ok = False

    try:
        from web.server import app

        paths = []
        for route in app.routes:
            p = getattr(route, "path", None)
            if p:
                paths.append(p)
        need = {"/api/run", "/api/run/stream", "/api/run/stop"}
        found = set(paths) & need
        if need <= found:
            print(f"[OK] 網頁 API 路由已註冊: {sorted(need)}")
        else:
            print(f"[FAIL] 缺少路由: {need - found}（請更新程式並重啟 python -m web）")
            ok = False
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] 无法载入 web.server: {exc}")
        ok = False

    try:
        from app.config import load_settings

        s = load_settings()
        print(
            f"[OK] AUTOMATION_ENGINE={s.automation_engine}  "
            f"LLM_PROVIDER={s.llm_provider}  AGENT_MODEL={s.agent_model!r}"
        )
        if s.automation_engine in ("browser_use", "auto") or s.browser_use_fallback:
            from app.services.llm import create_browser_llm

            llm = create_browser_llm(s)
            print(f"[OK] LLM 已建立: {type(llm).__name__}")
        else:
            print("[OK] Playwright 主流程不需要建立 LLM")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] 設定或 LLM 建立失敗: {exc}")
        ok = False

    url = "http://127.0.0.1:8765/api/meta"
    print(f"\n探測本機網頁（若未啟動會失敗）: {url}")
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310
            data = json.loads(resp.read().decode())
        ver = data.get("app_version", "?")
        rs = data.get("run_stream_supported")
        print(f"[OK] 已連上控制台  version={ver}  run_stream_supported={rs}")
        if rs is not True:
            print("[WARN] run_stream_supported 非 true 時，請更新 web 並重啟")
    except urllib.error.URLError as exc:
        print(f"- 無法連線（正常若尚未執行 python -m web）: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"- 探測異常: {exc}")

    print("\n下一步:")
    print("  1) 關掉舊的「python -m web」視窗，在 music-auto 執行:  .venv\\Scripts\\python -m web")
    print("  2) 開 Chrome 遠端偵錯並登入 Mureka 創作頁")
    print("  3) 瀏覽器開 http://127.0.0.1:8765 按執行，或命令列:")
    print("     .venv\\Scripts\\python -u app\\main.py --attach-open-page --dry-run true")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
