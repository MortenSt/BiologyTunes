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
            await page.wait_for_timeout(7000) # Wait for React to finish rendering all cards

            songs = await page.evaluate('''() => {
                const tagMap = {
                    'Genetics': ['gene', 'dna', 'rna', 'chromo', 'crispr', 'genome', 'heredity', 'nucleotide', 'mutation', 'ribozyme', 'code of life'],
                    'Cell Biology': ['cell', 'mitosis', 'organelle', 'membrane', 'nucleus', 'plasma', 'ribosome', 'atp', 'vesicle', 'haploid', 'gamete'],
                    'Evolution': ['evolution', 'selection', 'darwin', 'adaptation', 'species', 'phylogeny', 'ancestor', 'replicator', 'woese', 'domain'],
                    'Biochemistry': ['enzyme', 'protein', 'peptide', 'metabolism', 'catalyst', 'molecule', 'amino', 'photosynthesis'],
                    'Zoology': ['fly', 'beetle', 'ant', 'parrot', 'snake', 'constrictor', 'anglerfish', 'formica']
                };

                // Target the specific container for each song link
                const songLinks = Array.from(document.querySelectorAll('a[href*="/song/"]'));
                
                return songLinks.map(link => {
                    // Navigate up to the actual card container (Suno uses a specific div structure)
                    const card = link.closest('div[class*="gap-2"]') || link.closest('div[style*="grid"]');
                    
                    let caption = "";
                    if (card) {
                        // Get all text in the card and filter out the title to find the caption
                        const allText = Array.from(card.querySelectorAll('p, div, span'))
                                             .map(el => el.innerText.trim())
                                             .filter(t => t.length > 5 && t !== link.innerText);
                        caption = allText.join('\\n');
                    }

                    const searchText = (link.innerText + " " + caption).toLowerCase();
                    let tags = Object.keys(tagMap).filter(tag => 
                        tagMap[tag].some(keyword => searchText.includes(keyword))
                    );
                    
                    if (tags.length === 0) tags = ['Misc'];

                    return {
                        title: link.innerText.trim(),
                        id: link.href.split('/').pop(),
                        caption: caption || "No caption found.",
                        tags: tags
                    };
                }).filter(s => s.title.length > 1);
            }''')
            
            # Deduplicate by ID
            unique_songs = {s['id']: s for s in songs}.values()
            
            with open('songs.json', 'w', encoding='utf-8') as f:
                json.dump(list(unique_songs), f, indent=4, ensure_ascii=False)
            print(f"Success! Processed {len(list(unique_songs))} unique songs.")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_suno())
