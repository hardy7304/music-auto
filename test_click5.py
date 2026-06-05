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
        
        try:
            close_btn = await page.query_selector(".dialog-close")
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
        except: pass
        
        await page.mouse.click(0, 0)
        await asyncio.sleep(1)
        
        items = await page.query_selector_all(".song-audio-item")
        item = items[0]
        
        trigger = await item.query_selector(".audio-item-more-btn-download")
        if trigger:
            print("Clicking .audio-item-more-btn-download WITHOUT force=True")
            await trigger.scroll_into_view_if_needed()
            await trigger.click()
            await asyncio.sleep(2)
            
            menus = await page.query_selector_all(".el-dropdown-menu, [role='menu']")
            for i, menu in enumerate(menus):
                try:
                    if await menu.is_visible():
                        print(f"=== MENU {i} VISIBLE ===")
                except: pass
        else:
            print("No trigger found")

asyncio.run(main())
