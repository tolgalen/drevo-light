# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Main window of Drevo Light."""

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QActionGroup, QColor, QIcon, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import core, dialogs, proto
from .common import HEX_COLOR, MAX_RECENT
from .core import (
    ASSETS_DIR,
    CATEGORIES,
    I18,
    LAYOUT_IDS,
    LIGHT_PRESETS,
    SIZE_IDS,
    THEME_IDS,
    THEMES,
    tr,
)
from .autoprofile import AutoProfileMixin
from .gfx import _icon_cache, stylesheet, system_palette
from .hardware import HardwareMixin
from .page_colors import ColorsPageMixin
from .page_effects import EffectsPageMixin
from .page_keyboard import KeyboardPageMixin
from .profiles import ProfilesMixin
from .tray import TrayMixin
from .state import History, make_snapshot, resolve_color
from .widgets import Dot, LogoWidget, NavButton
from .worker import HardwareRunner


class MainWindow(KeyboardPageMixin, ColorsPageMixin, EffectsPageMixin, HardwareMixin,
                 ProfilesMixin, TrayMixin, AutoProfileMixin, QMainWindow):
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
        self.close_to_tray = bool(cfg.get("close_to_tray", False))
        self._quitting = False
        self.anim = None
        self.recent = [c for c in cfg.get("recent", []) if HEX_COLOR.match(str(c))][:MAX_RECENT]
        for i, hx in enumerate(cfg.get("custom_colors", [])[:16]):
            if HEX_COLOR.match(str(hx)):
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
        self.setup_auto_profile(cfg)
        self.setup_tray()
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
            "close_to_tray": self.close_to_tray,
            "auto_profile": self.auto_enabled, "auto_rules": self.auto_rules,
            "recent": self.recent,
            "custom_colors": [QColorDialog.customColor(i).name() for i in range(QColorDialog.customCount())],
            "geometry": bytes(self.saveGeometry().toBase64()).decode(),
        })

    def closeEvent(self, e):
        if self.close_to_tray and not self._quitting and self.tray_enabled():
            e.ignore()
            self.hide()
            return
        self.live_timer.stop()
        self.stop_auto_profile()
        self.stop_animation()
        self.runner.wait()
        self.save_settings()
        super().closeEvent(e)
        if self.tray is not None:
            self.app.quit()  # the app does not quit on its own while the tray icon exists

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
        if self.tray is not None:
            self._check_action(m, tr("menu.close_to_tray"), self.close_to_tray,
                               lambda on: (setattr(self, "close_to_tray", on), self.save_settings()))
        if dialogs.udev_supported():
            m.addAction(tr("menu.install_udev"), lambda: dialogs.install_udev_rules(self))
        m.addSeparator()
        act = m.addAction(tr("menu.quit"), self.quit_app)
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
        self.build_tray_menu()
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
