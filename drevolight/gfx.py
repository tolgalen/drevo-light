# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Drawing helpers, palettes, style sheet and vector icons."""
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

UNIT = 46.0  # scene units per key


# ======================================================================
#  Drawing helpers
# ======================================================================
def rounded_path(pts, r):
    """QPainterPath of an orthogonal polygon with rounded corners."""
    n, path = len(pts), QPainterPath()
    for i, v in enumerate(pts):
        p, nx = pts[i - 1], pts[(i + 1) % n]

        def toward(a):
            d = max(math.hypot(a[0] - v[0], a[1] - v[1]), 1e-6)
            k = min(r, d / 2) / d
            return v[0] + (a[0] - v[0]) * k, v[1] + (a[1] - v[1]) * k
        a, b = toward(p), toward(nx)
        (path.moveTo if i == 0 else path.lineTo)(*a)
        path.quadTo(v[0], v[1], *b)
    path.closeSubpath()
    return path


def inset(pts, d, bottom_extra=0.0):
    xs = sorted({p[0] for p in pts})
    ys = sorted({p[1] for p in pts})
    cx, cy = (xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2
    return [(x + d if x < cx else x - d,
             y + d if y < cy else y - d - (bottom_extra if y == ys[-1] else 0)) for x, y in pts]


def rect_pts(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def gear_path(cx, cy, r, n=10):
    step, pts = 2 * math.pi / n, []
    for i in range(n):
        for da, rr in ((-0.30, 0.83), (-0.18, 1.0), (0.18, 1.0), (0.30, 0.83)):
            a = step * (i + da)
            pts.append(QPointF(cx + r * rr * math.cos(a), cy + r * rr * math.sin(a)))
    path = QPainterPath(pts[0])
    for p in pts[1:]:
        path.lineTo(p)
    path.closeSubpath()
    return path


def draw_logo(p, cx, cy, r, bg):
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(GOLD))
    p.drawPath(gear_path(cx, cy, r))
    p.setBrush(QColor(bg))
    p.drawEllipse(QPointF(cx, cy), r * .62, r * .62)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(GOLD), 1.2))
    p.drawEllipse(QPointF(cx, cy), r * .52, r * .52)
    f = QFont()
    f.setBold(True)
    f.setPixelSize(int(r * 0.85))
    p.setFont(f)
    p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), Qt.AlignCenter, "D")


def qcolor(h, alpha=255):
    c = QColor(h)
    c.setAlpha(alpha)
    return c


# ======================================================================
#  Effective palette and stylesheet
# ======================================================================
def system_palette(bg_hex, btn_hex=None, field_hex=None, fg_hex=None, sel_bg="#3584e4", sel_fg="#ffffff"):
    dark = luminance(bg_hex) < 128
    toward = "#ffffff" if dark else "#000000"
    btn = btn_hex or mix(bg_hex, "#ffffff" if dark else "#000000", 0.08)
    if btn.lower() == bg_hex.lower():
        btn = mix(bg_hex, "#ffffff" if dark else "#000000", 0.08)
    fg = fg_hex or ("#e6e6e6" if dark else "#111111")
    return dict(bg=bg_hex, fg=fg, field=field_hex or ("#2b2b2b" if dark else "#ffffff"), btn=btn,
                btn_active=mix(btn, toward, 0.1), border=mix(bg_hex, toward, 0.3), accent=sel_bg,
                sel_bg=sel_bg, sel_fg=sel_fg, canvas=mix(bg_hex, "#000000", 0.06),
                panel=mix(bg_hex, "#000000", 0.14), panel_edge=mix(bg_hex, "#000000", 0.35),
                rim="#000000", face="#121214", title=fg, sub=mix(bg_hex, toward, 0.6),
                legend_dark="#111111", legend_light="#f4f4f4")


def stylesheet(P):
    return f"""
    QWidget {{ background: {P['bg']}; color: {P['fg']}; }}
    QMainWindow, QDialog {{ background: {P['bg']}; }}
    QToolTip {{ background: {P['panel']}; color: {P['fg']}; border: 1px solid {P['border']}; }}
    QGroupBox {{ border: 1px solid {P['border']}; border-radius: 8px; margin-top: 14px;
                 padding: 10px 6px 6px 6px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {P['accent']};
                        font-weight: bold; }}
    QPushButton {{ background: {P['btn']}; border: 1px solid {P['border']}; border-radius: 6px;
                   padding: 5px 12px; }}
    QPushButton:hover {{ background: {P['btn_active']}; border-color: {P['accent']}; }}
    QPushButton:pressed {{ background: {P['border']}; }}
    QComboBox {{ background: {P['field']}; border: 1px solid {P['border']}; border-radius: 6px;
                 padding: 4px 28px 4px 8px; min-height: 20px; }}
    QComboBox:hover {{ border-color: {P['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{ background: {P['field']}; color: {P['fg']}; border: 1px solid {P['border']};
                                   selection-background-color: {P['sel_bg']}; selection-color: {P['sel_fg']}; }}
    QLineEdit, QPlainTextEdit {{ background: {P['field']}; border: 1px solid {P['border']};
                                 border-radius: 6px; padding: 4px 6px; }}
    QTableWidget {{ background: {P['field']}; gridline-color: {P['border']}; border: 1px solid {P['border']};
                    border-radius: 6px; selection-background-color: {P['sel_bg']}; selection-color: {P['sel_fg']}; }}
    QHeaderView::section {{ background: {P['btn']}; color: {P['fg']}; border: none;
                            border-right: 1px solid {P['border']}; padding: 4px; }}
    QSlider::groove:horizontal {{ height: 6px; background: {P['field']}; border-radius: 3px;
                                  border: 1px solid {P['border']}; }}
    QSlider::sub-page:horizontal {{ background: {P['accent']}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: {P['fg']}; width: 16px; margin: -6px 0; border-radius: 8px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {P['border']};
                            border-radius: 4px; background: {P['field']}; }}
    QCheckBox::indicator:checked {{ background: {P['accent']}; }}
    QScrollBar:vertical {{ background: {P['bg']}; width: 12px; }}
    QScrollBar::handle:vertical {{ background: {P['border']}; border-radius: 5px; min-height: 24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QLabel {{ background: transparent; }}
    QGraphicsView {{ border: none; }}
    QMenuBar {{ background: {P['bg']}; border-bottom: 1px solid {P['border']}; }}
    QMenuBar::item {{ padding: 5px 12px; background: transparent; border-radius: 5px; }}
    QMenuBar::item:selected {{ background: {P['btn_active']}; }}
    QMenu {{ background: {P['panel']}; border: 1px solid {P['border']}; border-radius: 6px; padding: 4px; }}
    QMenu::item {{ padding: 6px 28px 6px 20px; border-radius: 4px; background: transparent; }}
    QMenu::item:selected {{ background: {P['sel_bg']}; color: {P['sel_fg']}; }}
    QMenu::separator {{ height: 1px; background: {P['border']}; margin: 4px 8px; }}
    QTabWidget::pane {{ border: 1px solid {P['border']}; border-radius: 6px; }}
    QTabBar::tab {{ background: {P['btn']}; padding: 6px 14px; border: 1px solid {P['border']};
                    border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
    QTabBar::tab:selected {{ background: {P['panel']}; color: {P['accent']}; }}
    """


# ======================================================================
#  Custom widgets
# ======================================================================


# Lucide icons (ISC License, https://lucide.dev), vendored in assets/icons/*.svg
_icon_cache = {}


def icon_renderer(kind, color, width=1.7):
    """QSvgRenderer for assets/icons/<kind>.svg drawn with `color` and stroke `width`."""
    key = (kind, color, width)
    if key not in _icon_cache:
        svg = (ASSETS_DIR / "icons" / f"{kind}.svg").read_text(encoding="utf-8")
        svg = svg.replace("currentColor", color).replace('stroke-width="2"', f'stroke-width="{width}"')
        _icon_cache[key] = QSvgRenderer(QByteArray(svg.encode()))
    return _icon_cache[key]
