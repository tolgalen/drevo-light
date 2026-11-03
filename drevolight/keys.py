# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Key identifiers, their USB HID usage codes and the key groups used for lighting.

The codes are the standard "Keyboard/Keypad Page (0x07)" usage ids of the USB HID
Usage Tables, except ``FN`` (0xED) which is the vendor code the Drevo firmware uses.
Key *names* are layout independent: they name the physical position (``#`` is the
ISO key next to Enter, ``iso`` is the ISO key next to the left Shift).
"""

KEYCODES = {
    **{c: 0x04 + i for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")},
    **{d: 0x1E + i for i, d in enumerate("1234567890")},
    "enter": 0x28, "esc": 0x29, "BACKS": 0x2A, "tab": 0x2B, "space": 0x2C,
    "-": 0x2D, "=": 0x2E, "[": 0x2F, "]": 0x30, "\\": 0x31, "#": 0x32, ";": 0x33,
    "'": 0x34, "~": 0x35, ",": 0x36, ".": 0x37, "/": 0x38, "caps": 0x39,
    **{f"f{i}": 0x3A + i - 1 for i in range(1, 13)},
    "PS": 0x46, "SL": 0x47, "PB": 0x48,
    "ins": 0x49, "home": 0x4A, "p-up": 0x4B, "del": 0x4C, "end": 0x4D, "p-down": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
    "kpnlk": 0x53, "kpdiv": 0x54, "kpmul": 0x55, "kpsub": 0x56, "kpadd": 0x57, "kpent": 0x58,
    **{f"kp{i}": 0x59 + i - 1 for i in range(1, 10)},
    "kp0": 0x62, "kpdot": 0x63, "iso": 0x64, "compo": 0x65,
    "lctrl": 0xE0, "lshift": 0xE1, "lalt": 0xE2, "win": 0xE3,
    "rctrl": 0xE4, "rshift": 0xE5, "ralt": 0xE6, "FN": 0xED,
}

# Order in which a "paint the whole keyboard" command visits the keys (row by row).
KEY_ORDER = (
    ["esc"] + [f"f{i}" for i in range(1, 13)] + ["PS", "SL", "PB"]
    + ["~", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-", "=", "BACKS",
       "ins", "home", "p-up", "kpnlk", "kpdiv", "kpmul", "kpsub"]
    + ["tab"] + list("qwertyuiop") + ["[", "]", "\\", "#", "del", "end", "p-down",
                                         "kp7", "kp8", "kp9"]
    + ["caps"] + list("asdfghjkl") + [";", "'", "enter", "kp4", "kp5", "kp6", "kpadd"]
    + ["lshift"] + list("zxcvbnm") + [",", ".", "/", "rshift", "up", "kp1", "kp2", "kp3"]
    + ["lctrl", "win", "lalt", "space", "ralt", "FN", "compo", "rctrl", "left", "down",
       "right", "kp0", "kpdot", "kpent"]
    + ["iso"]
)

# Key groups that can be lit with a single command (and that the editor previews).
CATEGORY_KEYS = {
    "letters": list("abcdefghijklmnopqrstuvwxyz"),
    "digits": list("0123456789"),
    "function": ["esc"] + [f"f{i}" for i in range(1, 13)],
    "mod": ["lshift", "rshift", "lctrl", "rctrl", "lalt", "ralt", "win", "FN", "compo"],
    "edition": ["ins", "home", "p-up", "del", "end", "p-down"],
    "arrow": ["left", "right", "down", "up"],
}
CATEGORIES = list(CATEGORY_KEYS)
NUMPAD_KEYS = ["kpnlk", "kpdiv", "kpmul", "kpsub", "kp7", "kp8", "kp9", "kp4", "kp5", "kp6",
               "kp1", "kp2", "kp3", "kp0", "kpdot", "kpadd", "kpent"]
