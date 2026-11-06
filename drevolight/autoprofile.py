# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Automatic profiles: while a given process is running, switch to a profile (and back afterwards).

Works on any desktop (also Wayland) because it looks at running processes, not at the active window.
"""
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import core
from .core import tr

MAX_RULES = 20


def _norm(name):
    name = name.strip().lower()
    return name[:-4] if name.endswith(".exe") else name


def running_process_names():
    """Lower-case names of the running processes (without '.exe'). Empty set when not supported."""
    names = set()
    try:
        if sys.platform.startswith("linux"):
            for p in Path("/proc").iterdir():
                if not p.name.isdigit():
                    continue
                try:
                    names.add(_norm((p / "comm").read_text().strip()))
                    argv0 = (p / "cmdline").read_bytes().split(b"\0", 1)[0].decode(errors="replace")
                    if argv0:
                        names.add(_norm(os.path.basename(argv0)))
                except OSError:
                    continue
        elif sys.platform.startswith("win"):
            out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                                 timeout=10, creationflags=0x08000000).stdout
            names = {_norm(line.split('","')[0].strip('"')) for line in out.splitlines() if line}
        else:
            out = subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True, timeout=10).stdout
            names = {_norm(os.path.basename(line)) for line in out.splitlines() if line.strip()}
    except (OSError, subprocess.SubprocessError):
        pass
    names.discard("")
    return names


def pick_rule(rules, names, existing=None):
    """Profile slot of the first rule whose process is running (and whose slot exists), else None."""
    for r in rules:
        if _norm(r["process"]) in names and (existing is None or r["profile"] in existing):
            return r["profile"]
    return None


def clean_rules(raw):
    """Keep only well-formed rules: [{'process': str, 'profile': slot index}]."""
    rules = []
    if isinstance(raw, list):
        for r in raw[:MAX_RULES]:
            if (isinstance(r, dict) and isinstance(r.get("process"), str) and r["process"].strip()
                    and isinstance(r.get("profile"), int) and 0 <= r["profile"] < core.MAX_PROFILES):
                rules.append({"process": r["process"].strip()[:64], "profile": r["profile"]})
    return rules


class _Signals(QObject):
    names = Signal(object)


class _ScanJob(QRunnable):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals

    def run(self):
        self.signals.names.emit(running_process_names())


class AutoProfileMixin:
    def setup_auto_profile(self, cfg):
        self.auto_enabled = bool(cfg.get("auto_profile", False))
        self.auto_rules = clean_rules(cfg.get("auto_rules"))
        self._auto_target = None   # slot chosen by the rules right now
        self._auto_prev = None     # profile to return to when no rule matches any more
        self._auto_scanning = False
        self._auto_pool = QThreadPool(self)
        self._auto_pool.setMaxThreadCount(1)
        self._auto_signals = _Signals(self)
        self._auto_signals.names.connect(self._auto_names)
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self.auto_tick)
        self.auto_timer.start(3000)

    def stop_auto_profile(self):
        self.auto_timer.stop()
        self._auto_pool.waitForDone()

    def auto_tick(self):
        if self.auto_enabled and self.auto_rules and not self._auto_scanning:
            self._auto_scanning = True
            self._auto_pool.start(_ScanJob(self._auto_signals))

    def _auto_names(self, names):
        self._auto_scanning = False
        if not self.auto_enabled:
            return
        slots = core.load_profiles()
        target = pick_rule(self.auto_rules, names, {i for i, s in enumerate(slots) if s})
        if target == self._auto_target:
            return
        if self.is_dirty():
            return  # never discard the user's unsaved edits; try again on the next tick
        if target is not None:
            if self._auto_target is None:
                self._auto_prev = self.active_profile
            self.load_slot(target, ask=False, apply=True, silent=True)
        else:
            prev, self._auto_prev = self._auto_prev, None
            if prev is not None and slots[prev]:
                self.load_slot(prev, ask=False, apply=True, silent=True)
        self._auto_target = target

    def show_auto_profile_dialog(self):
        dlg = AutoProfileDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.auto_enabled, self.auto_rules = dlg.result_values()
            self._auto_target = self._auto_prev = None
            self.save_settings()


class AutoProfileDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.setWindowTitle(tr("auto.title"))
        self.resize(520, 420)
        self.slots = core.load_profiles()
        lay = QVBoxLayout(self)
        hint = QLabel(tr("auto.hint"))
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.enable = QCheckBox(tr("auto.enable"))
        self.enable.setChecked(win.auto_enabled)
        lay.addWidget(self.enable)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr("auto.process"), tr("auto.profile")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        for r in win.auto_rules:
            self._add_row(r["process"], r["profile"])
        row = QHBoxLayout()
        self.new_proc = QLineEdit()
        self.new_proc.setPlaceholderText("steam")
        self.new_proc.returnPressed.connect(self._add_clicked)
        row.addWidget(self.new_proc, 1)
        b = QPushButton(tr("auto.add"))
        b.clicked.connect(self._add_clicked)
        row.addWidget(b)
        b = QPushButton(tr("auto.remove"))
        b.clicked.connect(self._remove)
        row.addWidget(b)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addStretch(1)
        ok, cancel = QPushButton(tr("btn.ok")), QPushButton(tr("btn.cancel"))
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        lay.addLayout(row)

    def _add_row(self, process, profile):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(process))
        combo = QComboBox()
        for i, slot in enumerate(self.slots):
            combo.addItem(f"{i + 1:>2}.  " + (slot["name"] if slot else tr("profile.empty")), i)
        combo.setCurrentIndex(profile)
        self.table.setCellWidget(r, 1, combo)

    def _add_clicked(self):
        name = self.new_proc.text().strip()
        if name and self.table.rowCount() < MAX_RULES:
            self._add_row(name, 0)
            self.new_proc.clear()

    def _remove(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def result_values(self):
        rules = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            rules.append({"process": item.text() if item else "", "profile": self.table.cellWidget(r, 1).currentData()})
        return self.enable.isChecked(), clean_rules(rules)
