# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""The visual keyboard: key items and the view with click / area selection."""
import math

from PySide6.QtCore import (QByteArray, QMarginsF, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer,
                            Signal)
from PySide6.QtGui import (QAction, QActionGroup, QBrush, QColor, QFont, QFontMetricsF, QIcon,
                           QKeySequence, QLinearGradient, QPageLayout, QPageSize, QPainter,
                           QPainterPath, QPalette, QPen, QPixmap, QShortcut, QTextDocument)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup, QCheckBox, QColorDialog,
                               QComboBox, QDialog, QFileDialog, QFrame, QGraphicsItem,
                               QGraphicsScene, QGraphicsView, QGridLayout, QGroupBox,
                               QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
                               QRubberBand, QSlider, QStackedWidget, QTabWidget, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

from .core import (APP_VERSION, ASSETS_DIR, BASE_DIR, CAT_MEMBERS, CATEGORIES, DIRS, EFFECT_IDS,
                   GOLD, I18, KEY_GROUPS, LAYOUT_IDS, LAYOUTS, LIGHT_PRESETS, PRESETS,
                   SELECT_COLOR, SIZE_IDS, THEME_IDS, THEMES, build_layout, hex_to_rgb, luminance,
                   mix, tr)
from .gfx import UNIT, inset, mix as _unused, qcolor, rect_pts, rounded_path


class KeyItem(QGraphicsItem):
    def __init__(self, win, name, label, pts, lines_h):
        super().__init__()
        self.win, self.name, self.label = win, name, label
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.body = rounded_path(inset(pts, 2.5), 7)
        self.top = rounded_path(inset(pts, 6.5, bottom_extra=3.5), 5)
        self.rect_top = self.top.boundingRect()
        self.outline = self.body.boundingRect().adjusted(-9, -9, 9, 9)
        # small legend, like a real keyboard (~19 % of the key side)
        base = max(6.0, UNIT * (0.19 if len(label) <= 3 else 0.16))
        inner = self.rect_top.width() - 8
        font = QFont()
        font.setBold(True)
        px = base
        while px > 5:
            font.setPixelSize(int(round(px)))
            if QFontMetricsF(font).horizontalAdvance(label) <= inner:
                break
            px -= 0.5
        self.font = font

    def boundingRect(self):
        return self.outline

    def shape(self):
        return self.body

    def paint(self, p, option, widget=None):
        P = self.win.pal
        led = self.win.key_color(self.name)
        try:
            lit = luminance(led) > 4
        except ValueError:
            led, lit = "#000000", False
        p.setRenderHint(QPainter.Antialiasing)
        rim = mix(P["rim"], led, 0.55) if lit else P["rim"]
        face = mix(P["face"], led, 0.22) if lit else P["face"]
        if lit:  # LED glow
            for w, a in ((11, 22), (7, 46), (3.5, 90)):
                p.setPen(QPen(qcolor(led, a), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawPath(self.body)
        b = self.body.boundingRect()
        g = QLinearGradient(0, b.top(), 0, b.bottom())
        g.setColorAt(0, QColor(mix(rim, "#ffffff", 0.10)))
        g.setColorAt(1, QColor(mix(rim, "#000000", 0.30)))
        p.setBrush(g)
        p.setPen(QPen(QColor(mix(rim, "#000000", 0.5)), 1))
        p.drawPath(self.body)
        t = self.rect_top
        g = QLinearGradient(0, t.top(), 0, t.bottom())
        g.setColorAt(0, QColor(mix(face, "#ffffff", 0.07)))
        g.setColorAt(1, QColor(mix(face, "#000000", 0.18)))
        p.setBrush(g)
        p.setPen(QPen(QColor(mix(face, "#000000", 0.45)), 0.8))
        p.drawPath(self.top)
        p.setFont(self.font)
        p.setPen(QColor(P["legend_dark"] if luminance(face) > 140 else P["legend_light"]))
        p.drawText(t.adjusted(0, -1, 0, -1), Qt.AlignCenter, self.label)
        if self.isSelected():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(qcolor(SELECT_COLOR, 70), 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(self.body)
            p.setPen(QPen(QColor(SELECT_COLOR), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(self.body)


class KeyboardView(QGraphicsView):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self._press, self._dragging, self._base, self._toggle = None, False, set(), False
        self._replace, self._mods = False, Qt.NoModifier
        self._band = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(220)
        self.items = {}

    def build(self):
        P, sc = self.win.pal, self.scene()
        sc.blockSignals(True)
        self.items = {}
        sc.clear()
        shape, loc = LAYOUTS[self.win.layout_id]
        tkl = self.win.size_id == "tkl"
        keys, panels, width = build_layout(shape == "iso", loc, tkl)
        u, hdr = UNIT, 22.0
        X = lambda v: v * u            # noqa: E731
        Y = lambda v: v * u + hdr      # noqa: E731
        self.setBackgroundBrush(QColor(P["canvas"]))

        frame = QColor(mix(P["panel_edge"], "#ffffff", 0.45))
        path = rounded_path(rect_pts(X(-0.35), Y(-0.35), X(width + 0.2), Y(6.85)), 7)
        item = sc.addPath(path, QPen(frame, 2.5), QBrush(QColor(mix(P["panel"], P["canvas"], 0.5))))
        item.setZValue(-10)
        self.win.update_badge(len(keys))
        for x0, y0, x1, y1 in panels:
            it = sc.addPath(rounded_path(rect_pts(X(x0), Y(y0), X(x1), Y(y1)), 10),
                            QPen(QColor(P["panel_edge"]), 2), QBrush(QColor(P["panel"])))
            it.setZValue(-5)
        for n, label, rects, poly in keys:
            pts_u = poly or rect_pts(rects[0][0], rects[0][1], rects[0][0] + rects[0][2],
                                     rects[0][1] + rects[0][3])
            pts = [(X(px), Y(py)) for px, py in pts_u]
            ki = KeyItem(self.win, n, label, pts, 0)
            sc.addItem(ki)
            self.items[n] = ki
        sc.setSceneRect(X(-0.5), 0, (width + 0.75) * u, Y(6.95) + 4)
        sc.blockSignals(False)
        self.fit()

    def fit(self):
        if self.scene().sceneRect().isValid():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()

    # ---- selection: click, or drag an area from any point (even over a key) ----
    def keys_in(self, poly):
        return {i.name for i in self.scene().items(poly, Qt.IntersectsItemShape)
                if isinstance(i, KeyItem)}

    # Several areas can be accumulated: a plain drag ADDS the area to the current selection,
    # Ctrl+drag toggles the keys it touches, Shift+drag replaces the selection.
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        mods = e.modifiers()
        self._press = e.position().toPoint()
        self._dragging = False
        self._mods = mods
        self._toggle = bool(mods & Qt.ControlModifier)
        self._replace = bool(mods & Qt.ShiftModifier) and not self._toggle
        self._base = set() if self._replace else self.selected()
        e.accept()

    def mouseMoveEvent(self, e):
        if self._press is None:
            return super().mouseMoveEvent(e)
        if not e.buttons() & Qt.LeftButton:  # the release was lost (e.g. outside the view)
            return self.end_drag()
        pos = e.position().toPoint()
        if not self._dragging:
            if (pos - self._press).manhattanLength() < 4:
                return
            self._dragging = True
            self._band.show()
        rect = QRect(self._press, pos).normalized()
        self._band.setGeometry(rect)
        hits = self.keys_in(self.mapToScene(rect))
        self.select(self._base ^ hits if self._toggle else self._base | hits)
        e.accept()

    def mouseReleaseEvent(self, e):
        if self._press is None:
            return super().mouseReleaseEvent(e)
        if not self._dragging:  # plain click
            pt = self.mapToScene(self._press)
            hit = {i.name for i in self.scene().items(pt) if isinstance(i, KeyItem)}
            hit = set(list(hit)[:1])
            if hit:  # click on a key toggles it (Shift: only that key)
                self.select(hit if self._replace else self._base ^ hit)
            elif not self._toggle:  # click on the background clears the selection
                self.select(set())
        self._band.hide()
        self._press, self._dragging = None, False
        e.accept()

    def end_drag(self):
        """Abort any drag in progress so the selection stops following the mouse."""
        self._band.hide()
        self._press, self._dragging = None, False

    def leaveEvent(self, e):
        if self._press is not None and not QApplication.mouseButtons() & Qt.LeftButton:
            self.end_drag()
        super().leaveEvent(e)

    def selected(self):
        return {n for n, it in self.items.items() if it.isSelected()}

    def select(self, names):
        self.scene().blockSignals(True)
        for n, it in self.items.items():
            it.setSelected(n in names)
        self.scene().blockSignals(False)
        self.scene().selectionChanged.emit()
        self.scene().update()


# ======================================================================
#  Main window
