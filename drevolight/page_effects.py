# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Effects page of the main window."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import preview
from .core import DIRS, EFFECT_IDS, tr


class EffectsPageMixin:
    def build_effects_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        g = QGroupBox(tr("fx.group"))
        gl = QGridLayout(g)
        gl.addWidget(QLabel(tr("fx.effect")), 0, 0)
        self.fx_combo = QComboBox()
        self.fx_combo.addItems([tr(f"fx.{k}") for k in EFFECT_IDS])
        self.fx_combo.setCurrentIndex(self.fx_state["effect"])
        gl.addWidget(self.fx_combo, 0, 1, 1, 2)
        self.fx_btn = []
        for i in range(2):
            gl.addWidget(QLabel(tr(f"fx.color{i + 1}")), 1 + i, 0)
            b = self.swatch(self.fx_color[i], 80)
            b.clicked.connect(lambda _=False, i=i: self.pick_fx(i))
            gl.addWidget(b, 1 + i, 1)
            self.fx_btn.append(b)
        self.fx_sliders = {}
        for r, (key, name) in enumerate((("bright", "fx.brightness"), ("speed", "fx.speed")), 3):
            gl.addWidget(QLabel(tr(name)), r, 0)
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 100)
            s.setValue(self.fx_state[key])
            lab = QLabel(str(self.fx_state[key]))
            s.valueChanged.connect(lambda val, lab=lab: lab.setText(str(val)))
            gl.addWidget(s, r, 1)
            gl.addWidget(lab, r, 2)
            self.fx_sliders[key] = s
        self.fx_rainbow = QCheckBox(tr("fx.rainbow"))
        self.fx_rainbow.setChecked(self.fx_state["rainbow"])
        gl.addWidget(self.fx_rainbow, 5, 0, 1, 3)
        gl.addWidget(QLabel(tr("fx.direction")), 6, 0)
        self.fx_dir = QComboBox()
        self.fx_dir.addItems([tr(f"dir.{d}") for d in DIRS])
        self.fx_dir.setCurrentIndex(self.fx_state["dir"])
        gl.addWidget(self.fx_dir, 6, 1)
        gl.setColumnStretch(1, 1)
        v.addWidget(g)
        brow = QHBoxLayout()
        b = QPushButton(tr("btn.apply_fx"))
        b.clicked.connect(lambda: self.apply_effect())
        brow.addWidget(b)
        brow.addStretch(1)
        v.addLayout(brow)
        self.preview_panel = preview.PreviewPanel(self, self.effect_params)
        v.addWidget(self.preview_panel, 10)
        v.addStretch(1)
        return w

    def effect_params(self):
        """(effect id, parameters) as currently set in the Effects tab, for the preview."""
        self.read_effect_widgets()
        st = self.fx_state
        return EFFECT_IDS[st["effect"]], dict(color1=self.fx_color[0], color2=self.fx_color[1],
                                              bright=st["bright"], speed=st["speed"], dir=DIRS[st["dir"]],
                                              rainbow=st["rainbow"])

    def pick_fx(self, n):
        hx = self.ask_color(self.fx_color[n])
        if hx:
            self.fx_color[n] = hx
            self.set_swatch(self.fx_btn[n], hx)

    def read_effect_widgets(self):
        self.fx_state.update(effect=self.fx_combo.currentIndex(), bright=self.fx_sliders["bright"].value(),
                             speed=self.fx_sliders["speed"].value(), dir=self.fx_dir.currentIndex(),
                             rainbow=self.fx_rainbow.isChecked())

    def write_effect_widgets(self):
        st = self.fx_state
        self.fx_combo.setCurrentIndex(st["effect"])
        self.fx_sliders["bright"].setValue(st["bright"])
        self.fx_sliders["speed"].setValue(st["speed"])
        self.fx_dir.setCurrentIndex(st["dir"])
        self.fx_rainbow.setChecked(st["rainbow"])
        for i in range(2):
            self.set_swatch(self.fx_btn[i], self.fx_color[i])
