# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Editor state helpers (pure Python, no Qt): color resolution, snapshots and undo history."""
import colorsys
import copy

from .core import CAT_MEMBERS, CATEGORIES, mix


def resolve_color(name, base, cat_enabled, cat_color, keys):
    """Color of a key: individual key > enabled group > base color."""
    if name in keys:
        return keys[name]
    color = base
    for cid in CATEGORIES:
        if cat_enabled.get(cid) and name in CAT_MEMBERS[cid]:
            color = cat_color[cid]
    return color


def make_snapshot(base, cat_enabled, cat_color, keys):
    return {"base": base,
            "categories": {c: {"on": bool(cat_enabled[c]), "color": cat_color[c]} for c in CATEGORIES},
            "keys": dict(keys)}


def gradient_colors(positions, mode, color1="#ff0000", color2="#0000ff"):
    """Colors for a list of positions in [0, 1]: 'two' blends color1->color2, 'rainbow' sweeps the hue."""
    out = []
    for t in positions:
        if mode == "rainbow":
            r, g, b = colorsys.hsv_to_rgb(min(max(t, 0.0), 1.0) * 0.83, 1.0, 1.0)
            out.append("#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255)))
        else:
            out.append(mix(color1, color2, t))
    return out


def normalise(values):
    """Map numbers to [0, 1] (all equal -> 0.5)."""
    lo, hi = min(values), max(values)
    return [0.5] * len(values) if hi - lo < 1e-9 else [(v - lo) / (hi - lo) for v in values]


class History:
    """Undo / redo stacks of editor snapshots."""

    def __init__(self, limit=100):
        self.limit = limit
        self.undo_stack, self.redo_stack = [], []

    def push(self, state):
        """Record `state` (the editor BEFORE a change)."""
        if self.undo_stack and self.undo_stack[-1] == state:
            return
        self.undo_stack.append(copy.deepcopy(state))
        del self.undo_stack[:-self.limit]
        self.redo_stack.clear()

    def undo(self, current):
        if not self.undo_stack:
            return None
        self.redo_stack.append(copy.deepcopy(current))
        return self.undo_stack.pop()

    def redo(self, current):
        if not self.redo_stack:
            return None
        self.undo_stack.append(copy.deepcopy(current))
        return self.redo_stack.pop()

    @property
    def can_undo(self):
        return bool(self.undo_stack)

    @property
    def can_redo(self):
        return bool(self.redo_stack)

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
