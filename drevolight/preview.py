# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Effect preview: an approximation of the firmware effects drawn on the keyboard layout.

`effect_colors` is a pure function (easy to test); `PreviewPanel` animates it on a read-only
keyboard view. The real firmware may differ in timing and exact look.
"""
import colorsys
import math
import random
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .core import LAYOUTS, build_layout, tr
from .gfx import mix
from .keyboard_view import KeyboardView
from .state import normalise

BLACK = "#000000"
MEM_FADE = 1.6  # seconds a pressed key stays lit in the "memory" effect


def key_positions(layout_id, size_id):
    """Map key id -> (x, y) centre in layout units, plus the bounding box (w, h)."""
    shape, loc = LAYOUTS[layout_id]
    keys, _panels, width = build_layout(shape == "iso", loc, size_id == "tkl")
    pos = {}
    for kid, _label, rects, poly in keys:
        if poly:
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            pos[kid] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        else:
            x, y, w, h = rects[0]
            pos[kid] = (x + w / 2, y + h / 2)
    return pos, (width, 6.5)


def period(speed):
    """Seconds for one cycle of an effect: 5 s at speed 0 down to 0.8 s at speed 100."""
    return 5.0 - 4.2 * min(max(speed, 0), 100) / 100


def _hue(h):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, 1.0, 1.0)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def effect_colors(name, t, params, pos, extent, presses=None):
    """Colors {key: '#rrggbb'} of every key at time `t` (seconds).

    params: dict(color1, color2, bright, speed, dir ('e','w','s','n'), rainbow).
    presses: {key: press_time} for the memory effect.
    """
    c1, c2 = params["color1"], params["color2"]
    k = min(max(params["bright"], 0), 100) / 100
    per = period(params["speed"])
    w, h = extent
    xs = normalise([p[0] for p in pos.values()]) if pos else []
    out = {}
    if name == "static":
        for n, x in zip(pos, xs):
            out[n] = _hue(x * 0.83) if params["rainbow"] else c1
    elif name == "breath":
        ph = t / (per * 1.5)
        level = (1 - math.cos(2 * math.pi * ph)) / 2          # 0..1 smooth pulse
        col = c1 if int(ph) % 2 == 0 else c2                  # alternate colors each breath
        out = {n: mix(BLACK, col, level) for n in pos}
    elif name == "radar":
        ang = (t / per) % 1.0
        for n, (x, y) in pos.items():
            a = (math.atan2(y - h / 2, x - w / 2) / (2 * math.pi)) % 1.0
            d = (ang - a) % 1.0                                # 0 = sweep head, 1 = just ahead
            tail = max(0.0, 1 - d * 2.2)                       # trailing glow behind the head
            out[n] = mix(c2, c1, tail) if tail > 0 else mix(BLACK, c2, 0.12)
            out[n] = mix(BLACK, out[n], 0.15 + 0.85 * tail)
    elif name == "stream":
        d = params["dir"]
        for n, (x, y) in pos.items():
            u = x / max(w, 1e-6) if d in ("e", "w") else y / max(h, 1e-6)
            if d in ("w", "n"):
                u = 1 - u
            ph = (u * 1.2 - t / per) % 1.0
            out[n] = _hue(ph) if params["rainbow"] else mix(c1, c2, (1 - math.cos(2 * math.pi * ph)) / 2)
    else:  # mem_effect: keys tint when pressed and fade back
        for n in pos:
            age = t - (presses or {}).get(n, -1e9)
            out[n] = mix(BLACK, c1, 1 - age / MEM_FADE) if 0 <= age < MEM_FADE else mix(BLACK, c2, 0.15)
    return {n: mix(BLACK, c, k) for n, c in out.items()}


class _Host:
    """Minimal stand-in for MainWindow that KeyItem / KeyboardView need."""

    def __init__(self, win):
        self.pal, self.layout_id, self.size_id = win.pal, win.layout_id, win.size_id
        self.colors = {}

    def key_color(self, name):
        return self.colors.get(name, BLACK)

    def update_badge(self, _n):
        pass


class PreviewView(KeyboardView):
    """Read-only keyboard: clicking a key 'types' it (visible in the memory effect)."""

    def __init__(self, host, on_press):
        super().__init__(host)
        self.on_press = on_press

    def build(self):
        super().build()
        for it in self.items.values():
            it.setFlag(it.GraphicsItemFlag.ItemIsSelectable, False)
            it.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, e):
        it = self.itemAt(e.position().toPoint())
        if it is not None and getattr(it, "name", None):
            self.on_press(it.name)
        e.accept()

    def mouseMoveEvent(self, e):
        e.accept()

    def mouseReleaseEvent(self, e):
        e.accept()


class PreviewPanel(QWidget):
    """Panel (embedded in the Effects tab) animating the effect currently configured there."""

    def __init__(self, win, get_params):
        super().__init__()
        self.get_params = get_params
        self.host = _Host(win)
        self.pos, self.extent = key_positions(win.layout_id, win.size_id)
        self.presses, self.t0, self.paused, self.pause_t = {}, time.monotonic(), False, 0.0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel("")
        self.title.setStyleSheet("font-weight: bold;")
        lay.addWidget(self.title)
        self.view = PreviewView(self.host, self.press)
        self.view.build()
        self.view.setMinimumHeight(260)
        lay.addWidget(self.view, 1)
        note = QLabel(tr("preview.note"))
        note.setWordWrap(True)
        lay.addWidget(note)
        row = QHBoxLayout()
        self.btn = QPushButton(tr("preview.pause"))
        self.btn.clicked.connect(self.toggle)
        row.addWidget(self.btn)
        row.addStretch(1)
        lay.addLayout(row)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def showEvent(self, e):
        super().showEvent(e)
        self.view.fit()
        self.tick()
        self.timer.start(33)  # animate only while visible

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def now(self):
        return (self.pause_t if self.paused else time.monotonic()) - self.t0

    def press(self, name):
        self.presses[name] = self.now()

    def toggle(self):
        if self.paused:
            self.t0 += time.monotonic() - self.pause_t  # resume without a time jump
        else:
            self.pause_t = time.monotonic()
        self.paused = not self.paused
        self.btn.setText(tr("preview.play" if self.paused else "preview.pause"))

    def tick(self):
        name, params = self.get_params()
        t = self.now()
        if name == "mem_effect" and not self.paused and random.random() < 0.08:
            self.press(random.choice(list(self.pos)))        # demo typing
        self.title.setText(tr(f"fx.{name}"))
        self.host.colors = effect_colors(name, t, params, self.pos, self.extent, self.presses)
        self.view.scene().update()
