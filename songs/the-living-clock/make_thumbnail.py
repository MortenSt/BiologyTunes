"""YouTube-thumbnail (1280×720) for «The Living Clock» -> thumbnail.png"""
import importlib.util
import math
import os

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
# lastes under eget navn: flere mapper har en make_video.py
_spec = importlib.util.spec_from_file_location("tlc_video", os.path.join(HERE, "make_video.py"))
v = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v)

W, H = 1280, 720
surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
ctx = cairo.Context(surf)
v.night(ctx, 3.0)
v.rgba(ctx, (0, 0, 0), 0.45); ctx.paint()
# klokke med livsstadier til høyre
v.glow(ctx, 930, 330, 330, (1, 0.7, 0.3), 0.18)
v.degree_clock(ctx, 1.2, 0.80, cx=930, cy=330, R=230)
v.fly(ctx, 1185, 625, 3.2, v.FLY_COLS["vicina"], -0.7, 0.0, 1.0)
# tittel til venstre
for i, (word, col) in enumerate((("THE", (1, 1, 1)), ("LIVING", v.C["hl"]), ("CLOCK", (1, 1, 1)))):
    y = 190 + i * 112
    v.text(ctx, word, 52, y + 5, 108, (0, 0, 0), 0.7, align="left", bold=True, font=v.LYRIC_FONT)
    v.text(ctx, word, 46, y, 108, col, 1, align="left", bold=True, font=v.LYRIC_FONT)
v.rgba(ctx, (0.95, 0.55, 0.25)); v.rrect(ctx, 48, 450, 420, 62, 14); ctx.fill()
v.text(ctx, "DEGREE DAYS", 258, 496, 40, (0.15, 0.06, 0.02), 1, bold=True, font=v.LYRIC_FONT)
v.text(ctx, "how blowflies tell the time since death", 48, 560, 25, (0.92, 0.92, 0.95), 0.95, align="left", font=v.LYRIC_FONT)
v.text(ctx, "BiologyTunes", 48, 668, 26, v.C["hl"], 0.9, align="left", bold=True, font=v.SANS)
surf.write_to_png(os.path.join(HERE, "thumbnail.png"))
print("thumbnail.png skrevet")
