# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import re

import pytest
from conftest import pump
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMessageBox, QPushButton


class FakeKeyboard:
    log = []

    def __init__(self, forced_path=None):
        pass

    def __getattr__(self, name):
        def call(*args, **kwargs):
            FakeKeyboard.log.append((name, args, kwargs))
        return call


@pytest.fixture
def hw(win, qapp, monkeypatch):
    from drevolight import proto
    FakeKeyboard.log = []
    monkeypatch.setattr(proto, "Keyboard", FakeKeyboard)
    return FakeKeyboard.log


def finish(win, qapp):
    win.runner.wait()
    pump(qapp)


def yes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))


def center(win, name):
    return win.kv.mapFromScene(win.kv.items[name].sceneBoundingRect().center())


def drag(win, qapp, a, b, mods=Qt.NoModifier):
    v = win.kv.viewport()
    QTest.mousePress(v, Qt.LeftButton, mods, a)
    QTest.mouseMove(v, QPoint((a.x() + b.x()) // 2, (a.y() + b.y()) // 2))
    QTest.mouseMove(v, b)
    QTest.mouseRelease(v, Qt.LeftButton, mods, b)
    pump(qapp)


# ---------------------------------------------------------------- selection
def test_drag_from_a_key_accumulates_areas(win, qapp):
    drag(win, qapp, center(win, "q"), center(win, "e"))
    first = win.kv.selected()
    assert {"q", "w", "e"} <= first
    drag(win, qapp, center(win, "n"), center(win, "m"))
    assert first < win.kv.selected() and {"n", "m"} <= win.kv.selected()


def test_ctrl_toggles_shift_replaces_click_outside_clears(win, qapp):
    win.set_selection({"a", "s"})
    drag(win, qapp, center(win, "s"), center(win, "d"), Qt.ControlModifier)
    assert "s" not in win.kv.selected() and "d" in win.kv.selected()
    drag(win, qapp, center(win, "z"), center(win, "x"), Qt.ShiftModifier)
    assert win.kv.selected() == {"z", "x"}
    QTest.mouseClick(win.kv.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(2, 2))
    assert win.kv.selected() == set()


def test_lost_release_does_not_keep_selecting(win, qapp):
    v = win.kv.viewport()
    QTest.mousePress(v, Qt.LeftButton, Qt.NoModifier, center(win, "q"))
    QTest.mouseMove(v, center(win, "l"))
    assert win.kv._dragging
    win.set_selection(set())
    assert not win.kv._dragging and win.kv.selected() == set()


def test_row_buttons_select_a_whole_row(win, qapp):
    btn = [b for b in win.findChildren(QPushButton) if b.text() == "1"][0]
    QTest.mouseClick(btn, Qt.LeftButton)
    assert {"esc", "f1", "f12"} <= win.kv.selected()


# --------------------------------------------------------------- editing
def test_paint_undo_redo(win):
    win.set_selection({"a", "b"})
    win.paint("#ff0000")
    assert win.keys == {"a": "#ff0000", "b": "#ff0000"}
    win.undo()
    assert win.keys == {}
    win.redo()
    assert win.keys == {"a": "#ff0000", "b": "#ff0000"}
    assert not win.history.can_redo


def test_undo_covers_base_groups_and_clear(win):
    win.user_set_base("#112233")
    win.pick_cat = None  # not used here
    win.checkpoint()
    win.cat_enabled["letters"] = True
    win.cat_color["letters"] = "#00ff00"
    win.refresh_keys()
    assert win.key_color("q") == "#00ff00"
    win.clear_editor()
    assert win.base_color == "#000000" and not win.cat_enabled["letters"]
    win.undo()
    assert win.base_color == "#112233" and win.cat_enabled["letters"]
    assert win.cat_chk["letters"].isChecked()


def test_copy_paste_color(win):
    win.keys = {"a": "#abcdef"}
    win.set_selection({"a"})
    win.copy_color()
    win.set_selection({"s", "d"})
    win.paste_color()
    assert win.keys["s"] == win.keys["d"] == "#abcdef"


def test_gradient_left_to_right(win):
    win.set_selection({"q", "w", "e", "r", "t"})
    from drevolight.state import gradient_colors, normalise
    xs = [win.kv.items[n].sceneBoundingRect().center().x() for n in sorted(win.kv.selected())]
    cols = gradient_colors(normalise(xs), "two", "#000000", "#ffffff")
    assert cols[xs.index(min(xs))] == "#000000" and cols[xs.index(max(xs))] == "#ffffff"
    rb = gradient_colors([0, 0.5, 1], "rainbow")
    assert len(set(rb)) == 3 and rb[0] == "#ff0000"


def test_recent_colors_and_unknown_key_validation(win):
    win.set_selection({"a"})
    for c in ("#111111", "#222222", "#111111"):
        win.paint(c)
    assert win.recent[:2] == ["#111111", "#222222"] and len(win.recent) == 2
    win.key_entry.setText("nope")
    win.add_key()
    assert "nope" in win.status.text() and "nope" not in win.keys
    win.key_entry.setText("backs")  # case-insensitive, canonical name is BACKS
    win.add_key()
    assert "BACKS" in win.keys


def test_add_selection_to_table(win):
    win.set_selection({"x", "c"})
    win.add_selection()
    assert set(win.keys) == {"x", "c"} and win.table.rowCount() == 2


def test_clear_editor_does_not_touch_the_keyboard(win, hw, qapp):
    win.keys = {"a": "#ff0000"}
    win.set_selection({"a"})
    win.clear_editor()
    finish(win, qapp)
    assert win.keys == {} and not win.kv.selected() and hw == []


# ----------------------------------------------------------- hardware (fake)
def test_apply_colors_runs_in_worker_and_snapshots_state(win, hw, qapp):
    win.keys = {"a": "#ff0000"}
    win.base_color = "#101010"
    win.cat_enabled["arrow"] = True
    win.cat_color["arrow"] = "#00ff00"
    win.apply_colors()
    win.keys["a"] = "#0000ff"  # later edits must not leak into the queued job
    finish(win, qapp)
    assert [c[0] for c in hw] == ["kbd", "category", "key_set"]
    assert hw[0][1][0] == (16, 16, 16)
    assert hw[2][1][0] == {"a": (255, 0, 0)}
    assert "Colores aplicados" in win.status.text()


def test_reset_keyboard_turns_lights_off(win, hw, qapp, monkeypatch):
    yes(monkeypatch)
    win.keys = {"a": "#ff0000"}
    win.reset_keyboard()
    finish(win, qapp)
    assert win.keys == {} and hw == [("kbd", ((0, 0, 0),), {})]


def test_errors_reach_the_user_without_freezing(win, qapp, monkeypatch):
    from drevolight import proto
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(a[2])))

    class Broken:
        def __init__(self, forced_path=None):
            pass

        def kbd(self, *_):
            raise proto.KeyboardError("boom")
    monkeypatch.setattr(proto, "Keyboard", Broken)
    win.turn_off()
    finish(win, qapp)
    assert shown and "boom" in shown[0]
    # live mode errors stay silent (status bar only)
    shown.clear()
    win.apply_colors(silent=True)
    finish(win, qapp)
    assert not shown


def test_live_mode_sends_changes(win, hw, qapp):
    win.live_chk.setChecked(True)
    finish(win, qapp)
    hw.clear()
    win.set_selection({"a"})
    win.paint("#ff00ff")
    QTest.qWait(400)
    finish(win, qapp)
    assert any(c[0] == "key_set" and c[1][0] == {"a": (255, 0, 255)} for c in hw)


# ---------------------------------------------------------------- profiles
def test_twenty_profile_slots_roundtrip(win, qapp, monkeypatch):
    from drevolight import core
    names = iter(f"P{i}" for i in range(100))
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText",
                        staticmethod(lambda *a, **k: (next(names), True)))
    yes(monkeypatch)
    for i in range(20):
        win.keys = {"a": f"#0000{i:02x}"}
        win.save_slot(i)
    slots = core.load_profiles()
    assert len(slots) == 20 and all(slots) and slots[19]["data"]["keys"] == {"a": "#000013"}
    win.keys = {}
    win.load_slot(5, ask=False)
    assert win.keys == {"a": "#000005"} and win.active_profile == 5


def test_profile_stores_layout_effect_and_mode(win, hw, qapp, monkeypatch):
    from drevolight import core
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", staticmethod(lambda *a, **k: ("fx", True)))
    win.fx_color = ["#123456", "#654321"]
    win.fx_combo.setCurrentIndex(3)
    win.fx_sliders["speed"].setValue(33)
    win.apply_effect()
    finish(win, qapp)
    win.save_slot(0)
    data = core.load_profiles()[0]["data"]
    assert data["mode"] == "effect" and data["effect"]["speed"] == 33
    assert data["effect"]["colors"] == ["#123456", "#654321"] and data["layout"]["size"] in ("tkl", "full")
    win.fx_combo.setCurrentIndex(0)
    win.fx_sliders["speed"].setValue(1)
    win.last_mode = "colors"
    win.load_slot(0, ask=False)
    assert win.fx_combo.currentIndex() == 3 and win.fx_sliders["speed"].value() == 33
    assert win.last_mode == "effect"


def test_dirty_flag_and_unsaved_prompt(win, monkeypatch):
    from drevolight import core
    assert not win.is_dirty()
    win.set_selection({"a"})
    win.paint("#ff0000")
    assert win.is_dirty() and win.windowTitle().endswith("*")
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(1) or QMessageBox.No))
    core.save_profiles([{"name": "x", "data": win.snapshot()}] + [None] * 19)
    win.load_slot(0)  # declined -> nothing changes
    assert asked and win.keys == {"a": "#ff0000"}
    win.load_slot(0, ask=False)
    assert not win.is_dirty()


def test_import_rejects_garbage_and_sanitises(win, tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2]")
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName",
                        staticmethod(lambda *a, **k: (str(bad), "")))
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(1)))
    win.import_profile()
    assert shown
    evil = tmp_path / "evil.json"
    evil.write_text(json.dumps({"base": "red", "keys": {"zzz": "#ffffff", "A": "#00ff00", "b": "oops"}}))
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName",
                        staticmethod(lambda *a, **k: (str(evil), "")))
    win.import_profile()
    assert win.base_color == "#000000" and win.keys == {"a": "#00ff00"}


def test_profile_manager_thumbnails(win, qapp, monkeypatch):
    from drevolight import core, dialogs
    core.save_profiles([{"name": "x", "data": win.snapshot()}] + [None] * 19)
    dlg = dialogs.ProfileManager(win)
    assert dlg.listw.count() == 20 and not dlg.listw.item(0).icon().isNull()
    assert dlg.listw.item(1).icon().isNull()


# ----------------------------------------------------------------- misc
def test_manual_pdf_exports_in_every_language(win, tmp_path):
    from drevolight import dialogs
    from drevolight.core import I18
    for code in I18.langs:
        I18.set(code)
        out = tmp_path / f"{code}.pdf"
        dialogs.export_manual_pdf(win.pal, str(out))
        assert out.read_bytes()[:4] == b"%PDF"
    I18.set("es")


def test_translations_are_complete_and_consistent():
    from drevolight.core import I18
    ref = I18.langs["en"]
    placeholder = lambda s: set(re.findall(r"\{\w+\}", s))  # noqa: E731
    for code, table in I18.langs.items():
        assert set(table) == set(ref), (code, set(table) ^ set(ref))
        for k, v in table.items():
            assert placeholder(v) == placeholder(ref[k]), (code, k)
    for code in I18.langs:
        assert (I18.langs and __import__("pathlib").Path(f"lang/manual_{code}.html").exists()), code


def test_every_ui_string_used_in_code_exists():
    import pathlib
    from drevolight.core import I18
    used = set()
    for f in pathlib.Path("drevolight").glob("*.py"):
        used |= set(re.findall(r'tr\(\s*"([a-z_]+\.[a-z_0-9.]+)"', f.read_text(encoding="utf-8")))
    missing = {k for k in used if k not in I18.langs["en"]}
    assert not missing, missing


def test_udev_command_is_well_formed():
    from drevolight.dialogs import udev_command
    cmd = udev_command("/opt/x/99-drevo-tyrfing.rules")
    assert cmd[:3] == ["pkexec", "sh", "-c"] and "/etc/udev/rules.d/99-drevo-tyrfing.rules" in cmd[3]
    assert "udevadm control --reload" in cmd[3]


def test_settings_roundtrip_and_geometry(win, qapp, tmp_path):
    from drevolight import core
    win.theme_id, win.live = "navy", True
    win.save_settings()
    saved = core.load_settings()
    assert saved["theme"] == "navy" and saved["live"] is True and saved["geometry"]


def test_effect_preview_colors_and_dialog(win, qapp):
    from drevolight import preview
    from conftest import pump
    pos, ext = preview.key_positions("es", "tkl")
    assert len(pos) == 88
    params = dict(color1="#ff0000", color2="#0000ff", bright=100, speed=50, dir="e", rainbow=False)
    for name in ("static", "breath", "radar", "stream", "mem_effect"):
        cols = preview.effect_colors(name, 1.3, params, pos, ext, {"a": 1.0})
        assert set(cols) == set(pos) and all(len(c) == 7 for c in cols.values())
    assert preview.effect_colors("static", 0, params, pos, ext)["a"] == "#ff0000"
    assert set(preview.effect_colors("static", 0, {**params, "bright": 0}, pos, ext).values()) == {"#000000"}
    a = preview.effect_colors("stream", 0.0, params, pos, ext)
    b = preview.effect_colors("stream", 0.5, params, pos, ext)
    assert a != b  # the animation moves
    win.show_preview()
    pump(qapp)
    d = win.preview_dlg
    d.tick()
    d.press("a")
    d.toggle()
    d.toggle()
    d.close()
    pump(qapp)
