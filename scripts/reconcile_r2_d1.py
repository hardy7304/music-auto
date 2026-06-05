"""
R2 <-> D1 Reconciliation & Auto-Healing Script.
Checks consistency between local downloads, Cloudflare D1 Database, and Cloudflare R2 Bucket.
Can run in check-only mode or auto-heal mode to re-sync missing records/files.

Usage:
    python scripts/reconcile_r2_d1.py [--heal]
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import load_settings
from app.services.d1_manager import D1Manager
from app.services.storage_manager import StorageManager

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

async def reconcile(heal: bool = False):
    settings = load_settings()
    d1 = D1Manager(settings)
    sm = StorageManager(settings)
    
    if not d1.enabled:
        print("[-] D1 is not enabled. Please check env settings.")
        return
        
    if not sm._r2_client:
        print("[-] R2 client is not configured. Please check env settings.")
        return
        
    print("==================================================")
    print(f"🔍 Starting reconciliation (heal_mode={heal})")
    print("==================================================")
    
    # 1. Get D1 records
    print("[+] Fetching records from D1 Database...")
    d1_songs = await d1.get_recent_songs(limit=1000)
    d1_by_id = {s["song_id"]: s for s in d1_songs}
    d1_by_folder = {s["folder_name"]: s for s in d1_songs if s.get("folder_name")}
    print(f"    Found {len(d1_songs)} records in D1.")

    # 2. Get R2 objects
    print("[+] Listing objects in Cloudflare R2...")
    r2_folders = set()
    r2_mp3s = set() # s3 key -> size
    try:
        paginator = sm._r2_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=settings.r2_bucket_name)
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if '/' in key:
                        parts = key.split('/')
                        # YYYY-MM/Author/Folder_Name/filename
                        if len(parts) >= 3:
                            folder_name = parts[2]
                            r2_folders.add(folder_name)
                    if key.endswith('.mp3'):
                        r2_mp3s.add(key)
        print(f"    Found {len(r2_folders)} unique song folders in R2.")
    except Exception as e:
        print(f"[-] Failed to list R2 objects: {e}")
        return

    # 3. Get Local Folders
    download_dir = Path(settings.download_dir)
    print(f"[+] Scanning local downloads directory ({download_dir})...")
    local_folders = []
    if download_dir.exists():
        for item in download_dir.iterdir():
            if item.is_dir() and "_" in item.name:
                local_folders.append(item)
    print(f"    Found {len(local_folders)} folders locally.")

    # 4. Compare and reconcile
    print("\n================== Analysis ==================")
    
    # Check A: Local folders missing from D1
    missing_in_d1 = []
    for f in local_folders:
        if f.name not in d1_by_folder:
            missing_in_d1.append(f)
            
    print(f"❓ Local folders missing in D1 database: {len(missing_in_d1)}")
    for f in missing_in_d1[:5]:
        print(f"   - {f.name}")
    if len(missing_in_d1) > 5:
        print(f"   ... and {len(missing_in_d1) - 5} more")

    # Check B: Local folders missing from R2
    missing_in_r2 = []
    for f in local_folders:
        if f.name not in r2_folders:
            missing_in_r2.append(f)
            
    print(f"❓ Local folders missing in R2 Bucket: {len(missing_in_r2)}")
    for f in missing_in_r2[:5]:
        print(f"   - {f.name}")
    if len(missing_in_r2) > 5:
        print(f"   ... and {len(missing_in_r2) - 5} more")

    # Check C: D1 records without corresponding R2 objects
    d1_missing_r2 = []
    for song_id, song in d1_by_id.items():
        folder = song.get("folder_name")
        if folder and folder not in r2_folders:
            d1_missing_r2.append(song)
            
    print(f"❓ D1 records referencing missing R2 objects: {len(d1_missing_r2)}")
    for s in d1_missing_r2[:5]:
        print(f"   - {s['title']} ({s['song_id']})")
    if len(d1_missing_r2) > 5:
        print(f"   ... and {len(d1_missing_r2) - 5} more")

    print("==============================================")

    # 5. Healing Process
    if heal:
        print("\n🛠️ Starting Healing Process...")
        
        # Heal A: Upsert missing local folders to D1
        if missing_in_d1:
            print(f"[+] Re-importing {len(missing_in_d1)} folders into D1...")
            for folder in missing_in_d1:
                folder_name = folder.name
                parts = folder_name.split("_")
                song_id = parts[-1] if len(parts) >= 4 else folder_name
                author = parts[1] if len(parts) >= 2 else "Unknown"
                title = parts[2] if len(parts) >= 3 else folder_name
                
                # Check for cover image in local folder
                cover_url = ""
                metadata_file = folder / "metadata.json"
                if metadata_file.exists():
                    try:
                        meta = json.loads(metadata_file.read_text(encoding="utf-8"))
                        cover_url = meta.get("cover_url", "")
                    except Exception:
                        pass
                
                category_path = sm._get_category_path(folder_name)
                print(f"   -> Importing {title} ({song_id})")
                await d1.upsert_song(
                    song_id=song_id,
                    title=title,
                    author=author,
                    folder_name=folder_name,
                    r2_category_path=category_path,
                    cover_url=cover_url
                )

        # Heal B: Upload missing local folders to R2
        if missing_r2_folders := set(f.name for f in missing_in_r2) | set(s["folder_name"] for s in d1_missing_r2 if s.get("folder_name")):
            print(f"[+] Uploading {len(missing_r2_folders)} missing folders to R2...")
            for folder_name in missing_r2_folders:
                local_path = download_dir / folder_name
                if local_path.exists():
                    print(f"   -> Uploading {folder_name} to R2...")
                    msgs = await sm.sync_all(local_path)
                    for msg in msgs:
                        print(f"      {msg}")
                else:
                    print(f"   [!] Local path {local_path} does not exist. Cannot heal R2.")
        
        print("\n✨ Healing completed! Please run the script again without --heal to verify.")
    else:
        print("\n💡 Run with '--heal' parameter to automatically synchronize and fix these issues.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile local, D1, and R2 assets.")
    parser.add_argument("--heal", action="store_true", help="Fix missing files and DB records")
    args = parser.parse_args()
    
    asyncio.run(reconcile(args.heal))
