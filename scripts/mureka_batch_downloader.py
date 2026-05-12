import os
import asyncio
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright

# 設定
TARGET_URL = "https://mureka.ai/create"
DOWNLOAD_DIR = os.path.abspath("downloads")
HISTORY_FILE = os.path.abspath("download_history.txt")
CDP_URL = "http://127.0.0.1:9222"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def get_downloaded_ids():
    """讀取下載歷史紀錄"""
    if not os.path.exists(HISTORY_FILE): return set()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_downloaded_id(song_id):
    """保存成功的 ID"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{song_id}\n")

async def human_delay(min_sec=3, max_sec=6):
    """模擬真人隨機等待"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def download_mureka_mp3s():
    downloaded_ids = get_downloaded_ids()
    
    async with async_playwright() as p:
        print(f"正在接管現有 Chrome...")
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            print("✅ 接管成功")
        except Exception:
            print("ℹ️ 無法連接到 Chrome，請確保已執行 start_chrome_debug.bat")
            return

        # 智能搜尋正確的 Mureka 頁面
        target_page = None
        for context in browser.contexts:
            for p_obj in context.pages:
                if "mureka.ai" in p_obj.url:
                    target_page = p_obj
                    break
        
        if not target_page:
            print("⚠️ 找不到 Mureka 分頁，請開啟 mureka.ai/create")
            await browser.close()
            return

        print(f"✅ 已鎖定分頁: {await target_page.title()}")
        print("\n=== 智能下載 (導航守衛 + JS 隔離點擊) ===")
        print(f"1. 已知歷史紀錄: {len(downloaded_ids)} 筆。")
        input("準備好後請按 Enter 開始...")

        count_new = 0
        consecutive_idle_rounds = 0

        while consecutive_idle_rounds < 15:
            # 1. 導航守衛：如果跑進了詳情頁，自動返回
            current_url = target_page.url
            if "song-detail" in current_url or "from=mine" in current_url:
                if "create" not in current_url:
                    print("⚠️ 偵測到進入詳情頁，正在嘗試返回清單...")
                    await target_page.go_back()
                    await asyncio.sleep(3)
                    continue

            # 2. 獲取目前所有歌曲項目
            items = await target_page.query_selector_all(".song-audio-item")
            found_any_new_in_this_round = False
            processed_in_round = set() # 防止同一輪迴圈重複處理

            for item in items:
                try:
                    # 擷取 ID (從 innerHTML 擷取 skm 圖片 ID)
                    html = await item.inner_html()
                    match = re.search(r'skm/image/[0-9]+/([^.?]+)', html)
                    song_id = match.group(1) if match else None

                    if not song_id or song_id in downloaded_ids or song_id in processed_in_round:
                        continue

                    processed_in_round.add(song_id)

                    # 抓取標題
                    title_el = await item.query_selector(".audio-item-title")
                    title = (await title_el.inner_text()).strip() if title_el else "Unknown"
                    
                    found_any_new_in_this_round = True
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
                    final_filename = f"{safe_title}_{timestamp}.mp3"
                    
                    print(f"--- 處理中: {final_filename} ---")
                    
                    # 3. 隔離點擊：使用 evaluate 直接點擊按鈕，不觸發外層 A 連結
                    trigger = await item.query_selector(".audio-item-more-btn-download") or \
                              await item.query_selector(".audio-item-more-btn")
                    
                    if trigger:
                        await trigger.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        
                        # 重要：使用 JS 點擊避開父級連結
                        await trigger.evaluate("el => el.click()")
                        
                        # 4. 等待並點擊選單中的 Download MP3
                        await asyncio.sleep(2)
                        js_click_script = """
                        (text) => {
                            const items = Array.from(document.querySelectorAll('*'));
                            const target = items.find(el => el.innerText && el.innerText.trim() === text);
                            if (target) { target.click(); return true; }
                            const fallback = items.find(el => el.innerText && el.innerText.includes(text));
                            if (fallback) { fallback.click(); return true; }
                            return false;
                        }
                        """
                        
                        try:
                            async with target_page.expect_download(timeout=20000) as download_info:
                                success = await target_page.evaluate(js_click_script, "Download MP3")
                                if not success: raise Exception("找不到下載按鈕文字")
                            
                            download = await download_info.value
                            save_path = os.path.join(DOWNLOAD_DIR, final_filename)
                            await download.save_as(save_path)
                            
                            save_downloaded_id(song_id)
                            downloaded_ids.add(song_id)
                            print(f"  -> ✅ 下載成功")
                            count_new += 1
                            await human_delay()
                        except Exception as e:
                            print(f"  ❌ 下載執行失敗: {e}")
                            await target_page.mouse.click(0, 0)
                except Exception:
                    continue

            # 5. 暴力捲動與等待
            print("正在捲動尋找更多作品...")
            await target_page.mouse.move(1200, 400)
            await target_page.mouse.wheel(0, 1000) 
            await asyncio.sleep(4) 
            
            if not found_any_new_in_this_round:
                consecutive_idle_rounds += 1
            else:
                consecutive_idle_rounds = 0

        print(f"\n🎉 批量下載結束！本次共下載 {count_new} 首新歌。")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(download_mureka_mp3s())
