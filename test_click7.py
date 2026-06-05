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
        
        # Click away to close any dialog
        await page.mouse.click(0, 0)
        await asyncio.sleep(1)
        
        items = await page.query_selector_all(".song-audio-item")
        if not items:
            print("No songs found")
            return
            
        item = items[0]
        
        selectors = [
            ".audio-item-more-btn-download",
            ".audio-item-more-btn",
            "[class*='more-btn']",
            "[class*='more']",
            "button",
        ]
        trigger = None
        for sel in selectors:
            trigger = await item.query_selector(sel)
            if trigger:
                print(f"Found trigger with selector: {sel}")
                break
        
        if trigger:
            print("Hovering and clicking download menu trigger")
            await trigger.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await trigger.hover()
            await trigger.click()
            
            try:
                await page.wait_for_selector(".el-popper:visible, .el-dropdown-menu:visible", timeout=3000)
                print("✅ Menu opened successfully!")
            except Exception as e:
                print(f"❌ Menu did NOT open: {e}")
                return
            
            # Now find the MP3 option
            labels = ["Download MP3", "下載MP3", "下載 MP3"]
            for label in labels:
                locs = page.get_by_text(label)
                count = await locs.count()
                for i in range(count):
                    loc = locs.nth(i)
                    if await loc.is_visible():
                        html = await loc.evaluate("el => el.outerHTML")
                        print(f"Found visible element for '{label}': {html}")
                        print("Clicking natively...")
                        async with page.expect_download(timeout=10000) as dl_info:
                            await loc.click()
                            dl = await dl_info.value
                            print(f"Download started! {dl.suggested_filename}")
                        return
            
            print("No visible menu item found")
        else:
            print("No trigger found")

asyncio.run(main())
