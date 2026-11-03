#!/usr/bin/env python3
# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Generate assets/icon.png and icon.ico (golden gear with a D). Requires Pillow."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

GOLD, BG = (240, 179, 35, 255), (27, 27, 28, 255)
OUT = Path(__file__).resolve().parent


def gear_points(cx, cy, r, n=10):
    step = 2 * math.pi / n
    pts = []
    for i in range(n):
        a = step * i
        for da, rr in ((-0.30, 0.83), (-0.18, 1.0), (0.18, 1.0), (0.30, 0.83)):
            pts.append((cx + r * rr * math.cos(a + step * da), cy + r * rr * math.sin(a + step * da)))
    return pts


def render(size=1024):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 5, fill=BG)
    cx = cy = size / 2
    r = size * 0.40
    d.polygon(gear_points(cx, cy, r), fill=GOLD)
    d.ellipse((cx - r * .62, cy - r * .62, cx + r * .62, cy + r * .62), fill=BG)
    d.ellipse((cx - r * .52, cy - r * .52, cx + r * .52, cy + r * .52), outline=GOLD, width=int(size * .012))
    font = None
    for f in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "LiberationSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(f, int(r * 0.85))
            break
        except OSError:
            pass
    d.text((cx, cy), "D", fill=GOLD, font=font, anchor="mm")
    return img


img = render()
img.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
img.save(OUT / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("ok")
