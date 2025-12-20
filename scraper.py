import json
import asyncio
from playwright.async_api import async_playwright

async def scrape_suno():
    async with async_playwright() as p:
        # 1. Launch a browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 2. Go to your public profile (page=songs ensures we see the list)
        url = "https://suno.com/@biology_tunes?page=songs"
        await page.goto(url, wait_until="networkidle")
        
        # 3. Wait for the song cards to appear
        # Suno uses specific data attributes or classes for song links
        await page.wait_for_selector('a[href*="/song/"]')
        
        # 4. Extract Title and Link
        songs = await page.evaluate('''() => {
            const songLinks = Array.from(document.querySelectorAll('a[href*="/song/"]'));
            return songLinks.map(link => {
                // Try to find the title in the nearest heading or the link text itself
                const title = link.innerText.trim();
                const url = link.href;
                return { title, url };
            }).filter(s => s.title.length > 2); // Filter out short/empty noise
        }''')

        # 5. Clean and Deduplicate
        unique_songs = []
        seen_urls = set()
        for s in songs:
            if s['url'] not in seen_urls:
                unique_songs.append(s)
                seen_urls.add(s['url'])

        # 6. Save as JSON
        with open('songs.json', 'w', encoding='utf-8') as f:
            json.dump(unique_songs, f, indent=4, ensure_ascii=False)
            
        await browser.close()
        print(f"Successfully synced {len(unique_songs)} songs.")

if __name__ == "__main__":
    asyncio.run(scrape_suno())
