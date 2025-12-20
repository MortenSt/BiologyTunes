import json
import asyncio
from playwright.async_api import async_playwright

async def scrape_suno():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://suno.com/@biology_tunes?page=songs"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector('a[href*="/song/"]', timeout=30000)
            
            songs = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/song/"]'));
                return links.map(link => ({
                    title: link.innerText.trim(),
                    id: link.href.split('/').pop()
                })).filter(s => s.title.length > 1);
            }''')
            
            unique_songs = {s['id']: s for s in songs}.values()
            with open('songs.json', 'w', encoding='utf-8') as f:
                json.dump(list(unique_songs), f, indent=4, ensure_ascii=False)
            print(f"Synced {len(list(unique_songs))} songs.")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_suno())
