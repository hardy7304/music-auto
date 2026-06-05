"""Storage Manager for Dual Backup to NAS and Cloudflare R2."""

import asyncio
import os
import shutil
from pathlib import Path

from app.config import AppSettings
from app.logger import get_logger

logger = get_logger(__name__)

class StorageManager:
    """Handles automatic backup of downloaded folders to NAS and Cloudflare R2."""
    
    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._nas_path = None
        if settings.nas_sync_path:
            self._nas_path = Path(settings.nas_sync_path).resolve()
            
        self._r2_client = None
        if all([settings.r2_account_id, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name]):
            try:
                import boto3
                self._r2_client = boto3.client(
                    's3',
                    endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
                    aws_access_key_id=settings.r2_access_key_id,
                    aws_secret_access_key=settings.r2_secret_access_key,
                    region_name='auto',
                )
            except Exception as exc:
                logger.error("Failed to initialize R2 client: %s", exc)

    def _get_category_path(self, folder_name: str) -> str:
        """Parse folder name (YYYYMMDD_Author_Title_ID) to create a category path (YYYY-MM/Author/Folder)."""
        parts = folder_name.split("_")
        if len(parts) >= 4 and len(parts[0]) == 8 and parts[0].isdigit():
            date_str = parts[0]
            year_month = f"{date_str[:4]}-{date_str[4:6]}"
            author = parts[1]
            return f"{year_month}/{author}/{folder_name}"
        return folder_name

    def _sync_to_nas_sync(self, source_folder: Path) -> str:
        """Synchronously copy to NAS."""
        if not self._nas_path:
            return ""
        
        try:
            category_path = self._get_category_path(source_folder.name)
            # Use os.path.normpath to handle Windows slash correctly for NAS
            target_folder = self._nas_path / Path(category_path)
            target_folder.parent.mkdir(parents=True, exist_ok=True)
            
            # If target exists, just copy missing files or overwrite
            if not target_folder.exists():
                shutil.copytree(source_folder, target_folder)
            else:
                for item in source_folder.iterdir():
                    target_item = target_folder / item.name
                    if not target_item.exists() or target_item.stat().st_size != item.stat().st_size:
                        if item.is_file():
                            shutil.copy2(item, target_item)
            
            logger.info("Backed up %s to NAS: %s", source_folder.name, self._nas_path)
            return "✅ NAS 備份完成"
        except Exception as exc:
            logger.error("NAS backup failed for %s: %s", source_folder.name, exc)
            return f"❌ NAS 備份失敗: {exc}"

    def _sync_to_r2_sync(self, source_folder: Path) -> str:
        """Synchronously upload to R2."""
        if not self._r2_client or not self._settings.r2_bucket_name:
            return ""
            
        bucket = self._settings.r2_bucket_name
        try:
            category_path = self._get_category_path(source_folder.name)
            # Ensure S3 keys always use forward slashes
            category_key = category_path.replace("\\", "/")
            for item in source_folder.iterdir():
                if item.is_file():
                    # Prefix with the category path
                    s3_key = f"{category_key}/{item.name}"
                    self._r2_client.upload_file(str(item), bucket, s3_key)
                    
            logger.info("Backed up %s to R2 Bucket: %s", source_folder.name, bucket)
            return "✅ Cloudflare R2 備份完成"
        except Exception as exc:
            logger.error("R2 backup failed for %s: %s", source_folder.name, exc)
            return f"❌ R2 備份失敗: {exc}"

    async def sync_all(self, source_folder: Path) -> list[str]:
        """Run NAS and R2 backups concurrently in thread pool."""
        results = []
        
        tasks = []
        if self._nas_path:
            tasks.append(asyncio.to_thread(self._sync_to_nas_sync, source_folder))
            
        if self._r2_client:
            tasks.append(asyncio.to_thread(self._sync_to_r2_sync, source_folder))
            
        if not tasks:
            return results
            
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        for res in completed:
            if isinstance(res, Exception):
                logger.error("Backup task raised exception: %s", res)
            elif res:
                results.append(str(res))
                
        return results
