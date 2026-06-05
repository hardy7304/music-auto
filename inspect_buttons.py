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
        # Query all buttons or clickable elements in the song item
        clickable = await item.query_selector_all("button, [role='button'], a, [class*='btn'], [class*='icon']")
        for i, el in enumerate(clickable):
            try:
                html = await el.outer_html()
                cls = await el.get_attribute("class")
                text = await el.inner_text()
                print(f"[{i}] class={cls} text='{text}' HTML={html[:200]}")
            except Exception as e:
                pass

asyncio.run(main())
