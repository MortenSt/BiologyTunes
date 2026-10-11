"""Musikkvideo for «The Coffin Fly: The Navigator of the Grave».

Tekst-timing fra stable-ts (timing.json/words.json). Instrumentstammene (stem_features.json) styrer
grafikken: gitar-anslag = fluas rykkvise løp, bass = duftpuls, trommer/perkusjon = jord som drysser,
strykere = lys, korstemmer = glød i refrenget.

Bruk:  python3 make_video.py            -> the-coffin-fly.mp4
       python3 make_video.py 40 120     -> PNG-forhåndsvisning
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
PTS = np.random.default_rng(13).random((400, 3))

TIMING = json.load(open(os.path.join(HERE, "timing.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(HERE, "words.json"), encoding="utf-8"))
END = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            os.path.join(HERE, "audio.mp3")], capture_output=True, text=True).stdout)

# ---- instrumentstammer
_SF = json.load(open(os.path.join(HERE, "stem_features.json"), encoding="utf-8"))
SFPS = _SF["fps"]


def _stem(name):
    return next(v for k, v in _SF["stems"].items() if k.endswith(f"({name})"))


STEM = {n: _stem(n) for n in ("Guitar", "Bass", "Drums", "Percussion", "Strings", "Backing Vocals", "Synth")}
HITS = sorted(STEM["Drums"]["onsets"] + STEM["Percussion"]["onsets"])


def rms(name, t, smooth_s=0.25):
    r = STEM[name]["rms"]
    i = int(t * SFPS); n = max(1, int(smooth_s * SFPS))
    seg = r[max(0, i - n):i + 1] or [0]
    return sum(seg) / len(seg)


def onset_info(name, t):
    """(antall anslag før t, tid siden siste anslag)."""
    o = STEM[name]["onsets"] if name != "hits" else HITS
    i = bisect.bisect_right(o, t)
    return i, (t - o[i - 1]) if i else 99.0


# ---- linjer og scener
LINES = []
for k, s in enumerate(TIMING["sections"]):
    for i, ((a, b), txt) in enumerate(zip(s["lines"], s["texts"])):
        LINES.append(dict(text=txt, t0=a, t1=b, words=WORDS[len(LINES)]["words"], sec=k, idx=i))


def L(sec, i):
    return next(l for l in LINES if l["sec"] == sec and l["idx"] == i)["t0"]


SCENES = [
    ("intro", 0.0, "Intro", "Dusk"),
    ("verse1", L(0, 0) - 1.0, "Verse 1", "Conicera tibialis"),
    ("chorus1", L(1, 0) - 1.5, "Chorus", "Navigator of the grave"),
    ("verse2", L(2, 0) - 1.5, "Verse 2", "The scent of sulfur"),
    ("chorus2", L(3, 0) - 0.5, "Chorus", "A whisper through the clay"),
    ("bridge", L(4, 0) - 1.5, "Bridge", "An ancient skill"),
    ("chorus3", L(5, 0) - 0.3, "Chorus", "A promise kept"),
    ("outro", L(6, 0) - 2.0, "Outro", "The silent witness"),
]
FACTS = {
    "intro": ("The coffin fly, Conicera tibialis, is a tiny scuttle fly (family Phoridae) found in buried remains, "
              "sometimes a metre or more below ground."),
    "verse1": ("Phorids are 'scuttle flies': small, hump-backed and known for running in quick, jerky bursts. "
               "They can fly, but coffin flies often walk and crawl through soil instead."),
    "chorus1": ("Coffin flies can reach buried remains by moving down through cracks and pores in the soil, "
                "and can breed for several generations underground without returning to the surface."),
    "verse2": ("Decay releases sulfur compounds such as dimethyl trisulfide (DMTS), a well-known attractant for "
               "carrion insects. Exactly which cues coffin flies follow underground is still being studied."),
    "chorus2": ("In forensic cases, coffin flies are evidence that a body was buried, or that insects reached it "
                "after burial, which helps reconstruct what happened."),
    "bridge": ("Long before human burials, phorids like these likely exploited dead animals in burrows and other "
               "hidden, low-oxygen places. Graves are just a newer version of an old niche."),
    "chorus3": "Eggs, larvae and pupae can all develop in the dark, oxygen-poor space around buried remains.",
    "outro": "Generation after generation, the coffin fly's life cycle can turn without ever seeing daylight.",
}


def scene_at(t):
    cur = SCENES[0]
    for s in SCENES:
        if t >= s[1]:
            cur = s
    i = SCENES.index(cur)
    return cur, (SCENES[i + 1][1] if i + 1 < len(SCENES) else END)


def mix(a, b, x):
    return tuple(lerp(p, q, x) for p, q in zip(a, b))


def bg(ctx, top, bottom):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bottom)
    ctx.set_source(g); ctx.paint()


# ------------------------------------------------------------------ figurer
def phorid(ctx, x, y, s=1.0, facing=1, a=1.0, t=0.0, run=0.0):
    """Liten pukkelrygget phoride sett fra siden. run = 0..1 beinbevegelse."""
    ctx.save(); ctx.translate(x, y); ctx.scale(s * facing, s)
    leg = 6 * math.sin(run * TAU * 3)
    rgba(ctx, (0.30, 0.26, 0.22), a); ctx.set_line_width(1.6)
    for i, bx in enumerate((-4, 2, 8)):   # bein
        sw = leg * (1 if i % 2 else -1)
        ctx.move_to(bx, 4); ctx.line_to(bx - 6 + sw, 12); ctx.line_to(bx - 9 + sw, 18); ctx.stroke()
    g = cairo.LinearGradient(-16, -12, 14, 8)
    g.add_color_stop_rgba(0, 0.55, 0.48, 0.40, a); g.add_color_stop_rgba(1, 0.25, 0.21, 0.18, a)
    ctx.set_source(g)
    ellipse(ctx, -10, 3, 11, 6); ctx.fill()                     # bakkropp
    ctx.move_to(-4, 6); ctx.curve_to(-4, -14, 14, -14, 14, 4); ctx.close_path(); ctx.fill()   # pukkel (bryst)
    ellipse(ctx, 15, 6, 5, 4.5); ctx.fill()                     # hode, bøyd ned
    rgba(ctx, (0.6, 0.15, 0.1), a); ctx.arc(17, 5, 2.2, 0, TAU); ctx.fill()
    rgba(ctx, (0.85, 0.88, 0.95), 0.45 * a); ellipse(ctx, -12, -4, 13, 4); ctx.fill()   # vinger lagt over ryggen
    rgba(ctx, (0.35, 0.3, 0.25), a); ctx.set_line_width(1)
    for k in range(4):   # børster på pukkelen
        ctx.move_to(2 + k * 3, -8); ctx.line_to(3 + k * 3, -12); ctx.stroke()
    ctx.restore()


def coffin(ctx, cx, cy, w, a=1.0, glow_a=0.0):
    """Lukket trekiste sett fra siden – ingen innhold vises."""
    h = w * 0.28
    if glow_a > 0:
        glow(ctx, cx, cy, w * 0.8, (0.9, 0.75, 0.4), 0.25 * glow_a)
    g = cairo.LinearGradient(0, cy - h / 2, 0, cy + h / 2)
    g.add_color_stop_rgba(0, 0.45, 0.30, 0.18, a); g.add_color_stop_rgba(1, 0.25, 0.15, 0.08, a)
    ctx.set_source(g)
    ctx.move_to(cx - w / 2, cy - h * 0.2); ctx.line_to(cx - w * 0.30, cy - h / 2); ctx.line_to(cx + w / 2, cy - h / 2)
    ctx.line_to(cx + w / 2, cy + h / 2); ctx.line_to(cx - w * 0.30, cy + h / 2); ctx.line_to(cx - w / 2, cy + h * 0.2)
    ctx.close_path(); ctx.fill()
    rgba(ctx, (0.15, 0.09, 0.05), a); ctx.set_line_width(2)
    ctx.move_to(cx - w * 0.45, cy - h * 0.12); ctx.line_to(cx + w / 2, cy - h * 0.12); ctx.stroke()   # lokk-fuge
    for k in range(3):
        rgba(ctx, (0.7, 0.6, 0.4), 0.6 * a); ctx.arc(cx - w * 0.2 + k * w * 0.25, cy - h * 0.12, 2.5, 0, TAU); ctx.fill()


def soil(ctx, t, top, a=1.0, shake=0.0):
    layers = [(0.36, 0.25, 0.16), (0.30, 0.20, 0.13), (0.24, 0.16, 0.10), (0.18, 0.12, 0.08)]
    hh = (PANEL_Y - top) / len(layers)
    for i, col in enumerate(layers):
        rgba(ctx, col, a); ctx.rectangle(0, top + i * hh, W, hh + 1); ctx.fill()
    for k in range(180):   # småstein og korn
        x = PTS[k, 0] * W + shake * 2 * math.sin(k * 7.1)
        y = top + 10 + PTS[k, 1] * (PANEL_Y - top - 20)
        rgba(ctx, (0.12 + 0.2 * PTS[k, 2], 0.09 + 0.12 * PTS[k, 2], 0.06), 0.8 * a)
        ctx.arc(x, y, 1.5 + 4 * PTS[k + 1, 2] ** 2, 0, TAU); ctx.fill()
    # gress og overflate
    rgba(ctx, (0.18, 0.30, 0.16), a); ctx.rectangle(0, top - 6, W, 8); ctx.fill()
    for k in range(120):
        x = PTS[k + 100, 0] * W; hgt = 10 + 20 * PTS[k + 100, 1]
        rgba(ctx, (0.25, 0.40, 0.20), a); ctx.set_line_width(2)
        ctx.move_to(x, top - 2); ctx.line_to(x + 4 * math.sin(t + k), top - 2 - hgt); ctx.stroke()


def crumbs(ctx, t, top, a=1.0):
    """Jord som drysser ved trommeslag."""
    n, dt = onset_info("hits", t)
    for j in range(3):
        i = n - 1 - j
        if i < 0:
            continue
        age = t - HITS[i]
        if age > 1.2:
            continue
        for k in range(6):
            x = (PTS[(i * 7 + k) % 400, 0] * W)
            y = top + 20 + PTS[(i * 3 + k) % 400, 1] * 200 + 160 * age * age
            rgba(ctx, (0.55, 0.42, 0.28), (1 - age / 1.2) * a); ctx.arc(x, y, 2 + PTS[k, 2] * 2, 0, TAU); ctx.fill()


def scent(ctx, t, x0, y0, x1, y1, a=1.0):
    """Duftmolekyler som siver fra kisten opp gjennom jorda; pulserer med bassen."""
    b = rms("Bass", t, 0.15)
    for k in range(40):
        p = (t * 0.06 + PTS[k + 200, 0]) % 1.0
        x = lerp(x0, x1, p) + 60 * math.sin(p * 9 + k) * (0.3 + p)
        y = lerp(y0, y1, p)
        al = math.sin(p * math.pi) * (0.35 + 0.65 * b) * a
        rgba(ctx, (0.35, 0.95, 0.88), al); ctx.arc(x, y, 3 + 2 * b, 0, TAU); ctx.fill()
        glow(ctx, x, y, 10 + 8 * b, (0.3, 1.0, 0.9), 0.25 * al)


def hop_pos(t, path, t0, t1):
    """Fluas posisjon langs en sti: den flytter seg rykkvis på gitar-anslag."""
    o = STEM["Guitar"]["onsets"]
    i0 = bisect.bisect_left(o, t0); i1 = max(i0 + 1, bisect.bisect_left(o, t1))
    n, dt = onset_info("Guitar", t)
    hops = clamp(n - i0, 0, i1 - i0)
    frac = (hops - (1 - smooth(min(1, dt / 0.18))) if 0 < hops < (i1 - i0) else hops) / (i1 - i0)
    frac = clamp(frac)
    seg = frac * (len(path) - 1); j = min(int(seg), len(path) - 2); f = seg - j
    x = lerp(path[j][0], path[j + 1][0], f); y = lerp(path[j][1], path[j + 1][1], f)
    facing = 1 if path[j + 1][0] >= path[j][0] else -1
    running = 1 - smooth(min(1, dt / 0.25))
    return x, y, facing, running


def dmts(ctx, x, y, s=1.0, a=1.0):
    """CH3–S–S–S–CH3"""
    atoms = [(-2, 0.4, "C", (0.3, 0.3, 0.32)), (-1, -0.3, "S", (0.95, 0.85, 0.2)), (0, 0.3, "S", (0.95, 0.85, 0.2)),
             (1, -0.3, "S", (0.95, 0.85, 0.2)), (2, 0.4, "C", (0.3, 0.3, 0.32))]
    rgba(ctx, (1, 1, 1), 0.7 * a); ctx.set_line_width(4 * s)
    for (xa, ya, _, _), (xb, yb, _, _) in zip(atoms, atoms[1:]):
        ctx.move_to(x + xa * 40 * s, y + ya * 40 * s); ctx.line_to(x + xb * 40 * s, y + yb * 40 * s); ctx.stroke()
    for xa, ya, lab, col in atoms:
        rgba(ctx, col, a); ctx.arc(x + xa * 40 * s, y + ya * 40 * s, 15 * s, 0, TAU); ctx.fill()
        text(ctx, lab, x + xa * 40 * s, y + ya * 40 * s + 6 * s, 16 * s, (0.1, 0.1, 0.1) if lab == "S" else C["white"], a, bold=True)
    text(ctx, "dimethyl trisulfide (DMTS)", x, y + 55 * s, 16 * s, C["white"], a, bold=True)
    text(ctx, "CH₃–S–S–S–CH₃", x, y + 78 * s, 14 * s, (0.9, 0.85, 0.6), a)


def eggs_cluster(ctx, x, y, n, a=1.0):
    for k in range(n):
        rgba(ctx, (0.97, 0.96, 0.9), a)
        ctx.save(); ctx.translate(x + (k % 5) * 9 - 18, y + (k // 5) * 6); ctx.rotate(0.3)
        ellipse(ctx, 0, 0, 4, 1.6); ctx.fill(); ctx.restore()


# ------------------------------------------------------------------ scener
def dusk_sky(ctx, t):
    bg(ctx, (0.10, 0.10, 0.20), (0.25, 0.18, 0.22))
    for k in range(50):
        rgba(ctx, (1, 1, 1), 0.5 * PTS[k, 2]); ctx.arc(PTS[k, 0] * W, PTS[k, 1] * 220, 1.2, 0, TAU); ctx.fill()
    glow(ctx, 1050, 160, 160, (0.9, 0.8, 0.9), 0.25 + 0.2 * rms("Strings", t, 1.0))
    rgba(ctx, (0.92, 0.9, 0.85)); ctx.arc(1050, 160, 34, 0, TAU); ctx.fill()


def gravestone(ctx, gy):
    """Gravstein rett over kista (x = 640), følger bakkenivået når kameraet glir ned."""
    rgba(ctx, (0.30, 0.30, 0.34)); ctx.move_to(600, gy); ctx.line_to(600, gy - 90); ctx.arc(640, gy - 90, 40, math.pi, 0); ctx.line_to(680, gy); ctx.fill()


def intro_scene(ctx, t):
    dusk_sky(ctx, t)
    gy = 430
    # trær og en enkel, gammel gravstein i silhuett
    for k, x in enumerate((120, 260, 980, 1160)):
        rgba(ctx, (0.06, 0.06, 0.09)); ctx.rectangle(x - 8, gy - 160, 16, 160); ctx.fill()
        ctx.arc(x, gy - 190, 70 + 15 * PTS[k, 0], 0, TAU); ctx.fill()
    gravestone(ctx, gy)
    soil(ctx, t, gy, 1.0)
    a = smooth((t - 2) / 2) * (1 - smooth((t - 13) / 2))
    if a > 0:
        rgba(ctx, (0, 0, 0), 0.4 * a); ctx.rectangle(0, 220, W, 160); ctx.fill()
        text(ctx, "The Coffin Fly", 640, 300, 62, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "The Navigator of the Grave", 640, 348, 26, C["hl"], a)


def verse1_scene(ctx, t):
    li = [L(0, i) for i in range(8)]
    sink = smooth((t - li[6]) / 6.0)   # kameraet glir ned under bakken mot slutten
    dusk_sky(ctx, t)
    gy = lerp(430, 120, sink)
    gravestone(ctx, gy)
    soil(ctx, t, gy, 1.0, rms("Drums", t, 0.1))
    crumbs(ctx, t, gy)
    # stor nærbilde-flue som løper rykkvis på gitarnappene
    path = [(150, gy - 30), (420, gy - 30), (700, gy - 30), (980, gy - 30), (1100, gy - 30)] if sink < 0.5 else \
           [(980, gy - 20), (1000, gy + 60), (960, gy + 160), (1000, gy + 260)]
    x, y, facing, run = hop_pos(t, path, li[0], li[6] if sink < 0.5 else li[7] + 4)
    phorid(ctx, x, y, 4.0 - 1.5 * sink, facing, 1.0, t, run * t * 4)
    if li[2] - 0.3 < t < li[4]:
        a = smooth((t - li[2] + 0.3) / 0.6) * (1 - smooth((t - li[4] + 0.6) / 0.6))
        badge(ctx, "Phoridae · scuttle flies · ~4,000 species", 800, 110, a, C["hl"], 18)
    if li[3] - 0.3 < t < li[5]:
        a = smooth((t - li[3] + 0.3) / 0.6) * (1 - smooth((t - li[5] + 0.6) / 0.6))
        badge(ctx, "runs in short, jerky bursts", 800, 170, a, (0.8, 0.9, 1.0), 17)
    if t > li[6] - 0.3:
        a = smooth((t - li[6] + 0.3) / 1.0)
        coffin(ctx, 640, lerp(700, 470, sink), 360, a, rms("Strings", t))


def underground(ctx, t, depth_top=120, coffin_y=470, show_scent=True, glow_vox=True):
    bg(ctx, (0.08, 0.06, 0.07), (0.03, 0.02, 0.02))
    soil(ctx, t, depth_top, 1.0, rms("Drums", t, 0.1))
    crumbs(ctx, t, depth_top)
    gv = rms("Backing Vocals", t, 0.5) if glow_vox else 0
    coffin(ctx, 640, coffin_y, 380, 1.0, 0.4 + 0.6 * max(gv, rms("Strings", t, 0.5)))
    if show_scent:
        scent(ctx, t, 640, coffin_y - 50, 640, depth_top + 10)
    # dybdemåler
    rgba(ctx, (1, 1, 1), 0.5); ctx.set_line_width(2); ctx.move_to(1210, depth_top); ctx.line_to(1210, coffin_y); ctx.stroke()
    for k, lab in enumerate(("0 m", "0.5 m", "1 m", "1.5 m")):
        y = lerp(depth_top, coffin_y - 40, k / 3)
        ctx.move_to(1200, y); ctx.line_to(1220, y); ctx.stroke()
        text(ctx, lab, 1195, y + 5, 13, C["white"], 0.7, align="right")


def chorus_scene(ctx, t, key):
    sc = next(s for s in SCENES if s[0] == key); t0 = sc[1]
    t1 = SCENES[[s[0] for s in SCENES].index(key) + 1][1]
    underground(ctx, t)
    # flua navigerer ned langs duftsporet i sikksakk
    path = [(300 + 140 * math.sin(k * 1.3), 140 + k * 45) for k in range(7)] + [(560, 410)]
    x, y, facing, run = hop_pos(t, path, t0 + 0.5, t1 - 4)
    phorid(ctx, x, y, 1.8, facing, 1.0, t, run * t * 4)
    # «A promise that my young will keep»: egg ved kistelokket
    sec = {"chorus1": 1, "chorus2": 3, "chorus3": 5}[key]
    lp = L(sec, 5)
    if t > lp - 0.5:
        a = smooth((t - lp + 0.5) / 1.0)
        eggs_cluster(ctx, 560, 432, int(5 + 10 * a), a)
        text(ctx, "eggs", 560, 470, 14, C["white"], a)


def verse2_scene(ctx, t):
    li = [L(2, i) for i in range(8)]
    underground(ctx, t, show_scent=t > li[1] - 0.5)
    if li[2] - 0.3 < t < li[4] + 0.5:
        a = smooth((t - li[2] + 0.3) / 0.8) * (1 - smooth((t - li[4]) / 0.5))
        rgba(ctx, (0, 0, 0), 0.55 * a); rrect(ctx, 760, 150, 380, 220, 18); ctx.fill()
        dmts(ctx, 950, 230, 1.1, a)
    # graving: flua går ned gjennom jorda, dybden teller opp
    if t > li[4] - 0.5:
        x, y, facing, run = hop_pos(t, [(250, 140), (300, 230), (240, 320), (320, 400), (470, 420)], li[4] - 0.5, li[6])
        phorid(ctx, x, y, 2.0, facing, 1.0, t, run * t * 4)
        rgba(ctx, (0.15, 0.10, 0.06), 0.8); ctx.set_line_width(14)
        ctx.move_to(250, 140); ctx.line_to(x, y); ctx.stroke()   # tunnel bak flua
        depth = lerp(0, 1.5, clamp((y - 140) / 280))
        badge(ctx, f"depth ≈ {depth:.1f} m", 900, 250, smooth((t - li[4]) / 0.6), C["hl"], 18)
    if t > li[6] - 0.3:   # lite oksygen
        a = smooth((t - li[6] + 0.3) / 0.8)
        o2 = lerp(21, 5, smooth((t - li[6]) / 4))
        rgba(ctx, (0, 0, 0), 0.5 * a); rrect(ctx, 820, 300, 300, 60, 12); ctx.fill()
        rgba(ctx, (0.4, 0.7, 1.0), a); rrect(ctx, 835, 330, 270 * o2 / 21, 18, 8); ctx.fill()
        text(ctx, f"O₂ ≈ {o2:.0f}%", 970, 322, 16, C["white"], a, bold=True)
        eggs_cluster(ctx, 520, 432, int(12 * smooth((t - li[6] - 1) / 2)), a)


def bridge_scene(ctx, t):
    li = [L(4, i) for i in range(8)]
    dusk_sky(ctx, t)
    gy = 200
    soil(ctx, t, gy, 1.0, rms("Drums", t, 0.1))
    # grevlinghi og revehi: tunneler med kamre
    for cx, name, ts in ((380, "badger's burrow", li[4]), (900, "fox's den", li[4] + 1.2)):
        a = smooth((t - ts + 0.5) / 1.0)
        rgba(ctx, (0.08, 0.05, 0.03), a); ctx.set_line_width(34)
        ctx.move_to(cx - 120, gy); ctx.curve_to(cx - 80, gy + 120, cx + 40, gy + 120, cx + 40, gy + 220); ctx.stroke()
        ellipse(ctx, cx + 60, gy + 250, 90, 45); ctx.fill()
        rgba(ctx, (0.5, 0.42, 0.35), 0.8 * a); ellipse(ctx, cx + 60, gy + 262, 40, 14); ctx.fill()   # gammelt bein-/hårrest, abstrakt
        text(ctx, name, cx + 60, gy + 330, 17, C["white"], a, bold=True)
        if t > ts:
            x, y, facing, run = hop_pos(t, [(cx - 120, gy), (cx - 60, gy + 90), (cx + 30, gy + 160), (cx + 50, gy + 240)], ts, ts + 8)
            phorid(ctx, x, y, 1.5, facing, a, t, run * t * 4)
    # tidslinje: lenge før menneskelige begravelser
    if t < li[4] - 0.5 or t > li[6] - 0.5:
        a = smooth((t - li[0]) / 1.0) if t < li[4] else smooth((t - li[6] + 0.5) / 1.0)
        x0, x1, y = 440, 1220, 60
        rgba(ctx, (0, 0, 0), 0.45 * a); rrect(ctx, x0 - 20, y - 30, x1 - x0 + 40, 80, 14); ctx.fill()
        rgba(ctx, C["white"], 0.8 * a); ctx.set_line_width(3); ctx.move_to(x0, y); ctx.line_to(x1, y); ctx.stroke()
        for f, lab in ((0.05, "dead animals in burrows: ancient"), (0.85, "human burials"), (1.0, "today")):
            x = lerp(x0, x1, f); rgba(ctx, C["white"], a); ctx.arc(x, y, 5, 0, TAU); ctx.fill()
            text(ctx, lab, x, y + 28, 13, C["white"], a, align="left" if f < 0.5 else ("right" if f == 1.0 else "center"))
        glow(ctx, lerp(x0, x1, 0.05), y, 30, C["hl"], 0.6 * a)


def outro_scene(ctx, t):
    sc = next(s for s in SCENES if s[0] == "outro"); t0 = sc[1]
    underground(ctx, t, show_scent=True, glow_vox=False)
    # syklus: egg -> larve -> puppe -> flue rundt kisten
    cx, cy, R = 640, 470, 210
    for k in range(6):
        th = (t - t0) * 0.25 + k * TAU / 6
        x, y = cx + R * math.cos(th), cy - 40 + 0.45 * R * math.sin(th)
        st = k % 3
        if st == 0:
            eggs_cluster(ctx, x, y, 5)
        elif st == 1:
            rgba(ctx, (0.95, 0.93, 0.85)); ellipse(ctx, x, y, 14, 5); ctx.fill()
        else:
            phorid(ctx, x, y, 1.2, 1 if math.cos(th) < 0 else -1, 1.0, t, 0)
    a = smooth((t - LINES[-1]["t1"] - 0.5) / 2.5)
    if a > 0:
        rgba(ctx, (0, 0, 0), 0.5 * a); ctx.rectangle(0, 200, W, 150); ctx.fill()
        text(ctx, "The Coffin Fly", 640, 280, 56, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "BiologyTunes", 640, 322, 22, C["hl"], a, bold=True)


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
    rgba(ctx, (0, 0, 0), 0.6 * a); rrect(ctx, x, y, w, h, 14); ctx.fill()
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
    tot = sum(widths) + space * (len(toks) - 1)
    if tot > W - 80:
        return karaoke(ctx, l, t, size * (W - 80) / tot, y)
    x = 640 - tot / 2
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
    elif k.startswith("chorus"):
        chorus_scene(ctx, t, k)
    elif k == "verse2":
        verse2_scene(ctx, t)
    elif k == "bridge":
        bridge_scene(ctx, t)
    else:
        outro_scene(ctx, t)
    for s in SCENES[1:]:
        d = t - s[1]
        if -0.3 < d < 0.3:
            rgba(ctx, (0, 0, 0), 0.6 * (1 - abs(d) / 0.3)); ctx.paint()
    if (k != "intro" or t > 2.5) and not (k == "outro" and t > LINES[-1]["t1"]):
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
        os.path.join(HERE, "the-coffin-fly.mp4")], stdin=subprocess.PIPE)
    with Pool() as pool:
        for k, buf in enumerate(pool.imap(frame_bytes, range(n), chunksize=8)):
            ff.stdin.write(buf)
            if k % 1500 == 0:
                print(f"{k}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print("ferdig")


if __name__ == "__main__":
    main()
