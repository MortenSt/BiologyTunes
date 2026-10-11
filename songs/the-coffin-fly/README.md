# The Coffin Fly: The Navigator of the Grave – lyric video

Conicera tibialis (Phoridae), the scuttle fly that finds buried remains up to a metre or more below ground and breeds there for generations.

🎬 [`the-coffin-fly.mp4`](the-coffin-fly.mp4)

| Section | Animation |
|---|---|
| Intro | Graveyard at dusk; title |
| Verse 1 | The hump-backed fly scuttles in jerky hops; descends into the soil |
| Chorus | Turquoise scent plume rising from a closed coffin; depth gauge; eggs |
| Verse 2 | Dimethyl trisulfide (DMTS) molecule; fly digs down; depth and O₂ gauges |
| Bridge | Badger burrow and fox den; timeline: burrows long before human burials |
| Outro | The life cycle circling the coffin; title |

The coffin stays closed (non-graphic).

## Stem-driven animation
`stem_features.json` (from `../tools/stem_features.py`) holds onsets and loudness for each Suno stem:
- **Guitar** onsets: the fly moves in hops
- **Drums/Percussion** hits: soil crumbs fall
- **Bass** loudness: the scent plume pulses
- **Strings/Backing Vocals** loudness: glow

## YouTube
- `thumbnail.png` (from `make_thumbnail.py`), `youtube-description.md`

## Files
- `audio.mp3` – the song from Suno
- `lyrics.txt` – lyrics (input to `../tools/align_lyrics.py`)
- `timing_raw.json`, `words_raw.json` – stable-ts output from the vocal stem
- `timing.json`, `words.json` – timings after fixes (late first words, held line endings)
- `stem_features.json` – onsets and loudness for each stem
- `make_video.py` – draws the video (`python make_video.py 62` writes a preview frame)
