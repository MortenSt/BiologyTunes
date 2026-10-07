"""YouTube-thumbnail (1280×720) for «The Order We Were Built» -> thumbnail.png"""
import math
import os
import sys

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "den-minste-motoren"))
from make_video import C, TAU, LYRIC_FONT, SANS, rgba, text, glow, rrect, proton, membrane, atp_synthase  # noqa: E402

W, H = 1280, 720
LAYERS = [("BREATH  O₂", (0.30, 0.55, 0.88)), ("KREBS WHEEL", (0.30, 0.68, 0.42)),
          ("GLYCOLYSIS", (0.86, 0.66, 0.25)), ("PROTON GRADIENT", (0.76, 0.33, 0.22))]

surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
ctx = cairo.Context(surf)
g = cairo.LinearGradient(0, 0, W, H)
g.add_color_stop_rgb(0, 0.05, 0.06, 0.13); g.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
ctx.set_source(g); ctx.paint()

# jordlag til høyre, skrått avskåret
x0, y0, hh = 600, 40, 160
ctx.save()
ctx.move_to(x0 + 90, 0); ctx.line_to(W, 0); ctx.line_to(W, H); ctx.line_to(x0 - 60, H); ctx.close_path(); ctx.clip()
for i, (name, col) in enumerate(LAYERS):
    yt = y0 + i * hh
    ctx.move_to(x0 - 100, yt)
    for x in range(x0 - 100, W + 21, 20):
        ctx.line_to(x, yt + 8 * math.sin(x * 0.012 + i * 1.3))
    for x in range(W + 20, x0 - 121, -20):
        ctx.line_to(x, yt + hh + 8 * math.sin(x * 0.012 + i * 1.3 + 1.3))
    ctx.close_path(); rgba(ctx, col); ctx.fill()
    text(ctx, name, W - 30, yt + 42, 24, (1, 1, 1), 0.85, align="right", bold=True)
ctx.restore()
# protoner i det nederste laget
for k, (px, py) in enumerate(((760, 640), (840, 600), (930, 655), (1010, 610), (1100, 650), (1190, 615))):
    proton(ctx, px, py, 0.95, 14)

# ATP-syntase med glød, midt i lagene
glow(ctx, 830, 330, 280, C["atp"], 0.35)
ctx.save(); ctx.translate(830, 225)
rgba(ctx, (0.1, 0.1, 0.2), 0.0)
membrane(ctx, 0, -175, 175)
atp_synthase(ctx, 0, 0, 1.2, 0.9, show_flux=False)
ctx.restore()
# bevegelsespiler rundt rotoren
rgba(ctx, (1, 1, 1), 0.85); ctx.set_line_width(6)
ctx.new_path(); ctx.arc(830, 225, 112, math.radians(200), math.radians(250)); ctx.stroke()
ctx.new_path(); ctx.arc(830, 225, 112, math.radians(-70), math.radians(-20)); ctx.stroke()

# venstre side: tittel
rgba(ctx, (0, 0, 0), 0.0)
for i, word in enumerate(("THE ORDER", "WE WERE", "BUILT")):
    y = 210 + i * 108
    text(ctx, word, 52, y + 5, 100, (0, 0, 0), 0.6, align="left", bold=True, font=LYRIC_FONT)   # skygge
    text(ctx, word, 46, y, 100, C["hl"] if word == "BUILT" else (1, 1, 1), 1, align="left", bold=True, font=LYRIC_FONT)
rgba(ctx, C["hl"]); rrect(ctx, 48, 470, 470, 64, 14); ctx.fill()
text(ctx, "4 BILLION YEARS", 283, 515, 40, (0.1, 0.07, 0.02), 1, bold=True, font=LYRIC_FONT)
text(ctx, "of cellular respiration — in the order it evolved", 48, 580, 24, (0.92, 0.93, 0.97), 0.95, align="left", font=LYRIC_FONT)
text(ctx, "BiologyTunes", 48, 670, 26, C["hl"], 0.9, align="left", bold=True, font=SANS)

surf.write_to_png(os.path.join(HERE, "thumbnail.png"))
print("thumbnail.png skrevet")
