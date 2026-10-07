# Den minste motoren – en sang om ATP-syntase

**Tema:** ATP-syntase, den roterende molekylmotoren i mitokondriene som lager nesten all ATP i kroppen.

🎬 **Video:** [`den-minste-motoren.mp4`](den-minste-motoren.mp4) – animasjon med karaoke-lyrikk (ord lyses opp i takt med melodien).

## Tekst

**Vers 1**
Inni hver celle, i mitokondriens hav
ligger en membran, foldet lag på lag
Elektroner vandrer, pumper protoner ut
som vann bak en demning, venter på sin tur

**Refreng**
Snurr, snurr, den minste motoren i deg
Protoner strømmer ned og viser vei
Hver runde rundt gir tre ATP
Hundre ganger i sekundet – kjenn energi!

**Vers 2**
Gjennom F-null-porten siver protoner inn
c-ringen dreier rundt, som et hjul i vind
Gamma-stilken snurrer inni hodet til F-en
Løs, så stram, så åpen – ATP er født igjen

**Refreng**

**Bro**
Hver eneste dag lager du din egen vekt
i ATP, fra motorens jevne takt
Boyer og Walker løste gåten om den
Nobelpris i nittisju – motoren vant!

**Refreng**

## Biologien i sangen
| Linje | Hva skjer |
|---|---|
| Vers 1 | Elektrontransportkjeden (kompleks I, III, IV) i indre mitokondriemembran pumper H⁺ ut i intermembranrommet → en protongradient («vann bak en demning»). |
| Refreng | H⁺ strømmer tilbake gjennom ATP-syntase og driver rotoren. Hver omdreining gir 3 ATP (ADP + Pᵢ → ATP). Enzymet kan nå over 100 omdreininger i sekundet. |
| Vers 2 | F₀ (a-underenhet + c-ring) i membranen; c-ringen roterer; γ-stilken vrir seg inne i F₁-hodet, og de tre β-lommene går gjennom tilstandene løs → tett → åpen (Boyers «binding change»-mekanisme). |
| Bro | Et menneske omsetter omtrent sin egen kroppsvekt i ATP per døgn. Paul D. Boyer og John E. Walker fikk Nobelprisen i kjemi 1997 for å forklare mekanismen. |

## Musikk og video
Alt er generert med kode (ingen eksterne ressurser):
- `song.py` – tekst, akkorder, melodi og timing (100 BPM, A-moll), felles for lyd og bilde.
- `make_music.py` – syntetiserer lydsporet: pad, bass, arpeggio, trommer og en «vokal»-linje laget med additiv syntese formet av vokalformanter (a, e, i, o, u, æ, ø, å) – én tone per stavelse.
- `make_video.py` – tegner animasjonen med Cairo og setter den sammen med ffmpeg.

```bash
pip install numpy scipy pycairo   # + ffmpeg
python3 make_music.py && python3 make_video.py
```

Den syntetiske vokalen synger vokallyder, ikke ord. Vil du ha ekte vokal, kan du lime teksten inn i Suno med denne stilbeskrivelsen:
> upbeat synth-pop, 100 bpm, A minor, Norwegian vocals, pulsing bass, bright arpeggios, catchy chorus
