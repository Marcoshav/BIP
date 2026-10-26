# -*- coding: utf-8 -*-
"""Ventana de Bip: movimiento flotante, mouse, pose, cara y dibujo."""
import math
import random
import time

from PyQt6.QtCore import Qt, QPointF, QRectF, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QCursor, QFontMetricsF, QPainterPath
from PyQt6.QtWidgets import QWidget, QApplication

import bip_cara as C
import bip_props as P
from bip_fx import clamp, rgba
from bip_sistema import log

W, H = 380, 420
CY_ = 180          # centro del cuerpo dentro de la ventana
INK = QColor(10, 14, 22, 238)


class PetUI(QWidget):
    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(W, H)
        self.t = 0.0
        self.dt = 0.03
        self.timers = {}
        # movimiento
        g = QApplication.primaryScreen().availableGeometry()
        self.px, self.py = float(g.center().x()), float(g.center().y())
        self.vx = self.vy = 0.0
        self.tx, self.ty = self.px, self.py
        self.max_speed = 260.0
        self.kin = False
        self.offscreen_ok = False
        self.reading = False
        self.cover_pm = None
        self.card_alpha = 0.0
        self.card_above = False
        self.sc, self.sc_t = 0.1, 1.0
        # pose
        self.tilt = self.shake = self.spin = 0.0
        self.hy = self.hv = 0.0
        self.sqx = self.sqy = 1.0
        self.spin_until = self.spin_t0 = 0.0
        self.dancing = False
        # cara
        self.face_name = "neutral"
        self.f = dict(C.FACES["neutral"])
        self.fe = dict(self.f)
        self.kind = "normal"
        self.blink = 0.0
        self.blink_t = 99.0
        self.next_blink = time.monotonic() + 2
        self.look = [0.0, 0.0]
        self.look_override = None
        self.look_until = 0.0
        # globo y props
        self.bubble = None
        self.prop = None
        self.prop_since = 0.0
        self.prop_override = None
        self.prop_until = 0.0
        self.acc = dict(headphones=False, scarf=False, sunglasses=False, umbrella=False)
        # entrada
        self.dragging = False
        self.press_pos = None
        self.drag_off = (0.0, 0.0)
        self.hovering = False
        self.hover_t = 0.0
        self.pet_acc = 0.0
        self.stroking = False
        self.prev_cursor = None
        self.cursor_speed = 0.0
        self.interact_until = 0.0     # mientras vale: estás usando a Bip o su tarjeta (no se mueve ni se esconde)
        self.hold = False
        self.scrub = None             # fracción (0..1) mientras arrastrás la barra de progreso

    # ------------------------------------------------------------- utilidades
    def every(self, key, interval, jitter=0.3):
        if self.t >= self.timers.get(key, 0):
            self.timers[key] = self.t + interval * (1 + random.uniform(-jitter, jitter))
            return True
        return False

    def hit(self, x, y, margin=22):
        """Zona donde se lo puede agarrar: el cuerpo con un margen generoso (y siguiendo sus saltitos)."""
        s = max(self.sc, .6)
        cy = CY_ + self.hy * s
        return (abs(x - W / 2) <= C.BODY_W / 2 * s + margin and
                abs(y - cy) <= C.BODY_H / 2 * s + margin + 4)

    def hold_ok(self):
        """Los juegos con el mouse y las persecuciones no se frenan aunque el cursor esté cerca."""
        t = self.task
        name = getattr(getattr(t, "gi_code", None), "co_name", "") if t is not None else ""
        return name not in ("b_cursor_play", "b_tag_game", "b_hide_seek", "b_chase_cursor", "b_ball",
                            "b_race", "b_dj", "b_dance")

    def jump(self, power=1.0):
        if self.hy == 0 and self.hv == 0:
            self.hv = -380 * power

    # ----------------------------------------------------------------- mouse
    def mousePressEvent(self, e):
        self.interact_until = time.monotonic() + 4
        if e.button() == Qt.MouseButton.LeftButton and self.card_press(e.position().x(), e.position().y()):
            self.press_pos = None
            e.accept()
            return
        if e.button() == Qt.MouseButton.LeftButton and self.hit(e.position().x(), e.position().y()):
            gp = e.globalPosition()
            self.press_pos = gp
            self.drag_off = (gp.x() - self.px, gp.y() - self.py)
            e.accept()
        else:
            self.press_pos = None

    def mouseMoveEvent(self, e):
        if self.scrub is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            self.card_scrub_to(e.position().x())
            return
        if self.press_pos is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        self.interact_until = time.monotonic() + 4
        gp = e.globalPosition()
        if not self.dragging and abs(gp.x() - self.press_pos.x()) + abs(gp.y() - self.press_pos.y()) > 6:
            self.dragging = True
            self.on_drag_start()
        if self.dragging:
            # sigue al mouse directo (antes se trababa si el mouse se movía más de 40 px de golpe)
            nx, ny = gp.x() - self.drag_off[0], gp.y() - self.drag_off[1]
            self.vx, self.vy = (nx - self.px) * 20, (ny - self.py) * 20
            self.px, self.py = nx, ny
            self.tx, self.ty = nx, ny

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self.scrub is not None:
            self.card_scrub_end()
            self.press_pos = None
            return
        if self.dragging:
            self.dragging = False
            self.vx = self.vy = 0.0
            self.on_drag_end()
        elif self.press_pos is not None:
            self.on_click()
        self.press_pos = None

    def mouseDoubleClickEvent(self, e):
        # el 2º clic rápido llega como "doble clic": si cae en la tarjeta es un botón más, no un giro
        if e.button() == Qt.MouseButton.LeftButton:
            if self.card_press(e.position().x(), e.position().y()):
                self.press_pos = None
                e.accept()
                return
            if self.hit(e.position().x(), e.position().y()):
                self.on_double()

    def contextMenuEvent(self, e):
        self.build_menu().exec(e.globalPos())

    # ---------------------------------------------------------------- update
    def tick(self, dt=None):
        now = time.monotonic()
        if dt is None:
            dt = min(0.06, now - getattr(self, "last_t", now))
        self.last_t = now
        self.dt = dt
        self.t += dt
        try:
            self.run_task(dt)
            self.update_motion(dt)
            self.update_cursor(dt, now)
            self.update_pose(dt, now)
            self.update_look(dt, now)
            self.update_face(dt, now)
            self.brain_tick(dt, now)
        except Exception:
            if getattr(self, "debug", False):
                raise
            log("tick: " + __import__("traceback").format_exc())
        x, y = int(round(self.px - W / 2)), int(round(self.py - CY_))
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)
        self.update()

    def clamp_pos(self, x, y):
        """Mantiene el cuerpo entero dentro de alguna pantalla (sin cortarse con los bordes)."""
        hw = C.BODY_W / 2 * self.sc + 6
        hh = C.BODY_H / 2 * self.sc + 6
        best = None
        for s in QApplication.screens():
            g = s.availableGeometry()
            cx = clamp(x, g.left() + hw, max(g.left() + hw, g.right() - hw))
            cy = clamp(y, g.top() + hh, max(g.top() + hh, g.bottom() - hh - 14))
            d = (cx - x) ** 2 + (cy - y) ** 2
            if best is None or d < best[0]:
                best = (d, cx, cy)
        return (best[1], best[2]) if best else (x, y)

    def update_motion(self, dt):
        self.sc += (self.sc_t - self.sc) * min(1.0, dt * 4)
        if self.dragging or self.kin:
            return
        if self.hold:                       # frena suave mientras apuntás con el mouse
            a = 1 - math.exp(-dt * 14)
            self.vx -= self.vx * a
            self.vy -= self.vy * a
            self.px += self.vx * dt
            self.py += self.vy * dt
            return
        tx, ty = (self.tx, self.ty) if self.offscreen_ok else self.clamp_pos(self.tx, self.ty)
        dx, dy = tx - self.px, ty - self.py
        d = math.hypot(dx, dy)
        des = min(self.max_speed, d * 5.0)
        dvx, dvy = (dx / d * des, dy / d * des) if d > 0.5 else (0.0, 0.0)
        a = 1 - math.exp(-dt * 6)
        self.vx += (dvx - self.vx) * a
        self.vy += (dvy - self.vy) * a
        self.px += self.vx * dt
        self.py += self.vy * dt
        if not self.offscreen_ok:
            nx, ny = self.clamp_pos(self.px, self.py)
            if .5 < abs(nx - self.px) < 40:
                if abs(self.vx) > 160:
                    self.on_bump(abs(self.vx))
                self.vx = -self.vx * 0.5
            if .5 < abs(ny - self.py) < 40:
                if abs(self.vy) > 160:
                    self.on_bump(abs(self.vy))
                self.vy = -self.vy * 0.5
            if abs(nx - self.px) < 40:
                self.px = nx
            if abs(ny - self.py) < 40:
                self.py = ny

    def update_cursor(self, dt, now):
        gp = QCursor.pos()
        lp = self.mapFromGlobal(gp)
        over = self.isVisible() and not self.dragging and self.hit(lp.x(), lp.y())
        moved = 0.0
        if self.prev_cursor is not None:
            moved = math.hypot(gp.x() - self.prev_cursor.x(), gp.y() - self.prev_cursor.y())
        self.cursor_speed += (moved / max(dt, 1e-3) - self.cursor_speed) * min(1.0, dt * 6)
        self.prev_cursor = gp
        self.pet_acc = max(0.0, self.pet_acc - 90 * dt) + (moved if over else 0.0)
        self.hovering = over
        self.hover_t = self.hover_t + dt if over else 0.0
        self.stroking = over and self.pet_acc > 110
        # ¿vas a usarlo? (cursor cerca del cuerpo o sobre la tarjeta): se queda quieto y no se esconde
        on_card = self.card_alpha > .3 and self.card_rect().adjusted(-8, -8, 8, 8).contains(QPointF(lp.x(), lp.y()))
        near = self.isVisible() and (self.hit(lp.x(), lp.y(), 46) or on_card)
        if near or self.dragging or self.scrub is not None:
            self.interact_until = max(self.interact_until, now + 1.5)
        self.hold = bool((near or self.scrub is not None) and not self.dragging and not self.kin
                         and self.mode in ("free", "perch") and self.hold_ok())
        if self.stroking:
            self.stroke_tick(dt, now)
        elif (self.cursor_speed > 4200 and not self.hold and not self.dragging and now > self.interact_until
              and 110 < math.hypot(gp.x() - self.px, gp.y() - self.py) < 240):
            self.startle(gp)

    def update_pose(self, dt, now):
        fn = self.face_name
        tt = clamp(self.vx * 0.03, -16, 16)
        if self.dancing or (self.activity == "music" and not self.sleeping):
            tt += math.sin(self.t * 5) * 10
        if self.stroking:
            tt += math.sin(self.t * 3) * 5
        if fn == "dizzy":
            tt += math.sin(self.t * 6) * 8
        self.tilt += (tt - self.tilt) * min(1.0, dt * 8)
        self.shake = math.sin(self.t * 55) * 1.8 if fn in ("cold", "scared") else (math.sin(self.t * 30) * 1.2 if fn == "laugh" else 0.0)
        if self.hy < 0 or self.hv < 0:
            self.hv += 1600 * dt
            self.hy += self.hv * dt
            if self.hy >= 0:
                self.hy = self.hv = 0.0
        if now < self.spin_until:
            p = (now - self.spin_t0) / max(.01, self.spin_until - self.spin_t0)
            self.spin = 360 * (1 - (1 - p) ** 2)
        else:
            self.spin = 0.0
        sq = clamp(abs(self.vx) / 5000, 0, .1)
        self.sqx = 1 + sq
        self.sqy = 1 - sq + clamp(-self.hv / 6000, -.08, .08)

    def update_look(self, dt, now):
        tx = ty = 0.0
        if self.look_override and now >= self.look_until:
            self.look_override = None
        if self.sleeping:
            pass
        elif self.look_override:
            tx, ty = self.look_override
        elif self.reading and self.hover_t <= 0:
            tx, ty = math.sin(self.t * 1.1) * .9, .35 + .1 * math.sin(self.t * .37)
        else:
            gp = QCursor.pos()
            dx, dy = gp.x() - self.px, gp.y() - self.py
            d = math.hypot(dx, dy)
            if d > 1:
                s = clamp(d / 200.0, 0, 1)
                tx, ty = dx / d * s, dy / d * s
            if math.hypot(self.vx, self.vy) > 120:
                v = math.hypot(self.vx, self.vy)
                tx, ty = clamp(tx * .3 + self.vx / v * .8, -1, 1), clamp(ty * .3 + self.vy / v * .8, -1, 1)
        k = min(1.0, dt * 9)
        self.look[0] += (tx - self.look[0]) * k
        self.look[1] += (ty - self.look[1]) * k

    def update_face(self, dt, now):
        name = self.choose_face(now)
        if name != self.face_name:
            new_kind = C.FACE_KIND.get(name, "normal")
            if new_kind != self.kind:
                self.blink_t = 0.0
            self.face_name = name
            self.kind = new_kind
        tgt = C.FACES[self.face_name]
        k = min(1.0, dt * 10)
        for key, v in tgt.items():
            if key == "col":
                self.f["col"] = tuple(self.f["col"][i] + (v[i] - self.f["col"][i]) * k for i in range(3))
            else:
                self.f[key] += (v - self.f[key]) * k
        if not self.sleeping and now >= self.next_blink and self.blink_t > .2:
            self.blink_t = 0.0
            self.next_blink = now + random.uniform(2.2, 6)
        self.blink_t += dt
        self.blink = math.sin(math.pi * self.blink_t / .16) if self.blink_t < .16 else 0.0
        fe = dict(self.f)
        if self.face_name == "hot":
            fe["mo"] = .45 + .2 * math.sin(self.t * 6)
        if self.bubble and now - self.bubble["t0"] < 1.4 and not self.sleeping and self.face_name not in ("yawn", "laugh"):
            fe["mo"] = max(fe["mo"], .15 + .3 * abs(math.sin(self.t * 14)))
            fe["mw"] = max(fe["mw"], 9)
        self.fe = fe

    # ----------------------------------------------------------------- dibujo
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        try:
            self.draw(p)
        except Exception:
            if getattr(self, "debug", False):
                raise
            log("draw: " + __import__("traceback").format_exc())
        p.end()

    def draw(self, p):
        now = time.monotonic()
        f = self.fe
        col = tuple(f["col"])
        bob = math.sin(self.t * (0.9 if self.sleeping else 1.8)) * (3 if self.sleeping else 5)
        hop = abs(math.sin(self.t * 5)) * 10 if (self.dancing or (self.activity == "music" and not self.sleeping)) else 0.0
        p.save()
        p.translate(W / 2 + self.shake, CY_ + bob + self.hy - hop)
        p.rotate(self.tilt + self.spin)
        p.scale(self.sc * self.sqx, self.sc * self.sqy)
        scr = C.draw_body(p, self, f, col)
        p.save()
        p.setClipPath(scr)
        C.draw_screen_content(p, self, f, col, self.kind)
        p.restore()
        if self.acc["sunglasses"] and not self.sleeping:
            P.sunglasses(p, f)
        if self.acc["headphones"]:
            P.headphones(p, self.t)
        if self.acc["scarf"]:
            P.scarf(p, self.t)
        if self.acc["umbrella"]:
            P.umbrella(p)
        self.draw_prop(p, now)
        self.draw_status(p, col)
        self.draw_mark(p, col)
        p.restore()
        self.draw_card(p, now)
        self.draw_bubble(p, now, bob)

    def draw_prop(self, p, now):
        name = self.prop_override if (self.prop_override and now < self.prop_until) else self.prop
        if not name:
            return
        pop = clamp((now - self.prop_since) * 5, 0, 1)
        p.save()
        p.translate(124, -30 + math.sin(self.t * 2) * 4)
        p.scale(pop, pop)
        p.rotate(math.sin(self.t * 1.5) * 6)
        if name == "music" and self.cover_pm is not None:
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(-18, -18, 36, 36), 8, 8)
            p.setPen(QPen(rgba(tuple(self.fe["col"]), 200), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(-20, -20, 40, 40), 10, 10)
            p.setClipPath(clip)
            p.drawPixmap(QRectF(-18, -18, 36, 36), self.cover_pm, QRectF(self.cover_pm.rect()))
        else:
            P.draw_prop(p, name, self.t)
        p.restore()

    def draw_status(self, p, col):
        p.setPen(Qt.PenStyle.NoPen)
        led = self.led_color()
        a = 160 + 90 * math.sin(self.t * (1.2 if self.sleeping else 3))
        p.setBrush(rgba(led, a))
        p.drawEllipse(QPointF(0, 58), 2.8, 2.8)
        if self.pomo:
            prog = clamp(self.pomo_progress(), 0, 1)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawRoundedRect(QRectF(-50, 56, 100, 4), 2, 2)
            p.setBrush(rgba((255, 150, 90) if self.pomo["phase"] == "work" else (125, 255, 160)))
            p.drawRoundedRect(QRectF(-50, 56, 100 * prog, 4), 2, 2)

    def draw_mark(self, p, col):
        mark = {"curious": "?", "think": "…", "surprised": "!", "scared": "!", "dizzy": "@", "angry": "💢"}.get(self.face_name)
        if not mark or self.sleeping:
            return
        pop = 1 + .15 * math.sin(self.t * 8)
        p.save()
        p.translate(84, -78)
        p.scale(pop, pop)
        p.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        p.setPen(rgba(col))
        p.drawText(QRectF(-20, -20, 40, 40), Qt.AlignmentFlag.AlignCenter, mark)
        p.restore()

    def draw_bubble(self, p, now, bob):
        b = self.bubble
        if b and now > b["until"]:
            self.bubble = b = None
        text = None
        a = 1.0
        if b and self.cfg.get("bubbles", True):
            text = b["text"]
            a = clamp(min((now - b["t0"]) / .18, (b["until"] - now) / .35), 0, 1)
        elif self.hovering and self.hover_t > .7 and not self.dragging:
            text = self.hover_text()
            a = clamp((self.hover_t - .7) / .2, 0, 1)
        if not text:
            return
        if self.card_alpha > .1 and self.card_above == (not self.bubble_below()):
            return                                  # el reproductor ocupa ese lado
        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.Medium)
        flags = Qt.AlignmentFlag.AlignCenter.value | Qt.TextFlag.TextWordWrap.value
        scr = QApplication.screenAt(QPoint(int(self.px), int(self.py))) or QApplication.primaryScreen()
        sg = scr.geometry()
        vis_l = max(0.0, sg.left() + 6 - self.x())
        vis_r = min(float(W), sg.right() - 6 - self.x())
        tw = clamp(vis_r - vis_l - 24, 110, 240)      # si está asomando por un borde, el globo se angosta
        r = QFontMetricsF(font).boundingRect(QRectF(0, 0, tw, 600), flags, text)
        pad = 10
        bw, bh = r.width() + pad * 2, r.height() + pad * 2
        half = C.BODY_H / 2 * self.sc
        below = self.bubble_below()
        if below:
            top = CY_ + bob + half + 24
            tail_y = top
        else:
            top = CY_ + bob - half - 22 - bh
            tail_y = top + bh
        x = clamp(W / 2 - bw / 2, 4, W - bw - 4)
        x = clamp(x, vis_l, max(vis_l, vis_r - bw))   # el globo siempre dentro de la pantalla
        x = clamp(x, 2, W - bw - 2)
        col = tuple(self.fe["col"])
        p.save()
        p.setOpacity(a)
        p.setPen(QPen(rgba(col, 200), 1.8))
        p.setBrush(INK)
        p.drawRoundedRect(QRectF(x, top, bw, bh), 14, 14)
        s = -1 if below else 1
        tcx = clamp(W / 2, x + 16, x + bw - 16)
        tail = QPainterPath(QPointF(tcx - 7, tail_y))
        tail.lineTo(QPointF(tcx, tail_y + s * 9))
        tail.lineTo(QPointF(tcx + 7, tail_y))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(INK)
        p.drawPath(tail)
        p.setPen(QPen(rgba(col, 200), 1.8))
        p.drawLine(QPointF(tcx - 7, tail_y), QPointF(tcx, tail_y + s * 9))
        p.drawLine(QPointF(tcx, tail_y + s * 9), QPointF(tcx + 7, tail_y))
        p.setPen(QColor(220, 245, 255))
        p.setFont(font)
        p.drawText(QRectF(x + pad, top + pad, bw - 2 * pad, bh - 2 * pad), flags, text)
        p.restore()
