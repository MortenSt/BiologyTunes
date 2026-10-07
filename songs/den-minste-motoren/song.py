"""Felles sangdata for «Den minste motoren» – brukes av både musikk- og videogeneratoren."""
import re

BPM = 100
BEAT = 60.0 / BPM          # 0.6 s
BAR = 4 * BEAT             # 2.4 s
EIGHTH = BEAT / 2

# A-moll naturlig, trinn 0 = A3 (MIDI 57)
SCALE = [0, 2, 3, 5, 7, 8, 10]
CHORDS = {
    "Am": (57, 60, 64), "F": (53, 57, 60), "C": (48, 52, 55), "G": (55, 59, 62),
    "Dm": (50, 53, 57), "E": (52, 56, 59),
}

# (navn, visningsnavn, akkorder per takt, tekstlinjer, melodikonturer A/B)
SECTIONS = [
    ("intro", "Intro", ["Am", "F", "C", "G"], [], None),
    ("verse1", "Vers 1", ["Am", "F", "C", "G"] * 2, [
        "Inni hver celle, i mitokondriens hav",
        "ligger en membran, foldet lag på lag",
        "Elektroner vandrer, pumper protoner ut",
        "som vann bak en demning, venter på sin tur",
    ], ([2, 2, 4, 4, 5, 4, 2, 0], [4, 5, 7, 7, 5, 4, 3, 4])),
    ("chorus", "Refreng", ["C", "G", "Am", "F"] * 2, [
        "Snurr, snurr, den minste motoren i deg",
        "Protoner strømmer ned og viser vei",
        "Hver runde rundt gir tre ATP",
        "Hundre ganger i sekundet – kjenn energi!",
    ], ([9, 9, 8, 7, 8, 9, 7, 7], [7, 7, 9, 10, 9, 8, 7, 6])),
    ("verse2", "Vers 2", ["Am", "F", "C", "G"] * 2, [
        "Gjennom F-null-porten siver protoner inn",
        "c-ringen dreier rundt, som et hjul i vind",
        "Gamma-stilken snurrer inni hodet til F-en",
        "Løs, så stram, så åpen – ATP er født igjen",
    ], ([2, 2, 4, 4, 5, 4, 2, 0], [4, 5, 7, 7, 5, 4, 3, 4])),
    ("chorus", "Refreng", ["C", "G", "Am", "F"] * 2, None, None),
    ("bridge", "Bro", ["F", "C", "Dm", "E"] * 2, [
        "Hver eneste dag lager du din egen vekt",
        "i ATP, fra motorens jevne takt",
        "Boyer og Walker løste gåten om den",
        "Nobelpris i nittisju – motoren vant!",
    ], ([3, 4, 5, 7, 7, 5, 4, 3], [5, 5, 7, 9, 8, 7, 6, 6])),
    ("chorus2", "Refreng", ["C", "G", "Am", "F"] * 2, None, None),
    ("outro", "Outro", ["Am", "F", "C", "G", "Am"], [], None),
]
# refrengene gjentar tekst/melodi fra første refreng
_chorus = next(s for s in SECTIONS if s[0] == "chorus")
SECTIONS = [(n, d, c, _chorus[3] if l is None else l, _chorus[4] if m is None else m)
            for (n, d, c, l, m) in SECTIONS]

VOWELS = "aeiouyæøå"
LETTER_VOWEL = {"A": "a", "H": "å", "K": "å", "O": "o", "U": "u", "Y": "y", "I": "i"}


def syllables(word):
    """Grov stavelsesdeling -> liste med vokaler (én per stavelse)."""
    out = []
    for part in word.split("-"):
        letters = re.sub(r"[^\wæøåÆØÅ]", "", part)
        if not letters:
            continue
        if letters.isupper() or len(letters) == 1:   # forkortelse: ATP, F, c
            out += [LETTER_VOWEL.get(ch.upper(), "e") for ch in letters]
            continue
        groups = re.findall(f"[{VOWELS}]+", letters.lower())
        out += [g[-1] if g[0] == "i" and len(g) > 1 else g[0] for g in groups] or ["e"]
    return out


def degree_to_midi(d):
    return 57 + 12 * (d // 7) + SCALE[d % 7]


def snap_to_chord(midi, chord):
    pcs = {n % 12 for n in CHORDS[chord]}
    return min((m for m in range(midi - 4, midi + 5) if m % 12 in pcs), key=lambda m: (abs(m - midi), m))


def build_timeline():
    """Returnerer (seksjoner, linjer). Hver linje har ord med tider og stavelser med tone."""
    sections, lines = [], []
    t = 0.0
    for name, label, chords, lyr, contours in SECTIONS:
        start = t
        for i, text in enumerate(lyr):
            lstart = start + i * 2 * BAR
            words = [w for w in text.split() if re.search(r"\w", w)]
            sylw = [(wi, v) for wi, w in enumerate(words) for v in syllables(w)]
            n = len(sylw)
            unit, slots = (EIGHTH, 14) if n <= 13 else (EIGHTH / 2, 28)
            durs = [1] * n
            extra = slots - n
            add = min(extra, 3); durs[-1] += add; extra -= add
            finals = [k for k in range(n - 1) if sylw[k][0] != sylw[k + 1][0]]
            j = 0
            while extra > 0 and finals:
                durs[finals[j % len(finals)]] += 1; extra -= 1; j += 1
            contour = contours[i % 2]
            syls, pos = [], 0
            for k, (wi, vowel) in enumerate(sylw):
                st = lstart + pos * unit
                bar_idx = int((st - start + 1e-6) // BAR)
                chord = chords[bar_idx % len(chords)]
                x = pos * unit / (2 * BAR) * (len(contour) - 1)
                a = int(x); fr = x - a
                deg = round(contour[a] * (1 - fr) + contour[min(a + 1, len(contour) - 1)] * fr)
                on_beat_ = abs(((st - start) / BEAT) - round((st - start) / BEAT)) < 1e-6
                if not on_beat_:
                    deg += (0, 1, 0, -1)[k % 4]   # små nabotoner gir liv i melodien
                midi = degree_to_midi(deg)
                on_beat = abs(((st - start) / BEAT) - round((st - start) / BEAT)) < 1e-6
                if on_beat or k == n - 1:
                    midi = snap_to_chord(midi, chord)
                syls.append(dict(t=st, dur=durs[k] * unit, midi=midi, vowel=vowel, word=wi))
                pos += durs[k]
            wtimes = []
            for wi, w in enumerate(words):
                ss = [s for s in syls if s["word"] == wi]
                wtimes.append(dict(text=w, t0=ss[0]["t"], t1=ss[-1]["t"] + ss[-1]["dur"]))
            lines.append(dict(section=name, label=label, index=i, text=text, t0=lstart,
                              t1=lstart + 2 * BAR, words=wtimes, syls=syls))
        t += len(chords) * BAR
        sections.append(dict(name=name, label=label, t0=start, t1=t, chords=chords))
    return sections, lines


SECTIONS_T, LINES = build_timeline()
DURATION = SECTIONS_T[-1]["t1"] + 3.0   # rom for etterklang

if __name__ == "__main__":
    for s in SECTIONS_T:
        print(f'{s["label"]:8s} {s["t0"]:6.1f}-{s["t1"]:6.1f}')
    for l in LINES[:5]:
        print(l["text"], [(s["vowel"], s["midi"]) for s in l["syls"]])
    print("Varighet", DURATION)
