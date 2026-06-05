import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = None
        for ctx in browser.contexts:
            for p in ctx.pages:
                if "mureka.ai" in p.url:
                    page = p
                    break
        
        if not page:
            print("No mureka page found")
            return
            
        print(f"Connected to {page.url}")
        
        items = await page.query_selector_all(".song-audio-item")
        
        for idx in range(2):
            item = items[idx]
            print(f"\\n--- Song {idx} ---")
            trigger = await item.query_selector(".audio-item-more-box")
            if trigger:
                await trigger.hover()
                await asyncio.sleep(1)
                await trigger.click()
                await asyncio.sleep(1)
                
                # Try finding MP3 with visible=true
                mp3_locs = page.locator("text=下載MP3 >> visible=true")
                count = await mp3_locs.count()
                print(f"Found {count} visible MP3 buttons")
                for i in range(count):
                    loc = mp3_locs.nth(i)
                    print(f"  MP3 {i} HTML: {await loc.evaluate('el => el.outerHTML')}")
                
                # Try finding license
                lic_locs = page.locator("text=下載權屬證明 >> visible=true")
                count = await lic_locs.count()
                print(f"Found {count} visible license buttons")
                for i in range(count):
                    loc = lic_locs.nth(i)
                    print(f"  License {i} HTML: {await loc.evaluate('el => el.outerHTML')}")
                
                # Close menu by clicking elsewhere
                await page.mouse.click(0, 0)
                await asyncio.sleep(1)

asyncio.run(main())
