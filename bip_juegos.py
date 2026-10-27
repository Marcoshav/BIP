# -*- coding: utf-8 -*-
"""Juegos e interacciones de Bip con el usuario y sus apps: DJ, mancha, jugar con el mouse."""
import math
import random
import time

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QCursor

import bip_musica as M


class Juegos:
    def b_dj(self, mood=None, query=None, mine=False):
        self.prop_for("music", 12)
        self.mood("excited", 8)
        self.say("Dejame elegir algo de música...", 3, 2)
        self.sfx("think", 1, 2)
        M.request(self, mood, query, mine)
        t = 0.0
        while self.music_result is None and t < 11:
            t += self.dt
            yield 0
        if self.music_result is None:
            label, q = getattr(self, "music_pending", ("para vos", "música"))
            url = "https://music.youtube.com/search?q=" + __import__("urllib.parse").parse.quote_plus(q)
        else:
            label, url, q = self.music_result
        self.say("Pongo música %s: %s" % (label, q if len(q) < 42 else q[:39] + "..."), 5, 2)
        self.sfx("yay", 1, 2)
        for _ in range(3):
            self.fx.add("note", self.px + random.uniform(-60, 60), self.py - 50, 0, -60, 1.6, 9, col=(125, 255, 160))
        yield 1.2
        M.open_url(url)
        self.music_result = None
        self.dj_last = time.monotonic()
        self.spin_t0 = time.monotonic()
        self.spin_until = self.spin_t0 + .9
        self.mood("joy", 2)
        yield 2.5

    def b_cursor_play(self, manual=True):
        """Bip agarra tu mouse y lo pasea. Se suelta apenas lo movés vos."""
        self.mood("curious", 3.5)
        self.say("¿Juego con tu mouse un ratito? Movelo y lo suelto.", 4, 2)
        self.sfx("curious", 1, 2)
        yield 3.2
        c = QCursor.pos()
        yield from self.go(c.x(), c.y() - 70, 700, 3, 30)
        self.mood("excited", 10, snd=False)
        self.sfx("boop", 1, 2)
        self.say("¡Te lo agarré!", 2, 2)
        last = QCursor.pos()
        t, strikes, dur = 0.0, 0, random.uniform(6, 9)
        interrupted = False
        while t < dur:
            cur = QCursor.pos()
            if math.hypot(cur.x() - last.x(), cur.y() - last.y()) > 12:
                strikes += 1
            else:
                strikes = max(0, strikes - 1)
            if strikes >= 2:
                interrupted = True
                break
            g = self.cur_geo()
            a = t * 1.5
            self.tx = g.center().x() + math.cos(a) * g.width() * .3
            self.ty = g.center().y() + math.sin(a * 1.3) * g.height() * .25
            self.max_speed = 420
            QCursor.setPos(QPoint(int(self.px), int(self.py + 66)))
            last = QCursor.pos()
            if self.every("cp_sp", .3):
                self.fx.add("dot", self.px, self.py + 40, 0, 0, .5, 6, col=(255, 226, 106))
            t += self.dt
            yield 0
        if interrupted:
            self.mood("surprised", 1.5)
            self.say("¡Perdón! Es tu mouse, te lo devuelvo.", 3.5, 2)
        else:
            self.mood("laugh", 2)
            self.say("¡Jajaja! Gracias por prestármelo.", 3.5, 2)
            self.fx.confetti(self.px, self.py, 20)
        yield 2.2

    def b_tag_game(self):
        """A la mancha: Bip huye del mouse; si lo tocás medio segundo, lo atrapaste."""
        self.mood("excited", 4)
        self.say("¡Atrapame si podés! Pasame el mouse por arriba.", 4, 2)
        self.sfx("joy", 1, 2)
        yield 2.5
        t, touch, caught = 0.0, 0.0, 0
        while t < 28:
            c = QCursor.pos()
            dx, dy = self.px - c.x(), self.py - c.y()
            d = max(1.0, math.hypot(dx, dy))
            if d < 170:
                fx_, fy_ = self.clamp_pos(self.px + dx / d * 380, self.py + dy / d * 380)
                if math.hypot(fx_ - self.px, fy_ - self.py) < 60:   # arrinconado: se escapa para el otro lado
                    fx_, fy_ = self.rand_point(100)
                self.tx, self.ty, self.max_speed = fx_, fy_, 520 + (170 - d) * 3
                if self.face_name != "laugh":
                    self.mood("excited", .4, snd=False)
            else:
                self.max_speed = 140
            touch = touch + self.dt if d < 85 else max(0.0, touch - self.dt)
            if touch > .45:
                caught += 1
                touch = 0.0
                self.mood("laugh", 2)
                self.fx.confetti(self.px, self.py, 22)
                self.fx.hearts(self.px, self.py - 40, 3)
                self.say(random.choice(["¡Me atrapaste!", "¡Ay, qué rápido!", "Está bien, ganaste esta."]), 2.5, 2)
                self.affection = min(100, self.affection + 5)
                yield 1.6
                x, y = self.rand_point(120)
                self.tx, self.ty = x, y
                t += 1.6
            t += self.dt
            yield 0
        self.mood("proud", 2.5)
        self.say("¡Buen juego! Me atrapaste %d vez/veces." % caught if caught else "¡Gané! No me atrapaste.", 4, 2)
        yield 3

    def b_hide_seek(self):
        """Se esconde en un borde y espera a que lo encuentres con el mouse."""
        g = self.cur_geo()
        side = random.choice((-1, 1))
        y = random.uniform(g.top() + 200, g.bottom() - 200)
        self.offscreen_ok = True
        self.say("Voy a esconderme... ¡buscame!", 3, 2)
        self.sfx("whistle", .6, 2)
        yield from self.go(g.right() + 22 if side > 0 else g.left() - 22, y, 500)
        t = 0.0
        found = False
        while t < 30:
            c = QCursor.pos()
            if math.hypot(c.x() - self.px, c.y() - self.py) < 120:
                found = True
                break
            t += self.dt
            yield 0
        self.offscreen_ok = False
        if found:
            self.mood("surprised", 1.2)
            self.say("¡Me encontraste!", 3, 2)
            self.fx.confetti(self.px, self.py, 18)
        else:
            self.say("¿Nadie me busca? Salgo yo.", 3, 1)
        yield 2

    BEHAVIORS = dict(dj=b_dj, mouse=b_cursor_play, tag=b_tag_game, hideseek=b_hide_seek)
