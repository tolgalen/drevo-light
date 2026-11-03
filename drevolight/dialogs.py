# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Dialogs: user manual, about, licenses, gradient, profile manager and udev installer."""
import subprocess
import sys

from PySide6.QtCore import QMarginsF, QRectF, QSize, Qt
from PySide6.QtGui import (QColor, QFont, QIcon, QPageLayout, QPageSize, QPainter, QPixmap,
                           QTextDocument)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
                               QTabWidget, QTextBrowser, QVBoxLayout)

from . import core
from .core import (APP_VERSION, ASSETS_DIR, BASE_DIR, CAT_MEMBERS, CATEGORIES, I18, LAYOUTS,
                   build_layout, luminance, mix, tr)
from .state import resolve_color


# ---------------------------------------------------------------- user manual
def manual_html(pal, printing=False):
    """Manual of the current language wrapped with a stylesheet (dark text on white for printing)."""
    for code in (I18.cur, "en"):
        f = BASE_DIR / "lang" / f"manual_{code}.html"
        if f.exists():
            body = f.read_text(encoding="utf-8")
            break
    else:
        body = f"<p>{tr('manual.missing')}</p>"
    if printing:
        fg, head, acc = "#111111", "#000000", "#8a5a00"
    else:
        fg, head, acc = pal["fg"], pal["title"], pal["accent"]
    css = (f"body {{ color: {fg}; font-size: 11pt; }} h1 {{ color: {head}; font-size: 22pt; }} "
           f"h2 {{ color: {acc}; font-size: 15pt; margin-top: 18px; }} "
           f"h3 {{ color: {head}; font-size: 12pt; }} li {{ margin-bottom: 4px; }} "
           f"code {{ font-family: monospace; }}")
    return f"<html><head><style>{css}</style></head><body>{body}</body></html>"


def export_manual_pdf(pal, path):
    doc = QTextDocument()
    doc.setHtml(manual_html(pal, printing=True))
    pr = _new_printer()
    pr.setOutputFormat(QPrinter.PdfFormat)
    pr.setOutputFileName(path)
    doc.print_(pr)


def _new_printer():
    pr = QPrinter(QPrinter.HighResolution)
    pr.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait,
                                 QMarginsF(18, 16, 18, 16), QPageLayout.Millimeter))
    return pr


def show_manual(win):
    dlg = QDialog(win)
    dlg.setWindowTitle(tr("manual.title"))
    dlg.resize(900, 700)
    lay = QVBoxLayout(dlg)
    view = QTextBrowser()
    view.setOpenExternalLinks(True)
    view.setHtml(manual_html(win.pal))
    lay.addWidget(view, 1)

    def do_print():
        pr = _new_printer()
        if QPrintDialog(pr, dlg).exec() == QDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(manual_html(win.pal, printing=True))
            doc.print_(pr)

    def do_pdf():
        path, _ = QFileDialog.getSaveFileName(dlg, tr("btn.pdf"), "Drevo-Light-manual.pdf",
                                              f"{tr('file.pdf')} (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            export_manual_pdf(win.pal, path)
            win.status.setText(tr("msg.pdf_saved", path=path))

    h = QHBoxLayout()
    h.addStretch(1)
    for key, fn in (("btn.print", do_print), ("btn.pdf", do_pdf), ("btn.close", dlg.accept)):
        b = QPushButton(tr(key))
        b.clicked.connect(fn)
        h.addWidget(b)
    lay.addLayout(h)
    dlg.exec()


# ------------------------------------------------------------ about / licenses
def show_about(win):
    dlg = QDialog(win)
    dlg.setWindowTitle(tr("about.title"))
    dlg.setMinimumWidth(520)
    lay = QVBoxLayout(dlg)
    lay.setSpacing(10)
    top = QHBoxLayout()
    pm = QPixmap(str(ASSETS_DIR / "icon.png")).scaled(88, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    ic = QLabel()
    ic.setPixmap(pm)
    top.addWidget(ic, 0, Qt.AlignTop)
    info = QVBoxLayout()
    t = QLabel("Drevo Light")
    t.setStyleSheet("font-size: 24px; font-weight: bold;")
    info.addWidget(t)
    info.addWidget(QLabel(tr("app.version", v=APP_VERSION) + "  ·  GPL-3.0-or-later"))
    d = QLabel(tr("about.desc"))
    d.setWordWrap(True)
    info.addWidget(d)
    info.addWidget(QLabel(tr("about.copyright")))
    top.addLayout(info, 1)
    lay.addLayout(top)
    for text in (tr("about.note"), tr("about.credits")):
        lb = QLabel(text)
        lb.setWordWrap(True)
        lb.setStyleSheet(f"color: {win.pal['sub']};")
        lay.addWidget(lb)
    link = QLabel('<a href="https://www.gnu.org/licenses/gpl-3.0.html">https://www.gnu.org/licenses/gpl-3.0.html</a>')
    link.setOpenExternalLinks(True)
    lay.addWidget(link)
    h = QHBoxLayout()
    h.addStretch(1)
    b = QPushButton(tr("btn.license"))
    b.clicked.connect(lambda: (dlg.accept(), show_licenses(win, 0)))
    h.addWidget(b)
    b = QPushButton(tr("btn.close"))
    b.clicked.connect(dlg.accept)
    h.addWidget(b)
    lay.addLayout(h)
    dlg.exec()


def show_licenses(win, tab=0):
    dlg = QDialog(win)
    dlg.setWindowTitle(tr("license.title"))
    dlg.resize(820, 600)
    lay = QVBoxLayout(dlg)
    tabs = QTabWidget()
    mono = QFont("monospace")
    mono.setStyleHint(QFont.Monospace)
    for fname, title in (("LICENSE", tr("license.tab_app")),
                         ("THIRD_PARTY_LICENSES.txt", tr("license.tab_third"))):
        te = QPlainTextEdit()
        te.setReadOnly(True)
        te.setFont(mono)
        try:
            te.setPlainText((BASE_DIR / fname).read_text(encoding="utf-8"))
        except OSError:
            te.setPlainText(tr("license.missing", name=fname))
        tabs.addTab(te, title)
    tabs.setCurrentIndex(tab)
    lay.addWidget(tabs)
    h = QHBoxLayout()
    h.addStretch(1)
    b = QPushButton(tr("btn.close"))
    b.clicked.connect(dlg.accept)
    h.addWidget(b)
    lay.addLayout(h)
    dlg.exec()


# ------------------------------------------------------------------- gradient
class GradientDialog(QDialog):
    """Choose how to fill the selected keys: two-color blend or rainbow, horizontal or vertical."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(tr("gradient.title"))
        self.colors = [win.paint_color, "#0000ff"]
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("gradient.mode")))
        self.mode = QComboBox()
        self.mode.addItems([tr("gradient.two"), tr("gradient.rainbow")])
        self.mode.currentIndexChanged.connect(self._toggle)
        row.addWidget(self.mode, 1)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.btns = []
        for i in range(2):
            row.addWidget(QLabel(tr(f"fx.color{i + 1}")))
            b = win.swatch(self.colors[i], 64)
            b.clicked.connect(lambda _=False, i=i: self._pick(i))
            row.addWidget(b)
            self.btns.append(b)
        row.addStretch(1)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("gradient.dir")))
        self.direction = QComboBox()
        self.direction.addItems([tr("gradient.h"), tr("gradient.v")])
        row.addWidget(self.direction, 1)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addStretch(1)
        for key, fn in (("btn.ok", self.accept), ("btn.cancel", self.reject)):
            b = QPushButton(tr(key))
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)

    def _toggle(self):
        for b in self.btns:
            b.setEnabled(self.mode.currentIndex() == 0)

    def _pick(self, i):
        hx = self.win.ask_color(self.colors[i])
        if hx:
            self.colors[i] = hx
            self.win.set_swatch(self.btns[i], hx)

    def result_config(self):
        return {"mode": "two" if self.mode.currentIndex() == 0 else "rainbow",
                "color1": self.colors[0], "color2": self.colors[1],
                "axis": "x" if self.direction.currentIndex() == 0 else "y"}


# ------------------------------------------------------------ profile manager
def profile_thumbnail(data, layout_id, size_id, pal, w=220, h=82):
    """Small picture of the keyboard colored with a profile's data."""
    shape, loc = LAYOUTS[layout_id]
    keys, _panels, width = build_layout(shape == "iso", loc, size_id == "tkl")
    pm = QPixmap(w, h)
    pm.fill(QColor(pal["canvas"]))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    cats = data.get("categories", {})
    enabled = {c: cats.get(c, {}).get("on", False) for c in CATEGORIES}
    colors = {c: cats.get(c, {}).get("color", "#ffffff") for c in CATEGORIES}
    base, painted = data.get("base", "#000000"), data.get("keys", {})
    u = min((w - 8) / (width + 0.3), (h - 8) / 6.6)
    ox, oy = (w - width * u) / 2, (h - 6.5 * u) / 2
    for kid, _label, rects, _poly in keys:
        col = resolve_color(kid, base, enabled, colors, painted)
        try:
            lit = luminance(col) > 4
        except ValueError:
            col, lit = "#000000", False
        fill = QColor(col) if lit else QColor(mix(pal["rim"], pal["panel"], 0.5))
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        for x, y, rw, rh in rects:
            p.drawRoundedRect(QRectF(ox + x * u + 0.6, oy + y * u + 0.6, rw * u - 1.2, rh * u - 1.2), 1.6, 1.6)
    p.end()
    return pm


class ProfileManager(QDialog):
    """List of the 20 profile slots with thumbnails and the usual actions."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(tr("profile.manager_title"))
        self.resize(560, 640)
        lay = QVBoxLayout(self)
        self.listw = QListWidget()
        self.listw.setIconSize(QSize(220, 82))
        self.listw.setSpacing(2)
        self.listw.itemDoubleClicked.connect(lambda _it: self._act(win.load_slot))
        lay.addWidget(self.listw, 1)
        row = QHBoxLayout()
        for key, fn in (("btn.load", win.load_slot), ("profile.save_here", win.save_slot),
                        ("profile.rename", win.rename_slot), ("profile.delete", win.delete_slot)):
            b = QPushButton(tr(key))
            b.clicked.connect(lambda _=False, fn=fn: self._act(fn))
            row.addWidget(b)
        row.addStretch(1)
        b = QPushButton(tr("btn.close"))
        b.clicked.connect(self.accept)
        row.addWidget(b)
        lay.addLayout(row)
        self.refresh()

    def refresh(self):
        row = max(self.listw.currentRow(), 0)
        self.listw.clear()
        slots = core.load_profiles()
        for i, slot in enumerate(slots):
            name = slot["name"] if slot else tr("profile.empty")
            it = QListWidgetItem(f"{i + 1:>2}.  {name}")
            if slot:
                data = slot["data"]
                lay_id = data.get("layout", {}).get("id", self.win.layout_id)
                size_id = data.get("layout", {}).get("size", self.win.size_id)
                if lay_id not in LAYOUTS:
                    lay_id = self.win.layout_id
                it.setIcon(QIcon(profile_thumbnail(data, lay_id, size_id if size_id in ("tkl", "full") else "tkl",
                                                   self.win.pal)))
            self.listw.addItem(it)
        self.listw.setCurrentRow(row)

    def _act(self, fn):
        i = self.listw.currentRow()
        if i >= 0:
            fn(i)
            self.refresh()


# -------------------------------------------------------------- udev (Linux)
UDEV_RULES = (
    '# Drevo Tyrfing V2: grant access to the logged-in local user only (uaccess)\n'
    'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="a0f8", TAG+="uaccess"\n'
    'SUBSYSTEM=="usb", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="a0f8", TAG+="uaccess"\n')


def udev_command(rules_path=None):
    """Command (run through pkexec) that installs the udev rule for the keyboard.

    The rule text is a constant embedded here, NOT copied from a file in the (user-writable)
    install folder, so an unprivileged user cannot swap the content that root installs.
    `rules_path` is kept only for backward compatibility and is ignored.
    """
    import shlex
    return ["pkexec", "sh", "-c",
            f"printf %s {shlex.quote(UDEV_RULES)} > /etc/udev/rules.d/99-drevo-tyrfing.rules "
            "&& chmod 644 /etc/udev/rules.d/99-drevo-tyrfing.rules "
            "&& udevadm control --reload && udevadm trigger"]


def install_udev_rules(win):
    """Ask for confirmation, then install the rules with administrator permissions (Linux only)."""
    cmd = udev_command()
    if QMessageBox.question(win, tr("menu.install_udev"),
                            tr("udev.confirm", cmd=cmd[3])) != QMessageBox.Yes:
        return
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        QMessageBox.critical(win, tr("err.title"), tr("udev.fail", err=e))
        return
    if res.returncode == 0:
        QMessageBox.information(win, tr("menu.install_udev"), tr("udev.ok"))
    else:
        QMessageBox.critical(win, tr("err.title"), tr("udev.fail", err=(res.stderr or res.stdout).strip()))


def udev_supported():
    return sys.platform.startswith("linux")
