# -*- coding: utf-8 -*-
"""Comportamientos autónomos de Bip (generadores): explorar, visitar ventanas, jugar, dibujar..."""
import math
import random
import time
import datetime

from PyQt6.QtCore import QPoint, QRectF
from PyQt6.QtGui import QCursor, QFont, QPainterPath, QTransform
from PyQt6.QtWidgets import QApplication

from bip_sistema import SysInfo

PEN_DY = 64
PALETTE = [(89, 242, 255), (255, 105, 160), (255, 226, 106), (125, 255, 160), (200, 160, 255), (255, 150, 90)]


class Conductas:
    # ------------------------------------------------------------ helpers
    def go(self, x, y, speed=260, timeout=10.0, tol=14):
        if not self.offscreen_ok:
            x, y = self.clamp_pos(x, y)
        self.tx, self.ty, self.max_speed = x, y, speed
        t = 0.0
        while t < timeout and math.hypot(self.px - x, self.py - y) > tol:
            t += self.dt
            yield 0

    def step_to(self, x, y, speed):
        dx, dy = x - self.px, y - self.py
        d = math.hypot(dx, dy)
        st = speed * self.dt
        if d <= st:
            self.px, self.py, self.vx, self.vy = x, y, 0.0, 0.0
            self.tx, self.ty = x, y
            return True
        self.px += dx / d * st
        self.py += dy / d * st
        self.vx, self.vy = dx / d * speed, dy / d * speed
        self.tx, self.ty = self.px, self.py
        return False

    def look_at(self, x, y, secs=1.5):
        dx, dy = x - self.px, y - self.py
        d = max(1.0, math.hypot(dx, dy))
        self.look_override = (dx / d, dy / d)
        self.look_until = time.monotonic() + secs

    def geos(self):
        gs = [s.availableGeometry() for s in QApplication.screens()]
        return gs or [QApplication.primaryScreen().availableGeometry()]

    def cur_geo(self):
        s = QApplication.screenAt(QPoint(int(self.px), int(self.py)))
        return (s or QApplication.primaryScreen()).availableGeometry()

    def rand_point(self, margin=130):
        gs = self.geos()
        g = random.choices(gs, weights=[x.width() * x.height() for x in gs])[0]
        mx, my = min(margin, g.width() / 3), min(margin, g.height() / 3)
        if getattr(self, "user_busy", False):      # si estás usando la PC, explora por los bordes y no por el medio
            band = 130
            if random.random() < .7:
                x = random.choice((g.left() + band * .6, g.right() - band * .6)) + random.uniform(-30, 30)
                return (x, random.uniform(g.top() + my, g.bottom() - my))
            return (random.uniform(g.left() + mx, g.right() - mx), g.top() + band * .6)
        return (random.uniform(g.left() + mx, g.right() - mx), random.uniform(g.top() + my, g.bottom() - my))

    def start(self, gen):
        self.stop()
        self.task, self.task_wait = gen, 0.0

    def stop(self):
        if self.task is not None:
            try:
                self.task.close()
            except Exception:
                pass
        self.task = None
        self.reset_task_state()

    def reset_task_state(self):
        self.offscreen_ok = False
        self.kin = False
        self.max_speed = 260.0
        self.dancing = False
        self.look_override = None
        self.prop_override = None

    # ---------------------------------------------------- comportamientos
    def b_wander(self):
        x, y = self.rand_point()
        self.look_at(x, y, 1.2)
        self.sfx("fly", .6)
        yield from self.go(x, y, random.uniform(180, 320))
        if random.random() < .5:
            self.mood("curious", 2.0)
            yield 1.8

    def b_hello(self):
        self.mood("happy", 1.8)
        self.sfx("wink")
        self.spin_until = time.monotonic() + .9
        self.spin_t0 = time.monotonic()
        yield 1.2

    def b_stretch(self):
        self.mood("yawn", 2.2)
        self.sfx("yawn", .8)
        yield 2.4

    def b_peek_edge(self):
        g = random.choice(self.geos())
        side = random.choice(("left", "right", "top"))
        y = random.uniform(g.top() + 140, g.bottom() - 140)
        x = random.uniform(g.left() + 200, g.right() - 200)
        if side == "left":
            ex, ey, ix = g.left() - 45, y, g.left() + 70
        elif side == "right":
            ex, ey, ix = g.right() + 45, y, g.right() - 70
        else:
            ex, ey, ix = x, g.top() - 30, x
        self.sfx("fly", .6)
        self.offscreen_ok = True
        yield from self.go(ex, ey, 330)
        self.mood("curious", 3)
        self.look_at(g.center().x(), g.center().y(), 2.5)
        yield 2.5
        self.sfx("curious")
        yield from self.go(ix if side != "top" else x, ey if side != "top" else g.top() + 80, 220)
        self.offscreen_ok = False
        self.mood("surprised", 1.0)
        self.sfx("surprise", .7)
        yield 1.2

    def windows_or_none(self):
        try:
            return SysInfo.windows()
        except Exception:
            return []

    def b_visit_window(self):
        wins = self.windows_or_none()
        if not wins:
            yield from self.b_wander()
            return
        w = random.choice(wins)
        gx = random.uniform(w["x"] + 90, w["x"] + w["w"] - 90)
        gy = w["y"] - 60 if w["y"] > 130 else w["y"] + 60
        self.sfx("fly", .6)
        yield from self.go(gx, gy, 300)
        self.look_at(gx, w["y"] + w["h"] / 2, 2)
        self.mood("curious", 2.5)
        self.fx.ring(gx, gy + 40, (255, 210, 110), 70)
        self.sfx("think", .8)
        yield 2.0
        r = random.random()
        if r < .4:
            self.mood("happy", 1.5)
            self.say(random.choice(["Hola, ventana.", "Qué lindo lugar.", "Estuve acá. ¡Presente!"]), 3)
            yield 1.5
        elif r < .7:
            yield from self.b_scan_window(w)

    def b_scan_window(self, w=None):
        if w is None:
            wins = self.windows_or_none()
            if wins:
                w = random.choice(wins)
            else:
                g = self.cur_geo()
                w = dict(x=g.center().x() - 250, y=g.center().y() - 160, w=500, h=320, title="")
        gx, gy = w["x"] + w["w"] / 2, (w["y"] - 60 if w["y"] > 130 else w["y"] + 60)
        yield from self.go(gx, gy, 320)
        self.prop_for("mag", 3.2)
        self.mood("focus", 3.2)
        self.sfx("scan", .8)
        self.fx.add("scan", 0, 0, life=3.0, col=(89, 242, 255), rect=(w["x"], w["y"], w["w"], w["h"]))
        self.look_at(gx, w["y"] + w["h"], 3)
        yield 3.1
        self.mood("proud", 2)
        self.sfx("ding")
        try:
            msg = self.scan_comment(w)        # comentario según la app o la pestaña (bip_charla)
        except Exception:
            msg = None
        if msg:
            self.say(msg, None, 1)
        else:
            self.say(random.choice(["Escaneo completo: todo en orden.", "Nada raro por acá. ¡Ventana aprobada!",
                                    "Análisis listo. Parece que todo está bien."]), 4)
        yield 2.2

    def b_chase_cursor(self):
        self.mood("happy", 1.5)
        self.sfx("happy")
        dur = random.uniform(5, 9)
        t = 0.0
        while t < dur:
            c = QCursor.pos()
            a = t * 2.4
            self.tx, self.ty, self.max_speed = c.x() + math.cos(a) * 130, c.y() + math.sin(a) * 100, 520
            t += self.dt
            yield 0
        c = QCursor.pos()
        self.look_at(c.x(), c.y(), 1)
        yield from self.go(c.x() + 40, c.y() - 20, 900, 1.2, 40)
        self.sfx("boop")
        self.mood("love", 1.5)
        self.fx.hearts(self.px, self.py - 40, 3)
        yield 1.2

    def b_ball(self):
        g = self.cur_geo()
        ball = self.fx.add("ball", g.center().x() + random.uniform(-300, 300), g.top() + 120, random.uniform(-150, 150), 0,
                           life=14, size=16, col=random.choice(PALETTE))
        if ball is None:
            return
        self.mood("excited", 2)
        self.sfx("yay", .8)
        cd = 0.0
        t = 0.0
        while t < 13 and ball in self.fx.items:
            cd -= self.dt
            t += self.dt
            self.tx, self.ty, self.max_speed = ball["x"] - 30, ball["y"] - 70, 520
            if cd <= 0 and math.hypot(self.px - ball["x"], self.py + 20 - ball["y"]) < 120:
                ball["vx"] = (ball["x"] - self.px) * 3.5 + random.uniform(-200, 200)
                ball["vy"] = -random.uniform(520, 820)
                self.sfx("boop", .8)
                self.jump(.6)
                cd = .5
            self.look_at(ball["x"], ball["y"], .2)
            yield 0
        self.fx.confetti(self.px, self.py, 30)
        self.mood("joy", 2)
        self.sfx("joy")
        yield 1.8

    def shape_strokes(self, shape, cx, cy):
        if shape == "heart":
            pts = []
            for i in range(61):
                a = i / 60 * 2 * math.pi
                pts.append((cx + 9 * 16 * math.sin(a) ** 3 / 1.4,
                            cy - 9 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) / 1.4))
            return [pts]
        if shape == "star":
            pts = []
            for i in range(6):
                a = -math.pi / 2 + i * 4 * math.pi / 5
                pts.append((cx + 130 * math.cos(a), cy + 130 * math.sin(a)))
            return [pts]
        if shape == "spiral":
            return [[(cx + (4 + i * 2.3) * math.cos(i * .22), cy + (4 + i * 2.3) * math.sin(i * .22)) for i in range(70)]]
        if shape == "smile":
            circ = [(cx + 110 * math.cos(a / 40 * 6.283), cy + 110 * math.sin(a / 40 * 6.283)) for a in range(41)]
            mouth = [(cx + 60 * math.cos(math.radians(20 + i * 5)), cy + 10 + 60 * math.sin(math.radians(20 + i * 5))) for i in range(29)]
            e1 = [(cx - 40 + 6 * math.cos(a / 8 * 6.283), cy - 35 + 6 * math.sin(a / 8 * 6.283)) for a in range(9)]
            e2 = [(cx + 40 + 6 * math.cos(a / 8 * 6.283), cy - 35 + 6 * math.sin(a / 8 * 6.283)) for a in range(9)]
            return [circ, e1, e2, mouth]
        return self.text_strokes(shape, cx, cy)

    def text_strokes(self, text, cx, cy, size=120):
        path = QPainterPath()
        f = QFont("Segoe UI", 12)
        f.setPixelSize(size)
        f.setBold(True)
        path.addText(0, 0, f, text)
        br = path.boundingRect()
        strokes = []
        for poly in path.toSubpathPolygons(QTransform()):
            pts = [(poly.at(i).x() - br.center().x() + cx, poly.at(i).y() - br.center().y() + cy) for i in range(poly.size())]
            out = [pts[0]]
            for q in pts[1:]:
                if math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) >= 7:
                    out.append(q)
            if len(out) > 2:
                strokes.append(out)
        strokes.sort(key=lambda s: min(p[0] for p in s))
        return strokes

    def b_doodle(self, shape=None):
        hour = datetime.datetime.now().hour
        word = self.name if random.random() < .5 else ("¡Hola!" if hour < 20 else "Zzz")
        shape = shape or random.choice(["heart", "star", "spiral", "smile", word])
        cx, cy = self.rand_point(260)
        strokes = self.shape_strokes(shape, cx, cy)
        if not strokes:
            return
        col = random.choice(PALETTE)
        self.prop_for("brush", 30)
        self.mood("focus", 30)
        self.sfx("think")
        lines = []
        for st in strokes:
            yield from self.go(st[0][0], st[0][1] - PEN_DY, 520, 4)
            line = self.fx.add("line", 0, 0, life=9, size=5, col=col, pts=[(st[0][0], st[0][1])], done=False)
            self.kin = True
            for (x, y) in st[1:]:
                while not self.step_to(x, y - PEN_DY, 430):
                    if line is not None:
                        line["pts"].append((self.px, self.py + PEN_DY))
                    yield 0
                if line is not None:
                    line["pts"].append((x, y))
            if line is not None:
                line["done"] = True
                lines.append(line)
            self.kin = False
        self.prop_override = None
        self.override_until = 0
        self.mood("proud", 2.5)
        self.sfx("yay")
        self.fx.sparkles(self.px, self.py + 30, 14, col)
        yield 2.5

    def b_photo(self):
        x, y = self.rand_point(200)
        yield from self.go(x, y, 300)
        self.prop_for("cam", 2.5)
        self.mood("wink", 2.5)
        self.say("¡Sonrían! 3, 2, 1...", 2)
        self.sfx("think")
        yield 1.8
        self.fx.flash()
        self.sfx("shutter")
        yield .7
        self.mood("proud", 1.8)
        self.say("¡Quedó hermosa la pantalla!", 3)
        yield 2.0

    def b_dance(self):
        self.dancing = True
        self.mood("excited", 6)
        self.sfx("beat")
        t = 0.0
        while t < 6:
            t += self.dt
            if int(t * 4) != int((t - self.dt) * 4):
                self.fx.add("note", self.px + random.uniform(-70, 70), self.py - 40, 0, -60, 1.6, 9, col=(125, 255, 160))
            if int(t) != int(t - self.dt) and int(t) % 2 == 0:
                self.sfx("beat", .8)
            yield 0
        self.dancing = False
        self.mood("happy", 1.5)

    def b_sing(self):
        self.mood("happy", 3.5)
        self.sfx("whistle")
        for _ in range(4):
            self.fx.add("note", self.px + random.uniform(-50, 50), self.py - 50, random.uniform(-10, 10), -50, 1.8, 9, col=(130, 190, 255))
            yield .8

    def b_race(self):
        self.mood("excited", 4)
        self.sfx("fly")
        for _ in range(3):
            x, y = self.rand_point(80)
            while math.hypot(self.px - x, self.py - y) > 40:
                self.tx, self.ty, self.max_speed = x, y, 1300
                if self.every("trail", .02):
                    self.fx.add("dot", self.px, self.py, 0, 0, .5, 7, col=(89, 242, 255))
                yield 0
        self.mood("dizzy", 1.5)
        self.sfx("dizzy")
        yield 1.6

    def b_treasure(self):
        x, y = self.rand_point(100)
        yield from self.go(x, y, 280)
        self.mood("curious", 2)
        self.sfx("curious")
        self.fx.ring(x, y + 40, (255, 226, 106), 60)
        yield 1.5
        self.fx.sparkles(x, y + 30, 16, (255, 226, 106))
        self.fx.add("text", x - 20, y + 20, 0, -40, 1.6, 22, col=(255, 226, 106), text="★ +1")
        self.sfx("yay")
        self.mood("joy", 2)
        self.fun = min(100, self.fun + 8)
        yield 2

    def b_meteor(self):
        g = self.cur_geo()
        sx = random.uniform(g.center().x(), g.right())
        self.fx.add("meteor", sx, g.top() - 20, -520, 340, life=3, col=(255, 255, 255))
        self.look_at(sx - 200, g.top() + 100, 2)
        self.mood("surprised", 1.2)
        self.sfx("surprise", .7)
        yield 1.4
        self.mood("love", 2.2)
        self.say("¡Una estrella fugaz! Pedí un deseo.", 4)
        self.sfx("love")
        yield 2.4

    def b_stargaze(self):
        g = self.cur_geo()
        for _ in range(14):
            self.fx.add("star", random.uniform(g.left(), g.right()), random.uniform(g.top() + 20, g.top() + 220), 0, 0,
                        random.uniform(5, 8), random.uniform(5, 10), col=(255, 240, 180))
        self.look_at(self.px, self.py - 400, 6)
        self.mood("joy", 5)
        self.sfx("love", .8)
        yield 5.5

    def pick_hide_spot(self):
        g = self.cur_geo()
        self.hide_side = 1 if self.px > g.center().x() else -1
        if self.mode == "dock":
            self.hide_y = g.top() + g.height() * .55
        else:
            self.hide_y = max(g.top() + 160, min(g.bottom() - 160, self.py))
        self.hide_g = g

    def b_station(self):
        """Quedarse en su rincón: perch (esquina), dock/hide (escondido en el borde, asoma un ojo), sleep."""
        next_mini = time.monotonic() + random.uniform(80, 180)
        next_peek = time.monotonic() + random.uniform(18, 40)
        peek_until = 0.0
        if self.mode in ("hide", "dock"):
            self.pick_hide_spot()
        while self.mode in ("perch", "dock", "sleep", "hide"):
            now = time.monotonic()
            if self.mode in ("hide", "dock"):
                self.offscreen_ok = True
                g, sd, sc = self.hide_g, self.hide_side, self.sc_t
                c = QCursor.pos()
                hx = g.right() + 24 * sc if sd > 0 else g.left() - 24 * sc
                using = now < self.interact_until or (self.card_alpha > .3 and self.media_info is not None
                                                      and now < self.card_keep_until)
                near = using or (abs(c.x() - hx) < 130 and abs(c.y() - self.hide_y) < 130)
                if self.mode == "hide" and now >= next_peek and now >= peek_until:
                    next_peek = now + random.uniform(20, 45)
                    peek_until = now + 3.0
                    self.mood("curious", 2.5, snd=False)
                    self.look_at(g.center().x(), g.center().y(), 2.5)
                out = 85 * sc if (near or now < peek_until or self.hovering) else 0.0
                if using and self.media_info is not None:
                    out = 165 * sc          # sale más para que la tarjeta entera quede a la vista
                self.tx = hx - sd * out
                self.ty = self.hide_y
                self.max_speed = 380
            else:
                self.offscreen_ok = False
                ax, ay = self.anchor()
                self.tx, self.ty, self.max_speed = ax, ay, 320
                if self.mode == "perch" and now > next_mini and not self.sleeping:
                    next_mini = now + random.uniform(90, 200)
                    if self.cfg.get("explore") != "off":
                        yield from random.choice((self.b_hello, self.b_peek_edge))()
            yield .25

    def b_demo(self):
        from bip_cara import FACES, FACE_SND
        for name in FACES:
            self.mood(name, 2.0, snd=False)
            if name in FACE_SND:
                self.sfx(FACE_SND[name], 1, prio=2)
            self.say(name, 1.8, 2)
            yield 2.0

    BEHAVIORS = dict(wander=b_wander, hello=b_hello, stretch=b_stretch, peek=b_peek_edge, visit=b_visit_window,
                     scan=b_scan_window, chase=b_chase_cursor, ball=b_ball, doodle=b_doodle, photo=b_photo,
                     dance=b_dance, sing=b_sing, race=b_race, treasure=b_treasure, meteor=b_meteor,
                     stargaze=b_stargaze, demo=b_demo)

    def pick_behavior(self):
        night = datetime.datetime.now().hour >= 20 or datetime.datetime.now().hour < 6
        lazy = self.energy < 35
        opts = [(self.b_wander, 5), (self.b_peek_edge, 2), (self.b_chase_cursor, 2), (self.b_ball, 2),
                (self.b_doodle, 2), (self.b_photo, 1), (self.b_race, 1 if lazy else 1.5), (self.b_treasure, 2),
                (self.b_sing, 1), (self.b_dance, 1), (self.b_hello, 1)]
        if self.windows_or_none():
            opts += [(self.b_visit_window, 3), (self.b_scan_window, 2)]
        if night:
            opts += [(self.b_stargaze, 2), (self.b_meteor, 1)]
        if lazy:
            opts += [(self.b_stretch, 4)]
            opts = [(f, w * (.35 if f in (self.b_race, self.b_ball, self.b_chase_cursor, self.b_dance) else 1)) for f, w in opts]
        f = random.choices([o[0] for o in opts], [o[1] for o in opts])[0]
        return f()
