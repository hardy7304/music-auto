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
        if not items:
            print("No songs found")
            return
            
        item = items[0]
        # Hover the item to make buttons visible
        await item.hover()
        await asyncio.sleep(1)
        
        trigger = await item.query_selector(".audio-item-more-btn-download")
        if trigger:
            print("Found download button, clicking...")
            await trigger.click(force=True)
            await asyncio.sleep(2)
        else:
            print("No download button found")
            return
            
        # Dump the menu HTML
        menus = await page.query_selector_all(".el-dropdown-menu, [role='menu']")
        for i, menu in enumerate(menus):
            try:
                vis = await menu.is_visible()
                if vis:
                    menu_html = await menu.inner_html()
                    print(f"=== VISIBLE MENU {i} HTML ===")
                    print(menu_html)
            except:
                pass
                
        await page.screenshot(path="debug_after2.png", full_page=True)

asyncio.run(main())
