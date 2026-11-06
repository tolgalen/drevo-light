# -*- mode: python ; coding: utf-8 -*-
# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# PyInstaller spec: `pyinstaller packaging/drevo-light.spec --noconfirm`
import sys
from pathlib import Path

root = Path(SPECPATH).parent

datas = [
    (str(root / "lang"), "lang"),
    (str(root / "assets"), "assets"),
    (str(root / "LICENSE"), "."),
    (str(root / "THIRD_PARTY_LICENSES.txt"), "."),
    (str(root / "70-drevo-tyrfing.rules"), "."),
]

a = Analysis(
    [str(root / "drevo_light.py")],
    pathex=[str(root)],
    datas=datas,
    hiddenimports=["hid"],
    excludes=["tkinter", "dtv2", "colour", "pytest",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuick3D",
              "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtMultimedia", "PySide6.QtNetwork",
              "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtCharts", "PySide6.QtDataVisualization",
              "PySide6.QtBluetooth", "PySide6.QtPdf", "PySide6.QtDesigner", "PySide6.QtHelp"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="drevo-light",
    console=False,
    icon=str(root / "assets" / "icon.ico") if sys.platform.startswith("win") else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="drevo-light")
