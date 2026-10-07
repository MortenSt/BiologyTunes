# The Order We Were Built – lyric video

Celleånding fortalt i den rekkefølgen den oppsto, sunget av ATP-syntase (Suno-sang).

🎬 [`the-order-we-were-built.mp4`](the-order-we-were-built.mp4)

| Del | Animasjon |
|---|---|
| Intro | Alkaliske hydrotermale skorsteiner på havbunnen |
| Vers 1 – The Vent | Mineralvegg med alkalisk væske mot surt hav; ATP-syntase som turbin |
| Refreng | Jordlag: protongradient → glykolyse → Krebs-hjulet → ånding (O₂) |
| Vers 2 | Glukose (6 C) → 2 pyruvat (3 C), netto 2 ATP, uten oksygen |
| Vers 3 | Krebs-syklusen baklengs (binder CO₂) og deretter forlengs (brenner) |
| Bro | Den store oksygeneringen, elektrontransportkjeden (~2 vs ~30 ATP), endosymbiose |
| Outro | ATP-syntase som fortsatt snurrer |

## Filer
- `audio.mp3` – sangen fra Suno
- `lyrics_order.py` – tekst og faktabokser
- `timing.json` – start/slutt for hver tekstlinje (fra Gemini); juster her og kjør på nytt
- `beats.json` – taktslag (librosa), brukes til pulserende lys
- `make_video.py` – tegner videoen (gjenbruker tegnefunksjoner fra `../den-minste-motoren/`)

```bash
pip install numpy pycairo   # + ffmpeg
python3 make_video.py
```
