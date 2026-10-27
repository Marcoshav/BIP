# -*- coding: utf-8 -*-
"""Reproductor en la pantalla de Bip: portada, título, progreso y botones anterior / play / siguiente."""
import hashlib
import math
import time

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (QPainter, QColor, QPen, QPixmap, QFont, QFontMetricsF, QCursor, QPolygonF,
                         QPainterPath, QLinearGradient)
from PyQt6.QtWidgets import QApplication

import bip_cara as C
import bip_musica as M
from bip_fx import clamp, rgba
from bip_medios import MediaWatcher
from bip_ui import W, CY_, INK

CARD_W, CARD_H = 268, 88
TEXT_X, TEXT_W = 88, 168


def generated_cover(key, size=136):
    """Portada de respaldo: degradé según el título, con una notita."""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:6], 16)
    c1 = QColor.fromHsv(h % 360, 170, 230)
    c2 = QColor.fromHsv((h // 360 + 70) % 360, 200, 120)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, c1)
    g.setColorAt(1, c2)
    p.fillRect(0, 0, size, size, g)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 215))
    s = size / 136.0
    p.drawEllipse(QPointF(52 * s, 94 * s), 17 * s, 13 * s)
    p.drawEllipse(QPointF(92 * s, 86 * s), 17 * s, 13 * s)
    p.setPen(QPen(QColor(255, 255, 255, 215), 7 * s))
    p.drawLine(QPointF(66 * s, 92 * s), QPointF(66 * s, 36 * s))
    p.drawLine(QPointF(106 * s, 84 * s), QPointF(106 * s, 28 * s))
    p.drawLine(QPointF(66 * s, 36 * s), QPointF(106 * s, 28 * s))
    p.end()
    return pm


class PetMedia:
    def init_media(self, offline=False):
        self.media = MediaWatcher()
        if not offline:
            self.media.start()
        self.card_alpha = 0.0
        self.card_pin = bool(self.cfg.get("card_pin", False))
        self.card_auto_until = 0.0
        self.card_keep_until = 0.0
        self.card_btn = None
        self.card_above = False
        self.cover_pm = None
        self.cover_key = None
        self.media_info = None
        self.ytm_window = False

    # ----------------------------------------------------------------- datos
    def media_view(self):
        """Lo que se muestra: datos de Windows si hay; si no, el título de la ventana de música."""
        st = self.media.state if self.media.available else None
        if st:
            prog, pos = None, 0.0
            if st["dur"] > 1:
                pos = clamp(st["pos"] + ((time.monotonic() - st["stamp"]) if st["playing"] else 0.0), 0, st["dur"])
                prog = clamp(pos / st["dur"], 0, 1)
            return dict(title=st["title"], artist=st["artist"], playing=st["playing"], prog=prog, key=st["key"],
                        thumb=st["thumb"], app=st["app"], full=True, pos=pos, dur=st["dur"],
                        can_seek=st.get("can_seek", True))
        if self.song:
            return dict(title=self.song, artist="", playing=True, prog=None, key=self.song, thumb=None, app="",
                        full=False, pos=0.0, dur=0.0, can_seek=False)
        return None

    def music_ish(self, view):
        a = (view.get("app") or "").lower()
        return bool(self.ytm_window or self.app in ("ytmusic", "spotify") or "spotify" in a)

    def update_media(self, dt, now):
        view = self.media_view()
        self.media_info = view
        if view and view["key"] != self.cover_key:
            self.cover_key = view["key"]
            pm = QPixmap()
            if view["thumb"] and pm.loadFromData(view["thumb"]) and not pm.isNull():
                self.cover_pm = pm.scaled(136, 136, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                          Qt.TransformationMode.SmoothTransformation)
            else:
                self.cover_pm = generated_cover(view["key"])
            if self.music_ish(view) and self.mode != "dock" and self.activity != "meeting":
                self.card_auto_until = now + 6.5
                self.fx.add("note", self.px + 90, self.py - 30, 10, -55, 1.8, 9, col=(125, 255, 160))
                self.jump(.5)
        if not view:
            self.cover_pm, self.cover_key = None, None
        # aprende tus gustos: sólo cuando suena música de verdad (Spotify / YouTube Music)
        g = getattr(self, "gustos", None)
        if g is not None and view and self.music_ish(view):
            g.observe(view["title"], view["artist"] if view["full"] else "", view["playing"], min(dt, .5))
        # canción actual para el resto del cerebro (DJ, caras, "¿pausaste?")
        if view and view["full"]:
            song = view["title"] if (view["playing"] and self.music_ish(view)) else None
            if song != self.song:
                prev, self.song = self.song, song
                if song:
                    self.dj_pending = None
                elif prev and now - self.paused_said > 120 and view and self.music_ish(view):
                    self.paused_said = now
                    self.mood("curious", 2.5, snd=False)
        # visibilidad de la tarjeta
        lp = self.mapFromGlobal(QCursor.pos())
        r = self.card_rect()
        over_card = self.card_alpha > .3 and r.contains(QPointF(lp.x(), lp.y()))
        want = bool(view) and not self.sleeping and not self.dragging and (
            self.card_pin or now < self.card_auto_until or now < self.card_keep_until or over_card
            or self.scrub is not None
            or (self.hovering and self.hover_t > .35))
        if want and (over_card or self.hovering):
            self.card_keep_until = now + .9
        self.card_alpha += ((1.0 if want else 0.0) - self.card_alpha) * min(1.0, dt * 10)
        self.card_btn = self.card_button_at(lp.x(), lp.y()) if over_card else None

    # ------------------------------------------------------------- geometría
    def card_rect(self):
        sc = self.sc
        half = C.BODY_H / 2 * sc
        near_bottom = self.py > self.cur_geo().bottom() - 210
        self.card_above = near_bottom
        top = (CY_ - half - 18 - CARD_H) if near_bottom else (CY_ + half + 26)
        scr = QApplication.screenAt(self.pos_point()) or QApplication.primaryScreen()
        sg = scr.geometry()
        vis_l = max(0.0, sg.left() + 6 - self.x())
        vis_r = min(float(W), sg.right() - 6 - self.x())
        x = clamp((W - CARD_W) / 2, vis_l, max(vis_l, vis_r - CARD_W))
        x = clamp(x, 0, W - CARD_W)
        return QRectF(x, top, CARD_W, CARD_H)

    def pos_point(self):
        from PyQt6.QtCore import QPoint
        return QPoint(int(self.px), int(self.py))

    def button_centers(self, r):
        cy = r.top() + 71
        return {"prev": QPointF(r.left() + TEXT_X + 34, cy), "play": QPointF(r.left() + TEXT_X + 84, cy),
                "next": QPointF(r.left() + TEXT_X + 134, cy)}

    def card_button_at(self, x, y):
        r = self.card_rect()
        if not r.contains(QPointF(x, y)):
            return None
        for name, c in self.button_centers(r).items():
            if math.hypot(x - c.x(), y - c.y()) <= (19 if name == "play" else 16):
                return name
        if (r.left() + TEXT_X - 6 <= x <= r.left() + TEXT_X + TEXT_W + 6) and (r.top() + 41 <= y <= r.top() + 58):
            return "bar"
        if QRectF(r.left() + 10, r.top() + 10, 68, 68).contains(QPointF(x, y)):
            return "cover"
        return "card"

    def card_press(self, x, y):
        """True si el clic cayó en la tarjeta (y lo maneja)."""
        if self.card_alpha < .5 or not self.media_info:
            return False
        btn = self.card_button_at(x, y)
        if btn is None:
            return False
        if btn in ("prev", "play", "next"):
            self.media_cmd(btn)
        elif btn == "bar":
            v = self.media_info
            if v["prog"] is None or v["dur"] <= 1:
                pass
            elif not v.get("can_seek", True):
                self.say("Este reproductor no me deja adelantar ni volver.", 3, 2)
            else:
                self.scrub = self.bar_frac(x)
                self.sfx("click", .6, 2)
        elif btn == "cover":
            self.card_pin = not self.card_pin
            self.cfg["card_pin"] = self.card_pin
            self.sfx("click", .8, 2)
        self.card_keep_until = time.monotonic() + 2.5
        return True

    def bar_frac(self, x):
        r = self.card_rect()
        return clamp((x - (r.left() + TEXT_X)) / TEXT_W, 0.0, 1.0)

    def card_scrub_to(self, x):
        self.scrub = self.bar_frac(x)
        self.interact_until = self.card_keep_until = time.monotonic() + 2.5

    def card_scrub_end(self):
        """Soltaste la barra: salta a ese punto de la canción."""
        frac, self.scrub = self.scrub, None
        v = self.media_info
        if frac is None or not v or v["dur"] <= 1:
            return
        secs = frac * v["dur"]
        if self.media.seek(secs):
            st = self.media.state
            if st is not None:
                st["pos"], st["stamp"] = secs, time.monotonic()
            self.sfx("boop", .7, 2)
        self.card_keep_until = time.monotonic() + 2.5

    @staticmethod
    def fmt_time(s):
        s = int(max(0, s))
        return "%d:%02d" % (s // 60, s % 60)

    def media_cmd(self, name):
        now = time.monotonic()
        self.sfx("click", .8, 2)
        cmd = {"play": "playpause", "next": "next", "prev": "prev"}[name]
        ok = self.media.command(cmd)
        if not ok:
            M.media_key(cmd)
        st = self.media.state
        if name == "play" and st is not None:
            st["playing"] = not st["playing"]
            st["stamp"] = now
        if name in ("next", "prev"):
            self.card_auto_until = now + 6.5
            self.mood("happy", 1.2, snd=False)
            self.jump(.5)

    # ---------------------------------------------------------------- dibujo
    def draw_card(self, p, now):
        v = self.media_info
        if not v or self.card_alpha < .02:
            return
        r = self.card_rect()
        col = tuple(self.fe["col"])
        a = self.card_alpha
        p.save()
        p.setOpacity(a)
        slide = (1 - a) * (12 if not self.card_above else -12)
        p.translate(0, slide)
        p.setPen(QPen(rgba(col, 170), 1.6))
        p.setBrush(INK)
        p.drawRoundedRect(r, 18, 18)
        # portada
        cr = QRectF(r.left() + 10, r.top() + 10, 68, 68)
        clip = QPainterPath()
        clip.addRoundedRect(cr, 12, 12)
        p.save()
        p.setClipPath(clip)
        if self.cover_pm is not None:
            p.drawPixmap(cr, self.cover_pm, QRectF(self.cover_pm.rect()))
        else:
            p.fillRect(cr, QColor(40, 46, 60))
        if v["playing"]:     # ecualizador chiquito sobre la portada
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 120))
            p.drawRect(QRectF(cr.left(), cr.bottom() - 18, 68, 18))
            p.setBrush(rgba(col))
            for i in range(4):
                h = 4 + 11 * abs(math.sin(self.t * 7 + i * 1.7))
                p.drawRoundedRect(QRectF(cr.left() + 8 + i * 8, cr.bottom() - 3 - h, 5, h), 2, 2)
        p.restore()
        if self.card_pin:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(rgba(col))
            p.drawEllipse(QPointF(cr.right() - 6, cr.top() + 6), 3.5, 3.5)
        # texto
        f1 = QFont("Segoe UI", 10, QFont.Weight.Bold)
        f2 = QFont("Segoe UI", 9)
        p.setPen(QColor(235, 248, 255))
        p.setFont(f1)
        p.drawText(QPointF(r.left() + TEXT_X, r.top() + 24),
                   QFontMetricsF(f1).elidedText(v["title"], Qt.TextElideMode.ElideRight, TEXT_W))
        p.setPen(QColor(150, 200, 220))
        p.setFont(f2)
        sub = v["artist"] or ("Reproduciendo" if v["playing"] else "En pausa")
        p.drawText(QPointF(r.left() + TEXT_X, r.top() + 42), QFontMetricsF(f2).elidedText(sub, Qt.TextElideMode.ElideRight, TEXT_W))
        # progreso
        by = r.top() + 50
        hot_bar = self.card_btn == "bar" or self.scrub is not None
        bh = 6 if hot_bar else 4
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 55 if hot_bar else 40))
        p.drawRoundedRect(QRectF(r.left() + TEXT_X, by + 2 - bh / 2, TEXT_W, bh), bh / 2, bh / 2)
        prog = self.scrub if self.scrub is not None else v["prog"]
        if prog is not None:
            p.setBrush(rgba(col))
            p.drawRoundedRect(QRectF(r.left() + TEXT_X, by + 2 - bh / 2, max(bh, TEXT_W * prog), bh), bh / 2, bh / 2)
            if hot_bar and v.get("dur", 0) > 1:
                kx = r.left() + TEXT_X + TEXT_W * prog
                p.setBrush(QColor(245, 252, 255))
                p.drawEllipse(QPointF(kx, by + 2), 6, 6)
                # globito con el tiempo al que va a saltar
                secs = prog * v["dur"]
                txt = "%s / %s" % (self.fmt_time(secs), self.fmt_time(v["dur"]))
                f3 = QFont("Segoe UI", 8, QFont.Weight.Bold)
                p.setFont(f3)
                tw = QFontMetricsF(f3).horizontalAdvance(txt) + 14
                bx = clamp(kx - tw / 2, r.left() + 6, r.right() - tw - 6)
                p.setPen(QPen(rgba(col, 190), 1.2))
                p.setBrush(INK)
                ty_ = r.bottom() + 4 if self.card_above else r.top() - 24
                p.drawRoundedRect(QRectF(bx, ty_, tw, 20), 9, 9)
                p.setPen(QColor(235, 248, 255))
                p.drawText(QRectF(bx, ty_, tw, 20), Qt.AlignmentFlag.AlignCenter, txt)
                p.setPen(Qt.PenStyle.NoPen)
        # botones
        cs = self.button_centers(r)
        for name, c in cs.items():
            hot = self.card_btn == name
            rad = 16 if name == "play" else 12
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(rgba(col, 90 if hot else (50 if name == "play" else 0)))
            p.drawEllipse(c, rad, rad)
            p.setBrush(rgba(col) if hot or name == "play" else QColor(220, 240, 250))
            if name == "play":
                if v["playing"]:
                    p.drawRoundedRect(QRectF(c.x() - 6, c.y() - 7, 4.5, 14), 1.5, 1.5)
                    p.drawRoundedRect(QRectF(c.x() + 1.5, c.y() - 7, 4.5, 14), 1.5, 1.5)
                else:
                    p.drawPolygon(QPolygonF([QPointF(c.x() - 5, c.y() - 8), QPointF(c.x() - 5, c.y() + 8), QPointF(c.x() + 8, c.y())]))
            else:
                d = 1 if name == "next" else -1
                p.drawPolygon(QPolygonF([QPointF(c.x() - 7 * d, c.y() - 7), QPointF(c.x() - 7 * d, c.y() + 7), QPointF(c.x() + 1 * d, c.y())]))
                p.drawPolygon(QPolygonF([QPointF(c.x() + 0 * d, c.y() - 7), QPointF(c.x() + 0 * d, c.y() + 7), QPointF(c.x() + 8 * d, c.y())]))
        p.restore()
