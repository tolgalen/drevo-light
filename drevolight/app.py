# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Application entry point."""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .core import ASSETS_DIR
from .widgets import Splash
from .window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Drevo Light")
    app.setWindowIcon(QIcon(str(ASSETS_DIR / "icon.png")))
    win = MainWindow(app)
    if win.show_splash:
        splash = Splash()
        splash.done.connect(lambda: (win.show(), win.raise_(), win.activateWindow()))
        splash.show()
    else:
        win.show()
    sys.exit(app.exec())
