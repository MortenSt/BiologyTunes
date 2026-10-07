"""Syntetiserer lydsporet (instrumental + vokallinje med vokalformanter) -> audio.wav"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve
from song import SECTIONS_T, LINES, DURATION, BAR, BEAT, CHORDS

SR = 44100
N = int(DURATION * SR)
rng = np.random.default_rng(7)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def add(buf, sig, t):
    i = int(t * SR)
    j = min(N, i + len(sig))
    if j > i:
        buf[i:j] += sig[: j - i]


def env_adsr(n, a=0.01, r=0.05):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    na = min(na, n // 2); nr = min(nr, n - na)
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (freq * (1 + detune) * t + rng.random()) % 1.0
    return 2 * ph - 1


# ---------- vokal: additiv syntese formet av vokalformanter ----------
FORMANTS = {
    "a": (730, 1100, 2450), "e": (440, 1900, 2550), "i": (300, 2250, 3000),
    "o": (430, 750, 2400), "u": (330, 700, 2300), "y": (300, 1750, 2200),
    "æ": (650, 1700, 2450), "ø": (400, 1550, 2350), "å": (500, 850, 2450),
}


def voice_note(midi, dur, vowel, prev_midi):
    n = int((dur + 0.08) * SR)
    t = np.arange(n) / SR
    f_target = mtof(midi)
    f_prev = mtof(prev_midi) if prev_midi else f_target
    glide = np.exp(-t / 0.035)
    vib = 1 + 0.012 * np.sin(2 * np.pi * 5.4 * t) * np.clip((t - 0.18) / 0.25, 0, 1)
    f0 = (f_target + (f_prev - f_target) * glide) * vib
    phase = 2 * np.pi * np.cumsum(f0) / SR
    F = FORMANTS.get(vowel, FORMANTS["e"])
    out = np.zeros(n)
    for k in range(1, 40):
        fk = k * f_target
        if fk > 5000:
            break
        amp = sum(g * np.exp(-0.5 * ((fk - fc) / bw) ** 2)
                  for fc, bw, g in zip(F, (90, 120, 160), (1.0, 0.6, 0.25)))
        amp = (amp + 0.02) / k ** 0.6
        out += amp * np.sin(k * phase)
    # «konsonant»: kort, filtrert støystøt i starten
    burst = hp(rng.standard_normal(int(0.03 * SR)), 2500) * np.linspace(0.5, 0, int(0.03 * SR))
    out[: len(burst)] += burst * 0.15
    return out * env_adsr(n, 0.03, 0.09)


def render_voice():
    v = np.zeros(N)
    prev = None
    for line in LINES:
        for s in line["syls"]:
            add(v, voice_note(s["midi"], s["dur"], s["vowel"], prev), s["t"])
            prev = s["midi"]
        prev = None
    v /= np.max(np.abs(v)) + 1e-9
    return v


# ---------- instrumenter ----------
def chord_at(sec, b):
    return sec["chords"][b]


def render_pad():
    pad = np.zeros(N)
    for sec in SECTIONS_T:
        for b, ch in enumerate(sec["chords"]):
            n = int((BAR + 0.4) * SR)
            sig = np.zeros(n)
            for m in CHORDS[ch]:
                for det in (-0.004, 0.004):
                    sig += saw(mtof(m), n, det)
            sig = lp(sig, 1400 if sec["name"].startswith("chorus") else 900) * env_adsr(n, 0.25, 0.45)
            add(pad, sig * 0.12, sec["t0"] + b * BAR)
    return pad


def render_bass():
    bass = np.zeros(N)
    for sec in SECTIONS_T:
        if sec["name"] == "intro":
            continue
        for b, ch in enumerate(sec["chords"]):
            root = CHORDS[ch][0] - 12
            while root > 45:
                root -= 12
            last = sec["name"] == "outro" and b == len(sec["chords"]) - 1
            for e in range(1 if last else 8):
                n = int((BAR if last else BEAT / 2 * 0.9) * SR)
                t = np.arange(n) / SR
                f = mtof(root + (12 if e in (3, 7) and sec["name"] != "bridge" else 0))
                sig = 0.6 * np.sin(2 * np.pi * f * t) + 0.4 * lp(saw(f, n), 600)
                add(bass, sig * env_adsr(n, 0.005, 0.04) * 0.5, sec["t0"] + b * BAR + e * BEAT / 2)
    return bass


def render_arp():
    arp = np.zeros(N)
    for sec in SECTIONS_T:
        if not sec["name"].startswith("chorus") and sec["name"] != "verse2":
            continue
        for b, ch in enumerate(sec["chords"]):
            notes = [m + 12 for m in CHORDS[ch]] + [CHORDS[ch][0] + 24]
            for s in range(16):
                m = notes[(0, 1, 2, 3, 2, 1)[s % 6]]
                n = int(0.25 * SR)
                t = np.arange(n) / SR
                f = mtof(m)
                sig = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.07)
                vol = 0.09 if sec["name"] != "verse2" else 0.05
                add(arp, sig * vol, sec["t0"] + b * BAR + s * BEAT / 4)
    return arp


def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)


def snare():
    n = int(0.25 * SR); t = np.arange(n) / SR
    noise = hp(rng.standard_normal(n), 1500) * np.exp(-t / 0.07)
    return 0.6 * noise + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)


def hat(open_=False):
    n = int((0.2 if open_ else 0.05) * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t / (0.06 if open_ else 0.015))


def render_drums():
    d = np.zeros(N)
    K, S, H, HO = kick(), snare(), hat(), hat(True)
    for sec in SECTIONS_T:
        nm = sec["name"]
        for b in range(len(sec["chords"])):
            t0 = sec["t0"] + b * BAR
            if nm == "intro":
                if b >= 2:
                    for e in range(8):
                        add(d, H * 0.15, t0 + e * BEAT / 2)
                continue
            if nm == "outro" and b == len(sec["chords"]) - 1:
                add(d, K * 0.9, t0)
                continue
            chorus = nm.startswith("chorus")
            kicks = [0, 2, 2.5] if chorus else [0, 2]
            if nm == "bridge":
                kicks = [0]
            for k in kicks:
                add(d, K * 0.9, t0 + k * BEAT)
            if nm != "bridge" or b >= 4:
                for s in (1, 3):
                    add(d, S * 0.45, t0 + s * BEAT)
            for e in range(16 if chorus else 8):
                step = BEAT / (4 if chorus else 2)
                add(d, (HO if (not chorus and e == 7) else H) * (0.18 if e % 2 == 0 else 0.11), t0 + e * step)
            # fill i siste takt før refreng
            if b == len(sec["chords"]) - 1 and nm in ("verse1", "verse2", "bridge"):
                for s in range(8):
                    add(d, S * (0.2 + 0.04 * s), t0 + 2 * BEAT + s * BEAT / 4)
    return d


def reverb(x, secs=1.8, mix=0.25):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t / (secs / 5))
    ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
    wet = fftconvolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix


def main():
    voice = reverb(render_voice(), 2.0, 0.3)
    voice = hp(voice, 150)
    pad = reverb(render_pad(), 2.5, 0.35)
    mix = 0.42 * voice + pad + render_bass() * 0.9 + reverb(render_arp(), 1.2, 0.3) + render_drums() * 0.7
    # fade inn/ut
    mix[: int(0.5 * SR)] *= np.linspace(0, 1, int(0.5 * SR))
    mix[-int(3 * SR):] *= np.linspace(1, 0, int(3 * SR))
    mix = np.tanh(mix * 1.2)
    mix /= np.max(np.abs(mix)) / 0.9
    stereo = np.stack([mix, np.roll(mix, 30) * 0.98 + 0.02 * mix], axis=1)
    wavfile.write("audio.wav", SR, (stereo * 32767).astype(np.int16))
    print("audio.wav skrevet,", round(DURATION, 1), "s")


if __name__ == "__main__":
    main()
