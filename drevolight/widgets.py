# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Small custom widgets: connection dot, logo, sidebar button and splash screen."""
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
from .gfx import draw_logo, icon_renderer


class Dot(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(18, 18)
        self.color = "#999999"

    def set_color(self, c):
        self.color = c
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.color))
        p.drawEllipse(2, 2, 14, 14)


class LogoWidget(QWidget):
    def __init__(self, P):
        super().__init__()
        self.P = P
        self.setFixedSize(112, 112)

    def paintEvent(self, _):
        p = QPainter(self)
        bg = self.P["canvas"]
        p.fillRect(self.rect(), QColor(bg))
        draw_logo(p, 56, 44, 30, bg)
        f = QFont()
        f.setBold(True)
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(QColor(self.P["title"]))
        p.drawText(QRectF(0, 72, 112, 16), Qt.AlignCenter, "DREVO")
        f.setBold(False)
        f.setPixelSize(10)
        p.setFont(f)
        p.setPen(QColor(self.P["sub"]))
        p.drawText(QRectF(0, 88, 112, 14), Qt.AlignCenter, tr("app.version", v=APP_VERSION))




class NavButton(QAbstractButton):
    """Sidebar button: Lucide icon + text, with an accent bar when selected."""

    def __init__(self, kind, text, P):
        super().__init__()
        self.kind, self.P = kind, P
        self.setText(text)
        self.setCheckable(True)
        self.setFixedSize(108, 82)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, _):
        P, sel = self.P, self.isChecked()
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        if sel or self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(mix(P["canvas"], P["accent"], 0.16) if sel else P["btn_active"]))
            p.drawRoundedRect(r, 10, 10)
        if sel:  # accent bar on the left
            p.setBrush(QColor(P["accent"]))
            p.drawRoundedRect(QRectF(0, 20, 3.5, self.height() - 40), 1.7, 1.7)
        col = P["accent"] if sel else (P["fg"] if self._hover else P["sub"])
        icon_renderer(self.kind, col).render(p, QRectF(self.width() / 2 - 16, 12, 32, 32))
        f = QFont()
        f.setPixelSize(13)
        f.setWeight(QFont.DemiBold if sel else QFont.Medium)
        p.setFont(f)
        p.setPen(QColor(P["title"] if sel else col))
        p.drawText(QRectF(0, 50, self.width(), 22), Qt.AlignCenter, self.text())


class Splash(QWidget):
    done = Signal()

    def __init__(self):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.W, self.H, self.step = 560, 300, 0
        self.setFixedSize(self.W, self.H)
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - self.W // 2, scr.center().y() - self.H // 2 - 60)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(35)

    def tick(self):
        self.step += 1
        self.update()
        if self.step > 20:
            self.timer.stop()
            self.close()
            self.done.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = "#1b1b1c"
        g = QLinearGradient(0, 0, 0, self.H)
        g.setColorAt(0, QColor("#262628"))
        g.setColorAt(1, QColor(bg))
        p.fillRect(self.rect(), g)
        p.setPen(QPen(QColor("#6b6b6f"), 2))
        p.drawRect(1, 1, self.W - 2, self.H - 2)
        p.setPen(QPen(QColor("#3a3a3d"), 1))
        p.drawRect(12, 12, self.W - 24, self.H - 24)
        draw_logo(p, 112, 118, 58, bg)
        f = QFont()
        f.setBold(True)
        f.setPixelSize(18)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(32, 184, 160, 24), Qt.AlignCenter, "DREVO")
        f.setBold(False)
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(QColor("#bdbdc0"))
        p.drawText(QRectF(32, 208, 160, 18), Qt.AlignCenter, tr("app.version", v=APP_VERSION))
        f.setBold(True)
        f.setPixelSize(34)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(214, 66, 330, 46), Qt.AlignLeft | Qt.AlignVCenter, "TYRFING V2")
        f.setPixelSize(21)
        p.setFont(f)
        p.setPen(QColor(GOLD))
        p.drawText(QRectF(214, 112, 330, 32), Qt.AlignLeft | Qt.AlignVCenter, "KEYBOARD ENGINE")
        f.setBold(False)
        f.setPixelSize(13)
        p.setFont(f)
        p.setPen(QColor("#bdbdc0"))
        p.drawText(QRectF(214, 148, 330, 22), Qt.AlignLeft | Qt.AlignVCenter, tr("banner.subtitle"))
        p.setPen(QColor("#8f8f93"))
        f.setPixelSize(12)
        p.setFont(f)
        p.drawText(QRectF(40, 226, 300, 18), Qt.AlignLeft, tr("splash.loading"))
        p.setPen(QPen(QColor("#6b6b6f"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(40, 250, self.W - 80, 10), 5, 5)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(GOLD))
        p.drawRoundedRect(QRectF(41, 251, (self.W - 82) * min(self.step, 20) / 20, 8), 4, 4)


# ======================================================================
#  Visual keyboard (QGraphicsView)
