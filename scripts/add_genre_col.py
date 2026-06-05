import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.config import load_settings
from app.services.d1_manager import D1Manager

async def main():
    settings = load_settings()
    d1 = D1Manager(settings)
    
    if not d1.enabled:
        print("D1 not enabled")
        return
        
    sql = "ALTER TABLE mureka_songs ADD COLUMN genre TEXT DEFAULT 'Uncategorized';"
    try:
        await d1._execute_sql(sql)
        print("Successfully added genre column.")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("Column already exists.")
        else:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
