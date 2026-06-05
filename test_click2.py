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
        
        # Method 1: click on the bounding box directly
        trigger = await item.query_selector(".audio-item-more-box")
        if trigger:
            print("Clicking .audio-item-more-box via mouse")
            box = await trigger.bounding_box()
            await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
            await asyncio.sleep(2)
        else:
            print("No more box found")
            
        menus = await page.query_selector_all(".el-dropdown-menu, [role='menu']")
        found = False
        for i, menu in enumerate(menus):
            try:
                vis = await menu.is_visible()
                if vis:
                    print(f"=== VISIBLE MENU {i} HTML ===")
                    print(await menu.inner_html())
                    found = True
            except: pass
            
        if not found:
            print("Menu still not visible. Let's try hovering the trigger.")
            await trigger.hover()
            await asyncio.sleep(2)
            menus = await page.query_selector_all(".el-dropdown-menu, [role='menu']")
            for i, menu in enumerate(menus):
                try:
                    vis = await menu.is_visible()
                    if vis:
                        print(f"=== VISIBLE MENU (ON HOVER) {i} HTML ===")
                        print(await menu.inner_html())
                except: pass

asyncio.run(main())
