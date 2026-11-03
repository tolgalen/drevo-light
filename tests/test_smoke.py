# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from conftest import pump


def test_window_builds_with_every_theme_and_language(win, qapp):
    from drevolight.core import I18, THEME_IDS
    for t in THEME_IDS:
        win.change_theme(t)
        pump(qapp)
    for code in list(I18.langs):
        win.change_lang(code)
        pump(qapp)
    assert len(win.kv.items) == 88
