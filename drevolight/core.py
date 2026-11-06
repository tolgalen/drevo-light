# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Drevo Light - GUI-independent core: languages, themes, layouts, settings and profiles."""
import json
import locale
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .keys import CATEGORIES, CATEGORY_KEYS, NUMPAD_KEYS

BASE_DIR = Path(__file__).resolve().parent.parent
LANG_DIR = BASE_DIR / "lang"
ASSETS_DIR = BASE_DIR / "assets"
APP_VERSION = "1.1"
GOLD = "#f0b323"
VID, PID = 0x0416, 0xA0F8


def config_dir():
    """Per-user configuration folder (XDG on Linux, APPDATA on Windows, Application Support on macOS)."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    d = base / "drevo-light"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d


SETTINGS_FILE = config_dir() / "settings.json"
PROFILES_FILE = config_dir() / "profiles.json"
_LEGACY = {SETTINGS_FILE: Path.home() / ".drevo_light.json",
           PROFILES_FILE: Path.home() / ".drevo_light_profiles.json"}


def _migrate_legacy_files():
    """Copy the old dot-files of version 1.0 into the new config folder (once)."""
    for new, old in _LEGACY.items():
        try:
            if not new.exists() and old.exists():
                new.write_bytes(old.read_bytes())
        except OSError:
            pass


# ======================================================================
#  Languages (one XML file per language: lang/<code>.xml)
# ======================================================================
class I18N:
    def __init__(self):
        self.langs, self.names = {}, {}
        for f in sorted(LANG_DIR.glob("*.xml")):
            try:
                root = ET.parse(f).getroot()
                code = root.get("code") or f.stem
                self.names[code] = root.get("name", code)
                self.langs[code] = {s.get("id"): (s.text or "").replace("\\n", "\n")
                                    for s in root.iter("s")}
            except ET.ParseError:
                continue
        self.cur = "en" if "en" in self.langs else (next(iter(self.langs), "en"))

    def set(self, code):
        if code in self.langs:
            self.cur = code

    def tr(self, key, **kw):
        s = (self.langs.get(self.cur, {}).get(key)
             or self.langs.get("en", {}).get(key) or key)
        return s.format(**kw) if kw else s


I18 = I18N()
tr = I18.tr


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ======================================================================
#  Color themes
# ======================================================================
def mix(c1, c2, t):
    """Mix two #rrggbb colors (t=0 -> c1, t=1 -> c2)."""
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def luminance(c):
    r, g, b = hex_to_rgb(c)
    return 0.299 * r + 0.587 * g + 0.114 * b


THEMES = {
    "light": dict(bg="#f1f1f3", fg="#1b1b1f", field="#ffffff", btn="#e3e3e8", btn_active="#d3d3da",
                  border="#b4b4be", accent="#b97d00", sel_bg="#cfe3ff", sel_fg="#000000",
                  canvas="#e4e4e9", panel="#d2d2d9", panel_edge="#b0b0ba", rim="#8e8e99",
                  face="#fbfbfc", title="#202024", sub="#6a6a74", legend_dark="#111111",
                  legend_light="#ffffff"),
    "dark": dict(bg="#1f2023", fg="#e6e6e8", field="#2b2c30", btn="#33343a", btn_active="#44454c",
                 border="#4a4b52", accent="#e3a63b", sel_bg="#3a5f8f", sel_fg="#ffffff",
                 canvas="#151618", panel="#222327", panel_edge="#3a3b40", rim="#050505",
                 face="#151517", title="#ffffff", sub="#bdbdc4", legend_dark="#111111",
                 legend_light="#f2f2f2"),
    # Colors of the official Drevo software: charcoal, black keys and the logo's gold
    "drevo": dict(bg="#232324", fg="#ededed", field="#161617", btn="#1b1b1c", btn_active="#323234",
                  border="#58585b", accent="#f0b323", sel_bg="#5a4510", sel_fg="#ffffff",
                  canvas="#2e2e30", panel="#39393b", panel_edge="#5c5c60", rim="#000000",
                  face="#0d0d0e", title="#ffffff", sub="#cfcfcf", legend_dark="#111111",
                  legend_light="#f4f4f4"),
    "navy": dict(bg="#0f1a2e", fg="#dce6f5", field="#0a1322", btn="#1b2b47", btn_active="#27406b",
                 border="#36507f", accent="#5aa9ff", sel_bg="#2a5599", sel_fg="#ffffff",
                 canvas="#0b1424", panel="#16253f", panel_edge="#2e4670", rim="#02060d",
                 face="#0a1220", title="#ffffff", sub="#9fb4d6", legend_dark="#111111",
                 legend_light="#eef4ff"),
}
THEME_IDS = ["system", "light", "dark", "navy", "drevo"]
SELECT_COLOR = "#3aa0ff"


# ======================================================================
#  Keyboard layouts (Tyrfing V2 = 88-key TKL; full size also supported)
# ======================================================================
KEY_UNIT = 46  # px per key unit
NAV_X = 15.6   # start of the editing / arrow-key block
NUM_X = NAV_X + 3.35

LAYOUTS = {"us": ("ansi", "us"), "uk": ("iso", "uk"), "es": ("iso", "es"),
           "de": ("iso", "de"), "fr": ("iso", "fr"), "it": ("iso", "it")}
LAYOUT_IDS = list(LAYOUTS)
SIZE_IDS = ["tkl", "full"]

_US = {"~": "` ~", "1": "1 !", "2": "2 @", "3": "3 #", "4": "4 $", "5": "5 %", "6": "6 ^",
       "7": "7 &", "8": "8 *", "9": "9 (", "0": "0 )", "-": "- _", "=": "= +", "[": "[ {",
       "]": "] }", "\\": "\\ |", ";": "; :", "'": "' \"", ",": ", <", ".": ". >", "/": "/ ?"}
_ISO_COMMON = {"iso": "< >", ",": ", ;", ".": ". :", "/": "- _"}
LEGENDS = {
    "us": _US,
    "uk": {**_US, "~": "` ¬", "2": '2 "', "3": "3 £", "'": "' @", "#": "# ~", "iso": "\\ |"},
    "es": {**_US, **_ISO_COMMON, "~": "º ª", "2": '2 "', "3": "3 ·", "6": "6 &", "7": "7 /",
           "8": "8 (", "9": "9 )", "0": "0 =", "-": "' ?", "=": "¡ ¿", "[": "` ^", "]": "+ *",
           "#": "ç Ç", ";": "ñ Ñ", "'": "´ ¨"},
    "de": {**_US, **_ISO_COMMON, "~": "^ °", "2": '2 "', "3": "3 §", "6": "6 &", "7": "7 /",
           "8": "8 (", "9": "9 )", "0": "0 =", "-": "ß ?", "=": "´ `", "[": "ü Ü", "]": "+ *",
           "#": "# '", ";": "ö Ö", "'": "ä Ä", "y": "Z", "z": "Y"},
    "fr": {**_US, **_ISO_COMMON, "~": "²", "1": "& 1", "2": "é 2", "3": '" 3', "4": "' 4",
           "5": "( 5", "6": "- 6", "7": "è 7", "8": "_ 8", "9": "ç 9", "0": "à 0", "-": ") °",
           "=": "= +", "[": "^ ¨", "]": "$ £", "#": "* µ", ";": "M", "'": "ù %", ",": "; .",
           ".": ": /", "/": "! §", "a": "Q", "q": "A", "z": "W", "w": "Z", "m": ", ?"},
    "it": {**_US, **_ISO_COMMON, "~": "\\ |", "2": '2 "', "3": "3 £", "6": "6 &", "7": "7 /",
           "8": "8 (", "9": "9 )", "0": "0 =", "-": "' ?", "=": "ì ^", "[": "è é", "]": "+ *",
           "#": "ù §", ";": "ò ç", "'": "à °"},
}
FIXED_LABELS = {"esc": "Esc", "BACKS": "← Backspace", "tab": "Tab ⇆", "caps": "CapsLock",
                "lshift": "Shift ⇧", "rshift": "Shift ⇧", "lctrl": "Ctrl", "rctrl": "Ctrl",
                "win": "⊞", "lalt": "Alt", "compo": "☰", "FN": "Fn", "enter": "Enter ↵",
                "ins": "Ins", "home": "Home", "p-up": "PgUp", "del": "Del", "end": "End",
                "p-down": "PgDn", "up": "↑", "down": "↓", "left": "←", "right": "→",
                "kpnlk": "Num", "kpdiv": "/", "kpmul": "*", "kpsub": "-", "kpadd": "+",
                "kpent": "↵", "kpdot": ".", "PS": "PrtSc", "SL": "ScrLk", "PB": "Pause"}


KEY_GROUPS = {
    "group.letters": CATEGORY_KEYS["letters"],
    "group.digits": CATEGORY_KEYS["digits"],
    "group.fkeys": CATEGORY_KEYS["function"],
    "group.mods": CATEGORY_KEYS["mod"],
    "group.edit": CATEGORY_KEYS["edition"],
    "group.arrows": CATEGORY_KEYS["arrow"],
    "group.numpad": NUMPAD_KEYS,
}
CAT_MEMBERS = CATEGORY_KEYS  # what the editor previews is exactly what is sent to the keyboard
PRESETS = {"white": "#ffffff", "red": "#ff0000", "green": "#00ff00", "blue": "#0000ff",
           "cyan": "#00ffff", "magenta": "#ff00ff", "amber": "#ffb000"}
LIGHT_PRESETS = ("white", "green", "cyan", "amber")
EFFECT_IDS = ["static", "breath", "radar", "stream", "mem_effect"]
DIRS = ["e", "w", "s", "n"]


def build_layout(iso=False, loc="us", tkl=True):
    """Return (keys, panels, width). keys = [(id, label, [(x,y,w,h)], polygon|None)]."""
    L = []
    legends = LEGENDS[loc]

    def add(name, x, y, w=1.0, h=1.0, rects=None, poly=None):
        if name in legends:
            lab = legends[name]
        elif name == "space":
            lab = tr("key.space")
        elif name == "ralt":
            lab = tr("key.altgr") if loc in ("es", "de", "fr", "it") else "Alt"
        elif name in FIXED_LABELS:
            lab = FIXED_LABELS[name]
        elif name.startswith("kp") and name[2:].isdigit():
            lab = name[2:]
        else:
            lab = name.upper()
        L.append((name, lab, rects or [(x, y, w, h)], poly))

    # row K
    add("esc", 0, 0)
    for i in range(12):
        add(f"f{i + 1}", 2 + i + 0.5 * (i // 4), 0)
    for i, n in enumerate(("PS", "SL", "PB")):
        add(n, NAV_X + i, 0)
    # row E
    for i, n in enumerate(["~"] + list("1234567890") + ["-", "="]):
        add(n, i, 1.5)
    add("BACKS", 13, 1.5, 2)
    # row D
    add("tab", 0, 2.5, 1.5)
    for i, n in enumerate("qwertyuiop"):
        add(n, 1.5 + i, 2.5)
    add("[", 11.5, 2.5)
    add("]", 12.5, 2.5)
    # row C
    add("caps", 0, 3.5, 1.75)
    for i, n in enumerate("asdfghjkl"):
        add(n, 1.75 + i, 3.5)
    add(";", 10.75, 3.5)
    add("'", 11.75, 3.5)
    # row B
    for i, n in enumerate("zxcvbnm,./"):
        add(n, 2.25 + i, 4.5)
    add("rshift", 12.25, 4.5, 2.75)
    if iso:
        add("#", 12.75, 3.5)
        add("enter", 0, 0, rects=[(13.5, 2.5, 1.5, 1), (13.75, 3.5, 1.25, 1)],
            poly=[(13.5, 2.5), (15, 2.5), (15, 4.5), (13.75, 4.5), (13.75, 3.5), (13.5, 3.5)])
        add("lshift", 0, 4.5, 1.25)
        add("iso", 1.25, 4.5)
    else:
        add("\\", 13.5, 2.5, 1.5)
        add("enter", 12.75, 3.5, 2.25)
        add("lshift", 0, 4.5, 2.25)
    # row A
    add("lctrl", 0, 5.5, 1.25)
    add("win", 1.25, 5.5, 1.25)
    add("lalt", 2.5, 5.5, 1.25)
    add("space", 3.75, 5.5, 6.25)
    add("ralt", 10, 5.5, 1.25)
    add("FN", 11.25, 5.5, 1.25)
    add("compo", 12.5, 5.5, 1.25)
    add("rctrl", 13.75, 5.5, 1.25)
    # editing and arrow keys
    for i, n in enumerate(("ins", "home", "p-up")):
        add(n, NAV_X + i, 1.5)
    for i, n in enumerate(("del", "end", "p-down")):
        add(n, NAV_X + i, 2.5)
    add("up", NAV_X + 1, 4.5)
    add("left", NAV_X, 5.5)
    add("down", NAV_X + 1, 5.5)
    add("right", NAV_X + 2, 5.5)
    panels = [(-0.15, -0.15, 15.15, 6.65),
              (NAV_X - 0.15, -0.15, NAV_X + 3.15, 1.15),
              (NAV_X - 0.15, 1.35, NAV_X + 3.15, 3.65),
              (NAV_X - 0.15, 4.35, NAV_X + 3.15, 6.65)]
    width = NAV_X + 3.15
    if not tkl:
        for i, n in enumerate(("kpnlk", "kpdiv", "kpmul", "kpsub")):
            add(n, NUM_X + i, 1.5)
        for r, row in enumerate((("kp7", "kp8", "kp9"), ("kp4", "kp5", "kp6"),
                                 ("kp1", "kp2", "kp3"))):
            for i, n in enumerate(row):
                add(n, NUM_X + i, 2.5 + r)
        add("kpadd", NUM_X + 3, 2.5, 1, 2)
        add("kp0", NUM_X, 5.5, 2)
        add("kpdot", NUM_X + 2, 5.5)
        add("kpent", NUM_X + 3, 4.5, 1, 2)
        panels.append((NUM_X - 0.15, 1.35, NUM_X + 4.15, 6.65))
        width = NUM_X + 4.15
    return L, panels, width




def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


MAX_PROFILES = 20


def load_profiles():
    """Return a list of MAX_PROFILES slots; each is None or {"name": str, "data": dict}."""
    try:
        raw = json.loads(PROFILES_FILE.read_text(encoding="utf-8")).get("slots", [])
    except Exception:  # noqa: BLE001
        raw = []
    slots = []
    for i in range(MAX_PROFILES):
        item = raw[i] if i < len(raw) else None
        ok = isinstance(item, dict) and isinstance(item.get("data"), dict)
        slots.append({"name": str(item.get("name") or ""), "data": item["data"]} if ok else None)
    return slots


def save_profiles(slots):
    try:
        PROFILES_FILE.write_text(json.dumps({"slots": slots[:MAX_PROFILES]}, indent=1), encoding="utf-8")
        return True
    except OSError:
        return False


def layout_rows(keys):
    """Group the keys returned by build_layout by physical row -> [[key ids]...] (top to bottom)."""
    rows = {}
    for kid, _label, rects, _poly in keys:
        rows.setdefault(round(rects[0][1] * 2) / 2, []).append(kid)
    return [rows[y] for y in sorted(rows)]


def layout_columns(keys):
    """Group the keys by physical column (left to right), using the unit cell under each key's center.

    Wide keys (Shift, Space...) belong to the column of their center, like a vertical sweep of the keyboard.
    """
    cols = {}
    for kid, _label, rects, _poly in keys:
        x, _y, w, _h = rects[0]
        cols.setdefault(int(x + w / 2), []).append(kid)
    return [cols[x] for x in sorted(cols)]


_migrate_legacy_files()
