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
        
        items = await page.query_selector_all(".song-audio-item")
        item = items[0]
        
        trigger = await item.query_selector(".audio-item-more-box")
        if trigger:
            print("Hovering .audio-item-more-box")
            await trigger.hover()
            await asyncio.sleep(2)
            
            menus = await page.query_selector_all(".el-dropdown-menu, [role='menu']")
            found = False
            for i, menu in enumerate(menus):
                try:
                    if await menu.is_visible():
                        text = await menu.inner_text()
                        print(f"=== MENU {i} TEXT ===")
                        print(text)
                        found = True
                except: pass
            
            if not found:
                print("Menu not visible after hover. Trying click...")
                await trigger.click()
                await asyncio.sleep(2)
                menus = await page.query_selector_all(".el-dropdown-menu, [role='menu']")
                for i, menu in enumerate(menus):
                    try:
                        if await menu.is_visible():
                            text = await menu.inner_text()
                            print(f"=== MENU {i} TEXT (AFTER CLICK) ===")
                            print(text)
                            found = True
                    except: pass
        else:
            print("No trigger found")

asyncio.run(main())
