"""Tegner musikkvideoen for «Den minste motoren» med Cairo og setter den sammen med ffmpeg.

Bruk:  python3 make_video.py            -> den-minste-motoren.mp4
       python3 make_video.py 12.0 40.5  -> PNG-forhåndsvisning av gitte tidspunkt
"""
import math
import subprocess
import sys
from multiprocessing import Pool

import cairo
import numpy as np

from song import SECTIONS_T, LINES, DURATION, BAR, BEAT

W, H, FPS = 1280, 720, 30
PANEL_Y = 584
TAU = 2 * math.pi
SANS = "DejaVu Sans"
LYRIC_FONT = "Inter"

C = dict(  # fargepalett
    bg0=(0.04, 0.06, 0.13), bg1=(0.08, 0.10, 0.22),
    ims=(0.20, 0.10, 0.20), matrix=(0.10, 0.14, 0.26),
    lipid=(0.98, 0.80, 0.45), lipid_d=(0.75, 0.55, 0.25),
    proton=(1.0, 0.42, 0.20), electron=(0.35, 0.75, 1.0),
    alpha=(0.86, 0.30, 0.36), beta=(0.30, 0.52, 0.92),
    ring=(0.36, 0.80, 0.62), a_sub=(0.62, 0.42, 0.85), gamma=(0.98, 0.72, 0.20),
    atp=(1.0, 0.84, 0.25), white=(1, 1, 1), hl=(1.0, 0.85, 0.30),
    L=(0.98, 0.85, 0.30), T=(0.95, 0.35, 0.30), O=(0.40, 0.85, 0.45),
)


# ---------------------------------------------------------------- hjelpere
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, x):
    return a + (b - a) * x


def rgba(ctx, col, a=1.0):
    ctx.set_source_rgba(col[0], col[1], col[2], a)


def text(ctx, s, x, y, size, col=C["white"], a=1.0, align="center", bold=False, font=SANS):
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    ext = ctx.text_extents(s)
    dx = {"center": -ext.x_advance / 2, "left": 0, "right": -ext.x_advance}[align]
    ctx.move_to(x + dx, y)
    rgba(ctx, col, a)
    ctx.show_text(s)
    return ext.x_advance


def rrect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -TAU / 4, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, TAU / 4)
    ctx.arc(x + r, y + h - r, r, TAU / 4, TAU / 2)
    ctx.arc(x + r, y + r, r, TAU / 2, 3 * TAU / 4)
    ctx.close_path()


def ellipse(ctx, cx, cy, rx, ry):
    ctx.save(); ctx.translate(cx, cy); ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, TAU); ctx.restore()


def glow(ctx, x, y, r, col, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, col[0], col[1], col[2], a)
    g.add_color_stop_rgba(1, col[0], col[1], col[2], 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, TAU); ctx.fill()


def proton(ctx, x, y, a=1.0, r=10):
    glow(ctx, x, y, r * 2.2, C["proton"], 0.35 * a)
    rgba(ctx, C["proton"], a); ctx.arc(x, y, r, 0, TAU); ctx.fill()
    if r >= 8:
        text(ctx, "H", x - 2, y + r * 0.4, r * 1.05, C["white"], a, bold=True)
        text(ctx, "+", x + r * 0.5, y - r * 0.05, r * 0.8, C["white"], a, bold=True)


def atp_mol(ctx, x, y, a=1.0, s=1.0):
    glow(ctx, x, y, 34 * s, C["atp"], 0.3 * a)
    rgba(ctx, C["atp"], a); rrect(ctx, x - 26 * s, y - 13 * s, 52 * s, 26 * s, 12 * s); ctx.fill()
    text(ctx, "ATP", x, y + 6 * s, 17 * s, (0.25, 0.15, 0.0), a, bold=True)


def background(ctx):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *C["bg1"]); g.add_color_stop_rgb(1, *C["bg0"])
    ctx.set_source(g); ctx.paint()


def badge(ctx, s, x, y, a, col=C["hl"], size=22):
    if a <= 0:
        return
    ctx.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    w = ctx.text_extents(s).x_advance + 32
    rgba(ctx, (0, 0, 0), 0.55 * a); rrect(ctx, x - w / 2, y - size - 8, w, size + 22, 14); ctx.fill()
    rgba(ctx, col, a); ctx.set_line_width(2); rrect(ctx, x - w / 2, y - size - 8, w, size + 22, 14); ctx.stroke()
    text(ctx, s, x, y + 4, size, col, a, bold=True)


# ---------------------------------------------------------------- celle / mitokondrie
def mito(ctx, cx, cy, w, h, glow_a=0.0):
    rx, ry = w / 2, h / 2
    rgba(ctx, (0.93, 0.47, 0.35)); ellipse(ctx, cx, cy, rx, ry); ctx.fill()
    rgba(ctx, C["ims"]); ellipse(ctx, cx, cy, rx * 0.95, ry * 0.9); ctx.fill()
    rgba(ctx, (0.98, 0.62, 0.42)); ellipse(ctx, cx, cy, rx * 0.91, ry * 0.81); ctx.fill()
    rgba(ctx, (0.40, 0.22, 0.38)); ellipse(ctx, cx, cy, rx * 0.88, ry * 0.76); ctx.fill()
    # cristae: folder fra topp og bunn
    n = 7
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(n):
        x = cx - rx * 0.72 + i * (rx * 1.44 / (n - 1))
        top = i % 2 == 0
        edge = cy + (-1 if top else 1) * ry * 0.78 * math.sqrt(max(0, 1 - ((x - cx) / (rx * 0.88)) ** 2))
        tip = cy + (0.22 if top else -0.22) * ry
        ctx.move_to(x, edge); ctx.line_to(x, tip)
        if glow_a > 0:
            rgba(ctx, C["hl"], glow_a); ctx.set_line_width(w * 0.06); ctx.stroke_preserve()
        rgba(ctx, (0.98, 0.62, 0.42)); ctx.set_line_width(w * 0.04); ctx.stroke_preserve()
        rgba(ctx, C["ims"]); ctx.set_line_width(w * 0.018); ctx.stroke()
    if glow_a > 0:
        ctx.set_line_width(w * 0.012); rgba(ctx, C["hl"], glow_a)
        ellipse(ctx, cx, cy, rx * 0.895, ry * 0.79); ctx.stroke()


MITOS = [(450, 160, 80, 34, 0.5), (360, 390, 90, 38, -0.3), (700, 170, 85, 36, -0.2),
         (900, 260, 80, 34, 1.2), (560, 470, 75, 32, 0.1), (940, 430, 70, 30, -0.8)]
TARGET = (780, 380, 110, 48)   # mitokondrien vi zoomer inn på


def cell_scene(ctx, zoom):
    """zoom 0 = hele cellen, 1 = målmitokondrien fyller skjermen."""
    s = math.exp(lerp(0, math.log(8.0), zoom))
    tx, ty = lerp(640, TARGET[0], zoom), lerp(290, TARGET[1], zoom)
    ctx.save()
    ctx.translate(640, 290); ctx.scale(s, s); ctx.translate(-tx, -ty)
    g = cairo.RadialGradient(640, 300, 50, 640, 300, 420)
    g.add_color_stop_rgb(0, 0.16, 0.24, 0.40); g.add_color_stop_rgb(1, 0.10, 0.16, 0.30)
    ctx.set_source(g); ellipse(ctx, 640, 300, 420, 270); ctx.fill_preserve()
    rgba(ctx, (0.55, 0.75, 1.0), 0.8); ctx.set_line_width(5); ctx.stroke()
    rgba(ctx, (0.45, 0.30, 0.65)); ellipse(ctx, 620, 300, 95, 80); ctx.fill()
    rgba(ctx, (0.60, 0.45, 0.80)); ellipse(ctx, 640, 290, 30, 26); ctx.fill()
    for (x, y, w, h, r) in MITOS:
        ctx.save(); ctx.translate(x, y); ctx.rotate(r); mito(ctx, 0, 0, w, h); ctx.restore()
    mito(ctx, *TARGET)
    ctx.restore()


# ---------------------------------------------------------------- membran
def membrane(ctx, y, x0=-20, x1=W + 20, thick=74, a=1.0):
    rgba(ctx, (0.55, 0.40, 0.20), 0.55 * a); ctx.rectangle(x0, y - thick / 2, x1 - x0, thick); ctx.fill()
    ctx.set_line_width(2)
    x = x0
    while x < x1:
        for side in (-1, 1):
            hy = y + side * (thick / 2 - 7)
            rgba(ctx, C["lipid_d"], a)
            ctx.move_to(x - 2, hy - side * 6); ctx.line_to(x - 3, y - side * 4); ctx.stroke()
            ctx.move_to(x + 2, hy - side * 6); ctx.line_to(x + 3, y - side * 4); ctx.stroke()
            rgba(ctx, C["lipid"], a); ctx.arc(x, hy, 7, 0, TAU); ctx.fill()
        x += 16


def blob(ctx, cx, cy, w, h, col, a=1.0, label=None):
    rgba(ctx, col, a); rrect(ctx, cx - w / 2, cy - h / 2, w, h, min(w, h) * 0.4); ctx.fill()
    rgba(ctx, (1, 1, 1), 0.25 * a); ctx.set_line_width(2)
    rrect(ctx, cx - w / 2, cy - h / 2, w, h, min(w, h) * 0.4); ctx.stroke()
    if label:
        text(ctx, label, cx, cy + 9, 26, C["white"], a, bold=True)


TOP_PROTONS = np.random.default_rng(3).random((60, 2))


def etc_scene(ctx, u, a=1.0):
    """Elektrontransportkjeden: protoner pumpes fra matriks (nede) til intermembranrom (oppe)."""
    my = 290
    rgba(ctx, C["ims"], 0.6 * a); ctx.rectangle(0, 0, W, my); ctx.fill()
    rgba(ctx, C["matrix"], 0.6 * a); ctx.rectangle(0, my, W, PANEL_Y - my); ctx.fill()
    membrane(ctx, my, a=a)
    text(ctx, "Intermembranrommet", 30, 40, 22, (1, 0.8, 0.8), a, align="left", bold=True)
    text(ctx, "Matriks", 30, PANEL_Y - 24, 22, (0.7, 0.85, 1), a, align="left", bold=True)
    cx = [260, 560, 860]
    # protoner som allerede er pumpet (bygges opp)
    n_top = int(lerp(6, 60, smooth(u / 9.0)))
    for i in range(n_top):
        px = 40 + TOP_PROTONS[i, 0] * (W - 80)
        py = 70 + TOP_PROTONS[i, 1] * (my - 140)
        px += 6 * math.sin(u * 2 + i); py += 5 * math.cos(u * 1.7 + i * 2)
        proton(ctx, px, py, a * 0.9, 9)
    # protoner på vei gjennom kompleksene
    for k, x in enumerate(cx):
        for j in range(2):
            p = ((u / 1.2) + k * 0.33 + j * 0.5) % 1.0
            proton(ctx, x + (j - 0.5) * 30, lerp(my + 140, my - 120, p), a * math.sin(p * math.pi), 9)
    for x, lab, col in zip(cx, ["I", "III", "IV"], [(0.25, 0.60, 0.70), (0.30, 0.55, 0.85), (0.35, 0.70, 0.50)]):
        blob(ctx, x, my, 110, 150, col, a, lab)
    # elektron som vandrer
    path = [(cx[0], my + 40), (410, my + 10), (cx[1], my), (710, my - 55), (cx[2], my), (cx[2] + 40, my + 110)]
    p = (u / 2.4) % 1.0
    seg = p * (len(path) - 1); i = int(seg); f = seg - i
    ex, ey = lerp(path[i][0], path[i + 1][0], f), lerp(path[i][1], path[i + 1][1], f)
    glow(ctx, ex, ey, 26, C["electron"], 0.6 * a)
    rgba(ctx, C["electron"], a); ctx.arc(ex, ey, 9, 0, TAU); ctx.fill()
    text(ctx, "e⁻", ex, ey - 16, 18, C["electron"], a, bold=True)
    text(ctx, "O₂ → H₂O", cx[2] + 90, my + 150, 18, (0.7, 0.85, 1), a)
    if u > 4.8:   # demningsbildet
        b = smooth((u - 4.8) / 0.8) * a
        badge(ctx, "høy [H⁺]  –  som vann bak en demning", 760, 46, b, C["proton"], 20)
        badge(ctx, "lav [H⁺]", 1120, PANEL_Y - 40, b, (0.7, 0.85, 1), 20)


# ---------------------------------------------------------------- ATP-syntase
def atp_synthase(ctx, cx, my, sc, ang, hl=None, show_flux=True, a=1.0, t=0.0):
    """Sidebilde: F0 i membranen (my), F1-hodet stikker ned i matriks. ang = rotorvinkel."""
    R, cw, chh = 70 * sc, 14 * sc, 64 * sc
    head_y = my + 165 * sc

    def hilite(name):
        return 1.0 if hl == name else 0.0

    # perifer stilk (stator) – fra a-underenheten til toppen av hodet
    ax = cx + R + 28 * sc
    rgba(ctx, (0.75, 0.62, 0.92), a); ctx.set_line_width(12 * sc)
    ctx.move_to(ax + 6 * sc, my + 20 * sc); ctx.curve_to(ax + 30 * sc, my + 80 * sc, ax + 20 * sc, head_y + 40 * sc,
                                                        cx + 40 * sc, head_y + 92 * sc); ctx.stroke()
    # γ-stilken (rotor-aksel)
    if hilite("gamma"):
        glow(ctx, cx, my + 90 * sc, 90 * sc, C["hl"], 0.5)
    rgba(ctx, C["gamma"], a); rrect(ctx, cx - 11 * sc, my, 22 * sc, 150 * sc, 8 * sc); ctx.fill()
    # stripe som viser at akselen roterer
    sx = math.sin(ang) * 9 * sc
    rgba(ctx, (0.6, 0.35, 0.0), a * (0.5 + 0.5 * math.cos(ang))); ctx.set_line_width(5 * sc)
    ctx.move_to(cx + sx, my + 10 * sc); ctx.line_to(cx + sx, my + 140 * sc); ctx.stroke()

    # F1-hodet: 6 lober (α/β) rundt γ – stasjonære
    lobes = []
    for k in range(6):
        th = k * TAU / 6 + 0.3
        lobes.append((math.sin(th), k, th))
    lobes.sort()
    rot_state = int(ang // (TAU / 3))
    for depth, k, th in lobes:
        lx = cx + math.cos(th) * 62 * sc
        ly = head_y + depth * 10 * sc
        if k % 2 == 0:
            st = "LTO"[(rot_state + k // 2) % 3]
            col = C["beta"]
        else:
            st, col = None, C["alpha"]
        shade = 0.55 + 0.45 * (depth + 1) / 2
        rgba(ctx, tuple(c * shade for c in col), a * (0.75 if depth < 0 else 0.95))
        ellipse(ctx, lx, ly, 42 * sc, 70 * sc); ctx.fill()
        if depth > 0 and st and hl == "head":
            text(ctx, st, lx, ly + 8 * sc, 22 * sc, C[st], a, bold=True)
    text(ctx, "F₁", cx - 120 * sc, head_y + 6 * sc, 22 * sc, (0.8, 0.85, 1), a * 0.8, bold=True)

    # c-ringen i membranen (roterer) – tegnes over membranbåndet
    subs = []
    for i in range(10):
        th = ang + i * TAU / 10
        subs.append((math.sin(th), i, th))
    subs.sort()
    if hilite("ring"):
        glow(ctx, cx, my, R * 1.8, C["hl"], 0.45)
    for depth, i, th in subs:
        x = cx + math.cos(th) * R
        shade = 0.45 + 0.55 * (depth + 1) / 2
        rgba(ctx, tuple(c * shade for c in C["ring"]), a)
        rrect(ctx, x - cw / 2, my - chh / 2, cw, chh, cw / 2); ctx.fill()
        if i == 0 and depth > 0:
            rgba(ctx, C["white"], a * 0.8); ctx.arc(x, my, 3 * sc, 0, TAU); ctx.fill()
    # a-underenhet (stator med halvkanaler)
    if hilite("a"):
        glow(ctx, ax, my, 70 * sc, C["hl"], 0.5)
    rgba(ctx, C["a_sub"], a); rrect(ctx, ax - 22 * sc, my - 40 * sc, 44 * sc, 80 * sc, 16 * sc); ctx.fill()

    # protonflyt: inn via a, en runde med c-ringen, ut i matriks
    if show_flux:
        rev = ang / TAU
        for k in range(10):
            p = (rev / 1.5 + k / 10) % 1.0
            if p < 0.2:
                q = p / 0.2
                px, py, al = lerp(ax + 60 * sc, ax, q), lerp(my - 120 * sc, my - 18 * sc, q), q
            elif p < 0.8:
                q = (p - 0.2) / 0.6
                th = q * TAU
                px, py = cx + math.cos(th) * R, my - 10 * sc
                al = 0.35 if math.sin(th) < 0 else 1.0
            else:
                q = (p - 0.8) / 0.2
                px, py, al = lerp(ax, ax + 70 * sc, q), lerp(my + 18 * sc, my + 110 * sc, q), 1 - q
            proton(ctx, px, py, al * a, 8 * sc)
        # ATP slippes ut fra hodet – tre per runde
        n = int(ang // (TAU / 3))
        for j in range(n - 3, n + 1):
            if j < 0:
                continue
            age = (ang - j * TAU / 3) / (TAU / 3)    # i «tredjedels runder»
            if age < 0 or age > 3:
                continue
            side = (-1, 1, -0.2)[j % 3]
            px = cx + side * (70 + 60 * age) * sc
            py = head_y + (60 + 30 * age) * sc
            atp_mol(ctx, px, py, a * clamp(1.5 - age / 2) * clamp(age * 4), 0.8 * sc)


def synthase_backdrop(ctx, my, a=1.0, n_prot=40, t=0.0):
    rgba(ctx, C["ims"], 0.6 * a); ctx.rectangle(0, 0, W, my); ctx.fill()
    rgba(ctx, C["matrix"], 0.6 * a); ctx.rectangle(0, my, W, PANEL_Y - my); ctx.fill()
    for i in range(n_prot):
        px = 30 + TOP_PROTONS[i, 0] * (W - 60)
        py = 20 + TOP_PROTONS[i, 1] * (my - 75)
        px += 6 * math.sin(t * 2 + i); py += 4 * math.cos(t * 1.7 + i * 2)
        proton(ctx, px, py, 0.8 * a, 8)
    membrane(ctx, my, a=a)


def chorus_scene(ctx, u, t, final=False):
    rev_time = 2 * BEAT                      # én omdreining per halvnote
    ang = u / rev_time * TAU
    li = int(u // (2 * BAR))
    if not final:
        my = 150
        synthase_backdrop(ctx, my, n_prot=30, t=t)
        atp_synthase(ctx, 640, my, 1.15, ang, t=t)
        text(ctx, "ATP-syntase", 40, my + 70, 26, C["white"], 0.9, align="left", bold=True)
        text(ctx, "ADP + Pᵢ → ATP", 40, my + 104, 20, C["atp"], 0.9, align="left")
    else:
        my = 170
        synthase_backdrop(ctx, my, n_prot=45, t=t)
        for k, x in enumerate((250, 640, 1030)):
            atp_synthase(ctx, x, my, 0.85, ang + k * 1.3, t=t)
    made = int(ang // (TAU / 3)) * (3 if final else 1)
    badge(ctx, f"ATP laget: {made}", 1120, 50, 1.0, C["atp"], 22)
    badge(ctx, "3 ATP per runde", 1120, 110, smooth((u - 2 * 2 * BAR) / 0.5) if li >= 2 else 0.0, C["hl"], 20)
    if li >= 3:
        badge(ctx, "≈ 100+ omdreininger i sekundet!", 640 if final else 1040, 520 if final else 300,
              smooth((u - 3 * 2 * BAR) / 0.5), C["O"], 20)


def topview(ctx, cx, cy, r, ang, a=1.0):
    """F1-hodet sett ovenfra: tre β-lommer bytter mellom Løs, Tett/stram og Åpen."""
    rgba(ctx, (0, 0, 0), 0.45 * a); ctx.arc(cx, cy, r * 1.25, 0, TAU); ctx.fill()
    rot_state = int(ang // (TAU / 3))
    for k in range(6):
        th = k * TAU / 6 - TAU / 4
        lx, ly = cx + math.cos(th) * r * 0.62, cy + math.sin(th) * r * 0.62
        if k % 2 == 0:
            st = "LTO"[(rot_state + k // 2) % 3]
            rgba(ctx, C["beta"], a); ctx.arc(lx, ly, r * 0.36, 0, TAU); ctx.fill()
            rgba(ctx, C[st], a); ctx.set_line_width(5); ctx.arc(lx, ly, r * 0.36, 0, TAU); ctx.stroke()
            text(ctx, st, lx, ly + 9, 26, C[st], a, bold=True)
            if st == "O":
                age = (ang % (TAU / 3)) / (TAU / 3)
                atp_mol(ctx, lx + math.cos(th) * r * 0.6 * age, ly + math.sin(th) * r * 0.6 * age,
                        a * (1 - age), 0.7)
        else:
            rgba(ctx, C["alpha"], a); ctx.arc(lx, ly, r * 0.32, 0, TAU); ctx.fill()
    # γ som asymmetrisk kam i midten
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang)
    rgba(ctx, C["gamma"], a); ellipse(ctx, r * 0.08, 0, r * 0.2, r * 0.12); ctx.fill()
    ctx.restore()
    text(ctx, "L = løs   T = tett (stram)   O = åpen", cx, cy + r * 1.25 + 30, 17, C["white"], a)


def verse2_scene(ctx, u, t):
    my = 150
    ang = u / (4 * BEAT) * TAU
    li = int(u // (2 * BAR))
    lu = u - li * 2 * BAR
    synthase_backdrop(ctx, my, n_prot=26, t=t)
    hl = ["a", "ring", "gamma", "head"][li]
    atp_synthase(ctx, 420, my, 1.15, ang, hl=hl, t=t)
    labels = [("F₀ – protonporten i membranen", "a-underenheten slipper H⁺ inn og ut"),
              ("c-ringen – rotoren", "hver c-del bærer ett proton en runde rundt"),
              ("γ-stilken – drivakselen", "vrir seg inne i det faste F₁-hodet"),
              ("β-lommene bytter form", "løs → tett → åpen: ATP slippes fri")]
    title, sub = labels[li]
    al = smooth(lu / 0.5)
    if li < 3:
        text(ctx, title, 690, 300, 28, C["hl"], al, align="left", bold=True)
        text(ctx, sub, 690, 338, 20, C["white"], al * 0.9, align="left")
    else:
        text(ctx, title, 960, 60, 26, C["hl"], al, align="center", bold=True)
        topview(ctx, 960, 300, 140, ang, al)


def bridge_scene(ctx, u, t):
    li = int(u // (2 * BAR))
    if li < 2:
        a = smooth(u / 0.6) * (1 - smooth((u - 9.2) / 0.4))
        # menneskesilhuett som fylles med ATP
        cx, top = 360, 70
        ctx.save()
        ctx.new_path()
        ctx.arc(cx, top + 50, 45, 0, TAU)
        rrect(ctx, cx - 75, top + 105, 150, 200, 50)
        rrect(ctx, cx - 70, top + 290, 60, 180, 28)
        rrect(ctx, cx + 10, top + 290, 60, 180, 28)
        rrect(ctx, cx - 120, top + 115, 45, 170, 22)
        rrect(ctx, cx + 75, top + 115, 45, 170, 22)
        rgba(ctx, (0.3, 0.35, 0.55), 0.6 * a); ctx.fill_preserve()
        ctx.clip()
        level = top + 480 - 420 * smooth(u / 9.0)
        g = cairo.LinearGradient(0, level, 0, top + 480)
        g.add_color_stop_rgba(0, 1.0, 0.9, 0.4, a); g.add_color_stop_rgba(1, 1.0, 0.6, 0.15, a)
        ctx.set_source(g); ctx.rectangle(0, level + 4 * math.sin(t * 3), W, 600); ctx.fill()
        for i in range(14):
            bx = cx - 60 + (i * 37) % 120
            by = top + 470 - ((t * 60 + i * 47) % 400)
            if by > level:
                rgba(ctx, (1, 1, 0.8), 0.5 * a); ctx.arc(bx, by, 4, 0, TAU); ctx.fill()
        ctx.restore()
        text(ctx, "Hver dag lager du", 860, 180, 30, C["white"], a, bold=True)
        text(ctx, "≈ din egen kroppsvekt", 860, 250, 44, C["atp"], a, bold=True)
        text(ctx, "i ATP", 860, 310, 44, C["atp"], a, bold=True)
        text(ctx, "Hvert ATP-molekyl gjenbrukes", 860, 400, 22, C["white"], a * 0.85)
        text(ctx, "hundrevis av ganger i døgnet", 860, 430, 22, C["white"], a * 0.85)
    else:
        a = smooth((u - 9.6) / 0.6)
        cx, cy = 360, 280
        glow(ctx, cx, cy, 230, C["atp"], 0.35 * a)
        g = cairo.RadialGradient(cx - 40, cy - 40, 20, cx, cy, 160)
        g.add_color_stop_rgba(0, 1.0, 0.92, 0.55, a); g.add_color_stop_rgba(1, 0.75, 0.52, 0.12, a)
        ctx.set_source(g); ctx.arc(cx, cy, 150, 0, TAU); ctx.fill()
        rgba(ctx, (0.55, 0.36, 0.05), a); ctx.set_line_width(6); ctx.arc(cx, cy, 132, 0, TAU); ctx.stroke()
        text(ctx, "NOBEL", cx, cy - 20, 34, (0.45, 0.28, 0.02), a, bold=True)
        text(ctx, "1997", cx, cy + 32, 46, (0.45, 0.28, 0.02), a, bold=True)
        text(ctx, "Nobelprisen i kjemi 1997", 870, 170, 32, C["hl"], a, bold=True)
        text(ctx, "Paul D. Boyer & John E. Walker", 870, 225, 26, C["white"], a)
        text(ctx, "for å ha forklart hvordan", 870, 300, 21, C["white"], a * 0.85)
        text(ctx, "ATP-syntase lager ATP", 870, 330, 21, C["white"], a * 0.85)
        # liten spinnende motor
        ctx.save(); ctx.translate(870, 380); ctx.scale(0.55, 0.55)
        membrane(ctx, 30, -300, 300, a=a)
        atp_synthase(ctx, 0, 30, 1.0, t * TAU / 1.2, show_flux=False, a=a)
        ctx.restore()


def verse1_scene(ctx, u, t):
    if u < 9.6:
        z = smooth((u - 7.6) / 2.0)
        ctx.save()
        s = 1 + 5 * z
        ctx.translate(640, 290); ctx.scale(s, s); ctx.translate(-640, -(290 + 150 * z))
        glow_a = 0.0 if u < 4.8 else 0.5 + 0.4 * math.sin(t * 6)
        mito(ctx, 640, 290, 880, 384, glow_a)
        ctx.restore()
        if u < 7.4:
            la = smooth(u / 0.6) * (1 - smooth((u - 6.8) / 0.6))
            text(ctx, "Mitokondrie – cellens kraftverk", 640, 50, 28, C["white"], la, bold=True)
            if u >= 4.8:
                badge(ctx, "indre membran (cristae)", 640, 560, smooth((u - 4.8) / 0.5) * la, C["hl"], 20)
        if u > 8.4:
            etc_scene(ctx, u - 8.4, smooth((u - 8.4) / 1.2))
    else:
        etc_scene(ctx, u - 8.4, 1.0)


def intro_scene(ctx, u):
    cell_scene(ctx, smooth((u - 3.0) / 6.6))
    a = smooth((u - 0.4) / 1.0) * (1 - smooth((u - 6.0) / 1.0))
    if a > 0:
        rgba(ctx, (0, 0, 0), 0.4 * a); ctx.rectangle(0, 210, W, 160); ctx.fill()
        text(ctx, "Den minste motoren", 640, 290, 64, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "en sang om ATP-syntase – cellens roterende motor", 640, 340, 24, C["hl"], a)


def outro_scene(ctx, u):
    cell_scene(ctx, 1 - smooth(u / 6.0))
    a = smooth((u - 5.0) / 1.2)
    if a > 0:
        rgba(ctx, (0, 0, 0), 0.45 * a); ctx.rectangle(0, 210, W, 170); ctx.fill()
        text(ctx, "Den minste motoren", 640, 290, 60, C["white"], a, bold=True, font=LYRIC_FONT)
        text(ctx, "BiologyTunes", 640, 345, 26, C["hl"], a, bold=True)


# ---------------------------------------------------------------- lyrikk-panel
def lyric_panel(ctx, t):
    g = cairo.LinearGradient(0, PANEL_Y - 20, 0, H)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(0.15, 0, 0, 0, 0.72); g.add_color_stop_rgba(1, 0, 0, 0, 0.85)
    ctx.set_source(g); ctx.rectangle(0, PANEL_Y - 20, W, H - PANEL_Y + 20); ctx.fill()
    sec = next((s for s in SECTIONS_T if s["t0"] <= t < s["t1"]), SECTIONS_T[-1])
    text(ctx, sec["label"].upper(), 28, PANEL_Y + 18, 14, C["hl"], 0.8, align="left", bold=True)
    # fremdriftslinje
    rgba(ctx, (1, 1, 1), 0.15); ctx.rectangle(0, H - 4, W, 4); ctx.fill()
    rgba(ctx, C["hl"], 0.8); ctx.rectangle(0, H - 4, W * t / DURATION, 4); ctx.fill()

    cur = next((i for i, l in enumerate(LINES) if l["t0"] - 0.4 <= t < l["t1"] - 0.4), None)
    if cur is None:
        nxt = next((l for l in LINES if 0 < l["t0"] - t < 2.4), None)
        if nxt:
            text(ctx, nxt["text"], 640, PANEL_Y + 80, 26, (0.75, 0.75, 0.8), 0.7, font=LYRIC_FONT)
        elif sec["name"] in ("intro", "outro"):
            text(ctx, "♪   ♪   ♪", 640, PANEL_Y + 70, 30, (0.8, 0.8, 0.9), 0.6)
        return
    line = LINES[cur]
    size = 38
    ctx.select_font_face(LYRIC_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    space = ctx.text_extents(" ").x_advance
    tokens = line["text"].split()
    widths = [ctx.text_extents(w).x_advance for w in tokens]
    total = sum(widths) + space * (len(tokens) - 1)
    if total > W - 80:
        size = size * (W - 80) / total
        ctx.set_font_size(size)
        space = ctx.text_extents(" ").x_advance
        widths = [ctx.text_extents(w).x_advance for w in tokens]
        total = sum(widths) + space * (len(tokens) - 1)
    x = 640 - total / 2
    y = PANEL_Y + 62
    wi = 0
    for tok, w in zip(tokens, widths):
        prog = 0.0
        if any(ch.isalnum() for ch in tok):
            wt = line["words"][wi]; wi += 1
            prog = clamp((t - wt["t0"]) / max(0.05, wt["t1"] - wt["t0"]))
        else:   # tankestrek følger forrige ord
            prog = 1.0 if wi and t >= line["words"][wi - 1]["t1"] else 0.0
        ctx.move_to(x, y); rgba(ctx, (1, 1, 1), 0.92); ctx.show_text(tok)
        if prog > 0:
            ctx.save(); ctx.rectangle(x - 2, y - size, w * prog + 2, size * 1.4); ctx.clip()
            ctx.move_to(x, y); rgba(ctx, C["hl"]); ctx.show_text(tok)
            ctx.restore()
        x += w + space
    if cur + 1 < len(LINES) and LINES[cur + 1]["t0"] - line["t1"] < 0.1:
        text(ctx, LINES[cur + 1]["text"], 640, PANEL_Y + 112, 22, (0.7, 0.7, 0.78), 0.75, font=LYRIC_FONT)


# ---------------------------------------------------------------- ramme
def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_GOOD)
    background(ctx)
    sec = next((s for s in SECTIONS_T if s["t0"] <= t < s["t1"]), SECTIONS_T[-1])
    u = t - sec["t0"]
    nm = sec["name"]
    if nm == "intro":
        intro_scene(ctx, u)
    elif nm == "verse1":
        verse1_scene(ctx, u, t)
    elif nm == "chorus":
        chorus_scene(ctx, u, t)
    elif nm == "verse2":
        verse2_scene(ctx, u, t)
    elif nm == "bridge":
        bridge_scene(ctx, u, t)
    elif nm == "chorus2":
        chorus_scene(ctx, u, t, final=True)
    else:
        outro_scene(ctx, u)
    # kort kryssfade-effekt (svart blink) ved seksjonsskifter
    for s in SECTIONS_T[1:]:
        d = abs(t - s["t0"])
        if d < 0.25 and s["name"] not in ("verse1",):
            rgba(ctx, (0, 0, 0), 0.6 * (1 - d / 0.25)); ctx.paint()
    lyric_panel(ctx, t)
    if t > DURATION - 2.0:
        rgba(ctx, (0, 0, 0), smooth((t - (DURATION - 2.0)) / 2.0)); ctx.paint()
    surf.flush()
    return surf


def frame_bytes(i):
    return bytes(render(i / FPS).get_data())


def main():
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            render(float(arg)).write_to_png(f"preview_{arg}.png")
        return
    n = int(DURATION * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", "audio.wav",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        "den-minste-motoren.mp4"], stdin=subprocess.PIPE)
    with Pool() as pool:
        for k, buf in enumerate(pool.imap(frame_bytes, range(n), chunksize=8)):
            ff.stdin.write(buf)
            if k % 300 == 0:
                print(f"{k}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("den-minste-motoren.mp4 ferdig")


if __name__ == "__main__":
    main()
