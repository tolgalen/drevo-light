# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Native lighting protocol of the Drevo Tyrfing V2 (USB HID 0416:a0f8).

Every command is a 32-byte HID output report. The packet builders are pure
functions (easy to test); `Keyboard` opens the device and writes them.
"""
from .core import tr
from .keys import CATEGORY_KEYS, KEY_ORDER, KEYCODES

try:
    import hid
except ImportError:  # the GUI still starts and explains what is missing
    hid = None

VENDOR_ID, PRODUCT_ID = 0x0416, 0xA0F8
PACKET_LEN = 32
KEYS_PER_PACKET = 5

# 7-byte command headers
_HDR_KEYS = (0x06, 0xBE, 0x19, 0x00, 0x01, 0x01, 0x0E)        # per-key colors
_HDR_PREPARE = (0x06, 0xBE, 0x15, 0x00, 0x01, 0x01, 0x0F)     # before a whole-keyboard paint
_HDR_COMMIT = (0x06, 0xBE, 0x15, 0x00, 0x02, 0x01, 0x01)      # after a whole-keyboard paint
_HDR_EFFECT = {name: (0x06, 0xBE, 0x15, 0x00, 0x01, 0x01, code) for name, code in
               (("static", 0x01), ("breath", 0x02), ("stream", 0x03),
                ("mem_effect", 0x0D), ("radar", 0x10))}
DIRECTIONS = {"e": 0, "w": 1, "s": 2, "n": 3}


def _blank():
    return [0] * PACKET_LEN


def _chunks(items, size=KEYS_PER_PACKET):
    return [items[i:i + size] for i in range(0, len(items), size)]


def _check_color(rgb):
    rgb = tuple(int(v) for v in rgb)
    if len(rgb) != 3 or any(not 0 <= v <= 255 for v in rgb):
        raise ValueError(f"invalid RGB color: {rgb}")
    return rgb


def key_packets(keys, colors):
    """Packets that set the color of `keys` (up to 5 keys per packet)."""
    if len(keys) != len(colors):
        raise ValueError("keys and colors must have the same length")
    packets = []
    for ks, cs in zip(_chunks(list(keys)), _chunks(list(colors))):
        pkt = _blank()
        pkt[0:7] = _HDR_KEYS
        for i, (k, c) in enumerate(zip(ks, cs)):
            if k not in KEYCODES:
                raise KeyError(f"unknown key: {k!r}")
            pkt[7 + i] = KEYCODES[k]
            pkt[12 + 4 * i:15 + 4 * i] = _check_color(c)
        packets.append(pkt)
    return packets


def whole_keyboard_packets(rgb):
    """Paint every key with one color: prepare packet + key packets + commit packet."""
    rgb = _check_color(rgb)
    prepare = _blank()
    prepare[0:7] = _HDR_PREPARE
    prepare[8] = 0x06
    prepare[12] = 0xFF
    body = key_packets(KEY_ORDER, [rgb] * len(KEY_ORDER))
    body[0][15] = 0x53  # marker bytes expected by the firmware in the first packet
    body[0][31] = 0x65
    commit = _blank()
    commit[0:7] = _HDR_COMMIT
    commit[7], commit[8] = 0x05, 0x09
    commit[12] = commit[16] = 0xFF
    return [prepare] + body + [commit]


def effect_packet(name, color1, color2=(255, 0, 0), brightness=100, speed=100,
                  direction=0, rainbow=False):
    """Packet that starts one of the effects stored in the keyboard firmware."""
    pkt = _blank()
    pkt[0:7] = _HDR_EFFECT[name]
    if name != "mem_effect":
        pkt[7] = int(round(speed / 100 * 9))
        pkt[9] = direction
        pkt[15] = 1 if rainbow else 0
    pkt[8] = int(round(brightness / 100 * 6))
    pkt[12:15] = _check_color(color1)
    pkt[16:19] = _check_color(color2)
    return pkt


class KeyboardError(RuntimeError):
    """Raised with a translated message when the keyboard cannot be reached."""


def list_interfaces(hid_module=None):
    h = hid_module or hid
    return list(h.enumerate(VENDOR_ID, PRODUCT_ID)) if h else []


def describe(i):
    return tr("iface.describe", n=i["interface_number"], up=f"{i['usage_page']:04x}",
              u=f"{i['usage']:04x}")


class Keyboard:
    """Opens the keyboard for each command and writes the packets."""

    def __init__(self, forced_path=None, hid_module=None):
        self.forced_path = forced_path
        self.hid = hid_module or hid

    def _candidates(self):
        interfaces = list_interfaces(self.hid)
        if self.forced_path:
            return [i for i in interfaces if i["path"] == self.forced_path]

        def rank(i):
            if i["interface_number"] == 1 and i["usage"] == 0:
                return 0
            if i["interface_number"] == 1:
                return 1
            return 2 if i["usage_page"] >= 0xFF00 else 3
        return sorted(interfaces, key=rank)

    def _open(self):
        """Open the best available interface -> (device, interface info)."""
        if self.hid is None:
            raise KeyboardError(tr("err.libs"))
        candidates = self._candidates()
        if not candidates:
            raise KeyboardError(tr("err.nokbd"))
        last = None
        for i in candidates:
            try:
                dev = self.hid.device()
                dev.open_path(i["path"])
                return dev, i
            except Exception as e:  # noqa: BLE001
                last = e
        raise KeyboardError(tr("err.open", err=last))

    @staticmethod
    def _write(dev, iface, packets):
        for pkt in packets:
            if dev.write(list(pkt)) == -1:
                try:
                    err = dev.error()
                except Exception:  # noqa: BLE001
                    err = "?"
                raise KeyboardError(tr("err.write", iface=describe(iface), err=err))

    def _send(self, packets):
        dev, iface = self._open()
        try:
            self._write(dev, iface, packets)
        finally:
            dev.close()

    def session(self):
        """Keep the device open for many writes (animations). Use as a context manager."""
        return Session(self)

    # -- commands -------------------------------------------------------------
    def kbd(self, rgb):
        """Whole keyboard in one color."""
        self._send(whole_keyboard_packets(rgb))

    def category(self, name, rgb):
        keys = CATEGORY_KEYS[name]
        self._send(key_packets(keys, [rgb] * len(keys)))

    def key_set(self, colors):
        """colors: {key name: (r, g, b)}"""
        self._send(key_packets(list(colors), list(colors.values())))

    def static(self, color1, brightness=100, speed=100, rainbow=False):
        self._send([effect_packet("static", color1, brightness=brightness, speed=speed,
                                  rainbow=rainbow)])

    def breath(self, color1, color2=(255, 0, 0), brightness=100, speed=100):
        self._send([effect_packet("breath", color1, color2, brightness, speed)])

    def radar(self, color1, color2=(255, 0, 0), brightness=100, speed=100, direction=0):
        self._send([effect_packet("radar", color1, color2, brightness, speed, direction)])

    def stream(self, color1, color2=(255, 0, 0), brightness=100, speed=100, direction="e",
               rainbow=False):
        self._send([effect_packet("stream", color1, color2, brightness, speed,
                                  DIRECTIONS[direction], rainbow)])

    def mem_effect(self, color1, color2=(255, 0, 0), brightness=100):
        self._send([effect_packet("mem_effect", color1, color2, brightness)])


class Session:
    """An open device that accepts many packet lists; closes on exit."""

    def __init__(self, keyboard):
        self._kb = keyboard
        self._dev = self._iface = None

    def __enter__(self):
        self._dev, self._iface = self._kb._open()
        return self

    def __exit__(self, *exc):
        if self._dev is not None:
            self._dev.close()
            self._dev = None

    def send(self, packets):
        self._kb._write(self._dev, self._iface, packets)
