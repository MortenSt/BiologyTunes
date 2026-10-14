"""Musikkvideo for «Secrets of the Female Body».

Skjematiske lærebok-diagrammer (ikke realistiske) av ytre og indre kjønnsorganer, menstruasjonssyklus og
eggstokk. Tekst-timing fra stable-ts (timing.json/words.json). Instrumentstammene (stem_features.json) styrer
grafikken: trommer/perkusjon = små lyspartikler og etiketter som spretter, bass = puls i markert organ,
strykere = bakgrunnslys, keyboard = nervesignaler, korstemmer = ekko-tekst.

Bruk:  python3 make_video.py            -> secrets-of-the-female-body.mp4
       python3 make_video.py 40 120     -> PNG-forhåndsvisning
"""
import bisect
import json
import math
import os
import re
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
PTS = np.random.default_rng(7).random((400, 3))
OUT = "secrets-of-the-female-body.mp4"

TIMING = json.load(open(os.path.join(HERE, "timing.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(HERE, "words.json"), encoding="utf-8"))
END = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            os.path.join(HERE, "audio.mp3")], capture_output=True, text=True).stdout)

# ---- instrumentstammer
_SF = json.load(open(os.path.join(HERE, "stem_features.json"), encoding="utf-8"))
SFPS = _SF["fps"]
STEM = {k.split(" ", 1)[1]: v for k, v in _SF["stems"].items()}
HITS = sorted(STEM["Drums"]["onsets"] + STEM["Percussion"]["onsets"])


def rms(name, t, smooth_s=0.25):
    r = STEM[name]["rms"]
    i = int(t * SFPS); n = max(1, int(smooth_s * SFPS))
    seg = r[max(0, i - n):i + 1] or [0]
    return sum(seg) / len(seg)


def onset_info(name, t):
    o = STEM[name]["onsets"] if name != "hits" else HITS
    i = bisect.bisect_right(o, t)
    return i, (t - o[i - 1]) if i else 99.0


# ---- linjer: hovedtekst + ekko i parentes (synges etter linja)
LINES = []
for k, s in enumerate(TIMING["sections"]):
    for i, ((a, b), txt) in enumerate(zip(s["lines"], s["texts"])):
        m = re.search(r"\(([^)]*)\)", txt)
        main = re.sub(r"\s*\([^)]*\)", "", txt).strip().rstrip(",.")
        LINES.append(dict(text=main, echo=m.group(1) if m else None, t0=a, t1=b,
                          words=WORDS[len(LINES)]["words"], sec=k, idx=i))
for i, l in enumerate(LINES):
    nxt = LINES[i + 1]["t0"] if i + 1 < len(LINES) else END
    l["e1"] = min(nxt - 0.3, l["t1"] + 4.5) if l["echo"] else l["t1"]


def ws(li, word):
    """Starttid for første ord i linje li som begynner med word."""
    return next(w["start"] for w in LINES[li]["words"] if w["w"].lower().startswith(word.lower()))


SCENES = [
    ("v1a", 0.0, "Verse 1", "The vulva"),
    ("v1b", 13.3, "Verse 1", "The clitoris"),
    ("pc1", LINES[4]["t0"] - 1.0, "Pre-Chorus", "Outside and inside"),
    ("ch1", LINES[6]["t0"] - 1.0, "Chorus", "From vulva to ovaries"),
    ("v2a", LINES[10]["t0"] - 0.6, "Verse 2", "Vagina and cervix"),
    ("v2b", LINES[12]["t0"] - 1.0, "Verse 2", "Uterus and fallopian tubes"),
    ("pc2", LINES[14]["t0"] - 1.0, "Pre-Chorus", "The pelvic floor"),
    ("ch2", LINES[16]["t0"] - 1.0, "Chorus", "The egg's journey"),
    ("br1", LINES[20]["t0"] - 1.0, "Bridge", "The ovaries"),
    ("br2", LINES[22]["t0"] - 1.0, "Bridge", "The menstrual cycle"),
    ("v3", LINES[24]["t0"] - 0.8, "Verse 3", "Bartholin's glands"),
    ("pc3", LINES[28]["t0"] - 1.0, "Pre-Chorus", "Health checks"),
    ("ch3", LINES[30]["t0"] - 1.0, "Chorus", "Use the real words"),
    ("outro", LINES[34]["t0"] - 0.4, "Outro", "Respect"),
]
FACTS = {
    "v1a": ("The vulva is the outer part: the mons pubis, labia majora and minora, clitoris, and the openings "
            "of the urethra and vagina. Every vulva looks different, and that variation is normal."),
    "v1b": ("Only the tip (glans) of the clitoris is visible. Its body, two crura and the vestibular bulbs lie "
            "inside, roughly 10 cm in total. A 2022 study counted about 10,000 nerve fibres in its main nerve."),
    "pc1": ("The vulva is outside. The vagina, cervix, uterus, fallopian tubes and ovaries are inside. "
            "'Vagina' is often used for everything, but it is only the inner canal."),
    "ch1": ("The ovaries store eggs and make hormones, the tubes carry the egg, the uterus can carry a "
            "pregnancy, and the vagina connects the uterus to the outside."),
    "v2a": ("The vagina is an elastic, muscular canal, roughly 7–10 cm long at rest. The cervix is the lower "
            "'neck' of the uterus; its small opening lets menstrual blood out and sperm in."),
    "v2b": ("The uterus is about the size of a small pear, with a thick muscular wall. Fertilization usually "
            "happens in a fallopian tube, and an embryo implants in the uterine lining about a week later."),
    "pc2": ("The pelvic floor is a sling of muscles that supports the bladder, uterus and bowel. "
            "Like other muscles, it can be trained."),
    "ch2": ("Tiny hair-like cilia and gentle muscle contractions move the egg along the fallopian tube "
            "towards the uterus over a few days."),
    "br1": ("A person is born with all their egg cells: 1–2 million at birth, about 300,000–400,000 by "
            "puberty. Only around 400–500 are released in a lifetime."),
    "br2": ("Estrogen builds up the uterine lining; after ovulation, progesterone maintains it. Without a "
            "pregnancy, hormone levels fall and the lining is shed as a period. 28 days is an average: "
            "about 21–35 days is normal in adults."),
    "v3": ("Bartholin's glands are two pea-sized glands beside the vaginal opening that release a little "
           "fluid. Most lubrication during arousal actually seeps through the vaginal walls as blood flow increases."),
    "pc3": ("Cervical screening finds early cell changes before they become cancer, and the HPV vaccine "
            "protects against the virus behind most cervical cancers."),
    "ch3": ("Knowing the correct names for body parts makes it easier to talk to a doctor, and to notice "
            "when something is not right."),
    "outro": ("Every body is different. Understanding how bodies work, and respecting other people's "
              "bodies and boundaries, is part of good health."),
}


def scene_at(t):
    cur = SCENES[0]
    for s in SCENES:
        if t >= s[1]:
            cur = s
    i = SCENES.index(cur)
    return cur, (SCENES[i + 1][1] if i + 1 < len(SCENES) else END)


def hi(t, t0, t1, tail=1.2):
    """Markering: tones inn ved t0, holdes til t1, tones ut etter."""
    return smooth((t - t0 + 0.25) / 0.4) * (1 - smooth((t - t1 - tail) / 0.8))


def on(t, t0, d=0.5):
    return smooth((t - t0) / d)


# ------------------------------------------------------------------ farger
COL = dict(
    wall=(0.93, 0.56, 0.60), wall_d=(0.70, 0.33, 0.40), lining=(0.78, 0.22, 0.32),
    cervix=(0.88, 0.48, 0.55), vagina=(0.86, 0.50, 0.60), canal=(0.55, 0.22, 0.32),
    tube=(0.95, 0.66, 0.62), ovary=(0.98, 0.84, 0.72), follicle=(1.0, 0.95, 0.80),
    majora=(0.62, 0.43, 0.56), minora=(0.80, 0.50, 0.62), vest=(0.96, 0.78, 0.82), hole=(0.32, 0.14, 0.24),
    clit=(0.98, 0.45, 0.70), bulb=(0.85, 0.40, 0.75), gland=(0.55, 0.85, 0.95),
    estro=(1.0, 0.55, 0.75), prog=(0.55, 0.75, 1.0), lh=(1.0, 0.85, 0.35), muscle=(0.85, 0.40, 0.40),
    label=(0.92, 0.93, 0.97),
)


def bg(ctx, t):
    s = rms("Strings", t, 1.0)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.10 + 0.04 * s, 0.07, 0.17 + 0.04 * s)
    g.add_color_stop_rgb(1, 0.04, 0.03, 0.09)
    ctx.set_source(g); ctx.paint()
    for k in range(40):   # rolige lysprikker
        x = (PTS[k, 0] * W + t * 6 * (PTS[k, 2] - 0.5)) % W
        y = (PTS[k, 1] * PANEL_Y - t * 4 * PTS[k + 40, 2]) % PANEL_Y
        glow(ctx, x, y, 14 + 10 * PTS[k, 2], (0.9, 0.6, 0.85), 0.05 + 0.05 * s)


def sparkles(ctx, t, cx, cy, spread=360, col=(1.0, 0.8, 0.9)):
    """Lyspartikler som sprer seg ut på trommeslag."""
    n, _ = onset_info("hits", t)
    for j in range(4):
        i = n - 1 - j
        if i < 0:
            continue
        age = t - HITS[i]
        if age > 1.0:
            continue
        for k in range(8):
            ang = TAU * PTS[(i * 11 + k) % 400, 0]
            r = spread * (0.3 + 0.7 * PTS[(i * 5 + k) % 400, 1]) * smooth(age / 1.0)
            glow(ctx, cx + r * math.cos(ang), cy + r * math.sin(ang) * 0.6, 8, col, 0.5 * (1 - age))


def label(ctx, ax, ay, lx, ly, s, a, col=COL["label"], size=16, hl=0.0):
    if a <= 0:
        return
    c = tuple(lerp(p, q, hl) for p, q in zip(col, C["hl"]))
    rgba(ctx, c, 0.7 * a); ctx.set_line_width(1.3)
    ctx.move_to(ax, ay); ctx.line_to(lx, ly); ctx.stroke()
    ctx.arc(ax, ay, 2.5, 0, TAU); ctx.fill()
    align = "left" if lx >= ax else "right"
    text(ctx, s, lx + (6 if align == "left" else -6), ly + 5, size, c, a, align=align, bold=hl > 0.5)


def outline_hl(ctx, path_fn, h, width=3.0):
    if h <= 0:
        return
    path_fn(); rgba(ctx, C["hl"], 0.25 * h); ctx.set_line_width(width * 4); ctx.stroke()
    path_fn(); rgba(ctx, C["hl"], 0.9 * h); ctx.set_line_width(width); ctx.stroke()


# ------------------------------------------------------------------ indre organer (frontalsnitt, skjematisk)
def internal(ctx, cx, cy, s, t, h=None, lining=0.6, a=1.0, labels=None, egg=None, floor=0.0, pulse=0.0):
    """h: {del: markering}. labels: {del: alfa}. egg: (side, p 0..1 langs tuben) eller None."""
    h = h or {}; labels = labels or {}
    b = rms("Bass", t, 0.2) * pulse
    ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s)
    ctx.push_group()

    def p_vagina():
        ctx.move_to(-26, 60); ctx.curve_to(-30, 110, -34, 150, -32, 190)
        ctx.line_to(32, 190); ctx.curve_to(34, 150, 30, 110, 26, 60); ctx.close_path()

    def p_uterus():
        ctx.move_to(-24, 70); ctx.line_to(-28, 22)
        ctx.curve_to(-60, 0, -82, -50, -80, -85); ctx.curve_to(-78, -125, -30, -128, 0, -122)
        ctx.curve_to(30, -128, 78, -125, 80, -85); ctx.curve_to(82, -50, 60, 0, 28, 22)
        ctx.line_to(24, 70); ctx.close_path()

    def p_cervix():
        ctx.move_to(-28, 26); ctx.line_to(-24, 72); ctx.line_to(24, 72); ctx.line_to(28, 26); ctx.close_path()

    def p_tube(sd):
        ctx.move_to(sd * 72, -100)
        ctx.curve_to(sd * 120, -128, sd * 170, -142, sd * 205, -118)
        ctx.curve_to(sd * 226, -102, sd * 232, -84, sd * 226, -66)

    def p_ovary(sd):
        ellipse(ctx, sd * 172, -44, 32, 20)

    def p_lining():
        w = 0.55 + 0.45 * lining
        ctx.save(); ctx.scale(w, 1)
        ctx.move_to(-56, -100); ctx.curve_to(-20, -108, 20, -108, 56, -100); ctx.line_to(0, 24); ctx.close_path()
        ctx.restore()

    # bekkenbunn (hengekøye under)
    if floor > 0:
        sag = 30 - 14 * b
        ctx.move_to(-230, 120); ctx.curve_to(-120, 120 + sag * 2, 120, 120 + sag * 2, 230, 120)
        rgba(ctx, COL["muscle"], 0.85 * floor); ctx.set_line_width(22); ctx.stroke()
        for k in range(-9, 10):   # muskelfibre
            x = k * 22
            yy = 120 + sag * 2 * (1 - (x / 230) ** 2) * 0.75
            rgba(ctx, (0.6, 0.22, 0.25), 0.6 * floor); ctx.set_line_width(1.5)
            ctx.move_to(x - 6, yy - 8); ctx.line_to(x + 6, yy + 8); ctx.stroke()
    # vagina
    p_vagina(); rgba(ctx, COL["vagina"]); ctx.fill()
    ctx.move_to(-12, 72); ctx.curve_to(-14, 120, -15, 160, -14, 190); ctx.line_to(14, 190)
    ctx.curve_to(15, 160, 14, 120, 12, 72); ctx.close_path(); rgba(ctx, COL["canal"], 0.8); ctx.fill()
    for k in range(7):   # rugae (folder)
        y = 90 + k * 14
        rgba(ctx, (0.65, 0.3, 0.4), 0.7); ctx.set_line_width(1.2)
        ctx.move_to(-24, y); ctx.curve_to(-18, y + 4, -14, y - 3, -12, y); ctx.stroke()
        ctx.move_to(24, y); ctx.curve_to(18, y + 4, 14, y - 3, 12, y); ctx.stroke()
    # eggledere og eggstokker
    for sd in (-1, 1):
        rgba(ctx, COL["wall_d"], 0.8); ctx.set_line_width(2.5)
        ctx.move_to(sd * 140, -44); ctx.line_to(sd * 72, -72); ctx.stroke()       # eggstokkbånd
        p_tube(sd); rgba(ctx, COL["tube"]); ctx.set_line_width(11); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
        p_tube(sd); rgba(ctx, COL["wall_d"], 0.6); ctx.set_line_width(3); ctx.stroke()
        for k in range(6):   # fimbrier
            ang = math.pi / 2 + sd * (-0.9 + 0.36 * k)
            ctx.move_to(sd * 226, -66)
            ctx.line_to(sd * 226 + 20 * math.cos(ang) * sd, -66 + 20 * math.sin(ang))
            rgba(ctx, COL["tube"]); ctx.set_line_width(4); ctx.stroke()
        p_ovary(sd); rgba(ctx, COL["ovary"]); ctx.fill()
        for k in range(6):
            rgba(ctx, COL["follicle"], 0.9); ctx.arc(sd * (152 + 40 * PTS[k + sd + 5, 0]), -50 + 14 * PTS[k + 7, 1],
                                                    2.5 + 3 * PTS[k, 2], 0, TAU); ctx.fill()
    # livmor
    g = cairo.LinearGradient(-80, 0, 80, 0)
    g.add_color_stop_rgb(0, *COL["wall_d"]); g.add_color_stop_rgb(0.5, *COL["wall"]); g.add_color_stop_rgb(1, *COL["wall_d"])
    p_uterus(); ctx.set_source(g); ctx.fill()
    p_cervix(); rgba(ctx, COL["cervix"]); ctx.fill()
    rgba(ctx, COL["canal"]); ctx.set_line_width(4); ctx.move_to(0, 24); ctx.line_to(0, 72); ctx.stroke()
    p_lining(); rgba(ctx, COL["lining"]); ctx.fill()
    cav = 1 - 0.55 * lining
    ctx.move_to(-34 * cav, -92); ctx.line_to(34 * cav, -92); ctx.line_to(0, 14); ctx.close_path()
    rgba(ctx, (0.45, 0.10, 0.18), 0.9); ctx.fill()
    # egg i eggleder
    if egg is not None:
        sd, p = egg
        pts = [(226, -66), (226, -90), (205, -118), (170, -138), (120, -128), (72, -100)]
        seg = p * (len(pts) - 1); j = min(int(seg), len(pts) - 2); f = seg - j
        ex = sd * lerp(pts[j][0], pts[j + 1][0], f); ey = lerp(pts[j][1], pts[j + 1][1], f)
        glow(ctx, ex, ey, 22, (1, 0.95, 0.7), 0.6)
        rgba(ctx, (1, 0.97, 0.85)); ctx.arc(ex, ey, 6, 0, TAU); ctx.fill()
    # markeringer
    outline_hl(ctx, p_vagina, h.get("vagina", 0) * (1 + 0.3 * b))
    outline_hl(ctx, p_cervix, h.get("cervix", 0) * (1 + 0.3 * b))
    outline_hl(ctx, p_uterus, h.get("uterus", 0) * (1 + 0.3 * b))
    outline_hl(ctx, p_lining, h.get("lining", 0))
    for sd in (-1, 1):
        if h.get("tubes", 0) > 0:
            p_tube(sd); rgba(ctx, C["hl"], 0.8 * h["tubes"]); ctx.set_line_width(4); ctx.stroke()
        outline_hl(ctx, lambda: p_ovary(sd), h.get("ovaries", 0))
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)
    ctx.restore()

    def P(x, y):
        return cx + s * x, cy + s * y
    L = [("uterus", (60, -90), (250, -150), "uterus"),
         ("lining", (-20, -60), (-110, -200), "endometrium (lining)"),
         ("tubes", (150, -136), (160, -200), "fallopian tube"),
         ("ovaries", (190, -36), (250, -8), "ovary"),
         ("cervix", (24, 50), (250, 50), "cervix"),
         ("vagina", (-30, 150), (-250, 150), "vagina")]
    for key, (ax, ay), (lx, ly), name in L:
        la = labels.get(key, 0) * a
        if la > 0:
            label(ctx, *P(ax, ay), *P(lx, ly), name, la, hl=clamp(h.get(key, 0)))
    if floor > 0:
        label(ctx, *P(-170, 140), *P(-300, 210), "pelvic floor muscles", floor * a, hl=floor)


# ------------------------------------------------------------------ vulva (forfra, skjematisk)
def vulva(ctx, cx, cy, s, t, h=None, a=1.0, labels=None, inner=0.0, ghost=0.0, drops=0.0):
    """inner: indre klitorisstruktur (0..1). ghost: tegn vulva bare som stiplet omriss."""
    h = h or {}; labels = labels or {}
    b = rms("Bass", t, 0.2)
    ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s)
    ctx.push_group()

    def p_majora():
        ctx.move_to(0, -132); ctx.curve_to(-98, -122, -112, 40, -30, 165)
        ctx.curve_to(-15, 176, 15, 176, 30, 165); ctx.curve_to(112, 40, 98, -122, 0, -132); ctx.close_path()

    def p_minora():
        ctx.move_to(0, -106); ctx.curve_to(-56, -96, -62, 60, -12, 136)
        ctx.curve_to(-5, 141, 5, 141, 12, 136); ctx.curve_to(62, 60, 56, -96, 0, -106); ctx.close_path()

    def p_vest():
        ctx.move_to(0, -72); ctx.curve_to(-30, -52, -34, 70, 0, 116); ctx.curve_to(34, 70, 30, -52, 0, -72)
        ctx.close_path()

    def p_glans():
        ctx.arc(0, -80, 8, 0, TAU)

    def p_vopen():
        ellipse(ctx, 0, 52, 15, 30)

    def p_glands():
        ctx.new_path(); ctx.arc(-34, 98, 10, 0, TAU); ctx.new_sub_path(); ctx.arc(34, 98, 10, 0, TAU)

    solid = 1 - ghost
    # venusberg (svak)
    glow(ctx, 0, -150, 140, COL["majora"], 0.35 * solid)
    if solid > 0:
        p_majora(); rgba(ctx, COL["majora"], solid); ctx.fill()
        p_minora(); rgba(ctx, COL["minora"], solid); ctx.fill()
        p_vest(); rgba(ctx, COL["vest"], solid); ctx.fill()
        ctx.move_to(-24, -80); ctx.curve_to(-22, -114, 22, -114, 24, -80); ctx.curve_to(10, -94, -10, -94, -24, -80)
        rgba(ctx, COL["minora"], solid); ctx.fill()   # forhud
        ctx.move_to(-24, -80); ctx.curve_to(-22, -114, 22, -114, 24, -80)
        rgba(ctx, (0.55, 0.30, 0.42), solid); ctx.set_line_width(1.5); ctx.stroke()
        p_glans(); rgba(ctx, COL["clit"], solid); ctx.fill()
        rgba(ctx, COL["hole"], solid); ellipse(ctx, 0, -26, 3, 4.5); ctx.fill()     # urinrør
        p_vopen(); rgba(ctx, COL["hole"], solid); ctx.fill()
    if ghost > 0:
        ctx.set_dash([6, 6]); ctx.set_line_width(2)
        for fn in (p_majora, p_minora, p_vest):
            fn(); rgba(ctx, (0.85, 0.75, 0.85), 0.5 * ghost); ctx.stroke()
        ctx.set_dash([])
        p_glans(); rgba(ctx, COL["clit"], ghost); ctx.fill()
    # Bartholins kjertler (under huden: stiplet + utførselsgang)
    ga = max(0.35 * solid, h.get("glands", 0))
    ctx.set_dash([4, 4]); ctx.set_line_width(1.6)
    p_glands(); rgba(ctx, COL["gland"], ga); ctx.stroke(); ctx.set_dash([])
    if h.get("glands", 0) > 0:
        p_glands(); rgba(ctx, COL["gland"], 0.35 * h["glands"]); ctx.fill()
        for sd in (-1, 1):
            rgba(ctx, COL["gland"], 0.8 * h["glands"]); ctx.set_line_width(2)
            ctx.move_to(sd * 30, 90); ctx.line_to(sd * 14, 76); ctx.stroke()
    if drops > 0:
        for k in range(10):
            p = (t * 0.5 + PTS[k + 60, 0]) % 1.0
            sd = -1 if k % 2 else 1
            x = sd * lerp(14, 6, p); y = 76 + 20 * p
            rgba(ctx, COL["gland"], drops * math.sin(p * math.pi)); ctx.arc(x, y, 2.5, 0, TAU); ctx.fill()
    # indre klitoris
    if inner > 0:
        sp = 1 + 0.15 * b
        for sd in (-1, 1):
            ctx.move_to(sd * 4, -66); ctx.curve_to(sd * 40, -60, sd * 44, 20, sd * 26, 70)
            ctx.curve_to(sd * 12, 70, sd * 14, -20, sd * 4, -66)
            rgba(ctx, COL["bulb"], 0.55 * inner); ctx.fill()                       # vestibulærløk
            ctx.move_to(0, -108); ctx.curve_to(sd * 50, -100, sd * 90, -30, sd * 92, 80)
            rgba(ctx, COL["clit"], 0.85 * inner); ctx.set_line_width(13 * sp); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
        ctx.move_to(0, -80); ctx.line_to(0, -110)
        rgba(ctx, COL["clit"], 0.9 * inner); ctx.set_line_width(16 * sp); ctx.stroke()       # kropp
        p_glans(); rgba(ctx, (1, 0.6, 0.8), inner); ctx.fill()
        # nervesignaler på keyboard-anslag
        n, _ = onset_info("Keyboard", t)
        for j in range(6):
            i = n - 1 - j
            if i < 0:
                continue
            age = t - STEM["Keyboard"]["onsets"][i]
            if age > 0.9:
                continue
            p = age / 0.9; sd = 1 if i % 2 else -1
            # punkt langs krus-kurven (bezier)
            x0, y0, x1, y1, x2, y2, x3, y3 = 0, -108, sd * 50, -100, sd * 90, -30, sd * 92, 80
            u = 1 - p
            x = u ** 3 * x0 + 3 * u * u * p * x1 + 3 * u * p * p * x2 + p ** 3 * x3
            y = u ** 3 * y0 + 3 * u * u * p * y1 + 3 * u * p * p * y2 + p ** 3 * y3
            glow(ctx, x, y, 16, (1, 0.95, 0.7), 0.8 * inner * (1 - p))
    outline_hl(ctx, p_majora, h.get("majora", 0) * (1 + 0.3 * b))
    outline_hl(ctx, p_minora, h.get("minora", 0) * (1 + 0.3 * b))
    outline_hl(ctx, p_glans, h.get("clit", 0), 2.5)
    outline_hl(ctx, p_vopen, h.get("vopen", 0), 2.5)
    if h.get("vulva", 0) > 0:
        outline_hl(ctx, p_majora, h["vulva"])
        glow(ctx, 0, 0, 200, C["hl"], 0.12 * h["vulva"])
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)
    ctx.restore()

    def P(x, y):
        return cx + s * x, cy + s * y
    L = [("clit", (6, -84), (150, -110), "clitoris (glans)"),
         ("urethra", (3, -26), (150, -40), "urethral opening"),
         ("vopen", (12, 40), (150, 30), "vaginal opening"),
         ("glands", (40, 100), (150, 105), "Bartholin's glands"),
         ("majora", (-92, -10), (-150, -40), "labia majora"),
         ("minora", (-50, 30), (-150, 40), "labia minora"),
         ("mons", (-40, -140), (-150, -140), "mons pubis"),
         ("body", (0, -104), (-150, -116), "body"),
         ("crura", (-88, 20), (-160, 0), "crus (leg)"),
         ("bulbs", (-30, 30), (-160, 80), "vestibular bulb")]
    for key, (ax, ay), (lx, ly), name in L:
        la = labels.get(key, 0) * a
        if la > 0:
            label(ctx, *P(ax, ay), *P(lx, ly), name, la, hl=clamp(h.get(key, 0)))


# ------------------------------------------------------------------ eggstokk-nærbilde og syklus
def ovary_zoom(ctx, t, a=1.0):
    t_ov = ws(20, "eggs")       # eggløsning på «eggs»
    t_hor = ws(21, "Hormones")
    cx, cy = 760, 330
    ctx.save(); ctx.push_group()
    glow(ctx, cx, cy, 330, COL["ovary"], 0.12)
    rgba(ctx, COL["ovary"]); ellipse(ctx, cx, cy, 260, 165); ctx.fill()
    rgba(ctx, (0.85, 0.65, 0.55)); ctx.set_line_width(3); ellipse(ctx, cx, cy, 260, 165); ctx.stroke()
    # små follikler
    for k in range(26):
        x = cx + 210 * (PTS[k + 100, 0] - 0.5) * 2 * 0.9; y = cy + 130 * (PTS[k + 100, 1] - 0.5) * 2 * 0.85
        if ((x - cx) / 230) ** 2 + ((y - cy) / 145) ** 2 > 1:
            continue
        r = 5 + 9 * PTS[k + 100, 2]
        rgba(ctx, COL["follicle"]); ctx.arc(x, y, r, 0, TAU); ctx.fill()
        rgba(ctx, (0.95, 0.75, 0.6)); ctx.arc(x, y, r * 0.35, 0, TAU); ctx.fill()
    # dominant follikkel vokser og brister
    fx, fy = cx + 150, cy - 70
    grow = smooth((t - (t_ov - 2.0)) / 2.0)
    burst = smooth((t - t_ov) / 0.4)
    r = lerp(14, 52, grow)
    if burst < 1:
        rgba(ctx, (1, 0.93, 0.75), 1 - burst); ctx.arc(fx, fy, r, 0, TAU); ctx.fill()
        rgba(ctx, (0.95, 0.75, 0.6), 1 - burst); ctx.set_line_width(3); ctx.arc(fx, fy, r, 0, TAU); ctx.stroke()
    else:   # gulllegeme (corpus luteum)
        cl = smooth((t - t_ov - 1.0) / 2.0)
        rgba(ctx, (0.98, 0.80, 0.30), cl); ctx.arc(fx, fy, 34, 0, TAU); ctx.fill()
    # egget forlater eggstokken mot fimbriene (opp til høyre)
    ep = clamp((t - t_ov) / 3.0)
    ex, ey = lerp(fx, 1150, smooth(ep)), lerp(fy, 150, smooth(ep))
    glow(ctx, ex, ey, 40, (1, 0.95, 0.7), 0.5)
    rgba(ctx, (1, 0.97, 0.88)); ctx.arc(ex, ey, 14, 0, TAU); ctx.fill()
    rgba(ctx, (0.9, 0.75, 0.5)); ctx.set_line_width(4); ctx.arc(ex, ey, 18, 0, TAU); ctx.stroke()
    # fimbrier i hjørnet
    for k in range(7):
        ang = math.pi * (0.55 + 0.12 * k)
        ctx.move_to(1210, 110); ctx.line_to(1210 + 70 * math.cos(ang), 110 + 70 * math.sin(ang))
        rgba(ctx, COL["tube"]); ctx.set_line_width(12); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    # østrogen strømmer ut i blodet (tre små E-er per bølge)
    ea = on(t, t_hor - 0.3)
    if ea > 0:
        for k in range(14):
            p = (t * 0.35 + PTS[k + 150, 0]) % 1.0
            x = lerp(cx - 120 + 240 * PTS[k + 150, 1], cx - 380 + 60 * PTS[k + 170, 0], p)
            y = lerp(cy + 20, cy + 150 - 300 * PTS[k + 150, 2], p)
            rgba(ctx, COL["estro"], ea * math.sin(p * math.pi)); ctx.arc(x, y, 9, 0, TAU); ctx.fill()
            text(ctx, "E", x, y + 5, 12, (0.3, 0.05, 0.15), ea * math.sin(p * math.pi), bold=True)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a); ctx.restore()
    label(ctx, cx - 150, cy + 110, cx - 330, cy + 190, "follicles (each holds an egg)", on(t, LINES[20]["t0"]) * a)
    label(ctx, fx + 40, fy - 30, fx + 120, fy - 140, "ovulation", on(t, t_ov) * (1 - on(t, t_ov + 6)) * a, hl=1)
    label(ctx, fx + 30, fy, fx + 160, fy + 60, "corpus luteum", on(t, t_ov + 2.5) * a)
    if ea > 0:
        badge(ctx, "estrogen", 330, 480, ea * a, COL["estro"], 20)


def curve_e(d):     # østrogen (relativ), dag 1..28
    return 0.15 + 0.75 * math.exp(-((d - 13) / 2.6) ** 2) + 0.3 * math.exp(-((d - 21) / 3.5) ** 2)


def curve_p(d):     # progesteron
    return 0.05 + 0.85 * math.exp(-((d - 21) / 3.8) ** 2)


def curve_lh(d):
    return 0.08 + 0.9 * math.exp(-((d - 14) / 0.8) ** 2)


def lining_at(d):   # endometriets tykkelse
    if d < 5:
        return lerp(0.6, 0.15, d / 5)
    if d < 14:
        return lerp(0.15, 0.7, (d - 5) / 9)
    return lerp(0.7, 1.0, min(1, (d - 14) / 7))


def cycle_day(t):
    t0 = LINES[22]["t0"]; t1 = LINES[23]["t1"]
    return 1 + 27 * clamp((t - t0) / (t1 - t0))


def cycle_chart(ctx, t, a=1.0):
    x0, x1, y0, y1 = 450, 1220, 80, 330
    d_now = cycle_day(t)
    ctx.save(); ctx.push_group()
    rgba(ctx, (0, 0, 0), 0.35); rrect(ctx, x0 - 20, y0 - 30, x1 - x0 + 40, 470, 16); ctx.fill()
    X = lambda d: lerp(x0, x1, (d - 1) / 27)     # noqa: E731
    Y = lambda v: lerp(y1, y0, v)                # noqa: E731
    # menstruasjon og eggløsning
    rgba(ctx, (0.8, 0.2, 0.3), 0.25); ctx.rectangle(X(1), y0, X(5) - X(1), y1 - y0); ctx.fill()
    text(ctx, "period", (X(1) + X(5)) / 2, y0 + 18, 14, (1, 0.6, 0.65), 0.9)
    rgba(ctx, COL["lh"], 0.5); ctx.set_dash([4, 4]); ctx.set_line_width(1.5)
    ctx.move_to(X(14), y0); ctx.line_to(X(14), y1 + 150); ctx.stroke(); ctx.set_dash([])
    text(ctx, "ovulation", X(14), y0 - 8, 14, COL["lh"], 0.9)
    reveal = 1 + 27 * clamp((t - (LINES[22]["t0"] - 0.8)) / 3.0)
    reveal = max(reveal, d_now)
    for fn, col, name, ly in ((curve_e, COL["estro"], "estrogen", 0), (curve_p, COL["prog"], "progesterone", 1),
                              (curve_lh, COL["lh"], "LH", 2)):
        n = int((reveal - 1) * 6) + 1
        for i in range(n):
            d = 1 + i / 6
            (ctx.move_to if i == 0 else ctx.line_to)(X(d), Y(fn(d)))
        rgba(ctx, col); ctx.set_line_width(3); ctx.stroke()
        text(ctx, "— " + name, x0 + 10 + 150 * ly, y1 + 28, 15, col, 1, align="left", bold=True)
    # endometrium-bånd
    by = y1 + 120
    text(ctx, "uterine lining", x0, by - 50, 15, COL["label"], 0.9, align="left")
    for i in range(int((reveal - 1) * 4) + 1):
        d = 1 + i / 4
        th = 8 + 56 * lining_at(d)
        rgba(ctx, COL["lining"] if d >= 5 else (0.9, 0.25, 0.3)); ctx.rectangle(X(d), by - th / 2, (x1 - x0) / 108 + 1, th); ctx.fill()
    # aksen
    rgba(ctx, (1, 1, 1), 0.5); ctx.set_line_width(1.5); ctx.move_to(x0, by + 45); ctx.line_to(x1, by + 45); ctx.stroke()
    for d in (1, 7, 14, 21, 28):
        text(ctx, f"day {d}", X(d), by + 66, 13, (0.85, 0.85, 0.9), 0.9)
    # markør for dagen nå
    rgba(ctx, (1, 1, 1), 0.9); ctx.set_line_width(2); ctx.move_to(X(d_now), y0); ctx.line_to(X(d_now), by + 45); ctx.stroke()
    badge(ctx, f"day {int(d_now)}", X(d_now), by + 102, 1, C["white"], 15)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a); ctx.restore()


# ------------------------------------------------------------------ scener
ALL_INT = dict(uterus=1, lining=1, tubes=1, ovaries=1, cervix=1, vagina=1)
ALL_VUL = dict(clit=1, urethra=1, vopen=1, majora=1, minora=1, mons=1)


def scene_v1(ctx, t, key):
    l0, l1, l2, l3 = LINES[0], LINES[1], LINES[2], LINES[3]
    h = dict(vulva=hi(t, l0["words"][1]["start"], l0["t1"], 0.6),
             majora=hi(t, l1["words"][0]["start"], l1["words"][1]["end"], 0.3) + 0.6 * hi(t, ws(1, "in"), l1["e1"], 0),
             minora=hi(t, l1["words"][2]["start"], l1["words"][3]["end"], 0.3) + 0.6 * hi(t, ws(1, "in"), l1["e1"], 0),
             clit=hi(t, ws(2, "clitoris"), l3["e1"], 0))
    labels = dict(mons=on(t, 1.5), majora=on(t, ws(1, "Labia")), minora=on(t, ws(1, "minora") - 0.3),
                  clit=on(t, ws(2, "clitoris")), urethra=on(t, 9.0), vopen=on(t, 10.0))
    inner = on(t, ws(2, "wonder"), 1.2)
    if inner > 0:
        labels.update(body=inner, crura=inner, bulbs=on(t, ws(2, "galore"), 1.0))
        labels.update(mons=0, majora=1 - inner, minora=1 - inner, urethra=1 - inner, vopen=1 - inner)
    vulva(ctx, 800, 320, 1.15, t, h, 1.0, labels, inner=inner, ghost=0.7 * inner)
    if t < 4.0:
        a = smooth(t / 0.8) * (1 - smooth((t - 3.0) / 1.0))
        text(ctx, "Secrets of the Female Body", 800, 60, 34, C["white"], a, bold=True, font=LYRIC_FONT)
    ba = hi(t, ws(2, "nerves"), l3["t0"] - 0.2, 0.5)
    badge(ctx, "≈10,000 nerve fibres", 1060, 140, ba, C["hl"], 18)
    ba2 = hi(t, ws(3, "function"), l3["e1"], 0.3)
    badge(ctx, "about 10 cm in total – mostly inside", 1010, 140, ba2, (1, 0.7, 0.85), 17)


def scene_pc(ctx, t, key):
    li = {"pc1": 4, "pc2": 14, "pc3": 28}[key]
    t0 = LINES[li]["t0"]; t2 = LINES[li + 1]["t0"]
    if key == "pc1":
        a1 = on(t, t0 - 1.0)
        vulva(ctx, 540, 330, 0.85, t, dict(vulva=hi(t, ws(li + 1, "female"), LINES[li + 1]["e1"], 0)), a1,
              dict(ALL_VUL, mons=0, urethra=0))
        internal(ctx, 980, 300, 0.85, t, {k: hi(t, ws(li + 1, "female"), LINES[li + 1]["e1"], 0) for k in ALL_INT},
                 a=a1, labels={k: on(t, t0 + 0.8 * i) for i, k in enumerate(ALL_INT)})
        text(ctx, "OUTSIDE", 540, 520, 22, C["hl"], a1, bold=True)
        text(ctx, "INSIDE", 980, 520, 22, C["hl"], a1, bold=True)
    elif key == "pc2":
        fl = on(t, t0 - 0.5, 1.0)
        internal(ctx, 790, 290, 1.0, t, {}, a=1.0, labels=dict(ALL_INT, lining=0), floor=fl, pulse=1.0)
        badge(ctx, "squeeze · hold · relax", 790, 545, hi(t, t2, LINES[li + 1]["e1"], 0), COL["muscle"], 17)
    else:
        internal(ctx, 790, 290, 1.0, t, dict(cervix=hi(t, t0, LINES[li + 1]["e1"], 0)), a=1.0,
                 labels=dict(ALL_INT))
        badge(ctx, "cervical screening", 640, 500, on(t, t0 + 0.5), (0.6, 0.9, 1.0), 18)
        badge(ctx, "HPV vaccine", 950, 500, on(t, t2), (0.6, 1.0, 0.7), 18)


def scene_chorus(ctx, t, key):
    li = {"ch1": 6, "ch2": 16, "ch3": 30}[key]
    L = LINES[li:li + 4]
    glow(ctx, 790, 290, 360, (1, 0.6, 0.8), 0.10 + 0.15 * rms("Brass", t, 0.5))
    sparkles(ctx, t, 790, 290)
    if key == "ch3":
        # alle navnene spretter fram på trommeslag
        n0 = bisect.bisect_left(HITS, L[0]["t0"])
        shown = bisect.bisect_right(HITS, t) - n0
        keys = ["majora", "minora", "clit", "vopen", "urethra", "uterus", "tubes", "ovaries", "cervix", "vagina", "lining"]
        lab = {k: smooth(clamp((shown - i * 2) / 2)) for i, k in enumerate(keys)}
        vulva(ctx, 470, 330, 0.8, t, {}, 1.0, {k: lab.get(k, 0) for k in ALL_VUL})
        internal(ctx, 980, 300, 0.85, t, {}, a=1.0, labels={k: lab.get(k, 0) for k in ALL_INT}, pulse=1)
        return
    # vandring fra vulva til eggstokk på «From the vulva to the ovaries»
    tj0, tj1 = ws(li + 2, "From"), ws(li + 2, "ovaries") + 0.6
    h = {}
    order = ["vagina", "cervix", "uterus", "tubes", "ovaries"]
    pj = clamp((t - tj0) / (tj1 - tj0))
    if tj0 - 0.3 < t < L[2]["e1"] + 1:
        for i, k in enumerate(order):
            h[k] = smooth(clamp(pj * 5 - i)) * (1 - smooth((t - L[2]["e1"] - 0.3) / 0.8))
    if key == "ch2":
        egg = (1, 1 - ((t - L[0]["t0"]) / 6.0) % 1.0)
    else:
        egg = None
    internal(ctx, 790, 290, 1.05, t, h, a=1.0, labels=dict(ALL_INT), egg=egg, pulse=1)
    if key == "ch2":
        # cilier langs eggleder (høyre side)
        for k in range(12):
            p = k / 11
            x = 790 + 1.05 * lerp(72, 205, p); y = 290 + 1.05 * lerp(-100, -125, math.sin(p * math.pi / 2))
            sw = 5 * math.sin(t * 12 + k)
            rgba(ctx, (1, 0.9, 0.8), 0.7); ctx.set_line_width(1.5)
            ctx.move_to(x, y - 6); ctx.line_to(x + sw, y - 14); ctx.stroke()


def scene_v2(ctx, t, key):
    if key == "v2a":
        h = dict(vagina=hi(t, ws(10, "vagina"), LINES[10]["e1"], 0.2), cervix=hi(t, ws(11, "cervix") - 0.4, LINES[11]["e1"], 0.5))
        lab = dict(vagina=on(t, ws(10, "vagina")), cervix=on(t, ws(11, "cervix") - 0.4), uterus=0.4, tubes=0.4, ovaries=0.4)
        internal(ctx, 790, 290, 1.05, t, h, a=1.0, labels=lab, lining=0.5, pulse=1)
        badge(ctx, "≈ 7–10 cm, elastic", 1080, 420, hi(t, ws(10, "canal"), LINES[10]["e1"], 0.2), (1, 0.75, 0.85), 17)
        badge(ctx, "opening of the cervix", 1080, 420, hi(t, ws(11, "secrets"), LINES[11]["e1"], 0.3), (1, 0.75, 0.85), 17)
    else:
        h = dict(uterus=hi(t, ws(12, "uterus"), LINES[12]["e1"], 0.2), tubes=hi(t, ws(13, "fallopian"), LINES[13]["e1"], 0.5))
        lab = dict(vagina=1, cervix=1, uterus=on(t, ws(12, "uterus")), tubes=on(t, ws(13, "fallopian")), ovaries=on(t, ws(13, "fallopian")))
        egg = None
        te = ws(13, "journey")
        if t > te - 1.0:
            egg = (-1, clamp((t - te + 1.0) / 4.0))
        internal(ctx, 790, 290, 1.05, t, h, a=1.0, labels=lab, lining=0.7, egg=egg, pulse=1)
        badge(ctx, "about the size of a small pear", 790, 520, hi(t, ws(12, "cradle"), LINES[12]["e1"], 0.2), (1, 0.75, 0.85), 17)


def scene_bridge(ctx, t, key):
    if key == "br1":
        ovary_zoom(ctx, t, on(t, LINES[20]["t0"] - 1.0))
    else:
        d = cycle_day(t)
        cycle_chart(ctx, t, on(t, LINES[22]["t0"] - 1.0))
        internal(ctx, 230, 330, 0.62, t, dict(lining=0.6), a=1.0, labels={}, lining=lining_at(d))
        text(ctx, "uterus", 230, 470, 15, COL["label"], 0.9)
        badge(ctx, "21–35 days is normal", 230, 520, on(t, ws(23, "twenty")), C["hl"], 16)


def scene_v3(ctx, t, key):
    l = LINES[24:28]
    hg = hi(t, ws(24, "Bartholin"), l[1]["e1"], 0.6) + 0.5 * hi(t, l[2]["t0"], l[3]["e1"], 0)
    h = dict(glands=clamp(hg))
    arousal = hi(t, ws(26, "arousal"), l[3]["e1"], 0.5)
    vulva(ctx, 800, 320, 1.15, t, h, 1.0, dict(glands=on(t, ws(24, "Bartholin")), vopen=1, clit=1, minora=1, majora=1),
          inner=0.6 * arousal, ghost=0.0, drops=hi(t, ws(25, "lubrication"), l[3]["e1"], 0.5))
    badge(ctx, "pea-sized", 560, 450, hi(t, ws(24, "glands"), l[0]["e1"], 0.2), COL["gland"], 17)
    badge(ctx, "more blood flow → swelling + lubrication", 800, 545, arousal, (1, 0.7, 0.85), 16)


def scene_outro(ctx, t, key):
    a = 1 - 0.6 * on(t, LINES[35]["t1"] + 0.5, 2.0)
    vulva(ctx, 470, 330, 0.8, t, {}, a, dict(ALL_VUL, mons=0, urethra=0))
    internal(ctx, 980, 300, 0.85, t, {}, a=a, labels=dict(ALL_INT))
    ta = on(t, LINES[35]["t1"] + 0.5, 1.5)
    if ta > 0:
        rgba(ctx, (0, 0, 0), 0.5 * ta); ctx.rectangle(0, 230, W, 140); ctx.fill()
        text(ctx, "Secrets of the Female Body", 640, 300, 50, C["white"], ta, bold=True, font=LYRIC_FONT)
        text(ctx, "BiologyTunes", 640, 345, 22, C["hl"], ta, bold=True)


SCENE_FN = dict(v1a=scene_v1, v1b=scene_v1, pc1=scene_pc, pc2=scene_pc, pc3=scene_pc, ch1=scene_chorus,
                ch2=scene_chorus, ch3=scene_chorus, v2a=scene_v2, v2b=scene_v2, br1=scene_bridge, br2=scene_bridge,
                v3=scene_v3, outro=scene_outro)


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
    key, t0, label_, title = sc
    a = smooth((t - t0 - 0.5) / 1.0) * (1 - smooth((t - t1 + 1.0) / 0.8))
    if a <= 0:
        return
    x, y, w = 20, 18, 380
    lines = wrap(ctx, FACTS[key], w - 28, 14.5)
    h = 66 + 20 * len(lines)
    rgba(ctx, (0, 0, 0), 0.6 * a); rrect(ctx, x, y, w, h, 14); ctx.fill()
    rgba(ctx, C["hl"], 0.7 * a); ctx.set_line_width(1.5); rrect(ctx, x, y, w, h, 14); ctx.stroke()
    text(ctx, label_.upper(), x + 14, y + 24, 12.5, C["hl"], a, align="left", bold=True)
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
        if l["t0"] - 0.3 <= t < max(l["t1"] + 0.4, l["e1"]):
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
    nxt = LINES[cur + 1] if cur + 1 < len(LINES) and LINES[cur + 1]["t0"] - l["e1"] < 3 else None
    if prev:
        text(ctx, prev["text"], 640, PANEL_Y + 26, 19, (0.65, 0.65, 0.72), 0.6, font=LYRIC_FONT)
    karaoke(ctx, l, t, 36, PANEL_Y + 74)
    ea = smooth((t - l["t1"] - 0.1) / 0.3) * (1 - smooth((t - l["e1"] + 0.2) / 0.3)) if l["echo"] else 0
    if ea > 0:
        bv = rms("Backing Vocals", t, 0.3)
        text(ctx, f"({l['echo']})", 640, PANEL_Y + 118, 26, (1.0, 0.70, 0.88), ea * (0.75 + 0.25 * bv),
             bold=True, font=LYRIC_FONT)
    elif nxt:
        text(ctx, nxt["text"], 640, PANEL_Y + 122, 20, (0.7, 0.7, 0.78), 0.7, font=LYRIC_FONT)


# ------------------------------------------------------------------ ramme
def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    sc, t1 = scene_at(t)
    bg(ctx, t)
    SCENE_FN[sc[0]](ctx, t, sc[0])
    for s in SCENES[1:]:
        d = t - s[1]
        if s[0] in ("v1b",):
            continue
        if -0.3 < d < 0.3:
            rgba(ctx, (0, 0, 0), 0.5 * (1 - abs(d) / 0.3)); ctx.paint()
    if t > 3.5 and not (sc[0] == "outro" and t > LINES[-1]["t1"] + 0.5):
        fact_card(ctx, sc, t1, t)
    lyric_panel(ctx, t)
    if t < 0.6:
        rgba(ctx, (0, 0, 0), 1 - t / 0.6); ctx.paint()
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
        os.path.join(HERE, OUT)], stdin=subprocess.PIPE)
    with Pool() as pool:
        for k, buf in enumerate(pool.imap(frame_bytes, range(n), chunksize=8)):
            ff.stdin.write(buf)
            if k % 1500 == 0:
                print(f"{k}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print("ferdig")


if __name__ == "__main__":
    main()
