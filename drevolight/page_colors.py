# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Colors page of the main window."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .common import KEY_BY_LOWER
from .core import CATEGORIES, PRESETS, luminance, tr
from .keys import KEYCODES


class ColorsPageMixin:
    def build_colors_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)

        g = QGroupBox(tr("colors.all"))
        h = QHBoxLayout(g)
        self.base_btn = self.swatch(self.base_color, 80)
        self.base_btn.clicked.connect(self.pick_base)
        h.addWidget(self.base_btn)
        for pid, hx in PRESETS.items():
            h.addWidget(self.preset_button(pid, hx, self.user_set_base))
        h.addStretch(1)
        v.addWidget(g)

        g = QGroupBox(tr("colors.groups"))
        gl = QGridLayout(g)
        self.cat_btn, self.cat_chk = {}, {}
        for i, cid in enumerate(CATEGORIES):
            chk = QCheckBox(tr(f"cat.{cid}"))
            chk.setChecked(self.cat_enabled[cid])
            chk.toggled.connect(lambda on, cid=cid: self.set_cat_enabled(cid, on))
            b = self.swatch(self.cat_color[cid], 48)
            b.clicked.connect(lambda _=False, cid=cid: self.pick_cat(cid))
            gl.addWidget(chk, i // 3, (i % 3) * 2)
            gl.addWidget(b, i // 3, (i % 3) * 2 + 1)
            self.cat_chk[cid], self.cat_btn[cid] = chk, b
        v.addWidget(g)

        g = QGroupBox(tr("colors.keys"))
        gl = QGridLayout(g)
        h = QHBoxLayout()
        h.addWidget(QLabel(tr("colors.key_prompt")))
        self.key_entry = QLineEdit()
        self.key_entry.setFixedWidth(110)
        comp = QCompleter(sorted(KEYCODES, key=str.lower))
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.key_entry.setCompleter(comp)
        self.key_entry.returnPressed.connect(self.add_key)
        h.addWidget(self.key_entry)
        self.key_btn = self.swatch(self.new_key_color, 48)
        self.key_btn.clicked.connect(self.pick_new_key)
        h.addWidget(self.key_btn)
        for key, fn in (("btn.add", self.add_key), ("btn.add_selection", self.add_selection),
                        ("btn.remove", self.remove_key)):
            b = QPushButton(tr(key))
            b.clicked.connect(lambda _=False, fn=fn: fn())
            h.addWidget(b)
        h.addStretch(1)
        gl.addLayout(h, 0, 0)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr("col.key"), tr("col.color")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        gl.addWidget(self.table, 1, 0)
        v.addWidget(g, 1)
        self.refresh_table()

        h = QHBoxLayout()
        for key, fn in (("btn.apply_colors", self.apply_colors), ("btn.off", self.turn_off),
                        ("btn.reset", self.reset_keyboard)):
            b = QPushButton(tr(key))
            b.clicked.connect(lambda _=False, fn=fn: fn())
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        return w

    def refresh_table(self):
        self.table.setRowCount(len(self.keys))
        for r, (k, c) in enumerate(self.keys.items()):
            self.table.setItem(r, 0, QTableWidgetItem(k))
            it = QTableWidgetItem(c)
            it.setBackground(QColor(c))
            it.setForeground(QColor("#000" if luminance(c) > 140 else "#fff"))
            self.table.setItem(r, 1, it)

    def set_base(self, hx):
        self.base_color = hx
        self.set_swatch(self.base_btn, hx)
        self.refresh_keys()

    def user_set_base(self, hx):
        if hx != self.base_color:
            self.checkpoint()
            self.set_base(hx)

    def pick_base(self):
        hx = self.ask_color(self.base_color)
        if hx:
            self.user_set_base(hx)

    def set_cat_enabled(self, cid, on):
        if self.cat_enabled[cid] != on:
            self.checkpoint()
            self.cat_enabled[cid] = on
        self.refresh_keys()

    def pick_cat(self, cid):
        hx = self.ask_color(self.cat_color[cid])
        if hx:
            self.checkpoint()
            self.cat_color[cid] = hx
            self.set_swatch(self.cat_btn[cid], hx)
            self.cat_enabled[cid] = True
            self.cat_chk[cid].blockSignals(True)
            self.cat_chk[cid].setChecked(True)
            self.cat_chk[cid].blockSignals(False)
            self.refresh_keys()

    def pick_new_key(self):
        hx = self.ask_color(self.new_key_color)
        if hx:
            self.new_key_color = hx
            self.set_swatch(self.key_btn, hx)

    def add_key(self):
        text = self.key_entry.text().strip()
        if not text:
            return
        name = KEY_BY_LOWER.get(text.lower())
        if name is None:
            self.status.setText(tr("msg.unknown_key", name=text))
            return
        self.checkpoint()
        self.keys[name] = self.new_key_color
        self.key_entry.clear()
        self.refresh_keys()

    def add_selection(self):
        sel = self.kv.selected()
        if not sel:
            self.status.setText(tr("msg.select_first"))
            return
        self.checkpoint()
        for n in sel:
            self.keys[n] = self.new_key_color
        self.refresh_keys()

    def remove_key(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        self.checkpoint()
        for idx in rows:
            self.keys.pop(self.table.item(idx, 0).text(), None)
        self.refresh_keys()
