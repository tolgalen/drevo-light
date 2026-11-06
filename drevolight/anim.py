# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Animations driven by the PC: per-key frames streamed to the keyboard.

`animation_frame` is a pure function (easy to test); `AnimationThread` streams its frames
over one open HID session at a limited frame rate.
"""
import colorsys
import math
import os
import sys
import threading
import time

from PySide6.QtCore import QThread, Signal

from . import proto
from .keys import KEYCODES

ANIMATIONS = ("rainbow", "scanner", "gradient", "cpu")
FPS = 15


def key_positions(layout_keys):
    """{key id: x in 0..1} (horizontal center of each key), only for keys the keyboard can light."""
    centers = {kid: rects[0][0] + rects[0][2] / 2 for kid, _l, rects, _p in layout_keys if kid in KEYCODES}
    if not centers:
        return {}
    lo, hi = min(centers.values()), max(centers.values())
    span = (hi - lo) or 1.0
    return {kid: (x - lo) / span for kid, x in centers.items()}


def _mix(a, b, f):
    return tuple(a[i] + (b[i] - a[i]) * f for i in range(3))


class CpuMeter:
    """System CPU load in 0..1, smoothed. Linux: /proc/stat, Windows: GetSystemTimes, else load average."""

    def __init__(self):
        self._prev = self._read()
        self.value = 0.0

    @staticmethod
    def _read():
        """(busy, total) counters, or None when unsupported."""
        try:
            if sys.platform.startswith("linux"):
                with open("/proc/stat", encoding="ascii") as f:
                    v = [int(x) for x in f.readline().split()[1:9]]
                idle = v[3] + v[4]
                return sum(v) - idle, sum(v)
            if sys.platform.startswith("win"):
                import ctypes
                from ctypes import wintypes
                idle, kernel, user = (wintypes.FILETIME() for _ in range(3))
                ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
                val = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime  # noqa: E731
                total = val(kernel) + val(user)  # kernel time already includes idle time
                return total - val(idle), total
        except (OSError, ValueError, IndexError, AttributeError):
            pass
        return None

    def level(self):
        cur = self._read()
        if cur is not None and self._prev is not None:
            busy, total = cur[0] - self._prev[0], cur[1] - self._prev[1]
            raw = busy / total if total > 0 else self.value
            self._prev = cur
        elif hasattr(os, "getloadavg"):
            raw = os.getloadavg()[0] / (os.cpu_count() or 1)
        else:
            raw = 0.0
        self.value += (max(0.0, min(1.0, raw)) - self.value) * 0.35  # smoothing: no flicker
        return self.value


def animation_frame(name, t, xs, color1, color2, bright=100, speed=60, level=0.0):
    """{key: (r, g, b)} for time `t` (seconds). `xs`: {key: x in 0..1}. `level` (0..1) drives 'cpu'."""
    rate = 0.1 + speed / 100 * 0.9  # cycles per second
    gain = max(0, min(100, bright)) / 100
    phase = t * rate
    out = {}
    for k, x in xs.items():
        if name == "rainbow":
            rgb = tuple(c * 255 for c in colorsys.hsv_to_rgb((x - phase) % 1.0, 1.0, 1.0))
        elif name == "scanner":
            pos = abs(((phase * 2) % 2) - 1)  # bounces 0 -> 1 -> 0
            level = max(0.0, 1 - abs(x - pos) / 0.12)
            rgb = _mix(color2, color1, level) if level else color2
            rgb = tuple(c * (0.1 + 0.9 * level) for c in rgb)
        elif name == "cpu":
            # a bar from the left edge whose length is the load; its color goes from color1 to color2
            lit = x <= level + 0.02
            rgb = _mix(color1, color2, x) if lit else (0, 0, 0)
        elif name == "gradient":
            rgb = _mix(color1, color2, 0.5 + 0.5 * math.sin(2 * math.pi * (phase - x)))
        else:
            raise ValueError(f"unknown animation: {name!r}")
        out[k] = tuple(max(0, min(255, int(round(c * gain)))) for c in rgb)
    return out


class AnimationThread(QThread):
    """Streams frames until `stop()`; reports a failure (e.g. keyboard unplugged) once."""
    failed = Signal(str)

    def __init__(self, name, xs, color1, color2, bright, speed, path=None, parent=None):
        super().__init__(parent)
        self.args = (name, xs, color1, color2, bright, speed)
        self.path = path
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()
        self.wait()

    def run(self):
        name, xs, c1, c2, bright, speed = self.args
        keys = list(xs)
        meter = CpuMeter() if name == "cpu" else None
        try:
            with proto.Keyboard(forced_path=self.path).session() as s:
                start = time.monotonic()
                while not self._stop.is_set():
                    frame_start = time.monotonic()
                    colors = animation_frame(name, frame_start - start, xs, c1, c2, bright, speed,
                                             meter.level() if meter else 0.0)
                    s.send(proto.key_packets(keys, [colors[k] for k in keys]))
                    self._stop.wait(max(0.0, 1 / FPS - (time.monotonic() - frame_start)))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e) or e.__class__.__name__)
