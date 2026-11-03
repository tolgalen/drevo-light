# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Main window of Drevo Light."""
import json
import re
import time

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QActionGroup, QColor, QIcon, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QComboBox, QCompleter, QDialog,
                               QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
                               QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QPlainTextEdit, QPushButton, QSlider, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from . import core, dialogs, proto
from .core import (ASSETS_DIR, CATEGORIES, DIRS, EFFECT_IDS, I18, KEY_GROUPS, LAYOUT_IDS, LAYOUTS,
                   LIGHT_PRESETS, PRESETS, SIZE_IDS, THEME_IDS, THEMES, build_layout, hex_to_rgb,
                   layout_rows, luminance, tr)
from .gfx import _icon_cache, stylesheet, system_palette
from .keyboard_view import KeyboardView
from .keys import KEYCODES
from .state import History, gradient_colors, make_snapshot, normalise, resolve_color
from .widgets import Dot, LogoWidget, NavButton
from .worker import HardwareRunner

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_KEY_BY_LOWER = {k.lower(): k for k in KEYCODES}
MAX_RECENT = 12


def clean_color(value, default):
    return value if isinstance(value, str) and _HEX.match(value) else default


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        app.aboutToQuit.connect(_icon_cache.clear)  # avoids shutdown crashes with orphaned Qt objects
        self.default_style = app.style().objectName()
        self.system_qpalette = QPalette(app.palette())  # OS palette, captured before any theme change
        cfg = core.load_settings()
        I18.set(cfg.get("lang") or (core.locale.getlocale()[0] or "en")[:2])
        self.theme_id = cfg.get("theme") if cfg.get("theme") in THEME_IDS else "drevo"
        self.layout_id = cfg.get("layout") if cfg.get("layout") in LAYOUT_IDS else (
            I18.cur if I18.cur in LAYOUT_IDS else "us")
        self.size_id = cfg.get("size") if cfg.get("size") in SIZE_IDS else "tkl"
        self.live = bool(cfg.get("live", False))
        self.apply_on_load = bool(cfg.get("apply_on_load", False))
        self.apply_on_start = bool(cfg.get("apply_on_start", False))
        self.show_splash = bool(cfg.get("show_splash", True))
        self.recent = [c for c in cfg.get("recent", []) if _HEX.match(str(c))][:MAX_RECENT]
        for i, hx in enumerate(cfg.get("custom_colors", [])[:16]):
            if _HEX.match(str(hx)):
                QColorDialog.setCustomColor(i, QColor(hx))
        self.page = 0
        self.base_color = "#000000"  # start from an unlit keyboard
        self.cat_enabled = {c: False for c in CATEGORIES}
        self.cat_color = {c: "#ffffff" for c in CATEGORIES}
        ap = cfg.get("profile")
        self.active_profile = ap if isinstance(ap, int) and 0 <= ap < core.MAX_PROFILES else None
        self.keys = {}
        self.new_key_color = "#ff0000"
        self.paint_color = "#ff0000"
        self.clip_color = None
        self.fx_color = ["#ff0000", "#0000ff"]
        self.fx_state = dict(effect=0, bright=100, speed=60, dir=0, rainbow=False)
        self.last_mode = "colors"
        self.iface_list, self.iface_sel, self._sig = [], 0, None
        self.history = History()
        self.saved_state = self.snapshot()
        self.kv = None
        self.runner = HardwareRunner(self)
        self.runner.done.connect(self._hardware_done)
        self.live_timer = QTimer(self)
        self.live_timer.setSingleShot(True)
        self.live_timer.timeout.connect(lambda: self.apply_colors(silent=True))
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "icon.png")))
        self.resize(1180, 860)
        geo = cfg.get("geometry")
        if isinstance(geo, str):
            self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
        self.setMinimumSize(900, 640)
        QShortcut(QKeySequence.SelectAll, self, activated=lambda: self.kv and self.set_selection(set(self.kv.items)))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.build_ui()
        self.timer.start(2000)
        if self.apply_on_start and self.active_profile is not None:
            QTimer.singleShot(700, self.startup_apply)

    # ---------- settings / theme ----------
    def save_settings(self):
        core.save_settings({
            "lang": I18.cur, "theme": self.theme_id, "layout": self.layout_id, "size": self.size_id,
            "profile": self.active_profile, "live": self.live, "apply_on_load": self.apply_on_load,
            "apply_on_start": self.apply_on_start, "show_splash": self.show_splash,
            "recent": self.recent,
            "custom_colors": [QColorDialog.customColor(i).name() for i in range(QColorDialog.customCount())],
            "geometry": bytes(self.saveGeometry().toBase64()).decode(),
        })

    def closeEvent(self, e):
        self.live_timer.stop()
        self.runner.wait()
        self.save_settings()
        super().closeEvent(e)

    def apply_theme(self):
        app = self.app
        if self.theme_id == "system":
            # Fusion + the OS palette + our stylesheet: consistent look on every platform
            sp = self.system_qpalette
            app.setStyle("Fusion")
            app.setPalette(sp)
            self.pal = system_palette(sp.color(QPalette.Window).name(), sp.color(QPalette.Button).name(),
                                      sp.color(QPalette.Base).name(), sp.color(QPalette.WindowText).name(),
                                      sp.color(QPalette.Highlight).name(),
                                      sp.color(QPalette.HighlightedText).name())
            app.setStyleSheet(stylesheet(self.pal))
        else:
            self.pal = THEMES[self.theme_id]
            app.setStyle("Fusion")
            app.setStyleSheet(stylesheet(self.pal))

    def change_theme(self, tid):
        self.theme_id = tid
        self.save_settings()
        self.build_ui()

    def change_lang(self, code):
        I18.set(code)
        self.save_settings()
        self.build_ui()

    def key_color(self, name):
        return resolve_color(name, self.base_color, self.cat_enabled, self.cat_color, self.keys)

    # ---------- undo / redo / dirty state ----------
    def snapshot(self):
        return make_snapshot(self.base_color, self.cat_enabled, self.cat_color, self.keys)

    def checkpoint(self):
        """Call BEFORE changing colors so the change can be undone."""
        self.history.push(self.snapshot())
        self.update_edit_state()

    def update_edit_state(self):
        if getattr(self, "act_undo", None) is not None:
            self.act_undo.setEnabled(self.history.can_undo)
            self.act_redo.setEnabled(self.history.can_redo)
        self.update_title()

    def is_dirty(self):
        return self.snapshot() != self.saved_state

    def update_title(self):
        self.setWindowTitle(tr("app.title") + (" *" if self.is_dirty() else ""))

    def undo(self):
        state = self.history.undo(self.snapshot())
        if state is not None:
            self.restore_colors(state)

    def redo(self):
        state = self.history.redo(self.snapshot())
        if state is not None:
            self.restore_colors(state)

    def confirm_discard(self):
        """True when it is safe to replace the editor contents."""
        if not self.is_dirty():
            return True
        return QMessageBox.question(self, tr("app.title"), tr("profile.unsaved")) == QMessageBox.Yes

    # ---------- construction ----------
    def build_ui(self):
        self.apply_theme()
        P = self.pal
        sel_keep = self.kv.selected() if self.kv else set()
        self.act_undo = None
        self.build_menus()
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(8)

        # connection (top)
        g = QGroupBox(tr("state.group"))
        gl = QGridLayout(g)
        self.dot = Dot()
        self.conn_lbl = QLabel(tr("state.checking"))
        self.conn_lbl.setStyleSheet("font-weight: bold;")
        self.access_lbl = QLabel("")
        self.last_lbl = QLabel(tr("state.last_none"))
        gl.addWidget(self.dot, 0, 0, 2, 1)
        gl.addWidget(self.conn_lbl, 0, 1)
        gl.addWidget(self.access_lbl, 1, 1)
        gl.addWidget(self.last_lbl, 0, 2, 2, 1, Qt.AlignRight | Qt.AlignVCenter)
        gl.setColumnStretch(2, 1)
        h = QHBoxLayout()
        h.addWidget(QLabel(tr("iface.label")))
        self.iface_combo = QComboBox()
        self.iface_combo.setSizePolicy(self.iface_combo.sizePolicy().horizontalPolicy().Expanding,
                                       self.iface_combo.sizePolicy().verticalPolicy())
        self.iface_combo.activated.connect(lambda i: setattr(self, "iface_sel", i))
        h.addWidget(self.iface_combo, 1)
        for key, cmd in (("btn.redetect", self.refresh_ifaces), ("btn.diag", self.diagnostics),
                         ("btn.check", self.check_access)):
            b = QPushButton(tr(key))
            b.clicked.connect(cmd)
            h.addWidget(b)
        gl.addLayout(h, 2, 0, 1, 3)
        v.addWidget(g)

        # main area: sidebar + content
        main = QHBoxLayout()
        main.setSpacing(10)
        side = QFrame()
        side.setObjectName("side")
        side.setStyleSheet(f"QFrame#side {{ background: {P['canvas']}; border: 1px solid {P['panel_edge']};"
                           f" border-radius: 8px; }} QFrame#side QWidget {{ background: {P['canvas']}; }}")
        sl = QVBoxLayout(side)
        sl.setContentsMargins(8, 8, 8, 8)
        sl.addWidget(LogoWidget(P), 0, Qt.AlignHCenter)
        self.nav_group = QButtonGroup(self)
        self.stack = QStackedWidget()
        for i, (kind, key) in enumerate((("keyboard", "tab.keyboard"), ("palette", "tab.colors"),
                                         ("sparkles", "tab.effects"))):
            nb = NavButton(kind, tr(key), P)
            self.nav_group.addButton(nb, i)
            sl.addWidget(nb, 0, Qt.AlignHCenter)
        sl.addStretch(1)
        self.nav_group.idClicked.connect(self.show_page)
        main.addWidget(side)
        right = QVBoxLayout()
        self.kv = None
        self.stack.addWidget(self.build_keyboard_page(sel_keep))
        self.stack.addWidget(self.build_colors_page())
        self.stack.addWidget(self.build_effects_page())
        right.addWidget(self.stack, 1)
        main.addLayout(right, 1)
        v.addLayout(main, 1)

        # footer
        foot = QHBoxLayout()
        self.status = QLabel(tr("status.ready") if proto.hid else tr("status.nolibs"))
        foot.addWidget(self.status, 1)
        foot.addWidget(QLabel("http://www.drevo.es/"))
        v.addLayout(foot)

        self.setCentralWidget(root)
        self.show_page(self.page)
        self.restore_colors(self.snapshot(), send=False)  # sync the new widgets with the state
        self.update_edit_state()
        self.refresh_ifaces()

    # ---------- menus ----------
    def _check_action(self, menu, text, checked, slot):
        act = menu.addAction(text)
        act.setCheckable(True)
        act.setChecked(checked)
        act.toggled.connect(slot)
        return act

    def build_menus(self):
        mb = self.menuBar()
        mb.clear()
        m = mb.addMenu(tr("menu.file"))
        self._check_action(m, tr("menu.show_splash"), self.show_splash,
                           lambda on: (setattr(self, "show_splash", on), self.save_settings()))
        if dialogs.udev_supported():
            m.addAction(tr("menu.install_udev"), lambda: dialogs.install_udev_rules(self))
        m.addSeparator()
        act = m.addAction(tr("menu.quit"), self.close)
        act.setShortcut(QKeySequence.Quit)

        m = mb.addMenu(tr("menu.edit"))
        self.act_undo = m.addAction(tr("menu.undo"), self.undo)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo = m.addAction(tr("menu.redo"), self.redo)
        self.act_redo.setShortcuts([QKeySequence.Redo, QKeySequence("Ctrl+Shift+Z")])
        m.addSeparator()
        m.addAction(tr("menu.copy_color"), self.copy_color).setShortcut(QKeySequence.Copy)
        m.addAction(tr("menu.paste_color"), self.paste_color).setShortcut(QKeySequence.Paste)
        m.addSeparator()
        m.addAction(tr("menu.select_all"), lambda: self.set_selection(set(self.kv.items)))
        m.addAction(tr("menu.select_none"), lambda: self.set_selection(set()))
        m.addAction(tr("btn.clear_editor"), self.clear_editor)

        self.build_profiles_menu(mb)

        m = mb.addMenu(tr("menu.theme"))
        grp = QActionGroup(m)
        for tid in THEME_IDS:
            act = m.addAction(tr(f"theme.{tid}"))
            act.setCheckable(True)
            act.setChecked(tid == self.theme_id)
            grp.addAction(act)
            act.triggered.connect(lambda _=False, tid=tid: QTimer.singleShot(0, lambda: self.change_theme(tid)))
        m = mb.addMenu(tr("menu.language"))
        grp = QActionGroup(m)
        for code in I18.langs:
            act = m.addAction(I18.names[code])
            act.setCheckable(True)
            act.setChecked(code == I18.cur)
            grp.addAction(act)
            act.triggered.connect(lambda _=False, code=code: QTimer.singleShot(0, lambda: self.change_lang(code)))
        old = mb.cornerWidget(Qt.TopRightCorner)
        if old is not None:
            old.deleteLater()
        self.badge = QLabel(getattr(self, "_badge_text", ""))
        self.badge.setStyleSheet(f"color: {self.pal['sub']}; padding: 5px 12px; font-size: 12px;")
        mb.setCornerWidget(self.badge, Qt.TopRightCorner)
        m = mb.addMenu(tr("menu.help"))
        act = m.addAction(tr("menu.manual"), lambda: dialogs.show_manual(self))
        act.setShortcut(QKeySequence.HelpContents)
        m.addAction(tr("menu.about"), lambda: dialogs.show_about(self))
        m.addSeparator()
        m.addAction(tr("menu.license"), lambda: dialogs.show_licenses(self, 0))
        m.addAction(tr("menu.third_party"), lambda: dialogs.show_licenses(self, 1))
        self.update_edit_state()

    def update_badge(self, n):
        """Show the key count (e.g. 'TKL 88 KEYS') at the right end of the menu bar."""
        self._badge_text = tr("kb.badge_tkl" if self.size_id == "tkl" else "kb.badge_full", n=n)
        if getattr(self, "badge", None) is not None:
            self.badge.setText(self._badge_text)

    def show_page(self, i):
        self.page = i
        self.stack.setCurrentIndex(i)
        self.nav_group.button(i).setChecked(True)

    # ---------- helpers ----------
    def tip(self, widget, key):
        widget.setToolTip(tr(key))
        return widget

    def swatch(self, color, w=64):
        b = QPushButton()
        b.setFixedSize(w, 28)
        b.setCursor(Qt.PointingHandCursor)
        self.set_swatch(b, color)
        return b

    @staticmethod
    def set_swatch(b, color):
        b.setStyleSheet(f"background: {color}; border: 1px solid #888; border-radius: 6px;")

    def preset_button(self, pid, hx, slot):
        b = QPushButton(tr(f"preset.{pid}"))
        fg = "#000" if pid in LIGHT_PRESETS else "#fff"
        b.setStyleSheet(f"background: {hx}; color: {fg}; border: 1px solid #00000066;"
                        " border-radius: 6px; padding: 5px 8px;")
        b.clicked.connect(lambda _=False, hx=hx: slot(hx))
        return b

    def ask_color(self, initial):
        c = QColorDialog.getColor(QColor(initial), self)
        return c.name() if c.isValid() else None

    def remember_color(self, hx):
        if hx in self.recent:
            self.recent.remove(hx)
        self.recent.insert(0, hx)
        del self.recent[MAX_RECENT:]
        self.refresh_recent()

    def refresh_recent(self):
        box = getattr(self, "recent_box", None)
        if box is None:
            return
        while box.count():
            it = box.takeAt(0)
            if it.widget():
                it.widget().hide()
                it.widget().deleteLater()
        for hx in self.recent:
            b = self.swatch(hx, 26)
            b.setToolTip(hx)
            b.clicked.connect(lambda _=False, hx=hx: self.paint(hx))
            box.addWidget(b)
        box.addStretch(1)

    # ---------- page: keyboard ----------
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

    # ---------- page: colors ----------
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
        name = _KEY_BY_LOWER.get(text.lower())
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

    # ---------- page: effects ----------
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
        b = QPushButton(tr("btn.apply_fx"))
        b.clicked.connect(lambda: self.apply_effect())
        v.addWidget(b, 0, Qt.AlignLeft)
        v.addStretch(1)
        return w

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

    # ---------- connection ----------
    def refresh_ifaces(self):
        self.iface_list = proto.list_interfaces()
        self.iface_combo.clear()
        self.iface_combo.addItems([tr("iface.auto")] + [proto.describe(i) for i in self.iface_list])
        self.iface_sel = 0
        self.check_access()

    def set_conn(self, state, title, detail=""):
        self.dot.set_color({"ok": "#2e9e4f", "warn": "#e0a100", "off": "#cc3333"}[state])
        self.conn_lbl.setText(title)
        self.access_lbl.setText(detail)

    def check_access(self):
        if proto.hid is None:
            return self.set_conn("off", tr("conn.nolibs.title"), tr("conn.nolibs.detail"))
        ifs = proto.list_interfaces()
        if not ifs:
            return self.set_conn("off", tr("conn.nokbd.title"), tr("conn.nokbd.detail"))
        name = ifs[0].get("product_string") or "Drevo Tyrfing V2"
        ok = 0
        for i in ifs:
            try:
                d = proto.hid.device()
                d.open_path(i["path"])
                d.close()
                ok += 1
            except Exception:  # noqa: BLE001
                pass
        if ok:
            self.set_conn("ok", tr("conn.ok.title", name=name), tr("conn.ok.detail", ok=ok, total=len(ifs)))
        else:
            self.set_conn("warn", tr("conn.warn.title", name=name), tr("conn.warn.detail"))

    def poll(self):
        if self.runner.pending:  # do not touch the device while a command is being sent
            return
        sig = tuple(i["path"] for i in proto.list_interfaces())
        if sig != self._sig:
            first = self._sig is None
            was_empty = not self._sig
            self._sig = sig
            if not first:
                self.refresh_ifaces()
                # keyboard plugged back in: re-send the active profile (same option as "apply at start")
                if sig and was_empty and self.apply_on_start and self.active_profile is not None:
                    QTimer.singleShot(1000, self.startup_apply)

    def diagnostics(self):
        if proto.hid is None:
            return QMessageBox.critical(self, tr("diag.title"), tr("diag.nolibs"))
        lines = [tr("diag.searching", vid=f"{core.VID:04x}", pid=f"{core.PID:04x}"), ""]
        ifs = proto.list_interfaces()
        if not ifs:
            lines.append(tr("diag.nodevs"))
            others = list(proto.hid.enumerate(core.VID, 0))
            for d in others:
                lines.append(f"  PID=0x{d['product_id']:04x} {proto.describe(d)} "
                             f"{tr('diag.product')}={d.get('product_string')}")
            if not others:
                lines.append("  " + tr("diag.none"))
        for i in ifs:
            lines.append(proto.describe(i))
            lines.append(f"   {tr('diag.product')}={i.get('product_string')}  path={i['path']!r}")
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("diag.title"))
        dlg.resize(820, 380)
        lay = QVBoxLayout(dlg)
        te = QPlainTextEdit("\n".join(lines))
        te.setReadOnly(True)
        lay.addWidget(te)
        dlg.exec()

    # ---------- keyboard actions (run on a worker thread) ----------
    def run(self, fn, ok, silent=False):
        """Send `fn(keyboard)` to the keyboard without blocking the window."""
        sel = self.iface_sel
        path = self.iface_list[sel - 1]["path"] if 0 < sel <= len(self.iface_list) else None
        self.status.setText(tr("status.sending"))
        self.runner.submit(fn, path, context=(ok, silent))

    def _hardware_done(self, ctx, error):
        ok, silent = ctx or ("", True)
        stamp = time.strftime("%H:%M:%S")
        if not error:
            if self.runner.pending == 0:
                self.status.setText(ok)
            self.last_lbl.setText(tr("state.last", msg=ok, time=stamp))
            return
        self.status.setText(tr("status.error"))
        self.last_lbl.setText(tr("state.last_error", time=stamp))
        self.check_access()
        if not silent:
            QMessageBox.critical(self, tr("err.title"), tr("err.msg", err=error))

    def apply_colors(self, silent=False):
        plan = self.snapshot()
        self.last_mode = "colors"

        def job(k):
            k.kbd(hex_to_rgb(plan["base"]))
            for cid, val in plan["categories"].items():
                if val["on"]:
                    k.category(cid, hex_to_rgb(val["color"]))
            if plan["keys"]:
                k.key_set({n: hex_to_rgb(c) for n, c in plan["keys"].items()})
        self.run(job, tr("msg.colors_applied"), silent)

    def restore_colors(self, data, send=True):
        """Load the colors of `data` (a snapshot or a profile) into the editor widgets."""
        self.base_color = clean_color(data.get("base"), "#000000")
        self.set_swatch(self.base_btn, self.base_color)
        cats = data.get("categories", {})
        for c in CATEGORIES:
            val = cats.get(c, {}) if isinstance(cats.get(c, {}), dict) else {}
            self.cat_enabled[c] = bool(val.get("on", False))
            self.cat_color[c] = clean_color(val.get("color"), "#ffffff")
            self.cat_chk[c].blockSignals(True)
            self.cat_chk[c].setChecked(self.cat_enabled[c])
            self.cat_chk[c].blockSignals(False)
            self.set_swatch(self.cat_btn[c], self.cat_color[c])
        self.keys = {}
        for k, hx in (data.get("keys") or {}).items():
            name = _KEY_BY_LOWER.get(str(k).lower())
            if name and isinstance(hx, str) and _HEX.match(hx):
                self.keys[name] = hx
        self.refresh_keys(send=send)
        self.update_edit_state()

    def reset_colors(self):
        """Clear every color of the editor: unlit base, no groups, no individual keys."""
        self.checkpoint()
        self.restore_colors({})
        self.kv.end_drag()
        self.kv.select(set())

    def clear_editor(self):
        """Remove every selection and color of the layout being edited (the real keyboard is untouched)."""
        self.reset_colors()
        self.status.setText(tr("msg.editor_cleared"))

    def reset_keyboard(self):
        """Reset: clear all colors in the editor and switch the keyboard lighting off."""
        if QMessageBox.question(self, tr("btn.reset"), tr("reset.confirm")) != QMessageBox.Yes:
            return
        self.reset_colors()
        self.run(lambda k: k.kbd((0, 0, 0)), tr("msg.reset"))

    def turn_off(self):
        self.run(lambda k: k.kbd((0, 0, 0)), tr("msg.off"))

    def set_live(self, on):
        self.live = on
        self.save_settings()
        if on:
            self.apply_colors(silent=True)

    def apply_effect(self, silent=False):
        self.read_effect_widgets()
        st = dict(self.fx_state)
        name = EFFECT_IDS[st["effect"]]
        c1, c2 = hex_to_rgb(self.fx_color[0]), hex_to_rgb(self.fx_color[1])
        b, s, d = st["bright"], st["speed"], DIRS[st["dir"]]
        self.last_mode = "effect"

        def job(k):
            if name == "static":
                k.static(c1, brightness=b, speed=s, rainbow=st["rainbow"])
            elif name == "breath":
                k.breath(c1, color2=c2, brightness=b, speed=s)
            elif name == "radar":
                k.radar(c1, color2=c2, brightness=b, speed=s)
            elif name == "stream":
                k.stream(c1, color2=c2, brightness=b, speed=s, direction=d, rainbow=st["rainbow"])
            else:
                k.mem_effect(c1, color2=c2, brightness=b)
        self.run(job, tr("msg.fx_applied", name=tr(f"fx.{name}")), silent)

    def apply_current(self, silent=False):
        """Send what the profile describes: its effect or its colors."""
        if self.last_mode == "effect":
            self.apply_effect(silent)
        else:
            self.apply_colors(silent)

    # ---------- profiles (up to 20 slots + import/export of files) ----------
    def profile_data(self):
        self.read_effect_widgets()
        data = self.snapshot()
        data["layout"] = {"id": self.layout_id, "size": self.size_id}
        data["effect"] = {**self.fx_state, "colors": list(self.fx_color)}
        data["mode"] = self.last_mode
        return data

    def apply_profile_data(self, data):
        """Load a whole profile: colors, effect settings, last mode and (if valid) the layout."""
        self.restore_colors(data)
        fx = data.get("effect")
        if isinstance(fx, dict):
            st = self.fx_state
            st["effect"] = fx.get("effect", st["effect"]) if fx.get("effect") in range(len(EFFECT_IDS)) else st["effect"]
            for key in ("bright", "speed"):
                if isinstance(fx.get(key), int):
                    st[key] = min(max(fx[key], 0), 100)
            if fx.get("dir") in range(len(DIRS)):
                st["dir"] = fx["dir"]
            st["rainbow"] = bool(fx.get("rainbow", st["rainbow"]))
            cols = fx.get("colors")
            if isinstance(cols, list) and len(cols) == 2:
                self.fx_color = [clean_color(cols[0], "#ff0000"), clean_color(cols[1], "#0000ff")]
            self.write_effect_widgets()
        self.last_mode = "effect" if data.get("mode") == "effect" else "colors"
        lay = data.get("layout")
        if isinstance(lay, dict) and lay.get("id") in LAYOUT_IDS and lay.get("size") in SIZE_IDS:
            if (lay["id"], lay["size"]) != (self.layout_id, self.size_id):
                self.layout_id, self.size_id = lay["id"], lay["size"]
                self.save_settings()
                self.rebuild_keyboard()

    def build_profiles_menu(self, mb):
        slots = core.load_profiles()
        label = lambda i: f"{i + 1:>2}.  " + (slots[i]["name"] if slots[i] else tr("profile.empty"))  # noqa: E731
        m = mb.addMenu(tr("menu.profiles"))
        m.addAction(tr("menu.manage_profiles"), lambda: dialogs.ProfileManager(self).exec())
        m.addSeparator()
        grp = QActionGroup(m)
        for i, slot in enumerate(slots):
            act = m.addAction(label(i))
            act.setCheckable(True)
            act.setChecked(i == self.active_profile and slot is not None)
            act.setEnabled(slot is not None)
            grp.addAction(act)
            act.triggered.connect(lambda _=False, i=i: self.load_slot(i))
        m.addSeparator()
        for key, fn, only_used in (("profile.save_in", self.save_slot, False),
                                   ("profile.rename", self.rename_slot, True),
                                   ("profile.delete", self.delete_slot, True)):
            sub = m.addMenu(tr(key))
            for i, slot in enumerate(slots):
                act = sub.addAction(label(i))
                act.setEnabled(slot is not None or not only_used)
                act.triggered.connect(lambda _=False, i=i, fn=fn: fn(i))
        m.addSeparator()
        m.addAction(tr("profile.import"), self.import_profile)
        m.addAction(tr("profile.export"), self.export_profile)
        m.addSeparator()
        self._check_action(m, tr("profile.apply_on_load"), self.apply_on_load,
                           lambda on: (setattr(self, "apply_on_load", on), self.save_settings()))
        self._check_action(m, tr("profile.apply_on_start"), self.apply_on_start,
                           lambda on: (setattr(self, "apply_on_start", on), self.save_settings()))

    def refresh_profiles_menu(self):
        QTimer.singleShot(0, self.build_menus)

    def ask_name(self, i, default):
        name, ok = QInputDialog.getText(self, tr("profile.name_title"),
                                        tr("profile.name_prompt", n=i + 1), text=default)
        return name.strip() if ok and name.strip() else None

    def save_slot(self, i):
        slots = core.load_profiles()
        old = slots[i]
        if old and QMessageBox.question(
                self, tr("profile.name_title"),
                tr("profile.overwrite", n=i + 1, name=old["name"])) != QMessageBox.Yes:
            return
        name = self.ask_name(i, old["name"] if old else tr("profile.default_name", n=i + 1))
        if not name:
            return
        slots[i] = {"name": name, "data": self.profile_data()}
        core.save_profiles(slots)
        self.active_profile = i
        self.saved_state = self.snapshot()
        self.update_title()
        self.save_settings()
        self.status.setText(tr("profile.saved_slot", n=i + 1, name=name))
        self.refresh_profiles_menu()

    def load_slot(self, i, ask=True, apply=None, silent=False):
        """Load slot `i` into the editor. `apply`: also send it to the keyboard (default: the menu option)."""
        slot = core.load_profiles()[i]
        if not slot or (ask and not self.confirm_discard()):
            return
        self.checkpoint()
        self.apply_profile_data(slot["data"])
        self.active_profile = i
        self.saved_state = self.snapshot()
        self.update_title()
        self.save_settings()
        self.status.setText(tr("profile.loaded_slot", n=i + 1, name=slot["name"]))
        self.refresh_profiles_menu()
        if self.apply_on_load if apply is None else apply:
            self.apply_current(silent=silent)

    def startup_apply(self):
        slot = core.load_profiles()[self.active_profile]
        if slot:
            self.load_slot(self.active_profile, ask=False, apply=True, silent=True)

    def rename_slot(self, i):
        slots = core.load_profiles()
        if not slots[i]:
            return
        name = self.ask_name(i, slots[i]["name"])
        if name:
            slots[i]["name"] = name
            core.save_profiles(slots)
            self.refresh_profiles_menu()

    def delete_slot(self, i):
        slots = core.load_profiles()
        if not slots[i]:
            return
        if QMessageBox.question(self, tr("profile.name_title"),
                                tr("profile.delete_confirm", n=i + 1, name=slots[i]["name"])) != QMessageBox.Yes:
            return
        slots[i] = None
        core.save_profiles(slots)
        if self.active_profile == i:
            self.active_profile = None
            self.save_settings()
        self.status.setText(tr("profile.deleted", n=i + 1))
        self.refresh_profiles_menu()

    def export_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("profile.export"), "", f"{tr('file.profile')} (*.json)")
        if not path:
            return
        if not path.endswith(".json"):
            path += ".json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.profile_data(), fh, indent=2)
        self.status.setText(tr("msg.profile_saved", path=path))

    def import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("profile.import"), "", f"{tr('file.profile')} (*.json)")
        if not path or not self.confirm_discard():
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("not a profile")
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, tr("err.title"), str(e))
            return
        self.checkpoint()
        self.apply_profile_data(data)
        self.status.setText(tr("msg.profile_loaded", path=path))
