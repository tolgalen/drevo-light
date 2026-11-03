# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(qapp, tmp_path, monkeypatch):
    """A MainWindow whose settings/profiles live in a temp folder and whose keyboard is fake."""
    from drevolight import core, window
    monkeypatch.setattr(core, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(core, "PROFILES_FILE", tmp_path / "profiles.json")
    # fixed settings: tests must not depend on the machine locale
    core.save_settings({"lang": "es", "layout": "es", "size": "tkl", "theme": "drevo"})
    w = window.MainWindow(qapp)
    w.show()
    pump(qapp)
    yield w
    w.close()
    pump(qapp)


def pump(app, n=8):
    from PySide6.QtCore import QCoreApplication, QEvent
    for _ in range(n):
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
