"""直接用 CDP WebSocket 測試 Mureka 表單填寫。"""
import asyncio
import requests
from playwright.async_api import async_playwright

async def main():
    # 1) 先用 HTTP 找到 mureka 分頁的 WebSocket URL
    tabs = requests.get("http://127.0.0.1:9222/json/list").json()
    mureka_tab = None
    for t in tabs:
        if t.get("type") == "page" and "mureka" in t.get("url", "").lower():
            mureka_tab = t
            break

    if not mureka_tab:
        print("ERROR: No mureka tab found via CDP!")
        return

    ws_url = mureka_tab.get("webSocketDebuggerUrl")
    print(f"[OK] Found Mureka tab: {mureka_tab['url']}")
    print(f"     WebSocket: {ws_url}")

    async with async_playwright() as p:
        # 連接到整個瀏覽器（不是單頁）
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")

        # 嘗試找頁面：遍歷所有 context
        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                u = pg.url or ""
                if "mureka" in u.lower():
                    page = pg
                    break
            if page:
                break

        # 如果找不到，可能需要重新導向一個現有頁面到 mureka
        if not page:
            print("Playwright can't see the mureka page directly.")
            print("Trying to navigate an existing page to mureka.ai/create...")
            if browser.contexts and browser.contexts[0].pages:
                # 找一個不重要的頁面來用
                for pg in browser.contexts[0].pages:
                    u = pg.url or ""
                    if "json/list" in u or u == "" or "about:blank" in u:
                        page = pg
                        break
                if not page:
                    page = browser.contexts[0].pages[0]
                
                print(f"  Navigating page (was: {page.url[:50]}) to mureka...")
                await page.goto("https://www.mureka.ai/create", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(3)
                print(f"  Now at: {page.url}")

        if not page or "mureka" not in page.url.lower():
            print("FATAL: Could not get a Mureka page. Please open mureka.ai/create manually.")
            return

        await page.bring_to_front()
        await asyncio.sleep(1)

        # === 開始測試填寫 ===
        print(f"\n=== Testing on: {page.url} ===")

        # Check active tab
        active_tab = await page.evaluate("""() => {
            const el = document.querySelector('.create-mode-tab-switch-item--active');
            return el ? el.innerText.trim() : 'NONE';
        }""")
        print(f"[1] Active tab: '{active_tab}'")

        # Click Custom
        if "Custom" not in active_tab:
            print("[2] Switching to Custom...")
            loc = page.locator('.create-mode-tab-switch-item:has-text("Custom")').first
            if await loc.count() > 0:
                await loc.click()
                await asyncio.sleep(1.5)
                new_tab = await page.evaluate("""() => {
                    const el = document.querySelector('.create-mode-tab-switch-item--active');
                    return el ? el.innerText.trim() : 'NONE';
                }""")
                print(f"    Now active: '{new_tab}'")
        else:
            print("[2] Already on Custom")

        # List fields
        fields = await page.evaluate("""() => {
            const els = document.querySelectorAll('input, textarea');
            return Array.from(els).map(el => {
                const r = el.getBoundingClientRect();
                return {
                    tag: el.tagName,
                    ph: el.placeholder || '',
                    y: Math.round(r.y),
                    w: Math.round(r.width),
                    h: Math.round(r.height),
                    vis: r.width > 2 && r.height > 2,
                };
            }).filter(f => f.vis);
        }""")
        print(f"[3] Visible fields ({len(fields)}):")
        for f in fields:
            print(f"    {f['tag']} ph='{f['ph'][:50]}' y={f['y']} {f['w']}x{f['h']}")

        # Fill lyrics
        print("[4] Fill lyrics...")
        ta_lyrics = page.locator('textarea[placeholder*="lyrics" i]').first
        if await ta_lyrics.count() > 0:
            await ta_lyrics.click()
            await ta_lyrics.fill("[Verse 1]\nTest lyrics")
            print("    OK")
        else:
            print("    SKIP - no lyrics textarea")

        # Fill style
        print("[5] Fill style...")
        ta_style = page.locator('textarea[placeholder*="style" i]').first
        if await ta_style.count() > 0:
            await ta_style.click()
            await ta_style.fill("Pop, Piano, Male Vocal, Energetic")
            print("    OK")
        else:
            print("    SKIP - no style textarea")

        # Fill title (CRITICAL)
        print("[6] Fill title...")
        inp_title = page.locator('input[placeholder="Song title"]').first
        tc = await inp_title.count()
        print(f"    Exact 'Song title' match: {tc}")
        if tc > 0:
            await inp_title.click()
            await inp_title.fill("TEST SONG 12345")
            print("    OK via exact match")
        else:
            # JS fallback
            ok = await page.evaluate("""() => {
                const inputs = Array.from(document.querySelectorAll('input'));
                for (const el of inputs) {
                    const r = el.getBoundingClientRect();
                    const ph = (el.placeholder || '').toLowerCase();
                    if (r.y > 100 && r.width > 50 && (ph.includes('title') || ph.includes('song'))) {
                        el.focus();
                        const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                        if (desc && desc.set) desc.set.call(el, 'TEST SONG 12345');
                        else el.value = 'TEST SONG 12345';
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return { ok: true, ph: el.placeholder, y: Math.round(r.y) };
                    }
                }
                return { ok: false };
            }""")
            print(f"    JS fallback: {ok}")

        await asyncio.sleep(1)

        # Button state
        print("[7] Button state:")
        btn = await page.evaluate("""() => {
            const b = document.querySelector('button.el-button');
            if (!b) return null;
            return {
                text: b.innerText.trim(),
                disabled: b.disabled,
                cls: b.className,
            };
        }""")
        print(f"    {btn}")

        # Screenshot
        await page.screenshot(path="scratch/test_fill_result.png")
        print("\n[Screenshot saved] scratch/test_fill_result.png")

asyncio.run(main())
