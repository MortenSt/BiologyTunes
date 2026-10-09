"""YouTube-thumbnail (1280×720) for «Turning Light Into Life» -> thumbnail.png"""
import math
import os
import sys

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
# lastes under eget navn: både denne mappen og den-minste-motoren har en make_video.py
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("tlil_video", os.path.join(HERE, "make_video.py"))
_v = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_v)
C, LYRIC_FONT, SANS = _v.C, _v.LYRIC_FONT, _v.SANS
rgba, text, rrect, glow, sun, photon, leaf = _v.rgba, _v.text, _v.rrect, _v.glow, _v.sun, _v.photon, _v.leaf
chloroplast, o2, glucose = _v.chloroplast, _v.o2, _v.glucose

W, H = 1280, 720
surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
ctx = cairo.Context(surf)
g = cairo.LinearGradient(0, 0, W, H)
g.add_color_stop_rgb(0, 0.04, 0.10, 0.08); g.add_color_stop_rgb(1, 0.01, 0.03, 0.02)
ctx.set_source(g); ctx.paint()

# høyre side: sol -> fotoner -> stort blad med kloroplast-innfelling
glow(ctx, 1150, 90, 260, (1.0, 0.85, 0.4), 0.35)
sun(ctx, 1150, 90, 62, 0.4)
for x1, y1 in ((760, 420), (900, 330), (1000, 300), (700, 520)):   # lysstråler
    g2 = cairo.LinearGradient(1150, 90, x1, y1)
    g2.add_color_stop_rgba(0, 1, 0.9, 0.5, 0.55); g2.add_color_stop_rgba(1, 1, 0.9, 0.5, 0.0)
    ctx.set_source(g2); ctx.set_line_width(22); ctx.move_to(1150, 90); ctx.line_to(x1, y1); ctx.stroke()
for x1, y1, p in ((880, 300, 0.6), (960, 360, 0.75), (1040, 300, 0.55), (820, 400, 0.7)):
    photon(ctx, 1150, 90, x1, y1, p, 1.0)
leaf(ctx, 640, 640, 620, -0.62, (0.22, 0.64, 0.30))
leaf(ctx, 760, 700, 420, -1.05, (0.18, 0.52, 0.26))
# innfelt kloroplast i en lupe
rgba(ctx, (0, 0, 0), 0.35); ctx.arc(1010, 470, 150, 0, 2 * math.pi); ctx.fill()
ctx.save(); ctx.arc(1010, 470, 140, 0, 2 * math.pi); ctx.clip()
rgba(ctx, (0.62, 0.86, 0.50)); ctx.paint()
chloroplast(ctx, 1010, 470, 330, 170, 1.0)
ctx.restore()
rgba(ctx, (1, 1, 1), 0.9); ctx.set_line_width(7); ctx.arc(1010, 470, 142, 0, 2 * math.pi); ctx.stroke()
ctx.move_to(910, 570); ctx.line_to(860, 620); ctx.stroke()
for x, y in ((1160, 330), (1200, 380), (1180, 250)):
    o2(ctx, x, y, 1.3, 0.95)
glucose(ctx, 860, 250, 1.1, 1.0, label=False)

# venstre side: tittel
for i, (word, col) in enumerate((("TURNING", (1, 1, 1)), ("LIGHT", C["hl"]), ("INTO LIFE", (0.55, 0.95, 0.55)))):
    y = 200 + i * 112
    text(ctx, word, 52, y + 5, 104, (0, 0, 0), 0.6, align="left", bold=True, font=LYRIC_FONT)
    text(ctx, word, 46, y, 104, col, 1, align="left", bold=True, font=LYRIC_FONT)
rgba(ctx, (1, 1, 1), 0.92); rrect(ctx, 48, 470, 560, 62, 14); ctx.fill()
text(ctx, "6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂", 328, 512, 32, (0.08, 0.2, 0.1), 1, bold=True, font=SANS)
text(ctx, "photosynthesis — from photon to glucose", 48, 578, 25, (0.92, 0.95, 0.92), 0.95, align="left", font=LYRIC_FONT)
text(ctx, "BiologyTunes", 48, 668, 26, C["hl"], 0.9, align="left", bold=True, font=SANS)

surf.write_to_png(os.path.join(HERE, "thumbnail.png"))
print("thumbnail.png skrevet")
