# -*- coding: utf-8 -*-
"""Accesorios (auriculares, bufanda, anteojos, paraguas) y objetos holográficos flotantes."""
import math

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QPolygonF

NOP = Qt.PenStyle.NoPen
NOB = Qt.BrushStyle.NoBrush


def headphones(p, t):
    pen = QPen(QColor("#3C3C46"), 8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(NOB)
    path = QPainterPath(QPointF(-96, -4))
    path.cubicTo(QPointF(-100, -112), QPointF(100, -112), QPointF(96, -4))
    p.drawPath(path)
    p.setPen(NOP)
    for s in (-1, 1):
        p.setBrush(QColor("#E0524F"))
        p.drawRoundedRect(QRectF(s * 96 - 9, -22, 18, 36), 8, 8)
        p.setBrush(QColor("#3C3C46"))
        p.drawRoundedRect(QRectF(s * 96 - 4, -14, 8, 20), 4, 4)


def scarf(p, t):
    red = QColor("#E0524F")
    p.setPen(NOP)
    p.setBrush(red)
    p.drawRoundedRect(QRectF(-88, 46, 176, 20), 10, 10)
    p.setBrush(QColor(255, 255, 255, 200))
    for i in range(-4, 5):
        p.drawRect(QRectF(i * 19 - 2, 48, 4, 16))
    p.save()
    p.translate(52, 56)
    p.rotate(-8 + math.sin(t * 3) * 3)
    p.setBrush(red)
    p.drawRoundedRect(QRectF(0, 0, 18, 38), 6, 6)
    p.setBrush(QColor(255, 255, 255, 190))
    p.drawRect(QRectF(0, 26, 18, 4))
    p.restore()


def sunglasses(p, f):
    p.setPen(NOP)
    p.setBrush(QColor(20, 20, 28, 250))
    for s in (-1, 1):
        p.drawRoundedRect(QRectF(s * f["sp"] - 24, f["ey"] - 20, 48, 38), 14, 14)
        p.setBrush(QColor(255, 255, 255, 70))
        p.drawEllipse(QPointF(s * f["sp"] - 10, f["ey"] - 10), 6, 3)
        p.setBrush(QColor(20, 20, 28, 250))
    p.setPen(QPen(QColor(20, 20, 28), 4))
    p.drawLine(QPointF(-18, f["ey"] - 8), QPointF(18, f["ey"] - 8))


def umbrella(p):
    p.setPen(QPen(QColor("#6B4A2B"), 3))
    p.drawLine(QPointF(0, -64), QPointF(0, -108))
    canopy = QPainterPath(QPointF(-78, -100))
    canopy.quadTo(QPointF(0, -170), QPointF(78, -100))
    for i in range(4):
        xa = 78 - 156 * i / 4
        xb = 78 - 156 * (i + 1) / 4
        canopy.quadTo(QPointF((xa + xb) / 2, -88), QPointF(xb, -100))
    p.setPen(NOP)
    p.setBrush(QColor("#5AA9E6"))
    p.drawPath(canopy)
    p.setBrush(QColor(255, 255, 255, 70))
    st = QPainterPath(QPointF(-14, -100))
    st.quadTo(QPointF(0, -164), QPointF(14, -100))
    st.closeSubpath()
    p.drawPath(st)


def draw_prop(p, name, t):
    """Objeto holográfico en una caja de ~40x40 centrada en el origen."""
    p.setPen(NOP)
    if name == "code":
        p.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        p.setPen(QColor(92, 242, 154))
        p.drawText(QRectF(-28, -14, 56, 28), Qt.AlignmentFlag.AlignCenter, "</>")
    elif name in ("word", "sheet", "slides"):
        c = {"word": "#2B6CD3", "sheet": "#1E8E4E", "slides": "#D9531E"}[name]
        p.setBrush(QColor(c))
        p.drawRoundedRect(QRectF(-17, -17, 34, 34), 6, 6)
        p.setBrush(QColor(255, 255, 255, 235))
        if name == "sheet":
            for i in range(3):
                for j in range(3):
                    p.drawRect(QRectF(-11 + i * 8, -11 + j * 8, 6, 6))
        else:
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
            p.drawText(QRectF(-17, -17, 34, 34), Qt.AlignmentFlag.AlignCenter, "W" if name == "word" else "P")
    elif name == "discord":
        p.setBrush(QColor("#5865F2"))
        p.drawRoundedRect(QRectF(-18, -14, 36, 28), 11, 11)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(-6, -1), 4, 5)
        p.drawEllipse(QPointF(6, -1), 4, 5)
    elif name == "music":
        p.setBrush(QColor(125, 255, 160))
        p.drawEllipse(QPointF(-6, 10), 7, 5)
        p.drawEllipse(QPointF(10, 6), 7, 5)
        p.setPen(QPen(QColor(125, 255, 160), 3))
        p.drawLine(QPointF(0, 10), QPointF(0, -14))
        p.drawLine(QPointF(16, 6), QPointF(16, -18))
        p.drawLine(QPointF(0, -14), QPointF(16, -18))
    elif name == "doc":
        p.setBrush(QColor("#F5F7FA"))
        p.drawRoundedRect(QRectF(-14, -18, 28, 36), 3, 3)
        p.setBrush(QColor("#7aa7ff"))
        for i in range(4):
            p.drawRect(QRectF(-9, -11 + i * 8, 18 - (i == 3) * 8, 3))
    elif name == "brush":
        p.setBrush(QColor("#E8C9A0"))
        p.drawEllipse(QPointF(0, 0), 18, 15)
        for i, c in enumerate(("#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF")):
            p.setBrush(QColor(c))
            p.drawEllipse(QPointF(-8 + (i % 2) * 14, -5 + (i // 2) * 10), 4, 4)
    elif name == "chat":
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(-18, -14, 36, 24), 9, 9)
        p.drawPolygon(QPolygonF([QPointF(-8, 9), QPointF(-12, 18), QPointF(0, 9)]))
        p.setBrush(QColor("#4D96FF"))
        for i in range(3):
            p.drawEllipse(QPointF(-9 + i * 9, -2 - 3 * max(0, math.sin(t * 7 - i)) ), 2.5, 2.5)
    elif name == "popcorn":
        p.setBrush(QColor("#FFF3C4"))
        for dx, dy in ((-7, -14), (0, -18), (8, -13), (-3, -9), (5, -8)):
            p.drawEllipse(QPointF(dx, dy), 5, 5)
        poly = QPolygonF([QPointF(-13, -8), QPointF(13, -8), QPointF(10, 18), QPointF(-10, 18)])
        p.setBrush(QColor("#FFFFFF"))
        p.drawPolygon(poly)
        p.setBrush(QColor("#E0524F"))
        for i in range(3):
            p.drawRect(QRectF(-9 + i * 8, -7, 4, 24))
    elif name == "gamepad":
        p.setBrush(QColor("#3D3F4E"))
        p.drawRoundedRect(QRectF(-20, -10, 40, 22), 10, 10)
        p.setBrush(QColor("#222"))
        p.drawRect(QRectF(-13, -1, 9, 3))
        p.drawRect(QRectF(-10, -4, 3, 9))
        p.setBrush(QColor("#FF6B6B") if int(t * 6) % 2 else QColor("#6BCB77"))
        p.drawEllipse(QPointF(10, -2), 2.5, 2.5)
        p.drawEllipse(QPointF(15, 3), 2.5, 2.5)
    elif name == "mag":
        p.setBrush(NOB)
        p.setPen(QPen(QColor("#CFE8FF"), 4))
        p.drawEllipse(QPointF(-3, -3), 11, 11)
        p.setPen(QPen(QColor("#CFE8FF"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(5, 5), QPointF(15, 15))
    elif name == "cup":
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(-12, -4, 24, 22), 4, 4)
        p.setBrush(NOB)
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.drawArc(QRectF(8, 0, 12, 12), -90 * 16, 180 * 16)
        p.setPen(QPen(QColor(255, 255, 255, 150), 2))
        for i in (-5, 3):
            p.drawLine(QPointF(i, -8 - math.sin(t * 3 + i) * 2), QPointF(i + 2, -16))
    elif name == "glass":
        p.setBrush(QColor(150, 210, 255, 190))
        p.drawPolygon(QPolygonF([QPointF(-11, -14), QPointF(11, -14), QPointF(8, 18), QPointF(-8, 18)]))
        p.setBrush(QColor(255, 255, 255, 140))
        p.drawRect(QRectF(-8, -8, 4, 16))
    elif name == "tomato":
        p.setBrush(QColor("#E8453C"))
        p.drawEllipse(QPointF(0, 2), 16, 14)
        p.setBrush(QColor("#4CAF50"))
        p.drawPolygon(QPolygonF([QPointF(-8, -9), QPointF(0, -5), QPointF(8, -9), QPointF(0, -17)]))
    elif name == "cam":
        p.setBrush(QColor("#3D3F4E"))
        p.drawRoundedRect(QRectF(-18, -10, 36, 24), 5, 5)
        p.setBrush(QColor("#9fd8ff"))
        p.drawEllipse(QPointF(0, 2), 8, 8)
        p.setBrush(QColor("#222"))
        p.drawEllipse(QPointF(0, 2), 4, 4)
    elif name == "bulb":
        p.setBrush(QColor("#FFE066"))
        p.drawEllipse(QPointF(0, -4), 11, 11)
        p.setBrush(QColor("#B8BCC6"))
        p.drawRect(QRectF(-6, 6, 12, 8))
    elif name == "battery":
        p.setBrush(NOB)
        p.setPen(QPen(QColor("#FF6B6B"), 3))
        p.drawRoundedRect(QRectF(-16, -9, 30, 18), 4, 4)
        p.setPen(NOP)
        p.setBrush(QColor("#FF6B6B"))
        p.drawRect(QRectF(15, -4, 4, 8))
        if int(t * 3) % 2:
            p.drawRect(QRectF(-13, -6, 6, 12))
