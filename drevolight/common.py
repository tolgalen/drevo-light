# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Small helpers and constants shared by the main window and its mixins."""
import re

from .keys import KEYCODES

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
KEY_BY_LOWER = {k.lower(): k for k in KEYCODES}
MAX_RECENT = 12


def clean_color(value, default):
    return value if isinstance(value, str) and HEX_COLOR.match(value) else default
