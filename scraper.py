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
            # Change: We use "domcontentloaded" instead of "networkidle" (much faster)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            print("Waiting for song elements to appear...")
            # Specifically wait for the link pattern Suno uses for tracks
            selector = 'a[href*="/song/"]'
            await page.wait_for_selector(selector, timeout=30000)
            
            # Give it a tiny bit of extra time to finish rendering text
            await page.wait_for_timeout(3000)

            songs = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/song/"]'));
                return links.map(link => ({
                    title: link.innerText.trim(),
                    url: link.href
                })).filter(s => s.title.length > 1);
            }''')
            
            if songs:
                # Deduplicate
                unique_songs = {s['url']: s for s in songs}.values()
                song_list = list(unique_songs)
                
                with open('songs.json', 'w', encoding='utf-8') as f:
                    json.dump(song_list, f, indent=4, ensure_ascii=False)
                print(f"Success! Found {len(song_list)} songs.")
            else:
                print("No songs found. Creating an empty list to prevent Git error.")
                with open('songs.json', 'w') as f:
                    json.dump([], f)

        except Exception as e:
            print(f"Scraper encountered an error: {e}")
            # Ensure file exists so the workflow doesn't crash on 'git add'
            with open('songs.json', 'w') as f:
                json.dump([], f)
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_suno())
