import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        # Find the active mureka page
        mureka_page = None
        for page in context.pages:
            if 'mureka' in page.url:
                mureka_page = page
                break
        if mureka_page:
            await mureka_page.screenshot(path='screenshots/debug_hang.png', full_page=True)
            print("Screenshot saved to screenshots/debug_hang.png")
        else:
            print("No Mureka page found")

asyncio.run(run())
