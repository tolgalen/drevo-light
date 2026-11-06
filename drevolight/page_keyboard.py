# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Keyboard page (selection, painting) of the main window."""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import dialogs
from .core import (
    KEY_GROUPS,
    LAYOUT_IDS,
    LAYOUTS,
    PRESETS,
    SIZE_IDS,
    build_layout,
    layout_columns,
    layout_rows,
    tr,
)
from .keyboard_view import KeyboardView
from .state import gradient_colors, normalise


class KeyboardPageMixin:
    def build_keyboard_page(self, sel_keep):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("kb.layout")))
        self.lay_combo = QComboBox()
        self.lay_combo.addItems([tr(f"layout.{i}") for i in LAYOUT_IDS])
        self.lay_combo.setCurrentIndex(LAYOUT_IDS.index(self.layout_id))
        self.size_combo = QComboBox()
        self.size_combo.addItems([tr(f"size.{i}") for i in SIZE_IDS])
        self.size_combo.setCurrentIndex(SIZE_IDS.index(self.size_id))
        self.lay_combo.activated.connect(self.on_layout_change)
        self.size_combo.activated.connect(self.on_layout_change)
        row.addWidget(self.lay_combo)
        row.addWidget(self.size_combo)
        hint = QLabel(tr("kb.hint2"))
        hint.setStyleSheet(f"color: {self.pal['sub']};")
        row.addWidget(hint, 1)
        v.addLayout(row)

        self.kv = KeyboardView(self)
        v.addWidget(self.kv, 1)
        self.kv.build()
        self.kv.select(sel_keep & set(self.kv.items))
        self.kv.scene().selectionChanged.connect(self.update_count)

        g = QGroupBox(tr("kb.selection"))
        gv = QVBoxLayout(g)
        h = QHBoxLayout()
        for key, fn in (("kb.all", lambda: set(self.kv.items)),
                        ("kb.none", lambda: set()),
                        ("kb.invert", lambda: set(self.kv.items) - self.kv.selected())):
            b = QPushButton(tr(key))
            b.clicked.connect(lambda _=False, fn=fn: self.set_selection(fn()))
            h.addWidget(b)
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        h.addWidget(sep)
        self._tkl_built = self.size_id == "tkl"
        for gid, ks in KEY_GROUPS.items():
            if gid == "group.numpad" and self.size_id == "tkl":  # no keypad on TKL
                continue
            b = QPushButton(tr(gid))
            b.clicked.connect(lambda _=False, ks=ks: self.set_selection(set(ks) & set(self.kv.items)))
            h.addWidget(b)
        h.addStretch(1)
        gv.addLayout(h)
        h = QHBoxLayout()
        h.addWidget(QLabel(tr("kb.rows")))
        shape, loc = LAYOUTS[self.layout_id]
        for n, ids in enumerate(layout_rows(build_layout(shape == "iso", loc, self.size_id == "tkl")[0]), 1):
            b = QPushButton(str(n))
            b.setFixedWidth(34)
            b.clicked.connect(lambda _=False, ids=ids: self.set_selection(set(ids)))
            h.addWidget(b)
        h.addStretch(1)
        gv.addLayout(h)
        h = QHBoxLayout()
        h.addWidget(QLabel(tr("kb.columns")))
        for n, ids in enumerate(layout_columns(build_layout(shape == "iso", loc, self.size_id == "tkl")[0]), 1):
            b = QPushButton(str(n))
            b.setFixedWidth(30)
            b.clicked.connect(lambda _=False, ids=ids: self.set_selection(set(ids)))
            h.addWidget(b)
        h.addStretch(1)
        gv.addLayout(h)
        v.addWidget(g)

        g = QGroupBox(tr("kb.color_group"))
        gv = QVBoxLayout(g)
        h = QHBoxLayout()
        self.paint_btn = self.swatch(self.paint_color)
        self.paint_btn.clicked.connect(self.pick_paint)
        h.addWidget(self.paint_btn)
        b = self.tip(QPushButton(tr("kb.paint")), "tip.paint")
        b.clicked.connect(lambda: self.paint(self.paint_color))
        h.addWidget(b)
        for pid, hx in PRESETS.items():
            h.addWidget(self.preset_button(pid, hx, self.paint))
        b = QPushButton(tr("kb.unpaint"))
        b.clicked.connect(self.unpaint)
        h.addWidget(b)
        h.addStretch(1)
        gv.addLayout(h)
        h = QHBoxLayout()
        h.addWidget(QLabel(tr("kb.recent")))
        self.recent_box = QHBoxLayout()
        h.addLayout(self.recent_box, 1)
        for key, fn, tip in (("kb.copy", self.copy_color, "tip.copy"), ("kb.paste", self.paste_color, "tip.paste"),
                             ("kb.gradient", self.gradient, "tip.gradient")):
            b = self.tip(QPushButton(tr(key)), tip)
            b.clicked.connect(fn)
            h.addWidget(b)
        gv.addLayout(h)
        self.refresh_recent()
        v.addWidget(g)

        h = QHBoxLayout()
        for key, fn, tip in (("kb.apply", self.apply_colors, "tip.apply"), ("btn.off", self.turn_off, "tip.off"),
                             ("btn.reset", self.reset_keyboard, "tip.reset"),
                             ("btn.clear_editor", self.clear_editor, "tip.clear")):
            b = self.tip(QPushButton(tr(key)), tip)
            b.clicked.connect(lambda _=False, fn=fn: fn())
            h.addWidget(b)
        self.live_chk = self.tip(QCheckBox(tr("kb.live")), "tip.live")
        self.live_chk.setChecked(self.live)
        self.live_chk.toggled.connect(self.set_live)
        h.addWidget(self.live_chk)
        h.addStretch(1)
        self.sel_lbl = QLabel("")
        h.addWidget(self.sel_lbl)
        v.addLayout(h)
        self.update_count()
        return w

    def set_selection(self, names):
        self.kv.end_drag()
        self.kv.select(names)

    def on_layout_change(self, _=None):
        self.layout_id = LAYOUT_IDS[self.lay_combo.currentIndex()]
        self.size_id = SIZE_IDS[self.size_combo.currentIndex()]
        self.save_settings()
        self.rebuild_keyboard()

    def rebuild_keyboard(self):
        QTimer.singleShot(0, self.build_ui)  # rows / numpad buttons depend on the layout

    def update_count(self):
        try:  # may fire while the previous scene is being destroyed
            self.sel_lbl.setText(tr("kb.count", n=len(self.kv.selected())))
            self.kv.scene().update()
        except RuntimeError:
            pass

    def refresh_keys(self, send=True):
        """Repaint the preview and, in live mode, send the colors to the keyboard."""
        if self.kv:
            self.kv.scene().update()
        if hasattr(self, "table"):
            self.refresh_table()
        self.update_title()
        if send and self.live:
            self.live_timer.start(250)

    # ---------- coloring ----------
    def paint(self, hx):
        sel = self.kv.selected()
        if not sel:
            self.status.setText(tr("msg.select_first"))
            return
        self.checkpoint()
        for n in sel:
            self.keys[n] = hx
        self.remember_color(hx)
        self.refresh_keys()

    def unpaint(self):
        if not self.kv.selected():
            return
        self.checkpoint()
        for n in self.kv.selected():
            self.keys.pop(n, None)
        self.refresh_keys()

    def pick_paint(self):
        hx = self.ask_color(self.paint_color)
        if hx:
            self.paint_color = hx
            self.set_swatch(self.paint_btn, hx)
            self.paint(hx)

    def copy_color(self):
        sel = sorted(self.kv.selected())
        if not sel:
            self.status.setText(tr("msg.select_first"))
            return
        self.clip_color = self.key_color(sel[0])
        self.paint_color = self.clip_color
        self.set_swatch(self.paint_btn, self.clip_color)
        self.status.setText(tr("msg.color_copied", color=self.clip_color))

    def paste_color(self):
        if self.clip_color is None:
            self.status.setText(tr("msg.no_copied_color"))
            return
        self.paint(self.clip_color)

    def gradient(self):
        sel = self.kv.selected()
        if not sel:
            self.status.setText(tr("msg.select_first"))
            return
        dlg = dialogs.GradientDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        cfg = dlg.result_config()
        names = sorted(sel)
        centers = [self.kv.items[n].sceneBoundingRect().center() for n in names]
        values = [c.x() if cfg["axis"] == "x" else c.y() for c in centers]
        colors = gradient_colors(normalise(values), cfg["mode"], cfg["color1"], cfg["color2"])
        self.checkpoint()
        for n, hx in zip(names, colors):
            self.keys[n] = hx
        for hx in (cfg["color1"], cfg["color2"]) if cfg["mode"] == "two" else ():
            self.remember_color(hx)
        self.refresh_keys()
