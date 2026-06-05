import asyncio
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to sys.path to import app modules
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import load_settings
from app.services.storage_manager import StorageManager
from app.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("sync_to_r2")

def sync_folder(sm: StorageManager, folder: Path) -> None:
    try:
        logger.info("Starting sync for: %s", folder.name)
        res = sm._sync_to_r2_sync(folder)
        logger.info("Sync result for %s: %s", folder.name, res)
    except Exception as e:
        logger.error("Error syncing %s: %s", folder.name, e)

async def main():
    settings = load_settings()
    sm = StorageManager(settings)
    
    if not sm._r2_client or not settings.r2_bucket_name:
        logger.error("R2 credentials not configured correctly.")
        return
        
    download_dir = Path(settings.download_dir).resolve()
    if not download_dir.exists():
        logger.error("Download directory does not exist: %s", download_dir)
        return
        
    folders = [f for f in download_dir.iterdir() if f.is_dir()]
    logger.info("Found %d folders to sync in %s", len(folders), download_dir)
    
    # Use ThreadPoolExecutor to run syncs in parallel, max 4 workers to prevent overwhelming connection
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = [
            loop.run_in_executor(executor, sync_folder, sm, folder)
            for folder in folders
        ]
        await asyncio.gather(*tasks)
        
    logger.info("All R2 sync tasks completed.")

if __name__ == "__main__":
    asyncio.run(main())
