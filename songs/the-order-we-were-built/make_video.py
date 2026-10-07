"""Musikkvideo for «The Order We Were Built» (Suno-lyd + animasjon + tekst).

Bruk:  python3 make_video.py            -> the-order-we-were-built.mp4
       python3 make_video.py 40 120     -> PNG-forhåndsvisning av gitte tidspunkt
Tidskoder justeres i timing.json.
"""
import bisect
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import cairo
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "den-minste-motoren"))
from make_video import (C, TAU, SANS, LYRIC_FONT, clamp, smooth, lerp, rgba, text, rrect,   # noqa: E402
                        ellipse, glow, proton, atp_mol, badge, atp_synthase, membrane, blob)
from lyrics_order import SECS, LINES, END, BEATS   # noqa: E402

W, H, FPS = 1280, 720, 30
PANEL_Y = 566
RNG = np.random.default_rng(11)
PTS = RNG.random((120, 3))
BEAT2 = BEATS[::2]


def pulse(t):
    i = bisect.bisect_right(BEAT2, t) - 1
    return math.exp(-(t - BEAT2[i]) / 0.18) if i >= 0 else 0.0


def bg(ctx, top, bottom):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bottom)
    ctx.set_source(g); ctx.paint()


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
    u = t - sec["t0"]
    a = smooth((u - 0.5) / 1.0) * (1 - smooth((t - sec["t1"] + 1.0) / 0.8))
    if a <= 0:
        return
    x, y, w = 20, 18, 380
    lines = wrap(ctx, sec["fact"], w - 28, 14.5)
    h = 66 + 20 * len(lines)
    rgba(ctx, (0, 0, 0), 0.55 * a); rrect(ctx, x, y, w, h, 14); ctx.fill()
    rgba(ctx, C["hl"], 0.7 * a); ctx.set_line_width(1.5); rrect(ctx, x, y, w, h, 14); ctx.stroke()
    text(ctx, sec["label"].upper(), x + 14, y + 24, 12.5, C["hl"], a, align="left", bold=True)
    text(ctx, sec["era"], x + 14, y + 48, 19, C["white"], a, align="left", bold=True)
    for i, l in enumerate(lines):
        text(ctx, l, x + 14, y + 72 + 20 * i, 14.5, (0.88, 0.9, 0.95), a, align="left")


# ------------------------------------------------------------------ scener
def vent_scene(ctx, t, zoom=0.0):
    bg(ctx, (0.02, 0.10, 0.16), (0.01, 0.03, 0.06))
    # svake lysstriper ovenfra
    for i in range(5):
        x = 200 + i * 230 + 40 * math.sin(t * 0.2 + i)
        g = cairo.LinearGradient(x, 0, x + 120, 400)
        g.add_color_stop_rgba(0, 0.4, 0.7, 0.8, 0.05); g.add_color_stop_rgba(1, 0.4, 0.7, 0.8, 0)
        ctx.set_source(g); ctx.move_to(x, 0); ctx.line_to(x + 60, 0); ctx.line_to(x + 220, 560); ctx.line_to(x + 120, 560); ctx.fill()
    ctx.save()
    s = 1 + 1.6 * zoom
    ctx.translate(760, 330); ctx.scale(s, s); ctx.translate(-760, -330)
    # havbunn
    rgba(ctx, (0.12, 0.10, 0.09)); ctx.move_to(0, 560)
    for x in range(0, W + 40, 40):
        ctx.line_to(x, 530 + 12 * math.sin(x * 0.02))
    ctx.line_to(W, H); ctx.line_to(0, H); ctx.fill()
    # skorsteiner
    for cx, top, wd in ((760, 120, 150), (980, 300, 90), (560, 330, 80)):
        ctx.move_to(cx - wd, 545)
        for k in range(9):
            f = k / 8
            ctx.line_to(cx - wd * (1 - 0.55 * f) + 12 * math.sin(k * 2.1), lerp(545, top, f))
        for k in range(9):
            f = 1 - k / 8
            ctx.line_to(cx + wd * (1 - 0.55 * f) + 10 * math.cos(k * 1.7), lerp(545, top, f))
        ctx.close_path()
        g = cairo.LinearGradient(cx - wd, 0, cx + wd, 0)
        g.add_color_stop_rgb(0, 0.30, 0.27, 0.24); g.add_color_stop_rgb(0.5, 0.62, 0.58, 0.50); g.add_color_stop_rgb(1, 0.25, 0.22, 0.20)
        ctx.set_source(g); ctx.fill()
        for k in range(30):   # porer
            px = cx + (PTS[k, 0] - 0.5) * wd * 1.1
            py = lerp(530, top + 20, PTS[k, 1])
            rgba(ctx, (0.12, 0.1, 0.1), 0.6); ctx.arc(px, py, 2 + 3 * PTS[k, 2], 0, TAU); ctx.fill()
        # varm, alkalisk plume
        for k in range(26):
            p = (t * 0.15 + PTS[k, 2]) % 1.0
            px = cx + (PTS[k, 0] - 0.5) * 50 * (1 + 2 * p) + 10 * math.sin(t + k)
            py = top - p * 260
            glow(ctx, px, py, 22 + 30 * p, (0.55, 0.85, 1.0), 0.18 * (1 - p))
    ctx.restore()
    # protoner i det sure havet
    for k in range(40):
        px = (PTS[k, 0] * W + 15 * t * (0.5 + PTS[k, 2])) % W
        py = 60 + PTS[k + 40, 1] * 420 + 8 * math.sin(t + k)
        proton(ctx, px, py, 0.45, 7)


def wall_scene(ctx, t, u):
    """Tverrsnitt av en tynn mineralvegg: surt hav (H⁺) til høyre, alkalisk ventilvæske til venstre."""
    bg(ctx, (0.03, 0.08, 0.16), (0.02, 0.04, 0.08))
    wx = 700
    g = cairo.LinearGradient(0, 0, wx, 0)
    g.add_color_stop_rgba(0, 0.15, 0.35, 0.65, 0.5); g.add_color_stop_rgba(1, 0.15, 0.35, 0.65, 0.15)
    ctx.set_source(g); ctx.rectangle(0, 0, wx, PANEL_Y); ctx.fill()
    g = cairo.LinearGradient(wx, 0, W, 0)
    g.add_color_stop_rgba(0, 0.75, 0.35, 0.15, 0.15); g.add_color_stop_rgba(1, 0.75, 0.35, 0.15, 0.45)
    ctx.set_source(g); ctx.rectangle(wx, 0, W - wx, PANEL_Y); ctx.fill()
    # mineralvegg (FeS)
    rgba(ctx, (0.35, 0.30, 0.25)); ctx.rectangle(wx - 34, 0, 68, PANEL_Y); ctx.fill()
    for k in range(60):
        rgba(ctx, (0.2 + 0.2 * PTS[k, 2], 0.17, 0.12), 0.9)
        ctx.arc(wx - 30 + PTS[k, 0] * 60, PTS[k, 1] * PANEL_Y, 3 + 5 * PTS[k + 1, 2], 0, TAU); ctx.fill()
    text(ctx, "alkaline vent fluid", 150, 522, 20, (0.6, 0.8, 1.0), 0.9, bold=True)
    text(ctx, "pH ≈ 10", 150, 546, 16, (0.6, 0.8, 1.0), 0.8)
    text(ctx, "acidic ocean", 1080, 470, 22, (1.0, 0.65, 0.45), 0.9, bold=True)
    text(ctx, "pH ≈ 6  ·  many H⁺", 1080, 500, 18, (1.0, 0.65, 0.45), 0.8)
    for k in range(45):
        px = wx + 60 + PTS[k, 0] * (W - wx - 80) + 6 * math.sin(t * 1.5 + k)
        py = 30 + PTS[k, 1] * 400 + 6 * math.cos(t * 1.3 + k)
        proton(ctx, px, py, 0.85, 9)
    # Ingen enzymer ennå: protoner siver gjennom porer i veggen, og FeS-klynger på
    # den alkaliske siden katalyserer CO₂ + H₂ → organiske molekyler.
    pores = (110, 230, 350, 470)
    for py in pores:
        rgba(ctx, (0.05, 0.08, 0.14), 0.9); rrect(ctx, wx - 34, py - 9, 68, 18, 9); ctx.fill()
        p = (t * 0.6 + py * 0.01) % 1.0
        proton(ctx, lerp(wx + 34, wx - 34, p), py, math.sin(p * math.pi), 8)
        # FeS-klynge (kubanstruktur) der poren munner ut
        cx, cy = wx - 62, py
        for j, (dx, dy) in enumerate(((-9, -9), (9, -9), (-9, 9), (9, 9))):
            col = (0.75, 0.35, 0.20) if j in (0, 3) else (0.95, 0.85, 0.25)
            rgba(ctx, col); ctx.arc(cx + dx, cy + dy, 7, 0, TAU); ctx.fill()
        glow(ctx, cx, cy, 34, (1.0, 0.8, 0.3), 0.25 + 0.25 * pulse(t))
        # produkter («organics») som driver ut i den alkaliske væsken
        q = (t * 0.35 + py * 0.013) % 1.0
        ox, oy = cx - 30 - 160 * q, cy + 25 * math.sin(q * 5 + py)
        rgba(ctx, (0.6, 1.0, 0.7), 0.9 * (1 - q)); ctx.arc(ox, oy, 6, 0, TAU); ctx.fill()
        ctx.arc(ox - 11, oy + 5, 4, 0, TAU); ctx.fill()
    for k in range(10):   # H₂ fra ventilvæsken
        p = (t * 0.2 + PTS[k, 2]) % 1.0
        hx = 80 + PTS[k, 0] * 420; hy = lerp(540, 60, p)
        rgba(ctx, (0.85, 0.95, 1), 0.6 * (1 - p)); ctx.arc(hx - 4, hy, 5, 0, TAU); ctx.fill(); ctx.arc(hx + 4, hy, 5, 0, TAU); ctx.fill()
    text(ctx, "H₂", 300, 120, 16, (0.85, 0.95, 1), 0.7)
    text(ctx, "FeS mineral catalysts", wx - 62, 30, 15, (1, 0.85, 0.4), 0.85, align="right", bold=True)
    if u > 2:
        badge(ctx, "the gradient drives chemistry: CO₂ + H₂ → organics", 940, 524, smooth((u - 2) / 1), C["hl"], 17)
    # «The engine was here before the fire»: et spøkelse av den fremtidige motoren
    lines = next(s for s in SECS if s["key"] == "verse1")["lines"]
    ga = smooth((t - lines[6]["t0"]) / 1.5)
    if ga > 0:
        ctx.save(); ctx.translate(430, 280)
        ctx.push_group()
        membrane(ctx, 0, -130, 130)
        atp_synthase(ctx, 0, 0, 0.6, t / 1.6 * TAU, show_flux=False)
        ctx.pop_group_to_source(); ctx.paint_with_alpha(0.35 * ga)
        ctx.restore()
        badge(ctx, "later: ATP synthase evolves to tap the same gradient", 395, 478, ga, (0.8, 0.85, 1.0), 16)


LAYERS = [("Breath  (O₂)", "≈ 2.4 Ga", (0.30, 0.55, 0.85)),
          ("Krebs wheel", "", (0.30, 0.65, 0.40)),
          ("Glycolysis — the ancient core", "", (0.80, 0.62, 0.25)),
          ("Proton gradient", "≈ 4 Ga", (0.70, 0.32, 0.22))]


def strata_scene(ctx, t, u, sec, final=False):
    bg(ctx, (0.08, 0.07, 0.10), (0.04, 0.03, 0.05))
    x0, x1, y0, y1 = 440, 1250, 60, 548
    hh = (y1 - y0) / 4
    dur = sec["t1"] - sec["t0"]
    # lag lyser opp ett for ett nedenfra, deretter alle
    order_t = clamp(u / (dur * 0.5)) * 4
    p = pulse(t)
    for i, (name, age, col) in enumerate(LAYERS):
        rank = 3 - i                     # 0 = eldst (nederst)
        lit = 1.0 if final else smooth(order_t - rank)
        ytop = y0 + i * hh
        ctx.move_to(x0, ytop)
        for x in range(x0, x1 + 1, 20):
            ctx.line_to(x, ytop + 6 * math.sin(x * 0.015 + i))
        for x in range(x1, x0 - 1, -20):
            ctx.line_to(x, ytop + hh + 6 * math.sin(x * 0.015 + i + 1))
        ctx.close_path()
        k = 0.35 + 0.65 * lit + 0.1 * p * lit
        rgba(ctx, tuple(min(1, c * k) for c in col)); ctx.fill()
        for j in range(40):     # sedimentkorn
            rgba(ctx, (0, 0, 0), 0.12)
            ctx.arc(x0 + PTS[j + i * 10, 0] * (x1 - x0), ytop + 10 + PTS[j, 1] * (hh - 20), 2 + 2 * PTS[j, 2], 0, TAU); ctx.fill()
        text(ctx, name, x0 + 30, ytop + hh / 2 + 9, 26, C["white"], 0.4 + 0.6 * lit, align="left", bold=True)
        cx, cy = x1 - 90, ytop + hh / 2
        a = 0.4 + 0.6 * lit
        if rank == 0:
            for q in range(4):
                proton(ctx, cx - 40 + q * 26, cy + 10 * math.sin(t * 3 + q), a, 9)
        elif rank == 1:
            ctx.save(); ctx.translate(cx, cy)
            rgba(ctx, (1, 0.9, 0.6), a); ctx.set_line_width(4); ctx.new_path()
            for q in range(6):
                th = q * TAU / 6
                ctx.line_to(30 * math.cos(th), 30 * math.sin(th))
            ctx.close_path(); ctx.stroke(); ctx.restore()
        elif rank == 2:
            ctx.save(); ctx.translate(cx, cy); ctx.rotate(t * 1.5)
            rgba(ctx, (0.8, 1, 0.8), a); ctx.set_line_width(5); ctx.new_path()
            ctx.arc(0, 0, 32, 0.3, TAU - 0.3); ctx.stroke()
            ctx.move_to(32, -14); ctx.line_to(42, 6); ctx.line_to(22, 6); ctx.fill()
            ctx.restore()
        else:
            for q in (-1, 1):
                rgba(ctx, (0.85, 0.92, 1), a); ctx.arc(cx + q * 16, cy, 18, 0, TAU); ctx.fill()
            text(ctx, "O₂", cx, cy + 7, 18, (0.1, 0.2, 0.5), a, bold=True)
    # tidsakse
    rgba(ctx, (1, 1, 1), 0.5); ctx.set_line_width(2); ctx.move_to(x0 - 20, y1); ctx.line_to(x0 - 20, y0); ctx.stroke()
    ctx.move_to(x0 - 28, y0 + 14); ctx.line_to(x0 - 20, y0); ctx.line_to(x0 - 12, y0 + 14); ctx.stroke()
    text(ctx, "today", x0 - 30, y0 + 4, 14, C["white"], 0.7, align="right")
    text(ctx, "4 billion", x0 - 30, y1 - 14, 14, C["white"], 0.7, align="right")
    text(ctx, "years ago", x0 - 30, y1 + 2, 14, C["white"], 0.7, align="right")
    # «dig down through time»: bor som går nedover i andre halvdel
    if u > dur * 0.5 or final:
        q = smooth((u - dur * 0.5) / (dur * 0.35)) if not final else (0.5 + 0.5 * math.sin(u * 0.4))
        dy = lerp(y0 - 10, y1 - 30, q)
        rgba(ctx, C["hl"], 0.9); ctx.set_line_width(5)
        ctx.move_to(x0 + (x1 - x0) * 0.62, y0 - 20); ctx.line_to(x0 + (x1 - x0) * 0.62, dy); ctx.stroke()
        glow(ctx, x0 + (x1 - x0) * 0.62, dy, 40, C["hl"], 0.6)
    if final:
        badge(ctx, "take one breath — and you run all four layers", 845, 40, smooth(u / 1.5), C["hl"], 18)


def glyco_scene(ctx, t, u):
    bg(ctx, (0.14, 0.08, 0.18), (0.06, 0.03, 0.08))
    for k in range(30):  # cytoplasma-partikler
        rgba(ctx, (0.8, 0.6, 1.0), 0.08)
        ctx.arc((PTS[k, 0] * W + 10 * t * PTS[k, 2]) % W, PTS[k, 1] * PANEL_Y, 10 + 20 * PTS[k, 2], 0, TAU); ctx.fill()
    text(ctx, "cytoplasm", 1180, 40, 18, (0.85, 0.7, 1), 0.7, align="right", bold=True)
    cyc = 9.0
    ph = (u % cyc) / cyc
    cy = 300
    # glukose (6 C) kommer inn
    if ph < 0.45:
        q = smooth(ph / 0.35)
        gx = lerp(470, 720, q)
        ctx.save(); ctx.translate(gx, cy); ctx.rotate(0.3 * math.sin(t))
        rgba(ctx, (1.0, 0.85, 0.5)); ctx.set_line_width(6); ctx.new_path()
        for i in range(6):
            th = i * TAU / 6
            ctx.line_to(60 * math.cos(th), 60 * math.sin(th))
        ctx.close_path(); ctx.stroke()
        for i in range(6):
            th = i * TAU / 6
            rgba(ctx, (0.3, 0.3, 0.3)); ctx.arc(60 * math.cos(th), 60 * math.sin(th), 10, 0, TAU); ctx.fill()
        ctx.restore()
        text(ctx, "glucose (6 C)", gx, cy + 100, 20, C["white"], 0.9, bold=True)
    else:
        q = smooth((ph - 0.45) / 0.3)
        for s in (-1, 1):
            px, py = 720 + 230 * q, cy + s * 110 * q
            rgba(ctx, (1.0, 0.6, 0.4)); ctx.set_line_width(5)
            ctx.move_to(px - 40, py + 25); ctx.line_to(px, py - 40); ctx.line_to(px + 40, py + 25); ctx.close_path(); ctx.stroke()
            text(ctx, "pyruvate (3 C)", px, py + 60, 17, C["white"], 0.9 * q, bold=True)
        for s in (-1, 1):   # 2 ATP-«mynter»
            a2 = smooth((ph - 0.55) / 0.15) * (1 - smooth((ph - 0.92) / 0.08))
            atp_mol(ctx, 720 + s * 60, cy - 120 - 40 * smooth((ph - 0.55) / 0.3), a2, 1.2)
        text(ctx, "net +2 ATP", 720, cy + 200, 26, C["atp"], smooth((ph - 0.6) / 0.15), bold=True)
    # «no oxygen needed»
    bx, by = 1100, 470
    rgba(ctx, (0.85, 0.92, 1), 0.85); ctx.arc(bx - 14, by, 18, 0, TAU); ctx.fill(); ctx.arc(bx + 14, by, 18, 0, TAU); ctx.fill()
    text(ctx, "O₂", bx, by + 7, 18, (0.1, 0.2, 0.5), 1, bold=True)
    rgba(ctx, (1, 0.3, 0.3)); ctx.set_line_width(6); ctx.arc(bx, by, 46, 0, TAU); ctx.stroke()
    ctx.move_to(bx - 32, by - 32); ctx.line_to(bx + 32, by + 32); ctx.stroke()
    text(ctx, "no oxygen needed", bx, by + 80, 17, C["white"], 0.85, bold=True)


KREBS = ["citrate", "isocitrate", "α-ketoglutarate", "succinyl-CoA", "succinate", "fumarate", "malate", "oxaloacetate"]


def krebs_scene(ctx, t, u, dur, half):
    fwd = u > half
    k = smooth((u - half + 1.5) / 3.0)   # overgang
    top = (lerp(0.05, 0.16, k), lerp(0.14, 0.08, k), lerp(0.10, 0.05, k))
    bg(ctx, top, (0.02, 0.03, 0.04))
    cx, cy, R = 800, 300, 190
    # vinkel: baklengs først, så forlengs (kontinuerlig)
    sp = 0.5
    ang = -sp * min(u, half) + sp * max(0.0, u - half) * 2
    col = (0.4, 0.85, 0.5) if not fwd else (1.0, 0.6, 0.3)
    rgba(ctx, col, 0.35); ctx.set_line_width(26); ctx.arc(cx, cy, R, 0, TAU); ctx.stroke()
    # piler langs ringen
    for i in range(8):
        th = ang + i * TAU / 8 + TAU / 16
        d = 1 if fwd else -1
        x, y = cx + R * math.cos(th), cy + R * math.sin(th)
        ctx.save(); ctx.translate(x, y); ctx.rotate(th + d * math.pi / 2)
        rgba(ctx, col, 0.9); ctx.move_to(12, 0); ctx.line_to(-8, -10); ctx.line_to(-8, 10); ctx.fill(); ctx.restore()
    for i, name in enumerate(KREBS):
        th = -math.pi / 2 + i * TAU / 8
        x, y = cx + R * math.cos(th), cy + R * math.sin(th)
        rgba(ctx, (0.1, 0.12, 0.15)); ctx.arc(x, y, 14, 0, TAU); ctx.fill()
        rgba(ctx, col); ctx.set_line_width(3); ctx.arc(x, y, 14, 0, TAU); ctx.stroke()
        tx = x + 34 * math.cos(th); ty = y + 34 * math.sin(th) + 5
        al = "left" if math.cos(th) > 0.3 else ("right" if math.cos(th) < -0.3 else "center")
        text(ctx, name, tx, ty, 15, C["white"], 0.85, align=al)
    # markør som kjører rundt
    th = ang * 2.2 - math.pi / 2
    glow(ctx, cx + R * math.cos(th), cy + R * math.sin(th), 36, col, 0.8)
    # CO₂ inn (bygger) eller ut (brenner)
    for j in range(6):
        p = (u * 0.35 + j / 6) % 1.0
        th = j * TAU / 6 + 0.4
        r = lerp(R + 170, R - 30, p) if not fwd else lerp(R - 30, R + 170, p)
        x, y = cx + r * math.cos(th), cy + r * math.sin(th)
        a = math.sin(p * math.pi)
        rgba(ctx, (0.2, 0.2, 0.2), a); ctx.arc(x, y, 11, 0, TAU); ctx.fill()
        rgba(ctx, (0.9, 0.3, 0.3), a); ctx.arc(x - 18, y, 9, 0, TAU); ctx.fill(); ctx.arc(x + 18, y, 9, 0, TAU); ctx.fill()
        text(ctx, "CO₂", x, y + 30, 13, C["white"], a)
    if not fwd:
        text(ctx, "reverse (reductive) TCA", cx, cy - 8, 22, (0.6, 1, 0.7), 1 - k, bold=True)
        text(ctx, "fixes CO₂ → builds the body", cx, cy + 22, 17, C["white"], 1 - k)
    else:
        text(ctx, "oxidative TCA (Krebs)", cx, cy - 8, 22, (1, 0.75, 0.5), k, bold=True)
        text(ctx, "burns fuel → CO₂ + energy", cx, cy + 22, 17, C["white"], k)


def bridge_scene(ctx, t, u, sec):
    ls = sec["lines"]
    def at(i):
        return ls[i]["t0"] - sec["t0"]
    if u < at(2):     # cyanobakterier fyller himmelen med O₂
        q = smooth(u / max(1, at(2)))
        sky = (lerp(0.45, 0.25, q), lerp(0.28, 0.50, q), lerp(0.15, 0.85, q))
        bg(ctx, sky, (0.03, 0.10, 0.18))
        rgba(ctx, (0.03, 0.18, 0.28)); ctx.rectangle(0, 300, W, PANEL_Y - 300); ctx.fill()
        n = int(lerp(5, 70, q))
        for k in range(n):
            x = 30 + PTS[k, 0] * (W - 60); y = 330 + PTS[k, 1] * 210
            ctx.save(); ctx.translate(x, y); ctx.rotate(PTS[k, 2] * 3)
            rgba(ctx, (0.2, 0.75, 0.35)); rrect(ctx, -16, -6, 32, 12, 6); ctx.fill(); ctx.restore()
        for k in range(int(n * 0.6)):
            p = (t * 0.12 + PTS[k, 2]) % 1.0
            x = 30 + PTS[k, 0] * (W - 60) + 10 * math.sin(t + k); y = lerp(320, 40, p)
            rgba(ctx, (0.9, 0.95, 1), 0.7 * (1 - p)); ctx.arc(x - 5, y, 6, 0, TAU); ctx.fill(); ctx.arc(x + 5, y, 6, 0, TAU); ctx.fill()
        badge(ctx, "Great Oxygenation Event · ~2.4 billion years ago", 840, 50, smooth(u / 1.0), C["hl"], 18)
    elif u < at(5):   # elektroner faller ned til O₂ → H₂O, ~10× mer ATP
        v = u - at(2)
        bg(ctx, (0.08, 0.10, 0.20), (0.03, 0.04, 0.08))
        x0, y0 = 470, 90
        for i in range(5):   # energitrapp
            rgba(ctx, (0.35, 0.55, 0.85), 0.8); rrect(ctx, x0 + i * 85, y0 + i * 75, 80, 16, 6); ctx.fill()
        p = (v / 2.2) % 1.0
        i = int(p * 5); f = p * 5 - i
        ex = x0 + 40 + (i + f) * 85; ey = y0 - 10 + i * 75 + (f ** 2) * 75
        glow(ctx, ex, ey, 26, C["electron"], 0.7)
        rgba(ctx, C["electron"]); ctx.arc(ex, ey, 9, 0, TAU); ctx.fill()
        text(ctx, "e⁻", ex, ey - 16, 16, C["electron"], 1, bold=True)
        ox, oy = x0 + 5 * 85 + 40, y0 + 5 * 75 + 10
        rgba(ctx, (0.85, 0.92, 1)); ctx.arc(ox - 14, oy, 18, 0, TAU); ctx.fill(); ctx.arc(ox + 14, oy, 18, 0, TAU); ctx.fill()
        text(ctx, "O₂", ox, oy + 7, 18, (0.1, 0.2, 0.5), 1, bold=True)
        text(ctx, "→ H₂O", ox + 75, oy + 7, 22, C["white"], 1, bold=True)
        text(ctx, "electron transport chain", x0 - 10, y0 - 40, 20, C["white"], 0.85, align="left", bold=True)
        # søylediagram
        b = smooth((v - 2) / 2)
        bx, by = 1080, 470
        for j, (lab, val, colr) in enumerate((("glycolysis", 2, C["L"]), ("with O₂", 30, C["O"]))):
            hgt = val * 11 * b
            rgba(ctx, colr, 0.9); ctx.rectangle(bx - 70 + j * 90, by - hgt, 60, hgt); ctx.fill()
            text(ctx, lab, bx - 40 + j * 90, by + 22, 14, C["white"], 0.9)
            text(ctx, f"~{val}", bx - 40 + j * 90, by - hgt - 10, 18, colr, b, bold=True)
        text(ctx, "ATP per glucose", bx - 5, by + 46, 15, C["white"], 0.8 * b)
    else:            # endosymbiose
        v = u - at(5)
        bg(ctx, (0.10, 0.12, 0.18), (0.04, 0.05, 0.08))
        cx, cy = 760, 300
        q = smooth(v / 6.0)
        rgba(ctx, (0.55, 0.75, 1.0), 0.18); ellipse(ctx, cx, cy, 300, 210); ctx.fill()
        rgba(ctx, (0.55, 0.75, 1.0), 0.8); ctx.set_line_width(4)
        # membranen buler innover og omslutter bakterien
        ctx.save(); ellipse(ctx, cx, cy, 300, 210); ctx.restore(); ctx.stroke()
        rgba(ctx, (0.45, 0.30, 0.65)); ellipse(ctx, cx - 120, cy - 30, 70, 60); ctx.fill()
        text(ctx, "nucleus", cx - 120, cy - 25, 15, C["white"], 0.8)
        bx = lerp(1180, cx + 130, q); by = lerp(260, cy + 40, q)
        ctx.save(); ctx.translate(bx, by); ctx.rotate(0.2)
        from make_video import mito
        mito(ctx, 0, 0, 120, 56)
        ctx.restore()
        if q > 0.6:
            a2 = smooth((q - 0.6) / 0.3)
            rgba(ctx, (0.55, 0.75, 1.0), 0.8 * a2); ctx.set_line_width(3); ellipse(ctx, bx, by, 72, 40); ctx.stroke()
        text(ctx, "oxygen-breathing bacterium", 1100, 200, 16, C["white"], 1 - q)
        badge(ctx, "endosymbiosis → the mitochondrion", 760, 552 - 20, smooth((v - 4) / 1.5), C["hl"], 18)


def outro_scene(ctx, t, u):
    bg(ctx, (0.04, 0.06, 0.12), (0.01, 0.02, 0.04))
    rgba(ctx, (0.10, 0.12, 0.25), 0.6); ctx.rectangle(0, 0, W, 200); ctx.fill()
    membrane(ctx, 200)
    atp_synthase(ctx, 760, 200, 1.2, t / (1.6 + 0.15 * u) * TAU, t=t)
    a = smooth((t - LINES[-1]["t1"] - 1.0) / 3)
    text(ctx, "The Order We Were Built", 640, 110, 52, C["white"], a, bold=True, font=LYRIC_FONT)
    text(ctx, "BiologyTunes", 640, 150, 22, C["hl"], a, bold=True)


def title_overlay(ctx, t):
    a = smooth((t - 0.8) / 1.5) * (1 - smooth((t - 9.5) / 1.5))
    if a <= 0:
        return
    rgba(ctx, (0, 0, 0), 0.35 * a); ctx.rectangle(0, 200, W, 170); ctx.fill()
    text(ctx, "The Order We Were Built", 640, 285, 62, C["white"], a, bold=True, font=LYRIC_FONT)
    text(ctx, "cellular respiration in the order it evolved — sung by ATP synthase", 640, 335, 21, C["hl"], a)


# ------------------------------------------------------------------ tekstpanel
def lyric_panel(ctx, t, sec):
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
    fade = smooth((t - l["t0"] + 0.3) / 0.3)
    prev = LINES[cur - 1] if cur > 0 and LINES[cur - 1]["section"] == l["section"] else None
    nxt = LINES[cur + 1] if cur + 1 < len(LINES) and LINES[cur + 1]["t0"] - l["t1"] < 3 else None
    if prev:
        text(ctx, prev["text"], 640, PANEL_Y + 26, 19, (0.65, 0.65, 0.72), 0.6, font=LYRIC_FONT)
    size = 36
    ctx.select_font_face(LYRIC_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    wdt = ctx.text_extents(l["text"]).x_advance
    if wdt > W - 80:
        size *= (W - 80) / wdt
    if "words" in l:
        karaoke(ctx, l, t, size)
    else:
        text(ctx, l["text"], 640, PANEL_Y + 78, size, lerp_col((1, 1, 1), C["hl"], fade), 1, bold=True, font=LYRIC_FONT)
    if nxt:
        text(ctx, nxt["text"], 640, PANEL_Y + 122, 20, (0.7, 0.7, 0.78), 0.7, font=LYRIC_FONT)


def karaoke(ctx, l, t, size):
    """Tegner linja og fyller hvert ord med farge mens det synges (ordtider fra stable-ts)."""
    ctx.select_font_face(LYRIC_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    toks = l["text"].split()
    space = ctx.text_extents(" ").x_advance
    widths = [ctx.text_extents(w).x_advance for w in toks]
    x = 640 - (sum(widths) + space * (len(toks) - 1)) / 2
    y = PANEL_Y + 78
    wi, prev_end = 0, -1.0
    for tok, w in zip(toks, widths):
        if any(ch.isalnum() for ch in tok) and wi < len(l["words"]):
            wd = l["words"][wi]; wi += 1
            prog = clamp((t - wd["start"]) / max(0.08, wd["end"] - wd["start"]))
            prev_end = wd["end"]
        else:   # tankestrek o.l. følger forrige ord
            prog = 1.0 if t >= prev_end else 0.0
        ctx.move_to(x, y); rgba(ctx, (1, 1, 1), 0.92); ctx.show_text(tok)
        if prog > 0:
            ctx.save(); ctx.rectangle(x - 2, y - size, w * prog + 2, size * 1.5); ctx.clip()
            ctx.move_to(x, y); rgba(ctx, C["hl"]); ctx.show_text(tok)
            ctx.restore()
        x += w + space


def lerp_col(a, b, x):
    return tuple(lerp(p, q, x) for p, q in zip(a, b))


# ------------------------------------------------------------------ ramme
def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    sec = next((s for s in SECS if s["t0"] <= t < s["t1"]), SECS[-1])
    u = t - sec["t0"]
    dur = sec["t1"] - sec["t0"]
    k = sec["key"]
    if k == "intro":
        vent_scene(ctx, t, smooth((u - 20) / 17))
        title_overlay(ctx, t)
    elif k == "verse1":
        wall_scene(ctx, t, u)
        if u < 1.5:   # overgang fra skorsteinen
            ctx.push_group(); vent_scene(ctx, t, 1.0); ctx.pop_group_to_source(); ctx.paint_with_alpha(1 - smooth(u / 1.5))
    elif k in ("chorus1", "chorus2"):
        strata_scene(ctx, t, u, sec)
    elif k == "final":
        strata_scene(ctx, t, u, sec, final=True)
    elif k == "verse2":
        glyco_scene(ctx, t, u)
    elif k == "verse3":
        krebs_scene(ctx, t, u, dur, sec["lines"][4]["t0"] - sec["t0"])
    elif k == "bridge":
        bridge_scene(ctx, t, u, sec)
    else:
                outro_scene(ctx, t, u)
    for s in SECS[1:]:
        d = t - s["t0"]
        if -0.3 < d < 0.3 and s["key"] != "verse1":
            rgba(ctx, (0, 0, 0), 0.7 * (1 - abs(d) / 0.3)); ctx.paint()
    if (k != "intro" or u > 11) and not (k == "outro" and t > LINES[-1]["t1"] + 0.5):
        fact_card(ctx, sec, t)
    lyric_panel(ctx, t, sec)
    if t < 1.0:
        rgba(ctx, (0, 0, 0), 1 - t); ctx.paint()
    if t > END - 2.5:
        rgba(ctx, (0, 0, 0), smooth((t - END + 2.5) / 2.5)); ctx.paint()
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
        os.path.join(HERE, "the-order-we-were-built.mp4")], stdin=subprocess.PIPE)
    with Pool() as pool:
        for k, buf in enumerate(pool.imap(frame_bytes, range(n), chunksize=8)):
            ff.stdin.write(buf)
            if k % 1500 == 0:
                print(f"{k}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print("ferdig")


if __name__ == "__main__":
    main()
