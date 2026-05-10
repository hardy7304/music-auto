# 依賴：pip install google-genai python-dotenv（專案 requirements 已含 dotenv；建議加上 google-genai）
"""
以 google-genai 串流呼叫 Gemma 4 31B，驗證 GEMINI_API_KEY 與模型可用。
與 browser-use 的 ChatGoogle 分開；此腳本僅作 API / 配額測試。

用法（在 music-auto 目錄）：
  python scripts/verify_gemma_stream.py
  python scripts/verify_gemma_stream.py --prompt "用繁體中文說明什麼是瀏覽器自動化"
  python scripts/verify_gemma_stream.py --no-search --thinking low
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

from google import genai
from google.genai import types


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Gemma 4 31B (google-genai)")
    parser.add_argument(
        "--prompt",
        default="你好，請用繁體中文簡短自我介紹。",
        help="使用者提示詞",
    )
    parser.add_argument(
        "--model",
        default="gemma-4-31b-it",
        help="模型 id（須為帳戶可用之 Gemma/Gemini 模型）",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="不啟用 Google Search 工具（部分方案或模型可能不支援）",
    )
    parser.add_argument(
        "--thinking",
        choices=("high", "low", "medium", "minimal"),
        default="high",
        help="ThinkingConfig.thinking_level（不支援時請改 low 或改用 --no-thinking）",
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="不傳 thinking_config（舊版 SDK 或部分模型可備援）",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("請在 .env 設定 GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=args.prompt)],
        ),
    ]

    tools: list = []
    if not args.no_search:
        tools.append(types.Tool(google_search=types.GoogleSearch()))

    thinking_cfg = None
    if not args.no_thinking:
        level = args.thinking.upper()
        thinking_cfg = types.ThinkingConfig(thinking_level=level)

    gen_cfg_kwargs: dict = {}
    if thinking_cfg is not None:
        gen_cfg_kwargs["thinking_config"] = thinking_cfg
    if tools:
        gen_cfg_kwargs["tools"] = tools

    generate_content_config = types.GenerateContentConfig(**gen_cfg_kwargs)

    try:
        stream = client.models.generate_content_stream(
            model=args.model,
            contents=contents,
            config=generate_content_config,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"generate_content_stream 失敗: {exc}", file=sys.stderr)
        print("可嘗試：--no-search、--no-thinking 或 --thinking low", file=sys.stderr)
        sys.exit(1)

    for chunk in stream:
        if text := getattr(chunk, "text", None):
            print(text, end="")
    print()


if __name__ == "__main__":
    main()
