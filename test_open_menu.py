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
                print("Found dialog, clicking close")
                await close_btn.click()
                await asyncio.sleep(1)
        except: pass
        
        await page.mouse.click(0, 0)
        await asyncio.sleep(1)
        
        items = await page.query_selector_all(".song-audio-item")
        item = items[0]
        
        selectors = [
            ".audio-item-more-box",
            ".audio-item-more-btn-download",
        ]
        trigger = None
        for sel in selectors:
            trigger = await item.query_selector(sel)
            if trigger:
                break
                
        if trigger:
            print("Found trigger, scrolling and clicking")
            await trigger.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await trigger.click(force=True)
            await asyncio.sleep(3)
            
            # evaluate visible items
            js_eval = """
            () => {
                const items = Array.from(document.querySelectorAll('*')).filter(el => {
                    return el.offsetWidth > 0 && el.offsetHeight > 0;
                });
                return items.map(el => (el.innerText || el.textContent || '').trim()).filter(t => t.includes('MP3') || t.includes('權屬證明'));
            }
            """
            result = await page.evaluate(js_eval)
            print(f"Visible menu items: {result}")
        else:
            print("No trigger found")

asyncio.run(main())
