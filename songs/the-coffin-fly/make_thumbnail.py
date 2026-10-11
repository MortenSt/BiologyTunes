"""YouTube-thumbnail (1280×720) for «The Coffin Fly» -> thumbnail.png"""
import importlib.util
import os

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
# lastes under eget navn: flere mapper har en make_video.py
_spec = importlib.util.spec_from_file_location("tcf_video", os.path.join(HERE, "make_video.py"))
v = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v)
v.PANEL_Y = 720   # jorda helt ned, ingen tekstpanel

W, H = 1280, 720
surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
ctx = cairo.Context(surf)
gy = 210
v.dusk_sky(ctx, 60.0)
# grav til høyre: stein over lukket kiste, turkis duftsky som stiger opp
ctx.save(); ctx.translate(220, 0)
v.gravestone(ctx, gy)
ctx.restore()
v.soil(ctx, 60.0, gy)
v.glow(ctx, 860, 420, 260, (0.3, 1.0, 0.9), 0.18)
for k, t in enumerate((61.0, 66.3, 71.7, 77.1)):
    v.scent(ctx, t, 860, 560, 860, gy + 20)
v.coffin(ctx, 860, 600, 400, 1.0, 0.6)
# stor phoride på vei ned mot kista
v.glow(ctx, 1110, 390, 140, (0.3, 1.0, 0.9), 0.12)
v.phorid(ctx, 1120, 390, 6.0, -1, 1.0, 0.0, 0.15)
# mørk tone bak tittelen
g = cairo.LinearGradient(0, 0, 620, 0)
g.add_color_stop_rgba(0, 0, 0, 0, 0.75); g.add_color_stop_rgba(1, 0, 0, 0, 0)
ctx.set_source(g); ctx.rectangle(0, 0, 620, H); ctx.fill()
for i, (word, col) in enumerate((("THE", (1, 1, 1)), ("COFFIN", (0.35, 0.95, 0.88)), ("FLY", (1, 1, 1)))):
    y = 170 + i * 112
    v.text(ctx, word, 52, y + 5, 108, (0, 0, 0), 0.7, align="left", bold=True, font=v.LYRIC_FONT)
    v.text(ctx, word, 46, y, 108, col, 1, align="left", bold=True, font=v.LYRIC_FONT)
v.rgba(ctx, v.C["hl"]); v.rrect(ctx, 48, 430, 530, 62, 14); ctx.fill()
v.text(ctx, "NAVIGATOR OF THE GRAVE", 313, 476, 36, (0.15, 0.10, 0.02), 1, bold=True, font=v.LYRIC_FONT)
v.text(ctx, "the tiny fly that finds buried remains", 48, 540, 25, (0.92, 0.92, 0.95), 0.95, align="left", font=v.LYRIC_FONT)
v.text(ctx, "BiologyTunes", 48, 668, 26, v.C["hl"], 0.9, align="left", bold=True, font=v.SANS)
surf.write_to_png(os.path.join(HERE, "thumbnail.png"))
print("thumbnail.png skrevet")
