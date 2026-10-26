# -*- coding: utf-8 -*-
"""Capa transparente a pantalla completa (click-through) donde Bip dibuja cosas:
corazones, confeti, pelota, dibujos, escaneos, flashes, meteoritos, etc."""
import math
import random

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (QPainter, QColor, QPen, QPainterPath, QFont, QRadialGradient, QLinearGradient)
from PyQt6.QtWidgets import QApplication, QWidget


def clamp(v, a, b):
    return max(a, min(b, v))


def rgba(c, a=255):
    return QColor(int(c[0]), int(c[1]), int(c[2]), int(clamp(a, 0, 255)))


def heart_path(cx, cy, s):
    p = QPainterPath()
    p.moveTo(cx, cy + s * 0.9)
    p.cubicTo(cx - s * 1.6, cy - s * 0.1, cx - s * 0.7, cy - s * 1.2, cx, cy - s * 0.35)
    p.cubicTo(cx + s * 0.7, cy - s * 1.2, cx + s * 1.6, cy - s * 0.1, cx, cy + s * 0.9)
    return p


def star_path(cx, cy, r):
    p = QPainterPath()
    p.moveTo(cx, cy - r)
    p.quadTo(cx, cy, cx + r, cy)
    p.quadTo(cx, cy, cx, cy + r)
    p.quadTo(cx, cy, cx - r, cy)
    p.quadTo(cx, cy, cx, cy - r)
    return p


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput |
                            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.items = []
        self.ox = self.oy = 0
        self.fit()

    def fit(self):
        geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)
        self.ox, self.oy = geo.x(), geo.y()

    def add(self, k, x, y, vx=0.0, vy=0.0, life=1.5, size=8.0, g=0.0, col=(255, 255, 255), **kw):
        if len(self.items) > 500:
            return None
        it = dict(k=k, x=x, y=y, vx=vx, vy=vy, life=life, max=life, s=size, g=g, col=col, age=0.0,
                  ph=random.uniform(0, 6.28))
        it.update(kw)
        self.items.append(it)
        return it

    # ---- atajos
    def hearts(self, x, y, n=3, spread=45):
        for _ in range(n):
            self.add("heart", x + random.uniform(-spread, spread), y + random.uniform(-10, 10),
                     random.uniform(-15, 15), random.uniform(-75, -45), 1.5, random.uniform(5, 8), col=(255, 92, 122))

    def sparkles(self, x, y, n=8, col=(120, 240, 255), speed=120):
        for _ in range(n):
            a = random.uniform(0, 6.28)
            s = random.uniform(.3, 1) * speed
            self.add("spark", x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(.5, 1), random.uniform(3, 6), col=col)

    def confetti(self, x, y, n=40):
        cols = [(255, 99, 132), (54, 162, 235), (255, 206, 86), (75, 192, 120), (153, 102, 255)]
        for _ in range(n):
            a = random.uniform(-2.8, -0.3)
            s = random.uniform(150, 420)
            self.add("confetti", x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(1.4, 2.4),
                     random.uniform(4, 7), g=520, col=random.choice(cols), rot=random.uniform(0, 6), vr=random.uniform(-9, 9))

    def flash(self):
        self.add("flash", 0, 0, life=.45)

    def ring(self, x, y, col=(120, 240, 255), r=90):
        self.add("ring", x, y, life=.9, size=r, col=col)

    # ---- simulación
    def tick(self, dt):
        alive = []
        for it in self.items:
            it["age"] += dt
            k = it["k"]
            if k == "line":
                if not it.get("done"):
                    it["life"] = it["max"]
                    it["max_age"] = it.get("max_age", 0) + dt
                    if it["max_age"] > 40:
                        it["done"] = True
            it["life"] -= dt
            if it["life"] <= 0:
                continue
            if k == "ball":
                self._ball(it, dt)
            else:
                it["vy"] += it["g"] * dt
                it["x"] += it["vx"] * dt
                it["y"] += it["vy"] * dt
                if "vr" in it:
                    it["rot"] += it["vr"] * dt
                if k in ("heart", "note", "zzz"):
                    it["x"] += math.sin(it["age"] * 3 + it["ph"]) * 14 * dt
                if k == "rain" and it["y"] > it.get("floor", 1e9):
                    continue
            alive.append(it)
        self.items = alive
        return bool(alive)

    def _ball(self, it, dt):
        scr = QApplication.screenAt(QApplication.primaryScreen().geometry().center()) or QApplication.primaryScreen()
        try:
            from PyQt6.QtCore import QPoint
            s2 = QApplication.screenAt(QPoint(int(it["x"]), int(it["y"])))
            scr = s2 or scr
        except Exception:
            pass
        g = scr.availableGeometry()
        r = it["s"]
        it["vy"] += 1100 * dt
        it["x"] += it["vx"] * dt
        it["y"] += it["vy"] * dt
        it["rot"] = it.get("rot", 0) + it["vx"] * dt * 0.02
        if it["y"] > g.bottom() - r:
            it["y"] = g.bottom() - r
            it["vy"] = -abs(it["vy"]) * 0.72
            it["vx"] *= 0.92
            if abs(it["vy"]) < 60:
                it["vy"] = 0
        if it["x"] < g.left() + r:
            it["x"] = g.left() + r
            it["vx"] = abs(it["vx"]) * 0.8
        if it["x"] > g.right() - r:
            it["x"] = g.right() - r
            it["vx"] = -abs(it["vx"]) * 0.8
        if it["y"] < g.top() + r:
            it["y"] = g.top() + r
            it["vy"] = abs(it["vy"]) * 0.6

    # ---- dibujo
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(-self.ox, -self.oy)
        for it in self.items:
            try:
                self._draw(p, it)
            except Exception:
                pass
        p.end()

    def _draw(self, p, it):
        k, x, y, s, col = it["k"], it["x"], it["y"], it["s"], it["col"]
        a = clamp(it["life"] / it["max"] * 1.8, 0, 1)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        if k == "heart":
            p.setOpacity(a)
            p.setBrush(rgba(col))
            p.drawPath(heart_path(x, y, s))
        elif k == "spark":
            p.setOpacity(a)
            p.setBrush(rgba(col))
            p.drawPath(star_path(x, y, s))
        elif k == "dot":
            p.setOpacity(a * .8)
            p.setBrush(rgba(col))
            p.drawEllipse(QPointF(x, y), s * a, s * a)
        elif k == "confetti":
            p.setOpacity(a)
            p.translate(x, y)
            p.rotate(math.degrees(it["rot"]))
            p.setBrush(rgba(col))
            p.drawRect(QRectF(-s, -s * .5, s * 2, s))
        elif k == "note":
            p.setOpacity(a)
            c = rgba(col)
            p.setBrush(c)
            p.drawEllipse(QPointF(x, y + s), s * .55, s * .4)
            p.setPen(QPen(c, 2))
            p.drawLine(QPointF(x + s * .5, y + s), QPointF(x + s * .5, y - s))
            p.drawLine(QPointF(x + s * .5, y - s), QPointF(x + s * 1.2, y - s * .4))
        elif k in ("zzz", "text"):
            p.setOpacity(a)
            f = QFont("Segoe UI", int(s), QFont.Weight.Bold)
            f.setItalic(k == "zzz")
            p.setFont(f)
            p.setPen(rgba(col))
            p.drawText(QPointF(x, y), it.get("text", "Z"))
        elif k == "puff":
            p.setOpacity(a * .8)
            p.setBrush(rgba(col))
            r = s * (1 + (1 - it["life"] / it["max"]) * 1.6)
            p.drawEllipse(QPointF(x, y), r, r)
        elif k == "rain":
            p.setOpacity(a)
            p.setPen(QPen(rgba(col, 200), 1.6))
            p.drawLine(QPointF(x, y), QPointF(x + it["vx"] * .02, y - 10))
        elif k == "snow":
            p.setBrush(rgba(col, 230))
            p.drawEllipse(QPointF(x, y), s, s)
        elif k == "star":
            tw = .5 + .5 * math.sin(it["age"] * 6 + it["ph"])
            p.setOpacity(a * (.35 + .65 * tw))
            p.setBrush(rgba(col))
            p.drawPath(star_path(x, y, s * (.7 + .5 * tw)))
        elif k == "flash":
            p.setOpacity(clamp(it["life"] / it["max"], 0, 1) * .85)
            p.setBrush(QColor(255, 255, 255))
            p.drawRect(QRectF(self.ox, self.oy, self.width(), self.height()))
        elif k == "ring":
            t = 1 - it["life"] / it["max"]
            p.setOpacity(1 - t)
            p.setPen(QPen(rgba(col), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(x, y), s * t, s * t)
        elif k == "ball":
            p.setOpacity(a)
            p.setBrush(QColor(0, 0, 0, 40))
            p.drawEllipse(QPointF(x, y + s * .95), s * .9, s * .25)
            g = QRadialGradient(QPointF(x - s * .3, y - s * .3), s * 1.4)
            g.setColorAt(0, QColor(255, 255, 255))
            g.setColorAt(.35, rgba(col))
            g.setColorAt(1, rgba((col[0] * .5, col[1] * .5, col[2] * .5)))
            p.setBrush(g)
            p.drawEllipse(QPointF(x, y), s, s)
            p.setPen(QPen(QColor(255, 255, 255, 170), 2))
            p.translate(x, y)
            p.rotate(math.degrees(it.get("rot", 0)))
            p.drawLine(QPointF(-s * .8, 0), QPointF(s * .8, 0))
        elif k == "line":
            pts = it["pts"]
            if len(pts) > 1:
                path = QPainterPath(QPointF(*pts[0]))
                for q in pts[1:]:
                    path.lineTo(QPointF(*q))
                p.setOpacity(clamp(it["life"] / it["max"] * 2.0, 0, 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                for w, al in ((it["s"] * 3, 40), (it["s"] * 1.8, 90), (it["s"], 255)):
                    pen = QPen(rgba(col, al), w)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    p.setPen(pen)
                    p.drawPath(path)
        elif k == "scan":
            rx, ry, rw, rh = it["rect"]
            t = clamp(it["age"] / (it["max"] * .9), 0, 1)
            p.setOpacity(clamp(it["life"] / it["max"] * 3, 0, 1))
            p.setBrush(rgba(col, 22))
            p.setPen(QPen(rgba(col, 200), 2))
            p.drawRect(QRectF(rx, ry, rw, rh))
            yy = ry + rh * (1 - abs(1 - 2 * t))
            g = QLinearGradient(0, yy - 30, 0, yy + 2)
            g.setColorAt(0, rgba(col, 0))
            g.setColorAt(1, rgba(col, 120))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawRect(QRectF(rx, yy - 30, rw, 32))
            p.setPen(QPen(rgba(col, 255), 3))
            p.drawLine(QPointF(rx, yy), QPointF(rx + rw, yy))
            p.setPen(QPen(rgba(col, 255), 3))
            for cx_, cy_, dx, dy in ((rx, ry, 1, 1), (rx + rw, ry, -1, 1), (rx, ry + rh, 1, -1), (rx + rw, ry + rh, -1, -1)):
                p.drawLine(QPointF(cx_, cy_), QPointF(cx_ + dx * 26, cy_))
                p.drawLine(QPointF(cx_, cy_), QPointF(cx_, cy_ + dy * 26))
        elif k == "meteor":
            tx, ty = x - it["vx"] * .18, y - it["vy"] * .18
            g = QLinearGradient(x, y, tx, ty)
            g.setColorAt(0, QColor(255, 255, 255, 255))
            g.setColorAt(1, QColor(150, 200, 255, 0))
            pen = QPen(g, 5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(x, y), QPointF(tx, ty))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QPointF(x, y), 5, 5)
        p.restore()
