# Turning Light Into Life – lyric video

Photosynthesis from photon to glucose (Suno song). Track 6 on the album proposal *From Geology to Biology*.

🎬 [`turning-light-into-life.mp4`](turning-light-into-life.mp4)

| Section | Animation |
|---|---|
| Intro | Sunrise, photons streaming onto leaves |
| Verse 1 | Leaf → chloroplast → thylakoid membrane: PSII splits water, electrons flow via b₆f to PSI (NADPH), H⁺ gradient drives ATP synthase |
| Pre-chorus | Light → power → ATP + NADPH |
| Chorus | 6 CO₂ + 6 H₂O + light → C₆H₁₂O₆ + 6 O₂ built term by term over a meadow |
| Verse 2 | Calvin cycle: RuBisCO fixes CO₂; six turns → one glucose |
| Pre-chorus 2 | Night: the "dark" reactions (light-regulated) |
| Bridge | Cyanobacteria, oxygen rising, timeline 3.5 Ga → GOE 2.4 Ga |
| Verse 3 | Earth's carbon uptake, efficiency of photosynthesis, food chains |
| Outro | Sunset over the meadow |

## Files
- `audio.mp3` – the song from Suno
- `lyrics.txt` – lyrics (input to `../tools/align_lyrics.py`)
- `timing.json`, `words.json`, `lyrics.srt` – line and word timings (stable-ts small + demucs; two words fixed by hand)
- `beats.json` – beat times (librosa)
- `make_video.py` – draws the video (reuses drawing code from `../den-minste-motoren/`)
