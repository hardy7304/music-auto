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
        item = items[0]
        
        # Click the more box to open menu
        trigger = await item.query_selector(".audio-item-more-box")
        if trigger:
            print("Clicking .audio-item-more-box")
            await trigger.click(force=True)
            await asyncio.sleep(2)
            
            # Now find the download text
            locs = page.get_by_text("下載MP3")
            count = await locs.count()
            print(f"Found {count} elements with text '下載MP3'")
            for i in range(count):
                loc = locs.nth(i)
                vis = await loc.is_visible()
                print(f"Element {i} is_visible: {vis}")
                if vis:
                    print(f"Clicking element {i}")
                    # Don't actually download, just see if it's found
                    pass
        else:
            print("No trigger found")

asyncio.run(main())
