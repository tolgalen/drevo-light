# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Profile slots and import/export."""
import json

from PySide6.QtCore import QTimer
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from . import core, dialogs
from .common import clean_color
from .core import DIRS, EFFECT_IDS, LAYOUT_IDS, SIZE_IDS, tr


class ProfilesMixin:
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
