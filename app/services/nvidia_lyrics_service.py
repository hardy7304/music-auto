import os
import json
import re
from openai import AsyncOpenAI
from app.config import (
    AppSettings,
    load_settings,
)

class NvidiaLyricsService:
    def __init__(self, api_key: str = None, model: str = None):
        self.settings = load_settings()
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.model = model or os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v3")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        )
        self.model = model or os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")

    async def generate_lrc(self, song_title: str, lyrics_text: str, duration_sec: int = 240) -> str:
        """
        利用 NVIDIA AI 預測歌詞時間點並輸出 LRC 格式。
        """
        prompt = f"""
你是一位專業的音樂製作助理。請幫我為以下歌詞加上精確的 [mm:ss.xx] 時間戳記。
這首歌的總長度大約是 {duration_sec} 秒。

歌曲標題：{song_title}
原始歌詞內容：
{lyrics_text}

任務要求：
1. 請根據歌詞的字數、段落（如 [Intro], [Verse], [Chorus]）合理分配時間。
2. 輸出格式必須是標準的 LRC 格式，每一行開頭都是 [mm:ss.xx]。
3. 確保最後一句歌詞在歌曲結束前完成。
4. 只輸出 LRC 內容，不要有任何其他解釋文字。
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個精準的音樂歌詞同步專家，只輸出 LRC 格式內容。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            lrc_content = response.choices[0].message.content
            return lrc_content.strip()
        except Exception as e:
            print(f"NVIDIA API Error: {e}")
            return lyrics_text # 回退到原始文字
