# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""System tray icon: show/hide the window, switch profile, turn the lights off, quit."""
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import core
from .core import ASSETS_DIR, tr


class TrayMixin:
    tray = None

    def setup_tray(self):
        """Create the tray icon if the desktop has a system tray; otherwise do nothing."""
        if self.tray is not None or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(str(ASSETS_DIR / "icon.png")), self)
        self.app.setQuitOnLastWindowClosed(False)  # keep running while hidden in the tray
        self.tray.setToolTip("Drevo Light")
        self.tray.activated.connect(self._tray_activated)
        self.build_tray_menu()
        self.tray.show()

    def tray_enabled(self):
        return self.tray is not None and self.tray.isVisible()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_window()

    def toggle_window(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def build_tray_menu(self):
        if self.tray is None:
            return
        menu = QMenu()
        menu.addAction(tr("tray.show"), self.toggle_window)
        menu.addSeparator()
        slots = core.load_profiles()
        for i, slot in enumerate(slots):
            if slot:
                act = menu.addAction(f"{i + 1:>2}.  {slot['name']}")
                act.setCheckable(True)
                act.setChecked(i == self.active_profile)
                act.triggered.connect(lambda _=False, i=i: self.tray_load_profile(i))
        menu.addSeparator()
        menu.addAction(tr("btn.off"), self.turn_off)
        menu.addAction(tr("menu.quit"), self.quit_app)
        self._tray_menu = menu  # keep a reference: the tray does not take ownership
        self.tray.setContextMenu(menu)

    def tray_load_profile(self, i):
        """Load slot `i` and send it to the keyboard, even when the window is hidden."""
        self.load_slot(i, apply=True, silent=True)

    def quit_app(self):
        self._quitting = True
        self.close()
        self.app.quit()
