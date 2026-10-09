"""Musikkvideo for «The Living Clock: A Song of Degree Days» (Suno-lyd + animasjon + karaoke).

Bruk:  python3 make_video.py            -> the-living-clock.mp4
       python3 make_video.py 40 120     -> PNG-forhåndsvisning av gitte tidspunkt
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
from make_video import C, TAU, SANS, LYRIC_FONT, clamp, smooth, lerp, rgba, text, rrect, ellipse, glow, badge  # noqa: E402

W, H, FPS = 1280, 720, 30
PANEL_Y = 566
PTS = np.random.default_rng(9).random((300, 3))

TIMING = json.load(open(os.path.join(HERE, "timing.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(HERE, "words.json"), encoding="utf-8"))
BEATS = json.load(open(os.path.join(HERE, "beats.json")))
END = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            os.path.join(HERE, "audio.mp3")], capture_output=True, text=True).stdout)

LINES, _wi = [], 0
for k, s in enumerate(TIMING["sections"]):
    for (a, b), txt in zip(s["lines"], s["texts"]):
        LINES.append(dict(text=txt, t0=a, t1=b, words=WORDS[_wi]["words"], sec=k, idx=len([l for l in LINES if l["sec"] == k])))
        _wi += 1


def L(sec, i):
    return next(l for l in LINES if l["sec"] == sec and l["idx"] == i)["t0"]


# scener i tid (instrumentalt parti mellom refreng 2 og broen)
SCENES = [
    ("intro", 0.0, "Intro", "Night falls"),
    ("verse1", L(0, 0) - 1.0, "Verse 1", "The call"),
    ("chorus1", L(1, 0) - 0.5, "Chorus", "Degree days"),
    ("verse2", L(2, 0) - 1.0, "Verse 2", "Egg and instars"),
    ("chorus2", L(3, 0) - 0.5, "Chorus", "Reading the clock"),
    ("inst", LINES[[i for i, l in enumerate(LINES) if l["sec"] == 3][-1]]["t1"] + 0.3, "Instrumental", "Heat adds up"),
    ("bridge", L(4, 0) - 1.0, "Bridge", "Leaving to pupate"),
    ("chorus3", L(5, 0) - 0.5, "Chorus", "A living clock"),
    ("outro", L(6, 0) - 1.0, "Outro", "Emergence"),
]
FACTS = {
    "intro": "Forensic entomology uses insects to estimate how long ago a death occurred.",
    "verse1": ("After death, cells break down (autolysis) and decay releases volatile compounds that blowflies "
               "detect within minutes to hours. Species differ: Lucilia sericata favours sunny, urban sites; "
               "Calliphora vicina shade and cooler weather; C. vomitoria rural woodland."),
    "chorus1": ("Insects can't control their body temperature, so their development runs on heat. Entomologists "
                "add up degree-days (ADD) above a lower threshold; below it, development stops."),
    "verse2": ("Blowflies lay eggs in wounds and natural openings such as the eyes. Larvae pass through three "
               "instars; the third is by far the largest and does most of the feeding."),
    "chorus2": ("Match the oldest larval stage to the heat accumulated at the scene, and you can work back to "
                "when the eggs were laid: a minimum post-mortem interval (PMImin)."),
    "inst": ("Warm days add many degree-days, cold days few or none. That's why weather records from the "
             "scene are essential."),
    "bridge": ("When feeding ends, post-feeding larvae (prepupae) wander off and usually burrow into soil to "
               "pupate, so investigators search the ground nearby. Cold-tolerant Protophormia terraenovae often "
               "pupates on or right beside the remains."),
    "chorus3": "From egg to adult, a blowfly's development is a clock that can be read days to weeks after death.",
    "outro": ("The adult pushes out of the puparium, inflates its wings and lets them harden before flying. "
              "Empty puparia show that at least one full cycle has passed."),
}


def scene_at(t):
    cur = SCENES[0]
    for s in SCENES:
        if t >= s[1]:
            cur = s
    i = SCENES.index(cur)
    t1 = SCENES[i + 1][1] if i + 1 < len(SCENES) else END
    return cur, t1


def pulse(t):
    i = bisect.bisect_right(BEATS, t) - 1
    return math.exp(-(t - BEATS[i]) / 0.25) if i >= 0 else 0.0


def mix(a, b, x):
    return tuple(lerp(p, q, x) for p, q in zip(a, b))


def bg(ctx, top, bottom):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bottom)
    ctx.set_source(g); ctx.paint()


# ------------------------------------------------------------------ figurer
FLY_COLS = {"lucilia": (0.35, 0.80, 0.45), "vicina": (0.35, 0.50, 0.90), "vomitoria": (0.25, 0.35, 0.75),
            "proto": (0.15, 0.25, 0.45)}


def fly(ctx, x, y, s=1.0, col=FLY_COLS["vicina"], ang=0.0, t=0.0, a=1.0, wings=1.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.scale(s, s)
    flap = 0.35 * math.sin(t * 60) if wings >= 1 else 0
    for side in (-1, 1):   # vinger
        ctx.save(); ctx.rotate(side * (0.5 + flap)); ctx.scale(1, wings)
        rgba(ctx, (0.85, 0.9, 1.0), 0.45 * a); ellipse(ctx, -4, side * 14, 18, 8); ctx.fill()
        ctx.restore()
    g = cairo.LinearGradient(-16, -8, 16, 8)
    g.add_color_stop_rgba(0, *(c * 0.6 for c in col), a); g.add_color_stop_rgba(0.5, *col, a); g.add_color_stop_rgba(1, *(c * 0.5 for c in col), a)
    ctx.set_source(g); ellipse(ctx, -2, 0, 16, 8); ctx.fill()           # bakkropp
    rgba(ctx, tuple(c * 0.7 for c in col), a); ctx.arc(14, 0, 6.5, 0, TAU); ctx.fill()   # brystparti
    rgba(ctx, (0.75, 0.15, 0.10), a); ctx.arc(20, -3.5, 3.5, 0, TAU); ctx.fill(); ctx.arc(20, 3.5, 3.5, 0, TAU); ctx.fill()   # øyne
    ctx.restore()


def larva(ctx, x, y, length, ang=0.0, a=1.0, t=0.0, col=(0.96, 0.94, 0.86)):
    """Segmentert, kremhvit larve: spiss fremende (høyre, munnkroker), butt bakende med spirakler."""
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang)
    n = 11
    for i in range(n):
        f = i / (n - 1)
        r = length * 0.09 * (0.45 + 0.55 * math.sin(math.pi * (0.25 + 0.75 * f)))
        cx = -length / 2 + f * length
        cy = 0.06 * length * math.sin(t * 4 + i * 0.7)
        rgba(ctx, tuple(c * (0.9 + 0.1 * (i % 2)) for c in col), a); ctx.arc(cx, cy, r, 0, TAU); ctx.fill()
    rgba(ctx, (0.15, 0.1, 0.1), a); ctx.arc(length / 2 + length * 0.01, 0.06 * length * math.sin(t * 4 + 7), length * 0.02, 0, TAU); ctx.fill()   # munnkroker i den spisse fremenden
    rgba(ctx, (0.45, 0.30, 0.15), 0.8 * a)   # bakre spirakler på den butte enden
    ctx.arc(-length / 2 + length * 0.02, -length * 0.025, length * 0.018, 0, TAU); ctx.fill()
    ctx.arc(-length / 2 + length * 0.02, length * 0.025, length * 0.018, 0, TAU); ctx.fill()
    ctx.restore()


def egg(ctx, x, y, s=1.0, ang=0.0, a=1.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang)
    rgba(ctx, (0.98, 0.97, 0.92), a); ellipse(ctx, 0, 0, 7 * s, 2.6 * s); ctx.fill()
    rgba(ctx, (1, 1, 1), 0.8 * a); ellipse(ctx, -2 * s, -0.8 * s, 3 * s, 0.8 * s); ctx.fill()
    ctx.restore()


def puparium(ctx, x, y, s=1.0, a=1.0, col=(0.45, 0.25, 0.12), crack=0.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    g = cairo.LinearGradient(0, -12, 0, 12)
    g.add_color_stop_rgba(0, *(min(1, c * 1.5) for c in col), a); g.add_color_stop_rgba(1, *(c * 0.6 for c in col), a)
    ctx.set_source(g); rrect(ctx, -26, -12, 52, 24, 12); ctx.fill()
    rgba(ctx, (0, 0, 0), 0.25 * a); ctx.set_line_width(1.5)
    for i in range(-3, 4):
        ctx.move_to(i * 7, -11); ctx.line_to(i * 7, 11); ctx.stroke()
    if crack > 0:   # lokket løsner
        ctx.save(); ctx.translate(26, 0); ctx.rotate(-0.9 * crack)
        ctx.set_source(g); rrect(ctx, -2, -12, 12, 24, 10); ctx.fill(); ctx.restore()
    ctx.restore()


def host(ctx, x, y, w, a=1.0):
    """Abstrakt, ikke-grafisk framstilling av levningene (en kappe over en form)."""
    rgba(ctx, (0.45, 0.42, 0.40), a)
    ctx.move_to(x - w / 2, y)
    ctx.curve_to(x - w * 0.4, y - w * 0.28, x + w * 0.25, y - w * 0.32, x + w / 2, y)
    ctx.close_path(); ctx.fill()
    rgba(ctx, (0.6, 0.57, 0.55), 0.6 * a); ctx.set_line_width(2)
    for k in range(4):
        ctx.move_to(x - w * 0.3 + k * w * 0.18, y - 4); ctx.curve_to(x - w * 0.25 + k * w * 0.18, y - w * 0.15, x - w * 0.2 + k * w * 0.18, y - w * 0.2, x - w * 0.15 + k * w * 0.18, y - w * 0.22); ctx.stroke()


def tree(ctx, x, y, s, col=(0.12, 0.28, 0.18), a=1.0):
    rgba(ctx, (0.18, 0.12, 0.08), a); ctx.rectangle(x - 6 * s, y - 40 * s, 12 * s, 40 * s); ctx.fill()
    rgba(ctx, col, a)
    for k in range(3):
        ctx.move_to(x - 50 * s + k * 8 * s, y - 30 * s - k * 40 * s); ctx.line_to(x, y - 110 * s - k * 40 * s); ctx.line_to(x + 50 * s - k * 8 * s, y - 30 * s - k * 40 * s); ctx.fill()


def grass(ctx, t, y0, a=1.0, col=(0.10, 0.22, 0.14)):
    rgba(ctx, col, a); ctx.rectangle(0, y0, W, PANEL_Y - y0); ctx.fill()
    for k in range(140):
        x = PTS[k, 0] * W; hgt = 20 + 45 * PTS[k, 1]; sway = 8 * math.sin(t * 1.1 + x * 0.02)
        rgba(ctx, (0.12 + 0.1 * PTS[k, 2], 0.30 + 0.15 * PTS[k, 2], 0.18), a); ctx.set_line_width(2)
        ctx.move_to(x, y0 + 15); ctx.curve_to(x, y0 - hgt * 0.4, x + sway * 0.5, y0 - hgt * 0.6, x + sway, y0 + 15 - hgt); ctx.stroke()


def night(ctx, t, a=1.0):
    bg(ctx, (0.03, 0.04, 0.10), (0.02, 0.05, 0.05))
    for k in range(90):
        rgba(ctx, (1, 1, 1), 0.6 * PTS[k, 2] * (0.6 + 0.4 * math.sin(t * 2 + k))); ctx.arc(PTS[k, 0] * W, PTS[k, 1] * 300, 1.3, 0, TAU); ctx.fill()
    glow(ctx, 1080, 110, 140, (0.8, 0.85, 1.0), 0.25)
    rgba(ctx, (0.92, 0.92, 0.85)); ctx.arc(1080, 110, 40, 0, TAU); ctx.fill()
    for k, x in enumerate((90, 230, 1180, 1050, 360, 900)):
        tree(ctx, x, 470, 1.3 + 0.4 * PTS[k, 0], (0.05, 0.12, 0.09))
    grass(ctx, t, 470, 1.0, (0.04, 0.10, 0.07))


# ------------------------------------------------------------------ scener
def intro_scene(ctx, t):
    night(ctx, t)
    for k in range(6):   # sirisser: små lydbølger i gresset
        x = 150 + k * 190; y = 500
        ph = (t * 1.6 + k * 0.37) % 1.0
        rgba(ctx, (0.8, 0.9, 0.8), 0.35 * (1 - ph)); ctx.set_line_width(2)
        ctx.new_path(); ctx.arc(x, y, 8 + 30 * ph, -2.4, -0.7); ctx.stroke()
    a = smooth((t - 6) / 2) * (1 - smooth((t - 21) / 2))
    if a > 0:
        rgba(ctx, (0, 0, 0), 0.4 * a); ctx.rectangle(0, 210, W, 170); ctx.fill()
        text(ctx, "The Living Clock", 640, 292, 64, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "A Song of Degree Days", 640, 340, 26, C["hl"], a)


def verse1_scene(ctx, t):
    l0, l2 = L(0, 0), L(0, 2)
    if t < l2 - 0.5:
        night(ctx, t)
        host(ctx, 640, 470, 280, 1.0)
        # celler som brytes ned
        ca = smooth((t - l0) / 1.0) * (1 - smooth((t - L(0, 1) - 1) / 1.5))
        for k in range(7):
            x, y = 520 + k * 40, 330 + 20 * math.sin(k)
            br = smooth((t - l0 - 1 - k * 0.3) / 1.5)
            rgba(ctx, (0.9, 0.6, 0.6), ca * (1 - br)); ctx.set_line_width(2); ctx.arc(x, y, 16, 0, TAU); ctx.stroke()
            for j in range(5):
                th = j * TAU / 5
                rgba(ctx, (0.9, 0.6, 0.6), ca * br * (1 - br)); ctx.arc(x + br * 25 * math.cos(th), y + br * 25 * math.sin(th), 3, 0, TAU); ctx.fill()
        # duft-signal stiger
        sa = smooth((t - L(0, 1)) / 1.0)
        for k in range(8):
            p = (t * 0.25 + k / 8) % 1.0
            rgba(ctx, (0.75, 0.9, 0.6), 0.35 * sa * (1 - p)); ctx.set_line_width(3); ctx.new_path()
            for i in range(30):
                yy = 440 - p * 300 - i * 4
                ctx.line_to(600 + k * 12 + 18 * math.sin(i * 0.4 + t * 2 + k), yy)
            ctx.stroke()
        for k in range(4):   # fluer på vei inn
            q = clamp((t - L(0, 1) - 1 - k * 0.8) / 4)
            if q > 0:
                fly(ctx, lerp(-60 + k * 400, 600 + k * 30, smooth(q)), lerp(80 + k * 40, 380, smooth(q)) + 10 * math.sin(t * 5 + k),
                    1.0, FLY_COLS["vicina"], 0.6, t, 1.0)
        if sa > 0:
            text(ctx, "volatile compounds", 820, 230, 18, (0.8, 0.95, 0.7), sa * 0.9)
        return
    # habitater: by/skog, sol/skygge – fire arter
    bg(ctx, (0.12, 0.16, 0.22), (0.05, 0.07, 0.08))
    sun_side = smooth((t - L(0, 4) + 0.3) / 0.8)
    panels = [("city", 640, (0.30, 0.32, 0.36)), ("woodland", 1060, (0.10, 0.25, 0.15))]
    for name, x, col in panels:
        rgba(ctx, col, 0.9); rrect(ctx, x - 200, 130, 400, 400, 20); ctx.fill()
    for k in range(6):   # bygninger
        hgt = 120 + 140 * PTS[k, 0]
        rgba(ctx, (0.40, 0.42, 0.46)); ctx.rectangle(460 + k * 60, 530 - hgt, 48, hgt); ctx.fill()
        for j in range(int(hgt // 30)):
            rgba(ctx, (1, 0.9, 0.5), 0.5 if (k + j) % 3 else 0.1); ctx.rectangle(470 + k * 60, 540 - hgt + j * 30, 10, 12); ctx.fill()
    for k in range(5):
        tree(ctx, 900 + k * 80, 530, 1.0 + 0.3 * PTS[k + 20, 0], (0.15, 0.40, 0.22))
    text(ctx, "city", 640, 160, 22, C["white"], 0.9, bold=True)
    text(ctx, "woodland", 1060, 160, 22, C["white"], 0.9, bold=True)
    species = [(600, 280, "lucilia", "Lucilia sericata", "sunny, urban"),
               (690, 410, "vicina", "Calliphora vicina", "shade, cooler, urban"),
               (1060, 300, "vomitoria", "Calliphora vomitoria", "rural woodland")]
    for k, (x, y, key, lab, hab) in enumerate(species):
        a = smooth((t - l2 - k * 0.8) / 0.8)
        fly(ctx, x + 15 * math.sin(t * 2 + k), y + 10 * math.cos(t * 3 + k), 1.8, FLY_COLS[key], 0.2 * math.sin(t + k), t, a)
        text(ctx, lab, x, y + 50, 17, C["white"], a, bold=True)
        text(ctx, hab, x, y + 72, 14, (0.8, 0.85, 0.9), a)
    if sun_side > 0:   # sol over Lucilia, skygge over Calliphora
        glow(ctx, 520, 210, 120, (1, 0.85, 0.4), 0.5 * sun_side)
        rgba(ctx, (1, 0.85, 0.35), sun_side); ctx.arc(520, 210, 26, 0, TAU); ctx.fill()


DAYS = 14
def _temp(h):
    day = h / 24
    base = 17 + 3 * math.sin(day * 0.7) - 9 * math.exp(-((day - 7.5) / 1.3) ** 2)   # kuldeperiode midt i
    return base + 6 * math.sin(TAU * (h - 9) / 24)                                    # døgnsyklus


TEMPS = [_temp(i) for i in range(DAYS * 24 + 1)]   # timetemperaturer
THRESH = 10.0
STAGES = [("egg", 0.0), ("1st instar", 0.08), ("2nd instar", 0.18), ("3rd instar", 0.32),
          ("prepupa", 0.55), ("pupa", 0.70), ("adult", 0.92)]


def stage_icon(ctx, name, x, y, s=1.0, a=1.0, t=0.0):
    if name == "egg":
        for j in range(3):
            egg(ctx, x - 8 + j * 8, y + 2 * j, s * 1.2, 0.3, a)
    elif "instar" in name:
        n = int(name[0])
        larva(ctx, x, y, s * (18 + 14 * n), 0.2, a, t)
    elif name == "prepupa":
        larva(ctx, x, y, s * 58, 0.2, a, t, (0.9, 0.85, 0.7))
    elif name == "pupa":
        puparium(ctx, x, y, s * 0.9, a)
    else:
        fly(ctx, x, y, s * 1.1, FLY_COLS["vicina"], -0.3, t, a)


def degree_clock(ctx, t, prog, cx=820, cy=300, R=200, show_graph=True, a=1.0):
    """Klokke der visern drives av akkumulerte døgngrader (prog 0..1)."""
    rgba(ctx, (0.10, 0.10, 0.14), 0.9 * a); ctx.arc(cx, cy, R, 0, TAU); ctx.fill()
    rgba(ctx, (0.85, 0.75, 0.5), a); ctx.set_line_width(6); ctx.arc(cx, cy, R, 0, TAU); ctx.stroke()
    # fyllt bue = akkumulert
    rgba(ctx, (0.95, 0.55, 0.25), 0.35 * a); ctx.move_to(cx, cy); ctx.arc(cx, cy, R - 6, -math.pi / 2, -math.pi / 2 + TAU * prog); ctx.close_path(); ctx.fill()
    for name, f in STAGES:
        th = -math.pi / 2 + TAU * f * 0.999
        x, y = cx + (R - 48) * math.cos(th), cy + (R - 48) * math.sin(th)
        lit = 1.0 if prog >= f - 0.01 else 0.35
        stage_icon(ctx, name, x, y, 0.8, a * lit, t)
        text(ctx, name, cx + (R + 34) * math.cos(th), cy + (R + 34) * math.sin(th) + 5, 14, C["white"], a * (0.4 + 0.6 * lit), bold=lit > 0.5)
    th = -math.pi / 2 + TAU * prog
    rgba(ctx, C["hl"], a); ctx.set_line_width(7); ctx.move_to(cx, cy); ctx.line_to(cx + (R - 80) * math.cos(th), cy + (R - 80) * math.sin(th)); ctx.stroke()
    rgba(ctx, C["hl"], a); ctx.arc(cx, cy, 12, 0, TAU); ctx.fill()


def temp_graph(ctx, t, hours, x0=40, y0=260, w=420, h=200, a=1.0):
    """Temperaturkurve med terskel; arealet over terskelen = døgngrader."""
    rgba(ctx, (0, 0, 0), 0.4 * a); rrect(ctx, x0 - 15, y0 - 25, w + 30, h + 75, 14); ctx.fill()
    tmin, tmax = 0, 30
    def Y(v):
        return y0 + h - (v - tmin) / (tmax - tmin) * h
    n = int(hours)
    ctx.new_path()
    for i in range(n + 1):
        ctx.line_to(x0 + i / (DAYS * 24) * w, Y(max(THRESH, TEMPS[i])))
    for i in range(n, -1, -1):
        ctx.line_to(x0 + i / (DAYS * 24) * w, Y(THRESH))
    ctx.close_path(); rgba(ctx, (0.95, 0.55, 0.25), 0.55 * a); ctx.fill()
    ctx.new_path()
    for i in range(n + 1):
        ctx.line_to(x0 + i / (DAYS * 24) * w, Y(TEMPS[i]))
    rgba(ctx, (1, 0.85, 0.5), a); ctx.set_line_width(2.5); ctx.stroke()
    rgba(ctx, (0.6, 0.8, 1.0), a); ctx.set_line_width(2); ctx.set_dash([8, 6]); ctx.move_to(x0, Y(THRESH)); ctx.line_to(x0 + w, Y(THRESH)); ctx.stroke(); ctx.set_dash([])
    text(ctx, "threshold", x0 + w, Y(THRESH) + 18, 13, (0.6, 0.8, 1.0), a, align="right")
    text(ctx, "temperature", x0, y0 - 6, 14, (1, 0.85, 0.5), a, align="left", bold=True)
    add = sum(max(0, v - THRESH) for v in TEMPS[:n + 1]) / 24
    text(ctx, f"ADD: {add:5.1f} °C·days", x0 + w / 2, y0 + h + 36, 20, C["hl"], a, bold=True)
    if n < len(TEMPS) and TEMPS[min(n, len(TEMPS) - 1)] < THRESH:
        text(ctx, "below threshold: clock paused", x0 + w / 2, y0 + 22, 14, (0.6, 0.8, 1.0), a)
    return add


TOTAL_ADD = sum(max(0, v - THRESH) for v in TEMPS) / 24


def chorus_scene(ctx, t, key):
    sc, t1 = next((s for s in SCENES if s[0] == key)), None
    t0 = sc[1]
    t1 = SCENES[[s[0] for s in SCENES].index(key) + 1][1]
    bg(ctx, (0.12, 0.08, 0.06), (0.03, 0.02, 0.02))
    u = clamp((t - t0 - 0.5) / (t1 - t0 - 3.0))
    hours = u * DAYS * 24
    add = temp_graph(ctx, t, hours)
    degree_clock(ctx, t, add / TOTAL_ADD)
    glow(ctx, 820, 300, 230, (1, 0.7, 0.3), 0.08 * pulse(t))


def verse2_scene(ctx, t):
    bg(ctx, (0.10, 0.12, 0.10), (0.03, 0.04, 0.03))
    host(ctx, 300, 470, 420, 1.0)
    li = [L(2, i) for i in range(6)]
    # egg i et sår/åpning
    ea = smooth((t - li[0] + 0.3) / 0.8)
    for k in range(9):
        egg(ctx, 250 + (k % 3) * 14, 405 + (k // 3) * 8, 1.6, 0.4, ea * (1 - smooth((t - li[2]) / 1.0)))
    if ea > 0:
        text(ctx, "eggs", 270, 380, 16, C["white"], ea * (1 - smooth((t - li[2]) / 1.0)))
    glow(ctx, 270, 415, 50, (1, 1, 0.9), 0.3 * smooth((t - li[1]) / 0.8) * (1 - smooth((t - li[2]) / 1.0)))
    # instarer vokser fram til høyre
    rows = [(li[2], "1st instar", 55, 600), (li[3], "2nd instar", 120, 760), (li[4], "3rd instar", 260, 1040)]
    for ts, lab, ln, x in rows:
        a = smooth((t - ts + 0.3) / 0.8)
        grow = 1 + 0.15 * smooth((t - li[5]) / 3) if "3rd" in lab else 1
        larva(ctx, x, 330, ln * grow, -0.1, a, t)
        text(ctx, lab, x, 410, 18, C["white"], a, bold=True)
    if t > li[4]:
        text(ctx, "≈ 5 × longer than the 1st instar · does most of the feeding", 840, 470, 16, C["hl"], smooth((t - li[4]) / 1.0))
    # størrelseslinjal
    rgba(ctx, (1, 1, 1), 0.4); ctx.set_line_width(2); ctx.move_to(620, 380); ctx.line_to(1100, 380); ctx.stroke()


def inst_scene(ctx, t):
    sc = next(s for s in SCENES if s[0] == "inst"); t0 = sc[1]
    t1 = SCENES[[s[0] for s in SCENES].index("inst") + 1][1]
    bg(ctx, (0.06, 0.08, 0.14), (0.02, 0.02, 0.04))
    u = clamp((t - t0) / (t1 - t0 - 1))
    # årstidsfarge og dag/natt-syklus
    for k in range(int(u * 14) + 1):
        x = 470 + k * 52
        rgba(ctx, (1, 0.85, 0.4) if TEMPS[min(k * 24 + 12, len(TEMPS) - 1)] > THRESH + 6 else (0.6, 0.75, 1.0), 0.8)
        ctx.arc(x, 120, 14, 0, TAU); ctx.fill()
        text(ctx, f"day {k + 1}", x, 155, 12, C["white"], 0.7)
    add = temp_graph(ctx, t, u * DAYS * 24, x0=120, y0=210, w=1040, h=240)
    prog = add / TOTAL_ADD
    name = [n for n, f in STAGES if prog >= f - 0.01][-1]
    stage_icon(ctx, name, 1010, 492, 1.3, 1.0, t)
    text(ctx, name, 1080, 500, 20, C["hl"], 1, align="left", bold=True)


def bridge_scene(ctx, t):
    li = [L(4, i) for i in range(6)]
    cold = smooth((t - li[4] + 0.5) / 1.5)
    bg(ctx, mix((0.30, 0.38, 0.50), (0.18, 0.22, 0.30), cold), (0.10, 0.10, 0.12))
    # morgensol
    sy = lerp(330, 120, smooth((t - li[0]) / 10))
    glow(ctx, 1120, sy, 140, (1, 0.8, 0.5), 0.5 * (1 - cold)); rgba(ctx, (1, 0.85, 0.5), 1 - cold); ctx.arc(1120, sy, 34, 0, TAU); ctx.fill()
    gy = 330
    rgba(ctx, (0.15, 0.30, 0.15)); ctx.rectangle(0, gy - 10, W, 14); ctx.fill()
    g = cairo.LinearGradient(0, gy, 0, PANEL_Y)
    g.add_color_stop_rgb(0, 0.35, 0.24, 0.14); g.add_color_stop_rgb(1, 0.18, 0.11, 0.06)
    ctx.set_source(g); ctx.rectangle(0, gy + 4, W, PANEL_Y - gy); ctx.fill()
    for k in range(60):
        rgba(ctx, (0.1, 0.06, 0.03), 0.5); ctx.arc(PTS[k, 0] * W, gy + 20 + PTS[k, 1] * 220, 2 + 3 * PTS[k, 2], 0, TAU); ctx.fill()
    host(ctx, 260, gy, 300, 1.0)
    # prepupper vandrer bort og graver seg ned
    for k in range(6):
        start = li[1] - 0.5 + k * 0.6
        p = clamp((t - start) / 6)
        dig = clamp((t - li[2] - k * 0.4) / 3)
        x = lerp(330, 560 + k * 110, smooth(p))
        y = gy - 8 + dig * (60 + 40 * PTS[k, 0])
        if t > start:
            if t > li[3] + k * 0.5:
                puparium(ctx, x, y + 6, 0.7, smooth((t - li[3] - k * 0.5) / 1.0))
            else:
                larva(ctx, x, y, 46, 0.0 if dig < 0.05 else 1.2, 1.0, t, (0.9, 0.85, 0.7))
    if t > li[2] - 0.3:
        text(ctx, "most burrow into the soil to pupate", 880, 300, 18, C["white"], smooth((t - li[2] + 0.3) / 0.8), bold=True)
    # Protophormia forpupper seg på stedet
    if t > li[4] - 0.3:
        a = smooth((t - li[4] + 0.3) / 0.8)
        for j in range(4):
            puparium(ctx, 190 + j * 38, gy - 40 - 8 * math.sin(j), 0.55, a, (0.25, 0.20, 0.18))
        text(ctx, "Protophormia terraenovae", 260, 200, 18, (0.75, 0.85, 1.0), a, bold=True)
        text(ctx, "pupates on or beside the remains", 260, 224, 15, C["white"], a)
    if cold > 0:   # frost og regn
        for k in range(70):
            p = (t * (0.4 + 0.3 * PTS[k, 2]) + PTS[k, 1]) % 1.0
            x = PTS[k, 0] * W + 30 * p
            if k % 2:
                rgba(ctx, (0.7, 0.8, 1.0), 0.6 * cold); ctx.set_line_width(1.5); ctx.move_to(x, p * gy); ctx.line_to(x + 4, p * gy + 14); ctx.stroke()
            else:
                rgba(ctx, (1, 1, 1), 0.8 * cold); ctx.arc(x, p * gy, 2.5, 0, TAU); ctx.fill()


def outro_scene(ctx, t):
    sc = next(s for s in SCENES if s[0] == "outro"); t0 = sc[1]
    li = [L(6, i) for i in range(4)]
    bg(ctx, (0.30, 0.40, 0.55), (0.12, 0.10, 0.10))
    gy = 380
    rgba(ctx, (0.30, 0.22, 0.14)); ctx.rectangle(0, gy, W, PANEL_Y - gy); ctx.fill()
    grass(ctx, t, gy, 1.0, (0.20, 0.35, 0.20))
    crack = smooth((t - li[1]) / 2.0)
    puparium(ctx, 560, gy - 14, 2.4, 1.0, crack=crack)
    if t > li[1] + 1.0:
        e = smooth((t - li[1] - 1.0) / 2.0)
        wings = smooth((t - li[2]) / 3.0)
        fx = lerp(640, 680, e); fy = gy - 30
        fly_away = smooth((t - li[3]) / 3.0)
        fx += fly_away * 700; fy -= fly_away * 300
        fly(ctx, fx, fy, 3.0, FLY_COLS["vicina"], -0.2 - 0.4 * fly_away, t, e, wings=0.2 + 0.8 * wings if fly_away == 0 else 1.0)
        if 0 < wings < 1 and fly_away == 0:
            text(ctx, "wings expanding and hardening", 680, gy - 120, 17, C["white"], 0.9)
    a = smooth((t - LINES[-1]["t1"] - 1.0) / 2.5)
    if a > 0:
        text(ctx, "The Living Clock", 640, 160, 56, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "BiologyTunes", 640, 200, 22, C["hl"], a, bold=True)


# ------------------------------------------------------------------ tekst
def wrap(ctx, s, width, size):
    ctx.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL); ctx.set_font_size(size)
    out, cur = [], ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if ctx.text_extents(trial).x_advance > width and cur:
            out.append(cur); cur = w
        else:
            cur = trial
    return out + ([cur] if cur else [])


def fact_card(ctx, sc, t1, t):
    key, t0, label, title = sc
    a = smooth((t - t0 - 0.5) / 1.0) * (1 - smooth((t - t1 + 1.0) / 0.8))
    if a <= 0:
        return
    x, y, w = 20, 18, 380
    lines = wrap(ctx, FACTS[key], w - 28, 14.5)
    h = 66 + 20 * len(lines)
    rgba(ctx, (0, 0, 0), 0.58 * a); rrect(ctx, x, y, w, h, 14); ctx.fill()
    rgba(ctx, C["hl"], 0.7 * a); ctx.set_line_width(1.5); rrect(ctx, x, y, w, h, 14); ctx.stroke()
    text(ctx, label.upper(), x + 14, y + 24, 12.5, C["hl"], a, align="left", bold=True)
    text(ctx, title, x + 14, y + 48, 19, C["white"], a, align="left", bold=True)
    for i, l in enumerate(lines):
        text(ctx, l, x + 14, y + 72 + 20 * i, 14.5, (0.9, 0.92, 0.96), a, align="left")


def karaoke(ctx, l, t, size, y):
    ctx.select_font_face(LYRIC_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
    toks = l["text"].split()
    space = ctx.text_extents(" ").x_advance
    widths = [ctx.text_extents(w).x_advance for w in toks]
    x = 640 - (sum(widths) + space * (len(toks) - 1)) / 2
    wi, prev_end = 0, -1.0
    for tok, w in zip(toks, widths):
        if any(ch.isalnum() for ch in tok) and wi < len(l["words"]):
            wd = l["words"][wi]; wi += 1
            prog = clamp((t - wd["start"]) / max(0.08, wd["end"] - wd["start"])); prev_end = wd["end"]
        else:
            prog = 1.0 if t >= prev_end else 0.0
        ctx.move_to(x, y); rgba(ctx, (1, 1, 1), 0.92); ctx.show_text(tok)
        if prog > 0:
            ctx.save(); ctx.rectangle(x - 2, y - size, w * prog + 2, size * 1.5); ctx.clip()
            ctx.move_to(x, y); rgba(ctx, C["hl"]); ctx.show_text(tok); ctx.restore()
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
    prev = LINES[cur - 1] if cur > 0 and LINES[cur - 1]["sec"] == l["sec"] else None
    nxt = LINES[cur + 1] if cur + 1 < len(LINES) and LINES[cur + 1]["t0"] - l["t1"] < 3 else None
    if prev:
        text(ctx, prev["text"], 640, PANEL_Y + 26, 19, (0.65, 0.65, 0.72), 0.6, font=LYRIC_FONT)
    karaoke(ctx, l, t, 36, PANEL_Y + 78)
    if nxt:
        text(ctx, nxt["text"], 640, PANEL_Y + 122, 20, (0.7, 0.7, 0.78), 0.7, font=LYRIC_FONT)


# ------------------------------------------------------------------ ramme
def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    sc, t1 = scene_at(t)
    k = sc[0]
    if k == "intro":
        intro_scene(ctx, t)
    elif k == "verse1":
        verse1_scene(ctx, t)
    elif k in ("chorus1", "chorus2", "chorus3"):
        chorus_scene(ctx, t, k)
    elif k == "verse2":
        verse2_scene(ctx, t)
    elif k == "inst":
        inst_scene(ctx, t)
    elif k == "bridge":
        bridge_scene(ctx, t)
    else:
        outro_scene(ctx, t)
    for s in SCENES[1:]:
        d = t - s[1]
        if -0.3 < d < 0.3:
            rgba(ctx, (0, 0, 0), 0.6 * (1 - abs(d) / 0.3)); ctx.paint()
    if (k != "intro" or t > 22) and not (k == "outro" and t > LINES[-1]["t1"]):
        fact_card(ctx, sc, t1, t)
    lyric_panel(ctx, t)
    if t < 1.5:
        rgba(ctx, (0, 0, 0), 1 - t / 1.5); ctx.paint()
    if t > END - 4:
        rgba(ctx, (0, 0, 0), smooth((t - END + 4) / 4)); ctx.paint()
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
        os.path.join(HERE, "the-living-clock.mp4")], stdin=subprocess.PIPE)
    with Pool() as pool:
        for k, buf in enumerate(pool.imap(frame_bytes, range(n), chunksize=8)):
            ff.stdin.write(buf)
            if k % 1500 == 0:
                print(f"{k}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print("ferdig")


if __name__ == "__main__":
    main()
