"""Musikkvideo for «Turning Light Into Life» (Suno-lyd + animasjon + karaoke-tekst).

Bruk:  python3 make_video.py            -> turning-light-into-life.mp4
       python3 make_video.py 40 120     -> PNG-forhåndsvisning av gitte tidspunkt
Tidskoder: timing.json + words.json (fra ../tools/align_lyrics.py).
"""
import bisect
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import cairo
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "den-minste-motoren"))
from make_video import (C, TAU, SANS, LYRIC_FONT, clamp, smooth, lerp, rgba, text, rrect,  # noqa: E402
                        ellipse, glow, proton, atp_mol, badge, atp_synthase, membrane, blob)

W, H, FPS = 1280, 720, 30
PANEL_Y = 566
RNG = np.random.default_rng(5)
PTS = RNG.random((200, 3))

# ------------------------------------------------------------------ data
TIMING = json.load(open(os.path.join(HERE, "timing.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(HERE, "words.json"), encoding="utf-8"))
BEATS = json.load(open(os.path.join(HERE, "beats.json")))[::2]
END = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            os.path.join(HERE, "audio.mp3")], capture_output=True, text=True).stdout)

KEYS = ["intro", "verse1", "pre1", "chorus1", "verse2", "pre2", "chorus2", "bridge", "verse3", "final", "outro"]
FACTS = {
    "intro": ("Every second the Sun delivers about 173,000 terawatts to Earth. Plants, algae and "
              "cyanobacteria capture a tiny fraction, and almost every food chain runs on it."),
    "verse1": ("Light reactions in the thylakoid membrane: Photosystem II splits water into O₂, H⁺ and "
               "electrons. The electrons pass through cytochrome b₆f (which pumps H⁺) to Photosystem I, "
               "which makes NADPH. The H⁺ gradient drives ATP synthase."),
    "pre1": "Light energy is stored as chemical energy in two carriers: ATP and NADPH.",
    "chorus1": ("6 CO₂ + 6 H₂O + light → C₆H₁₂O₆ + 6 O₂. The oxygen you breathe comes from the split "
                "water, not from the CO₂."),
    "verse2": ("Calvin cycle in the stroma: RuBisCO fixes CO₂ onto RuBP, ATP and NADPH reduce the "
               "product to G3P, and RuBP is regenerated. Six turns fix six CO₂, enough for one glucose."),
    "pre2": ("'Dark reactions' is an old name. The Calvin cycle uses no light directly, but its enzymes "
             "are switched on by light, so it runs mainly in daytime."),
    "chorus2": "Nearly all the carbon in your food was pulled out of the air by RuBisCO.",
    "bridge": ("Cyanobacteria-like fossils go back ~3.5 billion years, and molecular clocks put water-"
               "splitting at ~3.6–3.2 billion. Their O₂ was soaked up by iron and volcanic gases for "
               "ages; it filled the air ~2.4 billion years ago."),
    "verse3": ("Land plants take up ~120 billion tonnes of carbon a year; ocean algae add about as much "
               "again. At most ~4.6% (C3) to ~6% (C4) of sunlight ends up in biomass; fields manage ~1–2%."),
    "final": "All of it powered by one star, 150 million kilometres away.",
    "outro": "In every leaf, right now: light reactions in the thylakoids, the Calvin cycle in the stroma.",
}
TITLES = {"intro": "Sunlight", "verse1": "The light reactions", "pre1": "Light into power",
          "chorus1": "The equation of life", "verse2": "The Calvin cycle", "pre2": "The 'dark' reactions",
          "chorus2": "Every fruit, every grain", "bridge": "The first oxygen-makers",
          "verse3": "A planetary engine", "final": "Turning light into life", "outro": "Into life"}

SECS, LINES = [], []
_wi = 0
for k, s in enumerate(TIMING["sections"]):
    end = TIMING["sections"][k + 1]["start"] if k + 1 < len(TIMING["sections"]) else END
    sec = dict(key=KEYS[k], label=s["label"], t0=s["start"], t1=end, lines=[])
    for (a, b), txt in zip(s["lines"], s["texts"]):
        ln = dict(text=txt, t0=a, t1=b, words=WORDS[_wi]["words"], key=KEYS[k], idx=len(sec["lines"]))
        _wi += 1
        sec["lines"].append(ln); LINES.append(ln)
    SECS.append(sec)
SEC = {s["key"]: s for s in SECS}


def lt(key, i):
    """Starttid for linje i i seksjonen key."""
    return SEC[key]["lines"][i]["t0"]


def pulse(t):
    i = bisect.bisect_right(BEATS, t) - 1
    return math.exp(-(t - BEATS[i]) / 0.18) if i >= 0 else 0.0


# ------------------------------------------------------------------ tegnehjelpere
def bg(ctx, top, bottom):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bottom)
    ctx.set_source(g); ctx.paint()


def mix(a, b, x):
    return tuple(lerp(p, q, x) for p, q in zip(a, b))


def sun(ctx, x, y, r, t, a=1.0):
    glow(ctx, x, y, r * 4, (1.0, 0.85, 0.4), 0.35 * a)
    ctx.save(); ctx.translate(x, y); ctx.rotate(t * 0.15)
    for i in range(16):
        ctx.rotate(TAU / 16)
        rgba(ctx, (1.0, 0.85, 0.35), 0.5 * a)
        ctx.move_to(r * 1.2, -4); ctx.line_to(r * (1.7 + 0.15 * math.sin(t * 2 + i)), 0); ctx.line_to(r * 1.2, 4); ctx.fill()
    ctx.restore()
    g = cairo.RadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r)
    g.add_color_stop_rgba(0, 1, 1, 0.85, a); g.add_color_stop_rgba(1, 1, 0.75, 0.2, a)
    ctx.set_source(g); ctx.arc(x, y, r, 0, TAU); ctx.fill()


def photon(ctx, x0, y0, x1, y1, p, a=1.0):
    """Bølgete foton som beveger seg fra (x0,y0) til (x1,y1); p = 0..1."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    hx, hy = x0 + dx * p, y0 + dy * p
    rgba(ctx, (1.0, 0.92, 0.35), a); ctx.set_line_width(3)
    ctx.new_path()
    for k in range(22):
        s = k / 21 * 60
        w = 7 * math.sin(s * 0.45 - p * 30)
        ctx.line_to(hx - ux * s - uy * w, hy - uy * s + ux * w)
    ctx.stroke()
    glow(ctx, hx, hy, 14, (1, 0.95, 0.5), 0.8 * a)


def leaf(ctx, x, y, size, ang, col=(0.25, 0.68, 0.30), a=1.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang)
    ctx.move_to(0, 0)
    ctx.curve_to(size * 0.35, -size * 0.35, size * 0.8, -size * 0.25, size, 0)
    ctx.curve_to(size * 0.8, size * 0.25, size * 0.35, size * 0.35, 0, 0)
    rgba(ctx, col, a); ctx.fill()
    rgba(ctx, (0.75, 0.95, 0.6), 0.7 * a); ctx.set_line_width(max(1, size * 0.02))
    ctx.move_to(0, 0); ctx.line_to(size * 0.95, 0); ctx.stroke()
    ctx.restore()


def h2o(ctx, x, y, s=1.0, a=1.0):
    rgba(ctx, (0.92, 0.92, 0.95), a)
    ctx.arc(x - 11 * s, y + 8 * s, 6 * s, 0, TAU); ctx.fill()
    ctx.arc(x + 11 * s, y + 8 * s, 6 * s, 0, TAU); ctx.fill()
    rgba(ctx, (0.85, 0.25, 0.25), a); ctx.arc(x, y, 10 * s, 0, TAU); ctx.fill()


def o2(ctx, x, y, s=1.0, a=1.0):
    rgba(ctx, (0.88, 0.28, 0.28), a)
    ctx.arc(x - 8 * s, y, 9 * s, 0, TAU); ctx.fill(); ctx.arc(x + 8 * s, y, 9 * s, 0, TAU); ctx.fill()
    if s >= 0.9:
        text(ctx, "O₂", x, y + 5 * s, 12 * s, C["white"], a, bold=True)


def co2(ctx, x, y, s=1.0, a=1.0):
    rgba(ctx, (0.88, 0.28, 0.28), a)
    ctx.arc(x - 17 * s, y, 8 * s, 0, TAU); ctx.fill(); ctx.arc(x + 17 * s, y, 8 * s, 0, TAU); ctx.fill()
    rgba(ctx, (0.2, 0.2, 0.22), a); ctx.arc(x, y, 10 * s, 0, TAU); ctx.fill()


def glucose(ctx, x, y, s=1.0, a=1.0, label=True):
    ctx.save(); ctx.translate(x, y)
    ctx.new_path()
    for i in range(6):
        th = i * TAU / 6 + TAU / 12
        ctx.line_to(30 * s * math.cos(th), 30 * s * math.sin(th))
    ctx.close_path()
    rgba(ctx, (1.0, 0.85, 0.45), 0.25 * a); ctx.fill_preserve()
    rgba(ctx, (1.0, 0.85, 0.45), a); ctx.set_line_width(4 * s); ctx.stroke()
    ctx.restore()
    if label:
        text(ctx, "glucose", x, y + 50 * s, 15 * s, (1, 0.9, 0.6), a, bold=True)


def nadph(ctx, x, y, s=1.0, a=1.0):
    glow(ctx, x, y, 34 * s, (0.75, 0.55, 1.0), 0.3 * a)
    rgba(ctx, (0.68, 0.5, 0.95), a); rrect(ctx, x - 34 * s, y - 13 * s, 68 * s, 26 * s, 12 * s); ctx.fill()
    text(ctx, "NADPH", x, y + 6 * s, 15 * s, (0.15, 0.05, 0.3), a, bold=True)


def chloroplast(ctx, cx, cy, w, h, a=1.0, glow_a=0.0):
    rgba(ctx, (0.20, 0.55, 0.25), a); ellipse(ctx, cx, cy, w / 2, h / 2); ctx.fill()
    rgba(ctx, (0.55, 0.85, 0.45), 0.9 * a); ctx.set_line_width(max(2, w * 0.008)); ellipse(ctx, cx, cy, w / 2, h / 2); ctx.stroke()
    rgba(ctx, (0.62, 0.86, 0.50), a); ellipse(ctx, cx, cy, w * 0.46, h * 0.42); ctx.fill()   # stroma
    n = 6
    for i in range(n):           # grana: stabler av tylakoider
        gx = cx - w * 0.33 + i * (w * 0.66 / (n - 1))
        gy = cy + (h * 0.10 if i % 2 else -h * 0.08)
        if i < n - 1:
            nx = cx - w * 0.33 + (i + 1) * (w * 0.66 / (n - 1))
            rgba(ctx, (0.15, 0.45, 0.2), a); ctx.set_line_width(max(2, h * 0.02))
            ctx.move_to(gx, gy); ctx.line_to(nx, cy + (h * 0.10 if (i + 1) % 2 else -h * 0.08)); ctx.stroke()
        for j in range(5):
            dy = gy - h * 0.12 + j * h * 0.06
            if glow_a > 0:
                rgba(ctx, C["hl"], glow_a * a); rrect(ctx, gx - w * 0.055, dy - h * 0.028, w * 0.11, h * 0.056, h * 0.028); ctx.fill()
            rgba(ctx, (0.12, 0.42, 0.18), a); rrect(ctx, gx - w * 0.05, dy - h * 0.025, w * 0.10, h * 0.05, h * 0.025); ctx.fill()


def meadow(ctx, t, y0, a=1.0, fruits=False, wheat=False):
    rgba(ctx, (0.15, 0.40, 0.18), a); ctx.rectangle(0, y0, W, PANEL_Y - y0); ctx.fill()
    for k in range(120):
        x = PTS[k, 0] * W
        hgt = 40 + 70 * PTS[k, 1]
        sway = 10 * math.sin(t * 1.3 + x * 0.02)
        col = (0.25 + 0.2 * PTS[k, 2], 0.6 + 0.25 * PTS[k, 2], 0.25)
        rgba(ctx, col, a); ctx.set_line_width(3)
        ctx.move_to(x, y0 + 30); ctx.curve_to(x, y0 + 30 - hgt * 0.5, x + sway * 0.5, y0 - hgt * 0.6, x + sway, y0 + 30 - hgt); ctx.stroke()
    for k in range(10):
        x = 60 + k * 125 + 30 * PTS[k + 50, 0]
        leaf(ctx, x, y0 + 10, 50 + 20 * PTS[k, 1], -1.2 + 0.4 * PTS[k, 2] + 0.06 * math.sin(t + k), (0.22, 0.62, 0.28), a)
    if fruits:
        for k, x in enumerate((160, 560, 1060)):
            rgba(ctx, (0.40, 0.25, 0.12), a); ctx.rectangle(x - 7, y0 - 50, 14, 80); ctx.fill()
            rgba(ctx, (0.20, 0.55, 0.22), a); ctx.arc(x, y0 - 75, 52, 0, TAU); ctx.fill()
            for j in range(5):
                rgba(ctx, (0.9, 0.2, 0.15), a); ctx.arc(x - 36 + 18 * j, y0 - 80 + 16 * math.sin(j * 2.1), 8, 0, TAU); ctx.fill()
    if wheat:
        for k in range(14):
            x = 320 + k * 26 + 8 * math.sin(t * 1.5 + k)
            rgba(ctx, (0.85, 0.7, 0.3), a); ctx.set_line_width(2); ctx.move_to(320 + k * 26, y0 + 25); ctx.line_to(x, y0 - 50); ctx.stroke()
            for j in range(5):
                ellipse(ctx, x + (-4 if j % 2 else 4), y0 - 55 - j * 9, 4, 7); ctx.fill()


def wrap(ctx, s, width, size, bold=False):
    ctx.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    out, cur = [], ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if ctx.text_extents(trial).x_advance > width and cur:
            out.append(cur); cur = w
        else:
            cur = trial
    return out + ([cur] if cur else [])


def fact_card(ctx, sec, t):
    a = smooth((t - sec["t0"] - 0.5) / 1.0) * (1 - smooth((t - sec["t1"] + 1.0) / 0.8))
    if a <= 0:
        return
    x, y, w = 20, 18, 380
    lines = wrap(ctx, FACTS[sec["key"]], w - 28, 14.5)
    h = 66 + 20 * len(lines)
    rgba(ctx, (0, 0, 0), 0.58 * a); rrect(ctx, x, y, w, h, 14); ctx.fill()
    rgba(ctx, C["hl"], 0.7 * a); ctx.set_line_width(1.5); rrect(ctx, x, y, w, h, 14); ctx.stroke()
    text(ctx, sec["label"].split(" - ")[0].upper(), x + 14, y + 24, 12.5, C["hl"], a, align="left", bold=True)
    text(ctx, TITLES[sec["key"]], x + 14, y + 48, 19, C["white"], a, align="left", bold=True)
    for i, l in enumerate(lines):
        text(ctx, l, x + 14, y + 72 + 20 * i, 14.5, (0.9, 0.92, 0.96), a, align="left")


# ------------------------------------------------------------------ scener
def intro_scene(ctx, t):
    sky = mix((0.02, 0.02, 0.08), (0.10, 0.18, 0.35), smooth(t / 18))
    bg(ctx, sky, (0.02, 0.05, 0.05))
    for k in range(60):   # stjerner som blekner
        rgba(ctx, (1, 1, 1), 0.6 * (1 - smooth(t / 12)) * PTS[k, 2]); ctx.arc(PTS[k, 0] * W, PTS[k, 1] * 400, 1.5, 0, TAU); ctx.fill()
    sy = lerp(520, 140, smooth(t / 9))
    sun(ctx, 230, sy, 60, t, smooth(t / 2))
    # blad som tar imot lyset
    la = smooth((t - 5) / 3)
    for k, (x, y, s, ang) in enumerate(((900, 470, 260, -0.5), (1020, 520, 200, -1.0), (820, 540, 180, -0.1))):
        leaf(ctx, x, y, s, ang + 0.04 * math.sin(t + k), (0.22, 0.62, 0.28), la)
    for k in range(10):
        p = (t * 0.35 + k / 10) % 1.0
        if t > 3.5:
            photon(ctx, 230, sy, 1000 - k * 22, 430 + 8 * k, p, math.sin(p * math.pi))
    a = smooth((t - 13) / 1.5) * (1 - smooth((t - 20.5) / 1.5))
    if a > 0:
        rgba(ctx, (0, 0, 0), 0.35 * a); ctx.rectangle(0, 230, W, 150); ctx.fill()
        text(ctx, "Turning Light Into Life", 640, 312, 62, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "photosynthesis — from photon to glucose", 640, 355, 22, C["hl"], a)


def chloro_zoom(ctx, t, u, z):
    """Fra blad til kloroplast; z = 0..1 innzooming mot et granum."""
    bg(ctx, (0.06, 0.18, 0.10), (0.02, 0.06, 0.03))
    ctx.save()
    s = 1 + 4 * z
    gx, gy = 640 - 0.33 * 820 + 2 * (0.66 * 820 / 5), 300 - 0.08 * 380
    ctx.translate(640, 290); ctx.scale(s, s); ctx.translate(-lerp(640, gx, z), -lerp(290, gy, z))
    # celler med kloroplaster i bakgrunnen
    chloroplast(ctx, 640, 290, 820, 380, 1.0, 0.0)
    ctx.restore()
    for k in range(6):
        p = (t * 0.4 + k / 6) % 1.0
        photon(ctx, 300 + k * 140, -30, 340 + k * 120, 260, p, math.sin(p * math.pi) * (1 - z))
    text(ctx, "chloroplast", 1180, 120, 22, (0.8, 1, 0.7), 1 - z, align="right", bold=True)
    text(ctx, "grana = stacks of thylakoids", 1180, 148, 16, C["white"], 0.85 * (1 - z), align="right")


TX = dict(psii=470, b6f=680, psi=880, atp=1120)


def thylakoid_scene(ctx, t, stage, u_stage):
    """Lysreaksjonene. Lumen (inni tylakoiden) øverst, stroma nederst.
    stage: 0 vann, 1 spalting, 2 elektroner, 3 pumping, 4 gradient, 5 ATP-syntase."""
    my = 280
    bg(ctx, (0.30, 0.16, 0.28), (0.08, 0.20, 0.10))
    rgba(ctx, (0.34, 0.18, 0.32), 0.7); ctx.rectangle(0, 0, W, my); ctx.fill()
    rgba(ctx, (0.12, 0.32, 0.15), 0.8); ctx.rectangle(0, my, W, PANEL_Y - my); ctx.fill()
    text(ctx, "thylakoid lumen", 1250, 30, 17, (1, 0.8, 0.95), 0.85, align="right", bold=True)
    text(ctx, "stroma", 1250, PANEL_Y - 18, 17, (0.8, 1, 0.8), 0.85, align="right", bold=True)
    # protoner i lumen (bygges opp)
    n = int(lerp(4, 55, smooth((stage - 2.5 + u_stage) / 2.5))) if stage >= 3 else 4
    for i in range(n):
        px = 30 + PTS[i, 0] * 1180 + 5 * math.sin(t * 2 + i); py = 120 + PTS[i, 1] * (my - 170) + 4 * math.cos(t * 1.6 + i)
        proton(ctx, px, py, 0.85, 8)
    membrane(ctx, my)
    # vann ved PSII og spalting
    for k in range(3):
        p = (t * 0.3 + k / 3) % 1.0
        x = TX["psii"] - 120 + k * 50
        if stage < 1:
            h2o(ctx, x + 10 * math.sin(t + k), 150 + 15 * math.cos(t * 0.8 + k), 1.1)
        else:
            if p < 0.5:
                h2o(ctx, lerp(x, TX["psii"] - 20, p * 2), lerp(120, my - 60, p * 2), 1.0, 1.0)
            else:
                q = (p - 0.5) * 2
                o2(ctx, TX["psii"] - 30 - 40 * q, my - 70 - 200 * q, 1.0, 1 - q)
                proton(ctx, TX["psii"] + 10 + 60 * q, my - 60 - 30 * q, 1 - q * 0.3, 8)
    if stage >= 1:
        text(ctx, "2 H₂O → O₂ + 4 H⁺ + 4 e⁻", 230, 255, 18, C["white"], smooth(u_stage * 3) if stage == 1 else 1, bold=True)
    # komplekser
    for key, lab, col, w in (("psii", "PSII", (0.25, 0.62, 0.35), 120), ("b6f", "b₆f", (0.30, 0.50, 0.80), 90),
                             ("psi", "PSI", (0.20, 0.55, 0.45), 120)):
        blob(ctx, TX[key], my, w, 160, col, 1.0, lab)
    # fotoner treffer PSII og PSI
    if stage >= 2:
        for key in ("psii", "psi"):
            p = (t * 0.7 + (0.5 if key == "psi" else 0)) % 1.0
            photon(ctx, TX[key] - 160, -40, TX[key] - 10, my - 60, p, math.sin(p * math.pi))
        # elektronet: PSII -> (PQ) -> b6f -> (PC) -> PSI -> stroma -> NADPH
        path = [(TX["psii"], my - 20), (TX["psii"], my - 80), (TX["psii"] + 60, my), (TX["b6f"], my),
                (TX["b6f"] + 60, my - 70), (TX["psi"], my - 20), (TX["psi"], my - 90), (TX["psi"] + 20, my + 60),
                (TX["psi"] + 90, my + 140)]
        p = (t / 2.6) % 1.0
        sgm = p * (len(path) - 1); i = int(sgm); f = sgm - i
        ex, ey = lerp(path[i][0], path[i + 1][0], f), lerp(path[i][1], path[i + 1][1], f)
        glow(ctx, ex, ey, 26, C["electron"], 0.7)
        rgba(ctx, C["electron"]); ctx.arc(ex, ey, 9, 0, TAU); ctx.fill()
        text(ctx, "e⁻", ex + 14, ey - 12, 16, C["electron"], 1, bold=True)
        # NADPH i stroma
        q = (t * 0.25) % 1.0
        nadph(ctx, TX["psi"] + 60 + 30 * q, my + 160 + 40 * q, 0.9, 1 - q)
    # b6f pumper H+ fra stroma inn i lumen
    if stage >= 3:
        for j in range(2):
            p = (t / 1.2 + j * 0.5) % 1.0
            proton(ctx, TX["b6f"] + (j - 0.5) * 30, lerp(my + 130, my - 120, p), math.sin(p * math.pi), 9)
    # ATP-syntase: H+ strømmer tilbake til stroma og lager ATP
    a_syn = smooth((stage - 4 + u_stage) * 2) if stage >= 4 else 0.25
    ctx.push_group()
    atp_synthase(ctx, TX["atp"], my, 0.85, t / 1.4 * TAU if stage >= 5 else 0.0, show_flux=stage >= 5, t=t)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(lerp(0.25, 1.0, a_syn))
    if stage >= 4:
        badge(ctx, "H⁺ gradient", 800, 60, smooth(u_stage * 2) if stage == 4 else 1, C["proton"], 18)
    if stage >= 5:
        text(ctx, "ATP synthase", TX["atp"], my + 245, 17, C["white"], 0.9, bold=True)


def light_reactions(ctx, t):
    sec = SEC["verse1"]
    L = [l["t0"] for l in sec["lines"]]
    if t < L[2] - 0.6:
        z = smooth((t - (L[2] - 3.0)) / 2.4)
        chloro_zoom(ctx, t, t - sec["t0"], z)
        return
    stages = [L[2], L[3], L[4], L[5], L[6], L[7], 1e9]
    st = max(i for i in range(6) if t >= stages[i] - 0.6)
    u = clamp((t - stages[st]) / max(0.5, stages[st + 1] - stages[st])) if st < 5 else 1.0
    thylakoid_scene(ctx, t, st, u)
    if t < L[2] + 0.6:
        ctx.push_group(); chloro_zoom(ctx, t, 0, 1.0); ctx.pop_group_to_source()
        ctx.paint_with_alpha(1 - smooth((t - L[2] + 0.6) / 1.2))


def pre_light(ctx, t, key):
    sec = SEC[key]
    bg(ctx, (0.08, 0.06, 0.16), (0.02, 0.02, 0.05))
    L = [l["t0"] for l in sec["lines"]]
    p = pulse(t)
    a1, a2, a3 = smooth((t - L[0] + 0.3) / 0.6), smooth((t - L[0] - 0.8) / 0.6), smooth((t - L[1]) / 0.6)
    sun(ctx, 260, 280, 60 * (1 + 0.08 * p), t, a1)
    rgba(ctx, C["white"], a2); ctx.set_line_width(5)
    ctx.move_to(380, 280); ctx.line_to(520, 280); ctx.stroke()
    ctx.move_to(520, 280); ctx.line_to(505, 268); ctx.line_to(505, 292); ctx.fill()
    # lyn = «power»
    ctx.save(); ctx.translate(640, 280); ctx.scale(1 + 0.1 * p, 1 + 0.1 * p)
    rgba(ctx, C["hl"], a2); ctx.new_path()
    for x, y in ((10, -80), (-40, 10), (0, 10), (-15, 80), (45, -15), (5, -15)):
        ctx.line_to(x, y)
    ctx.close_path(); ctx.fill(); ctx.restore()
    glow(ctx, 640, 280, 120, C["hl"], 0.3 * a2 * (0.6 + 0.4 * p))
    rgba(ctx, C["white"], a3); ctx.set_line_width(5)
    ctx.move_to(760, 280); ctx.line_to(880, 280); ctx.stroke()
    ctx.move_to(880, 280); ctx.line_to(865, 268); ctx.line_to(865, 292); ctx.fill()
    atp_mol(ctx, 1010, 240, a3, 1.3)
    nadph(ctx, 1010, 320, 1.3, a3)
    text(ctx, "chemical energy", 1010, 390, 18, C["white"], a3)
    if len(L) > 2 and t > L[2] - 0.3:
        a4 = smooth((t - L[2] + 0.3) / 1.0)
        text(ctx, "When the sun feeds the world" if key == "pre1" else "", 640, 500, 26, C["hl"], a4, bold=True)


def dark_scene(ctx, t):
    sec = SEC["pre2"]
    L = [l["t0"] for l in sec["lines"]]
    dawn = smooth((t - L[2]) / 6.0)
    bg(ctx, mix((0.02, 0.03, 0.10), (0.30, 0.45, 0.70), dawn), mix((0.02, 0.04, 0.06), (0.10, 0.25, 0.15), dawn))
    for k in range(80):
        rgba(ctx, (1, 1, 1), 0.7 * PTS[k, 2] * (1 - dawn)); ctx.arc(PTS[k, 0] * W, PTS[k, 1] * 330, 1.6, 0, TAU); ctx.fill()
    rgba(ctx, (0.95, 0.95, 0.85), 1 - dawn); ctx.arc(1080, 110, 42, 0, TAU); ctx.fill()
    rgba(ctx, (0.02, 0.03, 0.10), 1 - dawn); ctx.arc(1100, 98, 38, 0, TAU); ctx.fill()
    sun(ctx, 1080, lerp(560, 140, dawn), 50, t, dawn)
    calvin_wheel(ctx, t, 640, 300, 150, turns=(t - sec["t0"]) * 0.25, speed_note=False, labels=False)
    if t > L[1] - 0.3:
        badge(ctx, "no light used directly — but its enzymes are switched on by light", 640, 520,
              smooth((t - L[1] + 0.3) / 0.8) * (1 - dawn), C["hl"], 16)


PHASES = [("Fixation", (0.35, 0.80, 0.45)), ("Reduction", (1.0, 0.65, 0.30)), ("Regeneration", (0.40, 0.65, 1.0))]


def calvin_wheel(ctx, t, cx, cy, R, turns, speed_note=True, labels=True, glu=0.0):
    ang = turns * TAU
    for i, (name, col) in enumerate(PHASES):
        a0 = -math.pi / 2 + i * TAU / 3
        rgba(ctx, col, 0.55); ctx.set_line_width(26); ctx.new_path(); ctx.arc(cx, cy, R, a0 + 0.06, a0 + TAU / 3 - 0.06); ctx.stroke()
        if labels:
            mid = a0 + TAU / 6
            text(ctx, name, cx + (R + 62) * math.cos(mid), cy + (R + 62) * math.sin(mid) + 6, 17, col, 1, bold=True)
    for i in range(9):   # piler langs hjulet
        th = ang + i * TAU / 9
        x, y = cx + R * math.cos(th), cy + R * math.sin(th)
        ctx.save(); ctx.translate(x, y); ctx.rotate(th + math.pi / 2)
        rgba(ctx, (1, 1, 1), 0.9); ctx.move_to(11, 0); ctx.line_to(-7, -9); ctx.line_to(-7, 9); ctx.fill(); ctx.restore()
    if labels:
        for name, th in (("RuBP", -math.pi / 2), ("3-PGA", math.pi / 6), ("G3P", math.pi * 5 / 6)):
            x, y = cx + R * math.cos(th), cy + R * math.sin(th)
            rgba(ctx, (0.08, 0.1, 0.1)); ctx.arc(x, y, 30, 0, TAU); ctx.fill()
            rgba(ctx, (1, 1, 1), 0.8); ctx.set_line_width(2); ctx.arc(x, y, 30, 0, TAU); ctx.stroke()
            text(ctx, name, x, y + 5, 14, C["white"], 1, bold=True)
    text(ctx, "Calvin", cx, cy - 6, 26, C["white"], 0.9, bold=True)
    text(ctx, "cycle", cx, cy + 22, 22, C["white"], 0.75)


def calvin_scene(ctx, t):
    sec = SEC["verse2"]
    L = [l["t0"] for l in sec["lines"]]
    bg(ctx, (0.10, 0.25, 0.14), (0.03, 0.08, 0.05))
    text(ctx, "stroma", 1250, 34, 17, (0.8, 1, 0.8), 0.85, align="right", bold=True)
    cx, cy, R = 760, 290, 160
    # tylakoidstabel til venstre – ATP og NADPH reiser inn
    for j in range(6):
        rgba(ctx, (0.12, 0.42, 0.18)); rrect(ctx, 70, 190 + j * 34, 150, 28, 14); ctx.fill()
    text(ctx, "thylakoids", 145, 420, 16, (0.8, 1, 0.8), 0.9, bold=True)
    for k in range(4):
        p = (t * 0.3 + k / 4) % 1.0
        x = lerp(230, cx - 40, p); y = cy + 80 + 30 * math.sin(p * 6 + k)
        (atp_mol if k % 2 == 0 else (lambda c, x, y, a, s: nadph(c, x, y, s, a)))(ctx, x, y, math.sin(p * math.pi), 0.9)
    t_on = L[2] - 0.5
    t_six = L[6] + 1.2
    turns = 6 * clamp((t - t_on) / (t_six - t_on)) + 0.15 * max(0, t - t_six)
    a_w = smooth((t - L[0]) / 1.5)
    ctx.push_group(); calvin_wheel(ctx, t, cx, cy, R, turns); ctx.pop_group_to_source(); ctx.paint_with_alpha(a_w)
    # RuBisCO griper CO2 ved fiksering
    ra = smooth((t - L[2] + 0.3) / 0.8)
    rx, ry = cx + (R + 10) * math.cos(-math.pi / 2 + 0.55), cy + (R + 10) * math.sin(-math.pi / 2 + 0.55)
    glow(ctx, rx, ry, 70, (0.4, 1, 0.5), 0.35 * ra * (0.6 + 0.4 * pulse(t)))
    rgba(ctx, (0.35, 0.80, 0.45), ra); ctx.new_path()
    for i in range(8):
        th = i * TAU / 8
        ctx.arc(rx + 22 * math.cos(th), ry + 22 * math.sin(th), 16, 0, TAU)
    ctx.fill()
    text(ctx, "RuBisCO", rx + 70, ry - 30, 18, (0.6, 1, 0.65), ra, bold=True)
    if t > L[2]:
        for k in range(3):
            p = (t * 0.45 + k / 3) % 1.0
            co2(ctx, lerp(rx + 260, rx + 10, p), lerp(ry - 160 + 60 * k, ry, p), 0.9, math.sin(p * math.pi))
    # tellerverk
    if t > t_on:
        badge(ctx, f"CO₂ fixed: {min(6, int(turns + 1e-6))} / 6", 1110, 470, smooth((t - t_on) / 0.6), C["hl"], 18)
    g = smooth((t - t_six) / 1.0)
    if g > 0:
        glow(ctx, cx, cy + R + 40, 80, (1, 0.85, 0.4), 0.4 * g)
        glucose(ctx, cx, cy + R + 40, 1.2 * g + 0.01, g)


def equation_scene(ctx, t, key, fruits=False, wheat=False):
    sec = SEC[key]
    L = [l["t0"] for l in sec["lines"]]
    night = smooth((t - L[5]) / 1.0) * (1 - smooth((t - L[6]) / 1.0)) if key != "final" else 0
    sky = mix((0.35, 0.65, 0.95), (0.03, 0.05, 0.15), night)
    if key == "final":
        sky = (0.95, 0.70, 0.40)
    bg(ctx, sky, (0.55, 0.80, 0.95))
    sun(ctx, 1190 if key != "final" else 820, 70, 38, t, 1 - night)
    if night > 0:
        rgba(ctx, (0.95, 0.95, 0.85), night); ctx.arc(1190, 70, 30, 0, TAU); ctx.fill()
    meadow(ctx, t, 430, 1.0, fruits or key == "final", wheat or key == "final")
    # likningen bygges opp
    terms = [("6 CO₂", co2), ("+ 6 H₂O", h2o), ("+ light", None), ("→  C₆H₁₂O₆", glucose), ("+ 6 O₂", o2)]
    shows = [L[0], L[1], L[2], L[3], L[3] + 1.2] if key != "final" else [sec["t0"] - 5] * 5
    xs = [500, 630, 760, 930, 1110]
    rgba(ctx, (0, 0, 0), 0.30); rrect(ctx, 420, 130, 820, 150, 24); ctx.fill()
    for (lab, fn), x, ts in zip(terms, xs, shows):
        a = smooth((t - ts + 0.2) / 0.6)
        if a <= 0:
            continue
        pop = 1 + 0.25 * math.exp(-(t - ts) * 4) if t > ts else 1
        text(ctx, lab, x, 255, 28 * pop, C["white"], a, bold=True, font=LYRIC_FONT)
        if fn is glucose:
            glucose(ctx, x + 15, 180, 0.7, a, label=False)
        elif fn is not None:
            fn(ctx, x + 5, 185, 1.1, a)
        else:
            sun(ctx, x + 5, 185, 16, t, a)
    # O2 stiger fra engen
    if t > L[min(6, len(L) - 1)] - 0.5 or key == "final":
        for k in range(18):
            p = (t * 0.2 + PTS[k, 2]) % 1.0
            o2(ctx, 40 + PTS[k, 0] * 1200, lerp(450, 360, p), 0.8, 0.8 * math.sin(p * math.pi))
    if night > 0.3:
        badge(ctx, "stored sugar powers life through the night", 640, 400, night, C["hl"], 17)


def bridge_scene(ctx, t):
    sec = SEC["bridge"]
    L = [l["t0"] for l in sec["lines"]]
    q = smooth((t - L[1]) / (L[5] - L[1] + 2))
    sky = mix((0.50, 0.32, 0.18), (0.30, 0.58, 0.92), q)
    bg(ctx, sky, (0.03, 0.12, 0.20))
    rgba(ctx, (0.04, 0.20, 0.30)); ctx.rectangle(0, 300, W, PANEL_Y - 300); ctx.fill()
    n = int(lerp(3, 80, smooth((t - L[1]) / 8)))
    for k in range(n):   # cyanobakterie-tråder
        x = 30 + PTS[k, 0] * (W - 60); y = 340 + PTS[k, 1] * 190
        ctx.save(); ctx.translate(x, y); ctx.rotate(PTS[k, 2] * 3 + 0.2 * math.sin(t + k))
        for j in range(4):
            rgba(ctx, (0.25, 0.75, 0.40)); ctx.arc(j * 11, 2 * math.sin(j + t), 5.5, 0, TAU); ctx.fill()
        ctx.restore()
    for k in range(int(n * 0.7)):
        p = (t * 0.12 + PTS[k, 2]) % 1.0
        o2(ctx, 30 + PTS[k, 0] * (W - 60) + 8 * math.sin(t + k), lerp(330, 90, p), 0.7, 0.7 * (1 - p) * q * 1.5)
    # tidslinje
    x0, x1, y = 460, 1220, 52
    rgba(ctx, (0, 0, 0), 0.4); rrect(ctx, x0 - 20, y - 30, x1 - x0 + 40, 74, 14); ctx.fill()
    rgba(ctx, C["white"], 0.8); ctx.set_line_width(3); ctx.move_to(x0, y); ctx.line_to(x1, y); ctx.stroke()
    marks = ((3.5, "3.5 Ga fossils"), (3.0, "first O₂ whiffs"), (2.4, "GOE"), (0.0, "today"))
    for ga, lab in marks:
        x = lerp(x1, x0, ga / 3.6)
        rgba(ctx, C["white"], 0.9); ctx.arc(x, y, 5, 0, TAU); ctx.fill()
        text(ctx, lab, x, y + 28, 13, C["white"], 0.9)
    now = 3.5 - 1.1 * smooth((t - L[0]) / (L[4] - L[0] + 1)) - 2.4 * smooth((t - L[6]) / 4)
    xm = lerp(x1, x0, now / 3.6)
    glow(ctx, xm, y, 22, C["hl"], 0.9); rgba(ctx, C["hl"]); ctx.arc(xm, y, 8, 0, TAU); ctx.fill()
    if t > L[4] - 0.3:
        badge(ctx, "Great Oxidation Event · ~2.4 billion years ago", 840, 140, smooth((t - L[4] + 0.3) / 0.8), C["hl"], 18)
    if t > L[6] - 0.3:   # hjerteslag
        a = smooth((t - L[6] + 0.3) / 0.8); s = 1 + 0.15 * pulse(t)
        ctx.save(); ctx.translate(1120, 250); ctx.scale(s, s)
        rgba(ctx, (0.9, 0.2, 0.3), a); ctx.new_path()
        ctx.move_to(0, 30); ctx.curve_to(-60, -10, -30, -55, 0, -25); ctx.curve_to(30, -55, 60, -10, 0, 30); ctx.fill()
        ctx.restore()


def earth_scene(ctx, t):
    sec = SEC["verse3"]
    L = [l["t0"] for l in sec["lines"]]
    bg(ctx, (0.02, 0.03, 0.10), (0.01, 0.01, 0.04))
    for k in range(70):
        rgba(ctx, (1, 1, 1), 0.5 * PTS[k, 2]); ctx.arc(PTS[k, 0] * W, PTS[k, 1] * PANEL_Y, 1.4, 0, TAU); ctx.fill()
    ex, ey, R = 330, 330, 190
    glow(ctx, ex, ey, R * 1.35, (0.4, 0.7, 1.0), 0.35)
    rgba(ctx, (0.12, 0.35, 0.75)); ctx.arc(ex, ey, R, 0, TAU); ctx.fill()
    ctx.save(); ctx.arc(ex, ey, R, 0, TAU); ctx.clip()
    off = (t * 18) % 800
    for k in range(9):   # kontinenter som roterer forbi
        x = ex - R - 200 + ((PTS[k + 100, 0] * 800 + off) % 800)
        y = ey - R * 0.8 + PTS[k + 100, 1] * R * 1.6
        rgba(ctx, (0.25, 0.62, 0.30)); ellipse(ctx, x, y, 50 + 60 * PTS[k + 100, 2], 30 + 30 * PTS[k, 2]); ctx.fill()
    ctx.restore()
    for k in range(10):   # CO2 inn i biosfæren
        p = (t * 0.3 + k / 10) % 1.0
        th = k * TAU / 10
        co2(ctx, ex + (R + 140 - 130 * p) * math.cos(th), ey + (R + 140 - 130 * p) * math.sin(th), 0.6, math.sin(p * math.pi))
    a0 = smooth((t - L[0] + 0.3) / 0.8) * (1 - smooth((t - L[2] + 0.8) / 0.5))
    text(ctx, "≈ 120 billion tonnes", 920, 250, 34, C["hl"], a0, bold=True)
    text(ctx, "of carbon taken up by land plants each year", 920, 285, 18, C["white"], 0.9 * a0)
    text(ctx, "(+ about as much again by ocean algae)", 920, 312, 16, C["white"], 0.75 * a0)
    rx = 700
    # effektivitet
    if L[2] - 0.3 < t < L[4] - 0.3:
        a = smooth((t - L[2] + 0.3) / 0.8) * (1 - smooth((t - L[4] + 0.8) / 0.5))
        text(ctx, "How much sunlight ends up in biomass?", rx, 170, 20, C["white"], a, align="left", bold=True)
        bars = (("sunlight", 100, (1, 0.85, 0.35)), ("max C3", 4.6, (0.4, 0.85, 0.45)),
                ("max C4", 6.0, (0.3, 0.75, 0.4)), ("real fields", 1.5, (0.6, 0.8, 0.5)))
        for i, (lab, val, col) in enumerate(bars):
            y = 210 + i * 62
            wbar = 480 * val / 100 * smooth((t - L[2] - i * 0.3) / 0.8)
            rgba(ctx, col, a); rrect(ctx, rx, y, max(6, wbar), 34, 8); ctx.fill()
            text(ctx, f"{lab}  {val:g}%", rx + max(6, wbar) + 12, y + 24, 17, C["white"], a, align="left", bold=True)
    # næringskjede
    if t > L[4] - 0.6:
        a = smooth((t - L[4] + 0.6) / 0.8)
        chain = ("algae", "krill", "fish", "seal")
        for i, lab in enumerate(chain):
            x = rx + 40 + i * 140
            y = 260
            if i == 0:
                for j in range(5):
                    rgba(ctx, (0.3, 0.8, 0.4), a); ctx.arc(x - 20 + 10 * j, y + 6 * math.sin(j), 7, 0, TAU); ctx.fill()
            elif i == 1:
                rgba(ctx, (1, 0.5, 0.4), a); ellipse(ctx, x, y, 26, 9); ctx.fill()
            elif i == 2:
                rgba(ctx, (0.6, 0.75, 0.9), a); ellipse(ctx, x, y, 34, 14); ctx.fill()
                ctx.move_to(x + 30, y); ctx.line_to(x + 50, y - 14); ctx.line_to(x + 50, y + 14); ctx.fill()
            else:
                rgba(ctx, (0.55, 0.55, 0.6), a); ellipse(ctx, x, y, 42, 18); ctx.fill(); ctx.arc(x - 38, y - 8, 14, 0, TAU); ctx.fill()
            text(ctx, lab, x, y + 50, 15, C["white"], a)
            if i < 3:
                rgba(ctx, C["white"], 0.7 * a); ctx.set_line_width(3); ctx.move_to(x + 55, y); ctx.line_to(x + 85, y); ctx.stroke()
        tree_a = smooth((t - L[4] - 1.5) / 0.8)
        rgba(ctx, (0.40, 0.25, 0.12), tree_a); ctx.rectangle(rx + 250, 430, 22, 80); ctx.fill()
        rgba(ctx, (0.20, 0.55, 0.22), tree_a); ctx.arc(rx + 261, 410, 55, 0, TAU); ctx.fill()
        text(ctx, "tallest tree", rx + 360, 420, 15, C["white"], tree_a, align="left")
        text(ctx, "every food chain starts with photosynthesis", rx + 230, 190, 17, C["hl"], a, bold=True)


def outro_scene(ctx, t):
    sec = SEC["outro"]
    u = t - sec["t0"]
    bg(ctx, mix((0.95, 0.60, 0.35), (0.10, 0.08, 0.20), smooth(u / 30)), (0.20, 0.15, 0.20))
    sun(ctx, 640, lerp(300, 470, smooth(u / 25)), 70, t, 1.0)
    meadow(ctx, t, 440, 1.0)
    for k in range(8):
        p = (t * 0.3 + k / 8) % 1.0
        photon(ctx, 640, lerp(300, 470, smooth(u / 25)), 120 + k * 150, 460, p, math.sin(p * math.pi) * 0.8)
    a = smooth((t - LINES[-1]["t1"] - 0.5) / 2.5)
    if a > 0:
        text(ctx, "Turning Light Into Life", 640, 160, 56, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "BiologyTunes", 640, 200, 22, C["hl"], a, bold=True)


# ------------------------------------------------------------------ tekstpanel
def karaoke(ctx, l, t, size, y):
    ctx.select_font_face(LYRIC_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    toks = l["text"].split()
    space = ctx.text_extents(" ").x_advance
    widths = [ctx.text_extents(w).x_advance for w in toks]
    x = 640 - (sum(widths) + space * (len(toks) - 1)) / 2
    wi, prev_end, paren = 0, -1.0, False
    for tok, w in zip(toks, widths):
        if tok.startswith("("):
            paren = True
        sung = (not paren) and any(ch.isalnum() for ch in tok) and wi < len(l["words"])
        if sung:
            wd = l["words"][wi]; wi += 1
            prog = clamp((t - wd["start"]) / max(0.08, wd["end"] - wd["start"]))
            prev_end = wd["end"]
        else:   # korstemme i parentes / tankestrek: lyser opp etter forrige ord
            prog = 1.0 if t >= prev_end + (0.25 if paren else 0) else 0.0
        col = (0.75, 0.85, 1.0) if paren else (1, 1, 1)
        ctx.move_to(x, y); rgba(ctx, col, 0.92); ctx.show_text(tok)
        if prog > 0:
            ctx.save(); ctx.rectangle(x - 2, y - size, w * prog + 2, size * 1.5); ctx.clip()
            ctx.move_to(x, y); rgba(ctx, (0.6, 0.9, 1.0) if paren else C["hl"]); ctx.show_text(tok)
            ctx.restore()
        if tok.endswith(")"):
            paren = False
        x += w + space


def lyric_panel(ctx, t):
    g = cairo.LinearGradient(0, PANEL_Y - 24, 0, H)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(0.15, 0, 0, 0, 0.75); g.add_color_stop_rgba(1, 0, 0, 0, 0.88)
    ctx.set_source(g); ctx.rectangle(0, PANEL_Y - 24, W, H - PANEL_Y + 24); ctx.fill()
    rgba(ctx, (1, 1, 1), 0.15); ctx.rectangle(0, H - 4, W, 4); ctx.fill()
    rgba(ctx, C["hl"], 0.8); ctx.rectangle(0, H - 4, W * t / END, 4); ctx.fill()
    cur = None
    for i, l in enumerate(LINES):
        if l["t0"] - 0.3 <= t < l["t1"] + 0.4:
            cur = i
    if cur is None:
        nxt = next((l for l in LINES if 0 < l["t0"] - t < 3.0), None)
        if nxt:
            text(ctx, nxt["text"], 640, PANEL_Y + 82, 24, (0.75, 0.75, 0.8), 0.6, font=LYRIC_FONT)
        else:
            text(ctx, "♪   ♪   ♪", 640, PANEL_Y + 80, 28, (0.8, 0.8, 0.9), 0.5)
        return
    l = LINES[cur]
    prev = LINES[cur - 1] if cur > 0 and LINES[cur - 1]["key"] == l["key"] else None
    nxt = LINES[cur + 1] if cur + 1 < len(LINES) and LINES[cur + 1]["t0"] - l["t1"] < 3 else None
    if prev:
        text(ctx, prev["text"], 640, PANEL_Y + 26, 19, (0.65, 0.65, 0.72), 0.6, font=LYRIC_FONT)
    size = 36
    ctx.select_font_face(LYRIC_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    wdt = ctx.text_extents(l["text"]).x_advance
    if wdt > W - 80:
        size *= (W - 80) / wdt
    karaoke(ctx, l, t, size, PANEL_Y + 78)
    if nxt:
        text(ctx, nxt["text"], 640, PANEL_Y + 122, 20, (0.7, 0.7, 0.78), 0.7, font=LYRIC_FONT)


# ------------------------------------------------------------------ ramme
def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    sec = next((s for s in SECS if s["t0"] <= t < s["t1"]), SECS[-1])
    k = sec["key"]
    if k == "intro":
        intro_scene(ctx, t)
    elif k == "verse1":
        light_reactions(ctx, t)
    elif k == "pre1":
        pre_light(ctx, t, k)
    elif k in ("chorus1", "chorus2", "final"):
        equation_scene(ctx, t, k, fruits=(k == "chorus2"), wheat=(k == "chorus2"))
    elif k == "verse2":
        calvin_scene(ctx, t)
    elif k == "pre2":
        dark_scene(ctx, t)
    elif k == "bridge":
        bridge_scene(ctx, t)
    elif k == "verse3":
        earth_scene(ctx, t)
    else:
        outro_scene(ctx, t)
    for s in SECS[1:]:
        d = t - s["t0"]
        if -0.3 < d < 0.3:
            rgba(ctx, (0, 0, 0), 0.6 * (1 - abs(d) / 0.3)); ctx.paint()
    if (k != "intro" or t > 22) and not (k == "outro" and t > LINES[-1]["t1"]):
        fact_card(ctx, sec, t)
    lyric_panel(ctx, t)
    if t < 1.0:
        rgba(ctx, (0, 0, 0), 1 - t); ctx.paint()
    if t > END - 3:
        rgba(ctx, (0, 0, 0), smooth((t - END + 3) / 3)); ctx.paint()
    surf.flush()
    return surf


def frame_bytes(i):
    return bytes(render(i / FPS).get_data())


def main():
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            render(float(arg)).write_to_png(f"preview_{arg}.png")
        return
    n = int(END * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", os.path.join(HERE, "audio.mp3"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        os.path.join(HERE, "turning-light-into-life.mp4")], stdin=subprocess.PIPE)
    with Pool() as pool:
        for k, buf in enumerate(pool.imap(frame_bytes, range(n), chunksize=8)):
            ff.stdin.write(buf)
            if k % 1500 == 0:
                print(f"{k}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print("ferdig")


if __name__ == "__main__":
    main()
