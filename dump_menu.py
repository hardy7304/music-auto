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
        
        # Save screenshot before clicking
        await page.screenshot(path="debug_before.png", full_page=True)
        
        # Find first song
        items = await page.query_selector_all(".song-audio-item")
        if not items:
            print("No songs found")
            return
            
        item = items[0]
        # Click more button
        trigger = None
        for sel in [".audio-item-more-btn-download", ".audio-item-more-btn", "[class*='more-btn']", "[class*='more-actions']", "[class*='more']", "button[aria-label*='more']"]:
            trigger = await item.query_selector(sel)
            if trigger:
                break
        
        if trigger:
            print("Found trigger:", trigger)
            await trigger.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await trigger.evaluate("el => el.click()")
            await asyncio.sleep(2)
        else:
            print("No more button found")
            
        # Save screenshot after clicking
        await page.screenshot(path="debug_after.png", full_page=True)
        
        # Dump the menu HTML
        menus = await page.query_selector_all(".el-dropdown-menu, [role='menu'], .dropdown, [class*='menu']")
        for i, menu in enumerate(menus):
            try:
                vis = await menu.is_visible()
                if vis:
                    menu_html = await menu.inner_html()
                    print(f"=== VISIBLE MENU {i} HTML ===")
                    print(menu_html)
            except:
                pass

asyncio.run(main())
