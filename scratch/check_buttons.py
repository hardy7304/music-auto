import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        for pg in context.pages:
            if 'mureka.ai' in pg.url:
                page = pg
                break
                
        print(f'Attached to: {page.url}')
        
        # Get all text that might be a button
        elements = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('button, [role=\"button\"], .button, a')).filter(el => {
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            }).map(el => ({
                tag: el.tagName,
                class: el.className,
                text: el.innerText.trim(),
                x: el.getBoundingClientRect().x,
                y: el.getBoundingClientRect().y
            }));
        }''')
        
        print('Visible buttons/links:')
        for el in elements:
            text = el['text']
            if text and len(text) < 30 and el['y'] > 200: # filter out long text and top nav
                print(f"- {el['tag']} class='{el['class']}' text='{text}' y={el['y']}")

asyncio.run(main())
