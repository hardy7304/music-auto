"""Cloudflare D1 Database Manager."""

import asyncio
import json
import urllib.request
from dataclasses import asdict
from typing import Any

from app.config import AppSettings
from app.logger import get_logger

logger = get_logger(__name__)

class D1Manager:
    """Handles communication with Cloudflare D1 via REST API."""

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self.account_id = settings.cloudflare_account_id
        self.db_id = settings.cloudflare_d1_database_id
        self.token = settings.cloudflare_api_token
        
        self.enabled = bool(self.account_id and self.db_id and self.token)
        if not self.enabled:
            logger.warning("D1Manager disabled: Missing Cloudflare credentials.")

    async def initialize_db(self) -> bool:
        """Create the table if it does not exist."""
        if not self.enabled:
            return False
            
        sql = """
        CREATE TABLE IF NOT EXISTS mureka_songs (
            song_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT,
            folder_name TEXT,
            r2_category_path TEXT,
            cover_url TEXT,
            lyrics TEXT,
            status TEXT DEFAULT 'downloaded',
            genre TEXT DEFAULT 'Uncategorized',
            downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            result = await self._execute_sql(sql)
            logger.info("D1 Database initialized successfully.")
            return True
        except Exception as e:
            logger.error("Failed to initialize D1 Database: %s", e)
            return False

    async def upsert_song(
        self,
        song_id: str,
        title: str,
        author: str | None = None,
        folder_name: str | None = None,
        r2_category_path: str | None = None,
        cover_url: str | None = None,
        lyrics: str | None = None,
        status: str = "downloaded",
        genre: str = "Uncategorized"
    ) -> bool:
        """Insert or update a song record."""
        if not self.enabled:
            return False

        sql = """
        INSERT INTO mureka_songs (
            song_id, title, author, folder_name, r2_category_path, cover_url, lyrics, status, genre, downloaded_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
        )
        ON CONFLICT(song_id) DO UPDATE SET
            title=excluded.title,
            author=excluded.author,
            folder_name=excluded.folder_name,
            r2_category_path=excluded.r2_category_path,
            cover_url=COALESCE(excluded.cover_url, mureka_songs.cover_url),
            lyrics=COALESCE(excluded.lyrics, mureka_songs.lyrics),
            status=excluded.status,
            genre=COALESCE(mureka_songs.genre, 'Uncategorized'),
            downloaded_at=CURRENT_TIMESTAMP
        """
        params = [
            song_id,
            title,
            author or "",
            folder_name or "",
            r2_category_path or "",
            cover_url or "",
            lyrics or "",
            status,
            genre
        ]
        
        try:
            await self._execute_sql(sql, params)
            logger.info("Saved metadata to D1 for song: %s (%s)", title, song_id)
            return True
        except Exception as e:
            logger.error("Failed to save to D1 for %s: %s", title, e)
            return False

    async def get_recent_songs(self, limit: int = 50, offset: int = 0, genre: str | None = None) -> list[dict[str, Any]]:
        """Fetch recently downloaded songs. Optionally filter by genre."""
        if not self.enabled:
            return []

        if genre:
            sql = "SELECT * FROM mureka_songs WHERE genre = ? ORDER BY downloaded_at DESC LIMIT ? OFFSET ?"
            params = [genre, limit, offset]
        else:
            sql = "SELECT * FROM mureka_songs ORDER BY downloaded_at DESC LIMIT ? OFFSET ?"
            params = [limit, offset]
            
        try:
            results = await self._execute_sql(sql, params)
            if results and isinstance(results, list) and len(results) > 0:
                # D1 returns results in the first item's "results" array
                if "results" in results[0]:
                    return results[0]["results"]
            return []
        except Exception as e:
            logger.error("Failed to fetch recent songs: %s", e)
            return []

    async def update_song_genre(self, song_id: str, genre: str) -> bool:
        """Update the genre of a specific song."""
        if not self.enabled:
            return False
            
        sql = "UPDATE mureka_songs SET genre = ? WHERE song_id = ?"
        try:
            await self._execute_sql(sql, [genre, song_id])
            logger.info("Updated genre for song %s to %s", song_id, genre)
            return True
        except Exception as e:
            logger.error("Failed to update genre for song %s: %s", song_id, e)
            return False

    async def _execute_sql(self, sql: str, params: list[Any] | None = None) -> Any:
        """Execute a SQL statement against Cloudflare D1 via HTTP."""
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/d1/database/{self.db_id}/query"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "sql": sql,
            "params": params or []
        }
        
        # Cloudflare D1 API expects an array of queries if using /query endpoint? 
        # Actually /query accepts an object, but /raw accepts an array. 
        # Wait, the official API spec says the body should be:
        # { "sql": "...", "params": [...] } for single, but actually it expects an array of objects?
        # No, wait, if you want multiple queries, you pass an array. Single query is often an object.
        # Let's pass the object directly, D1 often accepts both or we wrap it in a list.
        # It's safer to wrap it in a list? No, v4 D1 API /query takes a single object or array.
        # Wait, if we use /query, we should pass `{"sql": sql, "params": params}`. Let's wrap in a list just in case.
        # Wait, `https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database`
        # body: { "sql": string, "params": array } for single statement.
        
        data = json.dumps(payload).encode("utf-8")
        
        def _make_request():
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
                
        response_data = await asyncio.to_thread(_make_request)
        
        if not response_data.get("success"):
            raise Exception(f"D1 API Error: {response_data.get('errors')}")
            
        return response_data.get("result", [])
