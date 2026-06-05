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
            
        items = await page.query_selector_all(".song-audio-item")
        if not items:
            print("No songs found")
            return
            
        html = await items[0].evaluate("el => el.innerHTML")
        with open("song_html.txt", "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote song HTML to song_html.txt")

asyncio.run(main())
