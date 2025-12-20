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
            await page.wait_for_timeout(5000)

            songs = await page.evaluate('''() => {
                const songLinks = Array.from(document.querySelectorAll('a[href*="/song/"]'));
                
                const tagMap = {
                    'Genetics': ['gene', 'dna', 'rna', 'chromosome', 'crispr', 'genome', 'heredity'],
                    'Cell Biology': ['cell', 'mitosis', 'organelle', 'membrane', 'nucleus', 'cytoplasm'],
                    'Evolution': ['evolution', 'selection', 'darwin', 'adaptation', 'species', 'phylogeny'],
                    'Biochemistry': ['enzyme', 'protein', 'atp', 'metabolism', 'catalyst', 'molecule'],
                    'Microbiology': ['bacteria', 'virus', 'microbe', 'phage', 'fungi', 'pathogen']
                };

                return songLinks.map(link => {
                    const container = link.closest('div[class*="gap-"]') || link.parentElement.parentElement;
                    const metaElements = container.querySelectorAll('p, div');
                    let caption = "";
                    
                    for (let el of metaElements) {
                        if (el.innerText !== link.innerText && el.innerText.length > 5) {
                            caption = el.innerText.trim();
                            break;
                        }
                    }

                    const searchText = (link.innerText + " " + caption).toLowerCase();
                    let tags = Object.keys(tagMap).filter(tag => 
                        tagMap[tag].some(keyword => searchText.includes(keyword))
                    );
                    
                    // If no biology keywords found, tag as Oddity
                    if (tags.length === 0) tags = ['Misc'];

                    return {
                        title: link.innerText.trim(),
                        id: link.href.split('/').pop(),
                        caption: caption,
                        tags: tags
                    };
                }).filter(s => s.title.length > 1);
            }''')
            
            unique_songs = {s['id']: s for s in songs}.values()
            with open('songs.json', 'w', encoding='utf-8') as f:
                json.dump(list(unique_songs), f, indent=4, ensure_ascii=False)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_suno())
