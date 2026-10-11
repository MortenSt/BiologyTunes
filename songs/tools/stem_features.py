"""Lager en liten JSON med rytme-/energidata fra Suno-stammer, til å styre animasjoner.

    pip install librosa
    python stem_features.py "C:\\sti\\til\\stems-mappen"

For hver lydfil i mappen (wav/mp3/flac) lagres:
  - onsets: tidspunkt (s) for anslag (gitarnapp, trommeslag, nye toner)
  - rms:    lydstyrke 30 ganger i sekundet, normalisert 0..1
Skriver stem_features.json i samme mappe (typisk 100–500 kB). Last opp den hit.
"""
import json
import os
import sys

import librosa
import numpy as np

FPS = 30
folder = sys.argv[1] if len(sys.argv) > 1 else "."
out = {"fps": FPS, "stems": {}}
for name in sorted(os.listdir(folder)):
    if not name.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
        continue
    path = os.path.join(folder, name)
    print("Analyserer", name)
    y, sr = librosa.load(path, sr=22050, mono=True)
    hop = sr // FPS
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    peak = float(np.percentile(rms, 99)) or 1.0
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=False)
    key = os.path.splitext(name)[0]
    out["stems"][key] = {
        "onsets": [round(float(t), 3) for t in onsets],
        "rms": [round(min(1.0, float(v) / peak), 3) for v in rms],
    }
dst = os.path.join(folder, "stem_features.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("Ferdig:", dst, f"({os.path.getsize(dst) // 1024} kB)")
