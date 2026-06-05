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
        
        # 1. Close any existing dialogs
        try:
            close_btn = await page.query_selector(".dialog-close")
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
        except: pass
        
        # 2. Find song and click more
        items = await page.query_selector_all(".song-audio-item")
        item = items[0]
        
        trigger = await item.query_selector(".audio-item-more-box")
        if trigger:
            print("Clicking more box")
            await trigger.click(force=True)
            await asyncio.sleep(2)
            
            # Click Download commercial license
            locs = page.get_by_text("權屬證明")
            if await locs.count() > 0:
                print("Clicking license button")
                await locs.first.click(force=True)
                await asyncio.sleep(2)
                
                # Check for dialog
                dialog = await page.query_selector(".download-copyright")
                if dialog:
                    print("License dialog appeared! Filling inputs...")
                    inputs = await dialog.query_selector_all("input")
                    if len(inputs) >= 2:
                        await inputs[0].fill("Mureka User")
                        await inputs[1].fill("user@example.com")
                        
                        btn = await dialog.query_selector(".download-copyright-done-btn button")
                        if btn:
                            print("Clicking download in dialog...")
                            async with page.expect_download(timeout=15000) as dl_info:
                                await btn.click()
                            dl = await dl_info.value
                            path = await dl.path()
                            print(f"Success! Downloaded to {path}")
                        else:
                            print("No download button in dialog")
                else:
                    print("No dialog appeared")
            else:
                print("License menu item not found")

asyncio.run(main())
