# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The native protocol must produce exactly the same packets as the reference library
(dtv2, a dev-only dependency). Run with the keyboard unplugged: HID is faked."""
import sys

import pytest

dtv2 = pytest.importorskip("dtv2")
from drevolight import keys, proto  # noqa: E402

IFACE = {"interface_number": 1, "usage": 0, "usage_page": 0xFF00, "path": b"fake"}


class FakeDevice:
    def __init__(self, log):
        self.log = log

    def open_path(self, path):
        pass

    def write(self, packet):
        # The reference library sometimes sends shorter reports (a quirk when a packet holds
        # fewer than 5 keys); the native code always sends 32 bytes. Zero-padding the short
        # ones makes both comparable: the missing bytes are the zero padding.
        self.log.append(list(packet) + [0] * (32 - len(packet)))
        return len(packet)

    def close(self):
        pass


class FakeHid:
    def __init__(self):
        self.log = []

    def enumerate(self, vid=0, pid=0):
        return [IFACE]

    def device(self):
        return FakeDevice(self.log)


@pytest.fixture
def ref(monkeypatch):
    """Reference keyboard (dtv2) writing into a fake HID."""
    fake = FakeHid()
    monkeypatch.setattr(sys.modules["dtv2.dtv2"], "hid", fake)
    k = dtv2.dtv2("en")
    return k, fake


@pytest.fixture
def mine():
    fake = FakeHid()
    return proto.Keyboard(hid_module=fake), fake


def test_keycodes_match_reference():
    ref_keys = dtv2.dtv2("en")._keys
    for name, code in ref_keys.items():
        assert keys.KEYCODES[name] == code, name


def test_key_order_covers_every_key_once():
    assert sorted(keys.KEY_ORDER) == sorted(keys.KEYCODES)


def test_whole_keyboard(ref, mine):
    r, rf = ref
    m, mf = mine
    ref_keys = dict(r._keys)
    r._keys["iso"] = 0x64  # the reference library lacks the ISO key; the app added it too
    for color in [(12, 34, 56), (0, 0, 0), (255, 255, 255)]:
        rf.log.clear(); mf.log.clear()
        r.kbd(color)
        m.kbd(color)
        assert mf.log == rf.log
    assert ref_keys  # sanity


@pytest.mark.parametrize("cat", ["letters", "digits", "function", "edition", "arrow"])
def test_categories(ref, mine, cat):
    r, rf = ref
    m, mf = mine
    r.category(cat, (1, 2, 3))
    m.category(cat, (1, 2, 3))
    assert mf.log == rf.log


def test_modifier_category_is_a_key_set(ref, mine):
    r, rf = ref
    m, mf = mine
    m.category("mod", (9, 8, 7))
    r.key_set({k: (9, 8, 7) for k in keys.CATEGORY_KEYS["mod"] if k in r._keys})
    assert mf.log == rf.log


def test_key_set_many_keys(ref, mine):
    r, rf = ref
    m, mf = mine
    colors = {k: (i % 256, (i * 7) % 256, (i * 13) % 256)
              for i, k in enumerate(k for k in keys.KEY_ORDER if k in r._keys)}
    r.key_set(colors)
    m.key_set(colors)
    assert mf.log == rf.log


@pytest.mark.parametrize("brightness,speed", [(100, 100), (0, 0), (50, 60), (33, 77)])
def test_effects(ref, mine, brightness, speed):
    r, rf = ref
    m, mf = mine
    c1, c2 = (10, 20, 30), (200, 100, 50)
    for call in [
        lambda k: k.static(c1, brightness=brightness, speed=speed, rainbow=True),
        lambda k: k.static(c1, brightness=brightness, speed=speed),
        lambda k: k.breath(c1, color2=c2, brightness=brightness, speed=speed),
        lambda k: k.radar(c1, color2=c2, brightness=brightness, speed=speed),
        lambda k: k.mem_effect(c1, color2=c2, brightness=brightness),
        lambda k: k.stream(c1, color2=c2, brightness=brightness, speed=speed, direction="s", rainbow=True),
    ]:
        rf.log.clear(); mf.log.clear()
        call(r)
        call(m)
        assert mf.log == rf.log


def test_invalid_input_is_rejected():
    with pytest.raises(KeyError):
        proto.key_packets(["nope"], [(0, 0, 0)])
    with pytest.raises(ValueError):
        proto.key_packets(["a"], [(0, 0, 300)])
    with pytest.raises(ValueError):
        proto.key_packets(["a", "b"], [(0, 0, 0)])


def test_no_keyboard_gives_a_clear_error():
    class Empty(FakeHid):
        def enumerate(self, vid=0, pid=0):
            return []
    with pytest.raises(proto.KeyboardError):
        proto.Keyboard(hid_module=Empty()).kbd((0, 0, 0))
