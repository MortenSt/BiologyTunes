import json
import asyncio
from playwright.async_api import async_playwright

async def scrape_suno():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        url = "https://suno.com/@biology_tunes?page=songs"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector('a[href*="/song/"]', timeout=30000)
            await page.wait_for_timeout(5000) # Wait for images to load

            songs = await page.evaluate('''() => {
                // Find all song containers (Suno usually groups these in divs)
                const songLinks = Array.from(document.querySelectorAll('a[href*="/song/"]'));
                
                return songLinks.map(link => {
                    // Try to find the container that holds the image and text
                    const container = link.closest('div[class*="gap-"]') || link.parentElement;
                    const img = container ? container.querySelector('img') : null;
                    
                    // The song ID is needed for the embedded player
                    const songId = link.href.split('/').pop();
                    
                    return {
                        title: link.innerText.trim(),
                        url: link.href,
                        id: songId,
                        image: img ? img.src : 'https://suno.com/icons/suno-logo.png'
                    };
                }).filter(s => s.title.length > 1);
            }''')
            
            unique_songs = {s['url']: s for s in songs}.values()
            with open('songs.json', 'w', encoding='utf-8') as f:
                json.dump(list(unique_songs), f, indent=4, ensure_ascii=False)
            print(f"Synced {len(list(unique_songs))} songs with images.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_suno())
