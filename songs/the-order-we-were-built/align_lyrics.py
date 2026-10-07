"""Finner nøyaktige tidskoder for teksten med stable-ts (Whisper) – kjøres på din egen maskin.

    pip install stable-ts            # (valgfritt: pip install demucs  for å skille ut vokalen)
    python align_lyrics.py "The Order We Were Built.wav"

Bruker *forced alignment*: Whisper får den kjente teksten og finner bare når hvert ord synges.
Det er mye mer presist på sang enn fri transkripsjon. Skriver:
  - timing.json  (start/slutt for hver linje – brukes direkte av make_video.py)
  - words.json   (tidskode for hvert ord)
"""
import json
import os
import re
import sys

import stable_whisper

from lyrics_order import SECTIONS

ORDER = ["intro", "verse1", "chorus1", "verse2", "chorus2", "verse3", "bridge", "final", "outro"]
audio = sys.argv[1] if len(sys.argv) > 1 else "audio.mp3"
model_name = sys.argv[2] if len(sys.argv) > 2 else "small"


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("₂", "2"))


lines = [(key, text.replace("₂", "2")) for key in ORDER for text in SECTIONS[key][2]]
CACHE = "alignment.json"   # lagres så en ny kjøring slipper å justere på nytt (~8 min)
if os.path.exists(CACHE):
    print("Bruker lagret justering fra", CACHE)
    result = stable_whisper.WhisperResult(CACHE)
else:
    model = stable_whisper.load_model(model_name)
    kwargs = dict(language="en")
    try:
        import demucs  # noqa: F401
        kwargs["denoiser"] = "demucs"   # skiller ut vokalen før justering
        print("Bruker demucs for å isolere vokalen")
    except ImportError:
        pass
    result = model.align(audio, "\n".join(t for _, t in lines), **kwargs)
    result.save_as_json(CACHE)
words = [w for w in result.all_words() if norm(w.word)]

# fordel ordene tilbake på linjene i rekkefølge
out_words, i = [], 0
timing = {"_note": f"Fra stable-ts forced alignment ({model_name}).", "end": round(result.segments[-1].end + 5, 1),
          "sections": []}
for key in ORDER:
    sec = {"key": key, "start": None, "lines": []}
    for text in SECTIONS[key][2]:
        toks = [t for t in text.replace("₂", "2").split() if norm(t)]
        ws = words[i:i + len(toks)]
        i += len(toks)
        if len(ws) != len(toks) or any(norm(a.word) != norm(b) for a, b in zip(ws, toks)):
            print("Advarsel: ordene stemmer ikke helt for linja:", text)
        if not ws:
            continue
        sec["lines"].append([round(ws[0].start, 2), round(ws[-1].end, 2)])
        out_words.append({"line": text, "words": [{"w": b, "start": round(a.start, 3), "end": round(a.end, 3)}
                                                   for a, b in zip(ws, toks)]})
    timing["sections"].append(sec)
# seksjonsstart: litt før første linje (men ikke før forrige seksjons siste linje)
prev_end = 0.0
for s in timing["sections"]:
    first = s["lines"][0][0]
    s["start"] = 0.0 if s["key"] == "intro" else round(max(prev_end, first - 1.0), 2)
    prev_end = s["lines"][-1][1]

# utf-8 eksplisitt: Windows bruker ellers cp1252, som ikke kan skrive «₂»
with open("timing.json", "w", encoding="utf-8") as f:
    json.dump(timing, f, indent=1, ensure_ascii=False)
with open("words.json", "w", encoding="utf-8") as f:
    json.dump(out_words, f, indent=1, ensure_ascii=False)
result.to_srt_vtt("lyrics.srt")
print("Ferdig: timing.json, words.json og lyrics.srt")
