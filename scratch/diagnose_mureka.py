"""診斷 Mureka 頁面結構：找出所有 tab、按鈕、輸入框的真實 HTML。"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]

        # 找到 mureka 分頁
        page = None
        for pg in context.pages:
            if "mureka" in pg.url.lower():
                page = pg
                break
        if not page:
            print("ERROR: 找不到 Mureka 分頁！")
            return

        print(f"=== 已連接: {page.url} ===\n")

        # 1) 找出頂部的 tabs (Easy / Custom / Soundtrack)
        tabs = await page.evaluate(r"""() => {
            const all = document.querySelectorAll('*');
            const results = [];
            for (const el of all) {
                const txt = (el.innerText || '').trim();
                if (!txt) continue;
                // 只看文字非常短的元素
                if (txt.length > 20) continue;
                const lower = txt.toLowerCase();
                if (lower === 'easy' || lower === 'custom' || lower === 'soundtrack') {
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 2 || rect.height < 2) continue;
                    results.push({
                        tag: el.tagName,
                        text: txt,
                        class: el.className,
                        role: el.getAttribute('role'),
                        id: el.id,
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        childCount: el.children.length,
                        parentTag: el.parentElement ? el.parentElement.tagName : null,
                        parentClass: el.parentElement ? el.parentElement.className : null,
                    });
                }
            }
            return results;
        }""")
        print("=== TABS (Easy/Custom/Soundtrack) ===")
        for t in tabs:
            print(f"  [{t['text']}] tag={t['tag']} class='{t['class']}' role={t['role']} "
                  f"pos=({t['x']},{t['y']}) size={t['w']}x{t['h']} "
                  f"children={t['childCount']} parent={t['parentTag']}.{t['parentClass']}")
        print()

        # 2) 找出所有可見的 input / textarea / contenteditable
        inputs = await page.evaluate(r"""() => {
            const all = document.querySelectorAll('input, textarea, [contenteditable="true"]');
            const results = [];
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                const st = window.getComputedStyle(el);
                if (rect.width < 2 || rect.height < 2) continue;
                if (st.display === 'none' || st.visibility === 'hidden') continue;
                results.push({
                    tag: el.tagName,
                    type: el.getAttribute('type'),
                    placeholder: el.getAttribute('placeholder'),
                    name: el.getAttribute('name'),
                    ariaLabel: el.getAttribute('aria-label'),
                    class: el.className,
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    value: (el.value || el.textContent || '').substring(0, 50),
                });
            }
            return results;
        }""")
        print("=== VISIBLE INPUTS ===")
        for inp in inputs:
            print(f"  {inp['tag']} type={inp['type']} placeholder='{inp['placeholder']}' "
                  f"name='{inp['name']}' aria='{inp['ariaLabel']}' "
                  f"class='{inp['class'][:60]}' pos=({inp['x']},{inp['y']}) "
                  f"size={inp['w']}x{inp['h']} val='{inp['value'][:30]}'")
        print()

        # 3) 找出底部的 Create / Generate 按鈕
        buttons = await page.evaluate(r"""() => {
            const all = document.querySelectorAll('button, [role="button"], .el-button');
            const results = [];
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                if (rect.width < 10 || rect.height < 10) continue;
                const txt = (el.innerText || '').trim();
                if (!txt || txt.length > 40) continue;
                results.push({
                    tag: el.tagName,
                    text: txt,
                    class: el.className,
                    disabled: el.disabled,
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                });
            }
            return results;
        }""")
        print("=== BUTTONS ===")
        for b in buttons:
            print(f"  [{b['text']}] tag={b['tag']} class='{b['class'][:60]}' "
                  f"disabled={b['disabled']} pos=({b['x']},{b['y']}) size={b['w']}x{b['h']}")
        print()

        # 4) 找出 V9/O2 模型選擇元素
        models = await page.evaluate(r"""() => {
            const all = document.querySelectorAll('*');
            const results = [];
            for (const el of all) {
                const txt = (el.innerText || '').trim().toUpperCase();
                if (txt.length > 20) continue;
                if (txt.includes('V9') || txt.includes('O2') || txt.includes('V8')) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 2 || rect.height < 2) continue;
                    results.push({
                        tag: el.tagName,
                        text: (el.innerText || '').trim(),
                        class: el.className,
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        childCount: el.children.length,
                    });
                }
            }
            return results;
        }""")
        print("=== MODEL SELECTORS (V9/O2) ===")
        for m in models:
            print(f"  [{m['text']}] tag={m['tag']} class='{m['class'][:60]}' "
                  f"pos=({m['x']},{m['y']}) size={m['w']}x{m['h']} children={m['childCount']}")

asyncio.run(main())
