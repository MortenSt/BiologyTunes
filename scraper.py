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
            # Give the dynamic content a moment to settle
            await page.wait_for_timeout(5000)

            songs = await page.evaluate('''() => {
                const songLinks = Array.from(document.querySelectorAll('a[href*="/song/"]'));
                
                return songLinks.map(link => {
                    // Navigate to the card container to find the caption
                    const container = link.closest('div[class*="gap-"]') || link.parentElement.parentElement;
                    
                    // Suno captions often appear in elements with specific style/opacity classes
                    // We grab the text and clean up any 'newlines'
                    const metaElements = container.querySelectorAll('p, div');
                    let caption = "";
                    
                    for (let el of metaElements) {
                        // We avoid the title itself and look for the descriptive text
                        if (el.innerText !== link.innerText && el.innerText.length > 5) {
                            caption = el.innerText.trim();
                            break;
                        }
                    }

                    return {
                        title: link.innerText.trim(),
                        id: link.href.split('/').pop(),
                        caption: caption
                    };
                }).filter(s => s.title.length > 1);
            }''')
            
            unique_songs = {s['id']: s for s in songs}.values()
            with open('songs.json', 'w', encoding='utf-8') as f:
                json.dump(list(unique_songs), f, indent=4, ensure_ascii=False)
            print(f"Synced {len(list(unique_songs))} songs with captions.")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_suno())
