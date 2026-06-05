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
        
        # Check for dialogs
        dialogs = await page.query_selector_all(".dialog-container, .el-dialog, [role='dialog'], .custom-dialog")
        for i, d in enumerate(dialogs):
            try:
                vis = await d.is_visible()
                if vis:
                    print(f"Found visible dialog {i}")
                    print(await d.inner_html())
                    
                    # Try to close it
                    close_btn = await d.query_selector(".close-btn, .el-dialog__close, button[aria-label='Close'], .dialog-close, [class*='close']")
                    if close_btn:
                        print("Clicking close button")
                        await close_btn.click()
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"Error checking dialog {i}: {e}")

asyncio.run(main())
