# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Connection state and commands sent to the keyboard."""
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QMessageBox, QPlainTextEdit, QVBoxLayout

from . import core, proto
from .common import HEX_COLOR, KEY_BY_LOWER, clean_color
from .core import CATEGORIES, DIRS, EFFECT_IDS, hex_to_rgb, tr


class HardwareMixin:
    def refresh_ifaces(self):
        """Re-detect the keyboard (touches the hardware) and redraw the connection panel."""
        self.iface_list = proto.list_interfaces()
        self.iface_sel = 0
        self.populate_ifaces()
        self.check_access()

    def populate_ifaces(self):
        """Fill the interface combo from the cached list (no hardware access)."""
        self.iface_combo.clear()
        self.iface_combo.addItems([tr("iface.auto")] + [proto.describe(i) for i in self.iface_list])
        self.iface_combo.setCurrentIndex(self.iface_sel if self.iface_sel <= len(self.iface_list) else 0)

    def set_conn(self, state, title, detail=""):
        self.dot.set_color({"ok": "#2e9e4f", "warn": "#e0a100", "off": "#cc3333"}[state])
        self.conn_lbl.setText(title)
        self.access_lbl.setText(detail)

    def render_connection(self):
        """Redraw the last known connection state (e.g. after a theme/language change)."""
        if self._conn_spec is not None:
            state, tkey, tkw, dkey, dkw = self._conn_spec
            self.set_conn(state, tr(tkey, **tkw), tr(dkey, **dkw))

    def _set_conn_spec(self, state, tkey, dkey, tkw=None, dkw=None):
        self._conn_spec = (state, tkey, tkw or {}, dkey, dkw or {})
        self.render_connection()

    def check_access(self):
        if proto.hid is None:
            return self._set_conn_spec("off", "conn.nolibs.title", "conn.nolibs.detail")
        ifs = proto.list_interfaces()
        if not ifs:
            return self._set_conn_spec("off", "conn.nokbd.title", "conn.nokbd.detail")
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
            self._set_conn_spec("ok", "conn.ok.title", "conn.ok.detail", {"name": name},
                                {"ok": ok, "total": len(ifs)})
        else:
            self._set_conn_spec("warn", "conn.warn.title", "conn.warn.detail", {"name": name})

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
        self.stop_animation()  # one writer at a time
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
            name = KEY_BY_LOWER.get(str(k).lower())
            if name and isinstance(hx, str) and HEX_COLOR.match(hx):
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
