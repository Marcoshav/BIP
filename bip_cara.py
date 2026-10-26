# -*- coding: utf-8 -*-
"""Cuerpo rectangular, pantalla y caras (ojos LED) de Bip."""
import math

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (QPainter, QColor, QPen, QPainterPath, QLinearGradient, QRadialGradient, QPolygonF)
from bip_fx import heart_path, clamp, rgba

BODY_W, BODY_H = 180, 124
SCR_W, SCR_H = 160, 108


def G(**k):
    d = dict(ew=34, eh=46, rd=.45, sp=42, ey=-8, tilt=0.0, lid=0.0, blid=0.0, sm=0.0, wk=0.0, ea=0.0,
             mc=.25, mo=0.0, mw=11.0, my=26.0, wv=0.0, tg=0.0, md=0.0, bl=0.0, look=1.0, col=(89, 242, 255))
    d.update(k)
    return d


FACES = {
    "neutral": G(),
    "happy": G(blid=.4, mc=.85, ew=36, eh=44, bl=.5),
    "joy": G(sm=1, mc=1, mo=.7, ew=36, bl=.8, col=(120, 255, 190)),
    "excited": G(ew=40, eh=54, mc=1, mo=.8, bl=.6, col=(255, 226, 106)),
    "laugh": G(sm=1, mc=1, mo=1, mw=15, bl=.8, col=(255, 226, 106)),
    "love": G(mc=.9, ew=44, eh=44, bl=1, col=(255, 105, 160)),
    "kiss": G(sm=.9, mc=0, mo=.5, mw=5, bl=1, col=(255, 130, 180)),
    "wink": G(wk=1, mc=.9, blid=.2, bl=.4),
    "proud": G(sm=.8, mc=.7, bl=.5, col=(255, 226, 106)),
    "drink": G(sm=.8, mc=.3, bl=.4, col=(120, 220, 255)),
    "sleepy": G(lid=.55, eh=40, mc=-.05, look=.4, col=(120, 180, 200)),
    "sleep": G(eh=7, ew=44, rd=1, mc=0, mw=6, look=0, col=(70, 120, 160)),
    "yawn": G(lid=.8, mo=1, mc=0, mw=9, look=0, col=(120, 180, 200)),
    "tired": G(lid=.45, eh=38, mc=-.15, tilt=-.3, look=.5, col=(130, 170, 200)),
    "bored": G(lid=.5, mc=-.2, look=.6, col=(150, 190, 210)),
    "cold": G(ew=30, tilt=-.5, lid=.1, mc=0, wv=1, col=(160, 215, 255)),
    "hot": G(lid=.35, mo=.5, mc=-.1, tg=1, ew=36, col=(255, 150, 90)),
    "surprised": G(ew=42, eh=58, mo=.9, mc=0, mw=7, col=(255, 255, 255)),
    "scared": G(ew=38, eh=56, mc=-.4, mo=.3, mw=9, col=(200, 225, 255)),
    "angry": G(tilt=.85, lid=.2, mc=-.55, ew=36, col=(255, 80, 80)),
    "sad": G(tilt=-.9, lid=.15, mc=-.7, col=(120, 170, 255)),
    "cry": G(tilt=-.9, lid=.1, mc=-.8, mo=.4, col=(110, 160, 255)),
    "dizzy": G(mc=-.1, mo=.3, ew=44, eh=44, col=(200, 160, 255)),
    "curious": G(ea=-.25, mc=.1, eh=48, col=(255, 210, 110)),
    "suspicious": G(lid=.5, mc=-.05, tilt=.15, col=(255, 200, 120)),
    "focus": G(eh=34, lid=.25, tilt=.35, mc=.05, mw=8, col=(110, 200, 255)),
    "think": G(mc=0, mw=6, md=1, col=(150, 190, 255)),
    "music": G(mc=.7, col=(125, 255, 160)),
    "watch": G(ew=44, eh=44, mc=.1, col=(190, 215, 255)),
    "game": G(ew=40, eh=40, mc=.4, col=(255, 130, 215)),
    "mute": G(eh=8, rd=1, mc=0, mw=8, look=.2, col=(150, 160, 170)),
    "beg": G(ew=46, eh=58, mc=.2, mw=8, col=(160, 235, 255)),
    "calc": G(mc=.1, mw=8, col=(110, 255, 150)),
    "shy": G(ew=30, eh=38, sm=.25, mc=.3, bl=1, look=1.4, col=(255, 170, 200)),
    "sneaky": G(lid=.45, tilt=.3, mc=.6, bl=.2, col=(255, 200, 120)),
}
FACE_KIND = {"love": "heart", "dizzy": "spiral", "music": "bars", "watch": "play", "game": "pixel", "calc": "digits"}
FACE_SND = {"happy": "happy", "joy": "joy", "excited": "joy", "love": "love", "kiss": "love", "sad": "sad",
            "cry": "sad", "surprised": "surprise", "scared": "scared", "angry": "angry", "yawn": "yawn",
            "laugh": "giggle", "curious": "curious", "dizzy": "dizzy", "hot": "sigh", "bored": "sigh",
            "cold": "cold", "wink": "wink", "proud": "yay", "think": "think", "drink": "happy"}


def glow_path(p, path, col, a=1.0, fill=True):
    p.setBrush(Qt.BrushStyle.NoBrush)
    for w, al in ((16, 26), (9, 55), (4, 100)):
        pen = QPen(rgba(col, al * a), w)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(path)
    if fill:
        br = path.boundingRect()
        g = QLinearGradient(0, br.top(), 0, br.bottom())
        g.setColorAt(0, rgba([c + (255 - c) * .55 for c in col], 255 * a))
        g.setColorAt(1, rgba(col, 255 * a))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawPath(path)


def glow_stroke(p, path, col, a=1.0, w=6):
    p.setBrush(Qt.BrushStyle.NoBrush)
    for ww, al in ((w + 12, 26), (w + 6, 60), (w, 255)):
        pen = QPen(rgba(col, al * a), ww)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(path)


def draw_body(p, pet, f, col):
    # brillo de abajo (flota)
    mv = min(1.0, math.hypot(pet.vx, pet.vy) / 400)
    ga = 36 + 28 * math.sin(pet.t * 2.4) + 70 * mv
    g = QRadialGradient(0, 92, 85)
    g.setColorAt(0, rgba(col, ga))
    g.setColorAt(1, rgba(col, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(g)
    p.drawEllipse(QPointF(0, 92), 80, 16)
    # luces laterales
    p.setBrush(rgba(col, 150 + 60 * math.sin(pet.t * 3)))
    for s in (-1, 1):
        p.drawRoundedRect(QRectF(s * (BODY_W / 2) - (3 if s < 0 else 5), -16, 8, 32), 4, 4)
    # carcasa
    body = QPainterPath()
    body.addRoundedRect(QRectF(-BODY_W / 2, -BODY_H / 2, BODY_W, BODY_H), 40, 40)
    gr = QLinearGradient(0, -BODY_H / 2, 0, BODY_H / 2)
    gr.setColorAt(0, QColor("#2c313d"))
    gr.setColorAt(.5, QColor("#171a22"))
    gr.setColorAt(1, QColor("#0d0f14"))
    p.setBrush(gr)
    p.setPen(QPen(rgba(col, 110), 2))
    p.drawPath(body)
    # pantalla
    scr = QPainterPath()
    scr.addRoundedRect(QRectF(-SCR_W / 2, -SCR_H / 2, SCR_W, SCR_H), 32, 32)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#040507"))
    p.drawPath(scr)
    return scr


def draw_screen_content(p, pet, f, col, kind):
    draw_eyes(p, pet, f, col, kind)
    draw_mouth(p, pet, f, col)
    # mejillas
    if f["bl"] > .05:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 110, 150, int(clamp(f["bl"], 0, 1) * 150)))
        for s in (-1, 1):
            p.drawRoundedRect(QRectF(s * 58 - 10, 18, 20, 8), 4, 4)
    # lágrimas
    if pet.face_name in ("cry", "sad"):
        amt = 1.0 if pet.face_name == "cry" else .4
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(130, 190, 255, int(220 * amt)))
        for s in (-1, 1):
            yy = f["ey"] + 24 + ((pet.t * 45 + (10 if s > 0 else 0)) % 34)
            p.drawEllipse(QPointF(s * (f["sp"] - 8), yy), 3.2, 5)
    # reflejo
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 10))
    p.drawPolygon(QPolygonF([QPointF(-80, -54), QPointF(-10, -54), QPointF(-60, 54), QPointF(-80, 54)]))


def draw_eyes(p, pet, f, col, kind):
    lx, ly = pet.look
    t = pet.t
    for s in (-1, 1):
        ex = s * f["sp"] + lx * 9 * f["look"]
        ey = f["ey"] + ly * 6 * f["look"]
        p.save()
        p.translate(ex, ey)
        if kind == "heart":
            sz = 15 * (1 + .1 * math.sin(t * 8))
            glow_path(p, heart_path(0, 0, sz), col)
        elif kind == "spiral":
            path = QPainterPath()
            for i in range(40):
                a = i * .55 + t * 9 * s
                r = 1 + i * .5
                pt = QPointF(r * math.cos(a), r * math.sin(a))
                path.moveTo(pt) if i == 0 else path.lineTo(pt)
            glow_stroke(p, path, col, 1, 3)
        elif kind == "bars":
            p.setPen(Qt.PenStyle.NoPen)
            for i in range(3):
                bh = 10 + 34 * abs(math.sin(t * 7 + i * 1.9 + s * 1.2))
                c = [col[0] + (255 - col[0]) * i / 2 * .6, col[1] * (1 - i * .25), col[2] + i * 40]
                bp = QPainterPath()
                bp.addRoundedRect(QRectF((i - 1) * 13 - 4, 20 - bh, 8, bh), 4, 4)
                glow_path(p, bp, [clamp(v, 0, 255) for v in c])
        elif kind == "digits":
            from PyQt6.QtGui import QFont
            font = QFont("Consolas", 26, QFont.Weight.Bold)
            seed = int(t * 7) * 3 + (5 if s > 0 else 0)
            ch = "0123456789+=%"[(seed * 7 + 3) % 13]
            path = QPainterPath()
            path.addText(-9, 10, font, ch)
            glow_path(p, path, col)
        elif kind == "pixel":
            if s < 0:
                bp = QPainterPath()
                bp.addRoundedRect(QRectF(-16, -6, 32, 12), 4, 4)
                bp.addRoundedRect(QRectF(-6, -16, 12, 32), 4, 4)
                glow_path(p, bp.simplified(), col)
            else:
                for k, (bx, by) in enumerate(((-9, 9), (9, -9))):
                    on = int(t * 5) % 2 == k
                    bp = QPainterPath()
                    bp.addEllipse(QPointF(bx, by), 9, 9)
                    glow_path(p, bp, col, 1.0 if on else .35)
        else:
            _normal_eye(p, pet, f, col, s, kind)
        p.restore()


def _normal_eye(p, pet, f, col, s, kind):
    sme = max(f["sm"], f["wk"] if s == 1 else 0.0)
    w = f["ew"]
    h = max(4.0, f["eh"] * (1 + f["ea"] * s) * (1 - pet.blink))
    if sme < .97:
        r = min(w, h) / 2 * f["rd"]
        path = QPainterPath()
        path.addRoundedRect(QRectF(-w / 2, -h / 2, w, h), r, r)
        lid_in = f["lid"] + f["tilt"] * .45
        lid_out = f["lid"] - f["tilt"] * .35
        if lid_in > .01 or lid_out > .01:
            inner = -s
            yA = -h / 2 + h * clamp(lid_in, 0, 1)
            yB = -h / 2 + h * clamp(lid_out, 0, 1)
            cut = QPainterPath()
            cut.addPolygon(QPolygonF([QPointF(inner * (w / 2 + 6), -h), QPointF(inner * (w / 2 + 6), yA),
                                      QPointF(-inner * (w / 2 + 6), yB), QPointF(-inner * (w / 2 + 6), -h)]))
            cut.closeSubpath()
            path = path.subtracted(cut)
        if f["blid"] > .02:
            cheek = QPainterPath()
            cheek.addEllipse(QPointF(0, h / 2 + h * .12), w * .75, h * 1.1 * f["blid"])
            path = path.subtracted(cheek)
        glow_path(p, path, col, 1 - sme)
        p.save()
        p.setClipPath(path, Qt.ClipOperation.IntersectClip)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, int(110 * (1 - sme))))
        p.drawRoundedRect(QRectF(-w / 2 + 5, -h / 2 + 4, w * .36, max(3, h * .16)), 3, 3)
        if kind == "play":
            p.setBrush(QColor(4, 5, 7))
            p.drawPolygon(QPolygonF([QPointF(-6, -9), QPointF(-6, 9), QPointF(9, 0)]))
        p.restore()
    if sme > .03:
        arc = QPainterPath(QPointF(-w / 2 * .95, 8))
        arc.quadTo(QPointF(0, 8 - 26 * sme), QPointF(w / 2 * .95, 8))
        glow_stroke(p, arc, col, sme, 6)


def draw_mouth(p, pet, f, col):
    cx, my = 0, f["my"]
    mc, mo = f["mc"], f["mo"]
    mw = f["mw"] - 3 * mo + 4 * max(mc, 0)
    yc = my - mc * 3
    ctrl = my + mc * 11
    if f["md"] > .5:
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            yy = my + 2 - 6 * max(0, math.sin(pet.t * 7 - i * 1.1))
            path = QPainterPath()
            path.addEllipse(QPointF((i - 1) * 11, yy), 3, 3)
            glow_path(p, path, col, 1)
        return
    if f["wv"] > .5:
        path = QPainterPath(QPointF(-mw, my))
        for i in range(1, 7):
            path.lineTo(QPointF(-mw + 2 * mw * i / 6, my + (3 if i % 2 else -3)))
        glow_stroke(p, path, col, 1, 3)
        return
    if mo > .06:
        low = QPainterPath(QPointF(-mw, yc))
        low.quadTo(QPointF(0, ctrl), QPointF(mw, yc))
        low.quadTo(QPointF(0, ctrl + mo * 30), QPointF(-mw, yc))
        low.closeSubpath()
        glow_path(p, low, col, .9)
        if f["tg"] > .5:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 130, 150))
            p.drawEllipse(QPointF(4, yc + mo * 17 + 2), 6, 7)
        return
    path = QPainterPath(QPointF(-mw, yc))
    path.quadTo(QPointF(0, ctrl), QPointF(mw, yc))
    glow_stroke(p, path, col, 1, 3.2)
