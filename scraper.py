import json
import asyncio
from playwright.async_api import async_playwright

async def scrape_suno():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url = "https://suno.com/@biology_tunes?page=songs"
        print(f"Navigating to {url}...")
        
        try:
            # Increase timeout to 90 seconds for slow loads
            await page.goto(url, wait_until="networkidle", timeout=90000)
            
            print("Waiting for song list to render...")
            # Suno often uses a delay before showing public tracks
            await page.wait_for_timeout(10000) 
            
            # Target the song links
            selector = 'a[href*="/song/"]'
            await page.wait_for_selector(selector, timeout=30000)
            
            songs = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/song/"]'));
                return links.map(link => ({
                    title: link.innerText.trim(),
                    url: link.href
                })).filter(s => s.title.length > 1);
            }''')
            
            if not songs:
                print("Warning: Page loaded but no songs were found in the HTML.")
                return

            # Deduplicate
            unique_songs = {s['url']: s for s in songs}.values()
            song_list = list(unique_songs)
            
            with open('songs.json', 'w', encoding='utf-8') as f:
                json.dump(song_list, f, indent=4, ensure_ascii=False)
            
            print(f"Success! Saved {len(song_list)} songs.")

        except Exception as e:
            print(f"Error during scraping: {e}")
            # We exit with 0 so the workflow doesn't 'fail' if Suno is just down
            # but you can check logs to see why songs.json didn't update.
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_suno())
