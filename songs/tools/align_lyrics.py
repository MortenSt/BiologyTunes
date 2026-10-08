"""Finner tidskoder for en sangtekst med stable-ts (forced alignment) – kjøres på din egen maskin.

    pip install stable-ts demucs
    python align_lyrics.py "Sangen.wav" lyrics.txt

lyrics.txt: vanlig Suno-tekst. [Seksjon]-overskrifter blir seksjoner, linjer helt i parentes
(sceneanvisninger) hoppes over, og parenteser inni linjer (korstemmer) fjernes før justering.
Skriver timing.json, words.json, lyrics.srt og alignment.json (mellomlager) i samme mappe som lyrics.txt.
"""
import json
import os
import re
import sys

import stable_whisper

audio = sys.argv[1]
lyr_path = sys.argv[2] if len(sys.argv) > 2 else "lyrics.txt"
model_name = sys.argv[3] if len(sys.argv) > 3 else "small"
out_dir = os.path.dirname(os.path.abspath(lyr_path))


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("₂", "2").replace("₀", "0"))


def parse(path):
    secs, cur = [], None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^\[(.+)\]$", line)
        if m:
            cur = {"label": m.group(1).strip(), "lines": []}
            secs.append(cur)
            continue
        if line.startswith("(") and line.endswith(")"):
            continue   # sceneanvisning
        sung = re.sub(r"\([^)]*\)", "", line).strip()
        if not norm(sung):
            continue
        if cur is None:
            cur = {"label": "Intro", "lines": []}
            secs.append(cur)
        cur["lines"].append({"text": line, "sung": sung})
    return [s for s in secs if s["lines"]]


secs = parse(lyr_path)
all_lines = [l for s in secs for l in s["lines"]]
CACHE = os.path.join(out_dir, "alignment.json")
if os.path.exists(CACHE):
    print("Bruker lagret justering fra", CACHE)
    result = stable_whisper.WhisperResult(CACHE)
else:
    model = stable_whisper.load_model(model_name)
    kwargs = dict(language="en")
    try:
        import demucs  # noqa: F401
        kwargs["denoiser"] = "demucs"
        print("Bruker demucs for å isolere vokalen")
    except ImportError:
        pass
    text = "\n".join(l["sung"].replace("₂", "2") for l in all_lines)
    result = model.align(audio, text, **kwargs)
    result.save_as_json(CACHE)

words = [w for w in result.all_words() if norm(w.word)]
i, out_words, timing = 0, [], {"sections": []}
for n, s in enumerate(secs):
    sec = {"key": f"{n:02d}-" + re.sub(r"[^a-z0-9]+", "-", s["label"].lower()).strip("-"),
           "label": s["label"], "lines": [], "texts": []}
    for l in s["lines"]:
        toks = [t for t in l["sung"].replace("₂", "2").split() if norm(t)]
        ws = words[i:i + len(toks)]
        i += len(toks)
        if len(ws) != len(toks) or any(norm(a.word) != norm(b) for a, b in zip(ws, toks)):
            print("Advarsel: ordene stemmer ikke helt for linja:", l["text"])
        if not ws:
            continue
        sec["lines"].append([round(ws[0].start, 2), round(ws[-1].end, 2)])
        sec["texts"].append(l["text"])
        out_words.append({"line": l["text"], "words": [{"w": b, "start": round(a.start, 3), "end": round(a.end, 3)}
                                                        for a, b in zip(ws, toks)]})
    timing["sections"].append(sec)
prev_end = 0.0
for k, s in enumerate(timing["sections"]):
    s["start"] = 0.0 if k == 0 else round(max(prev_end, s["lines"][0][0] - 1.0), 2)
    prev_end = s["lines"][-1][1]
timing["end"] = round(result.segments[-1].end + 5, 1)

with open(os.path.join(out_dir, "timing.json"), "w", encoding="utf-8") as f:
    json.dump(timing, f, indent=1, ensure_ascii=False)
with open(os.path.join(out_dir, "words.json"), "w", encoding="utf-8") as f:
    json.dump(out_words, f, indent=1, ensure_ascii=False)
result.to_srt_vtt(os.path.join(out_dir, "lyrics.srt"))
print(f"Ferdig: {len(out_words)} linjer -> timing.json, words.json og lyrics.srt i {out_dir}")
