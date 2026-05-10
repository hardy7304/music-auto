"""python -m web → 啟動本機控制台（請在 music-auto 目錄執行）。"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    from web.server import app

    host = os.getenv("MUSIC_AUTO_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("MUSIC_AUTO_WEB_PORT", "8765"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
