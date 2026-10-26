# -*- coding: utf-8 -*-
"""El 'cerebro lento' de Bip: mira la PC, el clima y la hora, y decide cómo reaccionar."""
import os
import random
import time
import datetime
import traceback

from PyQt6.QtWidgets import QApplication

from bip_fx import clamp
from bip_sistema import SysInfo, classify, log, WX_ES
from bip_apps import APPS, identify, now_playing, unread
import bip_musica as M

ENTER_MSG = {
    "code": ["Modo código: yo vigilo los bugs.", "Shhh, a programar. Yo te acompaño.", "{ } listo. ¡Vos podés!"],
    "work": ["¡Qué productivo! Yo miro desde acá.", "A trabajar. No te olvides de descansar la vista."],
    "mail": ["Mails... ¡ánimo con la bandeja de entrada!"],
    "design": ["¡Diseñando! Eso se ve prometedor.", "Me encantan los colores. Seguí así."],
    "chat": ["¿Con quién charlás? Saludalo de mi parte.", "Chateando... yo no espío, lo juro."],
    "social": ["Hmm... redes sociales. Yo te vigilo.", "¿Otro ratito de scroll? Dale, pero poquito."],
    "shop": ["¿Comprando algo? Mirá bien el precio.", "Carrito de compras... ¡cuidado con la billetera!"],
    "browse": ["Mirá cuánto internet hay.", "¿Buscamos algo interesante?"],
}
LONG_MSG = {
    "social": (10, "Van 10 minutos de redes. ¿Y si hacemos una pausa?"),
    "game": (60, "Una hora de juego. ¡Tomá agua y estirá los dedos!"),
    "video": (90, "Mucho video. ¿Seguimos, o descansamos la vista?"),
    "code": (45, "45 minutos de código. Un buen momento para un mate."),
}
IDLE_CHATTER = ["¿Qué hacemos hoy?", "Estoy explorando por si hay algo interesante.", "Pasame el mouse por arriba para un mimo.",
                "Podés arrastrarme a donde quieras.", "Clic derecho: mi menú de trucos.", "Beep boop. Todo en orden."]


class PetThink:
    def init_think(self):
        self.unread_map = {}
        self.app_since = time.monotonic()
        self.last_think = time.monotonic()
        self.manual_until = 0.0

    # -------------------------------------------------- tick rápido (efectos)
    def brain_tick(self, dt, now):
        self.update_media(dt, now)
        alive = self.fx.tick(dt)
        if alive and not self.fx.isVisible():
            self.fx.show()
            self.raise_()
        elif not alive and self.fx.isVisible():
            self.fx.hide()
        elif alive:
            self.fx.update()
        self.update_props(now)
        fn = self.face_name
        px, py = self.px, self.py
        if fn == "love" and self.every("h", .3):
            self.fx.hearts(px, py - 50, 1)
        if self.sleeping and self.every("z", 1.6):
            self.fx.add("zzz", px + 62, py - 40, 12, -24, 2.6, 15, col=(130, 150, 255), text="Z")
            if self.every("snore", 6, .3):
                self.sfx("snore", .5, 1)
        if fn == "cold" and self.every("puff", 1.2):
            self.fx.add("puff", px + 30, py + 20, 14, -18, 1.4, 5, col=(255, 255, 255))
        if fn in ("hot", "scared") and self.every("sw", 1.1):
            self.fx.add("dot", px + 84, py - 45, 0, 40, 1.0, 5, col=(124, 196, 255))
        if fn == "beg" and self.every("sp", .6):
            self.fx.sparkles(px + random.uniform(-60, 60), py - 20, 2, (255, 255, 255), 30)
        if (self.activity == "music" and not self.sleeping) and self.every("note", .8):
            self.fx.add("note", px + random.choice((-1, 1)) * 100, py - 20, random.uniform(-20, 20), -55, 1.8, 9, col=(125, 255, 160))
        if (not self.dragging and (self.vx ** 2 + self.vy ** 2) > 420 ** 2) and self.every("trail", .035):
            self.fx.add("dot", px, py + 8, 0, 0, .55, 7, col=(89, 242, 255))
        if not self.sleeping and self.mode != "dock":
            if self.app == "excel" and self.every("xl", 8):
                self.fx.add("text", px + random.uniform(-90, 90), py - 70, 0, -35, 1.8, 16, col=(110, 255, 150),
                            text=random.choice(["=SUMA()", "Σ", "+1", "%", "=A1*2", "123"]))
            elif self.app == "word" and self.every("wd", 10):
                self.fx.add("text", px + random.uniform(-90, 90), py - 70, 0, -35, 1.8, 16, col=(120, 170, 255),
                            text=random.choice(["¶", "abc", "...", "ñ"]))
            elif self.app == "powerpoint" and self.every("pp", 12):
                self.fx.sparkles(px + 100, py - 30, 4, (255, 150, 90), 60)
        w = self.weather
        if w.ok and now < self.episode_until and self.every("wx", .09, .5):
            if w.kind in ("rain", "storm"):
                dx = random.uniform(-130, 130)
                self.fx.add("rain", px + dx, py - 170, -60, 520, 1.0, col=(90, 150, 220),
                            floor=(py - 100 if abs(dx) < 80 else py + 60))
            elif w.kind == "snow":
                self.fx.add("snow", px + random.uniform(-130, 130), py - 170, random.uniform(-10, 10), 55, 2.8, 3, col=(255, 255, 255))

    def update_props(self, now):
        if self.sleeping:
            new = None
        elif self.pomo and self.pomo["phase"] == "work":
            new = "tomato"
        else:
            info = APPS.get(self.app) if self.app else None
            new = info["prop"] if (info and info.get("prop")) else {
                "code": "code", "work": "doc", "mail": "doc", "design": "brush", "chat": "chat",
                "video": "popcorn", "game": "gamepad"}.get(self.activity)
        if new != self.prop:
            self.prop = new
            self.prop_since = now

    def update_accessories(self):
        w = self.weather
        feels = w.feels if (w.ok and w.feels is not None) else 20
        self.acc = dict(
            headphones=self.activity == "music" and not self.sleeping,
            scarf=bool(w.ok and feels <= 15),
            sunglasses=bool(w.ok and w.is_day and w.kind in ("clear", "partly") and feels >= 27),
            umbrella=bool(w.ok and w.kind in ("rain", "storm")))

    # ----------------------------------------------------------- cerebro lento
    def think(self):
        try:
            self._think()
        except Exception:
            if self.debug:
                raise
            log("think: " + traceback.format_exc())

    def is_fullscreen(self, rect, exe, title):
        if not rect or (exe == "explorer.exe" and title in ("", "Program Manager")):
            return False
        x, y, w, h = rect
        for s in QApplication.screens():
            g = s.geometry()
            if x <= g.x() + 2 and y <= g.y() + 2 and x + w >= g.right() - 1 and y + h >= g.bottom() - 1:
                return True
        return False

    def _think(self):
        now = time.monotonic()
        dt = min(now - self.last_think, 5.0)
        self.last_think = now
        dtm = datetime.datetime.now()
        hour = dtm.hour
        night = hour >= 23 or hour < 6
        idle = SysInfo.idle_seconds()
        title, exe, pid, rect = SysInfo.foreground()
        own = pid == os.getpid()
        w = self.weather

        self.busy_hist = (self.busy_hist + [idle < 2.0])[-60:]
        busy = sum(self.busy_hist) / max(1, len(self.busy_hist))
        if not own:
            self.fullscreen = self.is_fullscreen(rect, exe, title)

        # --- actividad
        if not own and title and title != self.last_title:
            self.last_title = title
            self.switches = [s for s in self.switches if now - s < 25] + [now]
            if len(self.switches) >= 9 and now > self.dizzy_cd and not self.sleeping:
                self.dizzy_cd = now + 90
                self.switches = []
                self.mood("dizzy", 3)
                self.say("¡Cuánto cambio de ventana! Me mareo...", 4, 1)
        app = self.app
        if own:
            act = self.activity
        elif idle > 180 and self.activity not in ("video", "meeting", "game", "music"):
            act = "away"
        else:
            app = identify(title, exe)
            act = APPS[app]["cat"] if app else classify(title, exe)
            if self.fullscreen and act in ("other", "browse", "files"):
                act = "video"
        if app != self.app and act != "away":
            self.app = app
            self.app_since = now
            self.song = None
            self.dj_pending = None
            self.reading = app in ("word", "pdf", "notes", "outlook")
            self.app_talk_next = now + random.uniform(240, 480)
            info = APPS.get(app)
            if info and info["enter"] and random.random() < .75 and not self.sleeping:
                self.say(random.choice(info["enter"]), None, 0)
            if app in ("excel", "calculator"):
                self.fx.add("text", self.px - 60, self.py - 70, 0, -35, 1.8, 18, col=(110, 255, 150), text="= ?")
            if app in ("word", "excel", "powerpoint", "discord", "vscode"):
                self.jump(.5)
        info = APPS.get(self.app) if self.app else None
        if info and info["talk"] and now > self.app_talk_next and act != "away":
            self.app_talk_next = now + random.uniform(300, 540)
            if random.random() < .55:
                self.say(random.choice(info["talk"]), None, 0)

        # --- música: canción actual y pausas
        if self.app in ("ytmusic", "spotify") and not own and not (self.media.available and self.media.state):
            song = now_playing(self.app, title)
            if song != self.song:
                prev, self.song = self.song, song
                if song:
                    self.dj_pending = None
                    self.say("♪ " + song[:70], 5, 1, silent=True)
                    self.fx.add("note", self.px + 90, self.py - 30, 10, -55, 1.8, 9, col=(125, 255, 160))
                    self.jump(.6)
                elif prev and now - self.paused_said > 120:
                    self.paused_said = now
                    self.mood("curious", 2.5, snd=False)
                    self.say("¿Pausaste la música?", 3, 1, silent=True)
        elif self.song and self.app not in ("ytmusic", "spotify") and not (self.media.available and self.media.state):
            self.song = None

        # --- DJ: si abrís YouTube Music sin nada sonando, ofrece elegir
        if (self.app == "ytmusic" and not self.song and not own and self.cfg.get("dj_auto", True)
                and self.dj_pending is None and now - self.dj_last > 1200 and now - self.app_since > 8
                and not self.sleeping):
            mood = M.pick_mood(self)
            self.dj_pending = (now + 6.5, mood)
            self.dj_last = now
            self.say("¿Te pongo música %s? La elijo en unos segundos. Tocame para cancelar." % M.MOODS[mood][0], 6.5, 2)
            self.sfx("curious", 1, 2)
        if self.dj_pending and now >= self.dj_pending[0]:
            mood = self.dj_pending[1]
            self.dj_pending = None
            self.run_dj(mood)

        # --- mensajes sin leer en segundo plano (Discord, WhatsApp, Telegram, mail)
        if now - getattr(self, "last_unread_scan", 0) > 10:
            self.last_unread_scan = now
            self.scan_unread()
        self.user_busy = busy > .25 and idle < 10

        if act != self.activity:
            self.activity = act
            self.act_since = now
            self.act_long_said = set()
            if act in ENTER_MSG and random.random() < .7 and self.mode != "sleep":
                self.say(random.choice(ENTER_MSG[act]), None, 0)
            if act == "music":
                self.spin_t0 = now
                self.spin_until = now + .9
            elif act in ("meeting", "video", "game"):
                self.fx.sparkles(self.px, self.py, 6, (150, 160, 170), 60)
        if act in LONG_MSG and act not in self.act_long_said and (now - self.act_since) > LONG_MSG[act][0] * 60:
            self.act_long_said.add(act)
            self.say(LONG_MSG[act][1], 6, 1)

        # --- tiempo activo y recordatorios
        if idle < 120:
            self.active_secs += dt
        elif idle > 300:
            self.active_secs = 0.0
            self.last_reminder = 0.0
        if (self.cfg.get("reminders", True) and self.active_secs - self.last_reminder >= 2700
                and self.activity != "meeting" and not self.fullscreen and not self.sleeping):
            self.last_reminder = self.active_secs
            self.reminder()

        # --- batería, CPU, RAM
        pct, plugged = SysInfo.battery()
        if pct is not None:
            if not plugged and pct <= 20 and not self.batt_warned:
                self.batt_warned = True
                self.say("Poca batería (%d%%). ¡Enchufá la compu, por favor!" % pct, 6, 1)
                self.sfx("alert", 1, 1)
                self.prop_for("battery", 6)
                self.mood("scared", 3, snd=False)
            elif plugged and self.batt_warned:
                self.batt_warned = False
                self.say("¡Ahhh, energía! Gracias por enchufar.", 4, 1)
                self.sfx("happy", 1, 1)
        cpu = self.cpu.read()
        self.cpu_hot = self.cpu_hot + dt if cpu > 88 else max(0.0, self.cpu_hot - dt * 2)
        if self.cpu_hot > 8 and now - self.cpu_said > 300:
            self.cpu_said = now
            self.say("¡La PC está a full! Le sale humo a los chips.", 5, 1)
        if SysInfo.ram_percent() > 93 and now - self.cpu_said > 600:
            self.cpu_said = now
            self.say("Memoria casi llena... cerrá alguna pestañita.", 5, 1)

        # --- estadísticas
        if self.sleeping:
            self.energy = min(100, self.energy + 0.1 * dt)
            self.affection = max(0, self.affection - 0.004 * dt)
        else:
            self.energy = max(0, self.energy - 0.0055 * (2 if night else 1) * dt)
            self.affection = max(0, self.affection - 0.0185 * dt)
            self.fun = max(0, self.fun - 0.02 * dt)

        # --- sueño
        busy_media = self.activity in ("video", "meeting", "game", "music")
        if not self.sleeping:
            if idle > 600 and not busy_media:
                self.go_sleep("idle")
            elif night and idle > 90 and not busy_media:
                self.go_sleep("night")
            elif self.energy < 8 and idle > 30:
                self.go_sleep("tired")
        else:
            if self.sleep_reason in ("idle", "night") and idle < 3:
                self.wake("¡Ah! ¿Volviste?")
            elif self.sleep_reason == "tired" and self.energy > 85:
                self.wake("¡Qué bien dormí!")

        # --- mensajes del clima
        if w.message:
            self.say(w.message, 5, 2)
            w.message = None
        if w.ok and w.version and self.weather_sig != (w.kind, self.weather_band()):
            first = self.weather_sig is None
            self.weather_sig = (w.kind, self.weather_band())
            self.episode_until = now + 25
            self.say(self.weather_text(first), 6, 1)
        if w.ok and now > self.next_episode:
            self.next_episode = now + random.uniform(150, 260)
            if self.weather_band() != "mild" or w.kind == "storm":
                self.episode_until = now + 18
        self.update_accessories()

        # --- pomodoro
        if self.pomo and now >= self.pomo["end"]:
            self.sfx("ring", 1, 2)
            if self.pomo["phase"] == "work":
                self.pomo = dict(phase="break", t0=now, end=now + 5 * 60)
                self.say("¡Pausa de 5 minutos! Estirá las piernas.", 6, 2)
                self.mood("proud", 3, snd=False)
                self.fx.confetti(self.px, self.py, 30)
            else:
                self.pomo = None
                self.say("Terminó la pausa. ¿Otra ronda? Menú > Pomodoro.", 6, 2)

        # --- eventos del día
        today = dtm.date()
        ev = None
        if 6 <= hour < 11:
            ev = ("morning", "¡Buen día! ¿Cómo amaneciste?")
        elif 12 <= hour < 14:
            ev = ("lunch", "Se acerca el almuerzo... ¡a recargar baterías!")
        elif 16 <= hour < 18:
            ev = ("merienda", "¡Hora de la merienda! Mate y facturas.")
        elif 20 <= hour < 22:
            ev = ("dinner", "¿Ya pensaste qué cenar?")
        elif night:
            ev = ("late", "Es muy tarde... ¿no deberíamos descansar?")
        if ev and (today, ev[0]) not in self.fired and not self.sleeping:
            if self.say(ev[1], 6, 1):
                self.fired.add((today, ev[0]))
        if dtm.minute == 0 and self.last_chime != hour and 8 <= hour <= 22 and not self.sleeping:
            self.last_chime = hour
            self.sfx("ding", .6)
            self.jump(.7)

        # --- pedir atención
        if not self.sleeping:
            if not self.begging and self.affection < 35 and now - self.last_petted > 45:
                self.begging = True
                self.beg_next = now
            elif self.begging and self.affection > 55:
                self.begging = False
            if self.begging and now >= self.beg_next:
                self.beg_next = now + random.uniform(25, 40)
                self.say(random.choice(["¡Mimos! ¿Me hacés cariño?", "Estoy solito... ¿me das un mimo?",
                                        "¡Acá! Pasame el mouse por arriba."]), 5, 1)
                self.sfx("curious", 1, 1)
                self.jump()
                if self.mode == "free" and self.task is None:
                    self.start(self.b_chase_cursor())
        else:
            self.begging = False

        # --- modo (dónde se queda)
        if now >= self.manual_until and now >= self.interact_until:
            if self.sleeping:
                want = "sleep"
            elif now < self.hide_until:
                want = "hide"
            elif self.activity == "meeting" or self.fullscreen or self.activity in ("video", "game"):
                want = "dock"
            elif (self.activity in ("code", "work", "mail", "design") and busy > .3) or (self.pomo and self.pomo["phase"] == "work"):
                want = "perch"
            elif 25 < idle < 180 and self.cfg.get("hide_idle", True):
                want = "hide"          # estás mirando la pantalla: se corre al borde y no estorba
            else:
                want = "free"
            self.set_mode(want)

        # --- exploración autónoma
        if (self.mode == "free" and self.task is None and not self.dragging and not self.sleeping
                and now >= self.next_action and self.cfg.get("explore", "normal") != "off"):
            if random.random() < .15:
                self.say(random.choice(IDLE_CHATTER), None, 0)
                self.next_action = now + random.uniform(6, 12)
            else:
                self.start(self.pick_behavior())
                self.fun = clamp(self.fun + 2, 0, 100)

    def scan_unread(self):
        newmap = {}
        wins = SysInfo.windows()
        self.ytm_window = any(identify(w["title"], "") == "ytmusic" for w in wins)
        for w in wins:
            key = identify(w["title"], "")
            if key in ("discord", "whatsapp", "telegram", "outlook"):
                n = unread(w["title"])
                if n:
                    newmap[key] = max(newmap.get(key, 0), n)
        for key, n in newmap.items():
            if n > self.unread_map.get(key, 0) and not self.sleeping:
                self.say("%s: tenés %d sin leer." % (APPS[key]["nombre"], n), 4, 1)
                self.sfx("alert", .5, 1)
                self.jump(.6)
                self.fx.add("ring", self.px, self.py, life=.9, size=80, col=(255, 210, 110))
        self.unread_map = newmap

    def reminder(self):
        kind = self.reminder_idx % 3
        self.reminder_idx += 1
        self.sfx("alert", 1, 1)
        if kind == 0:
            self.say("Hora de tomar agua. ¡Hidratación!", 6, 1)
            self.prop_for("glass", 8)
            self.mood("drink", 6, snd=False)
        elif kind == 1:
            self.say("Llevás un rato sentado. ¡Estirá las piernas!", 6, 1)
            self.prop_for("cup", 8)
            self.jump()
        else:
            self.say("Regla 20-20-20: mirá algo lejano por 20 segundos.", 7, 1)
            self.mood("sleepy", 6, snd=False)

    def weather_text(self, first):
        w = self.weather
        t = round(w.temp)
        band = self.weather_band()
        if w.kind == "storm":
            return "Hay tormenta... me da un poquito de miedo."
        if w.kind == "snow":
            return "¡Está nevando! Qué frío y qué lindo."
        if w.kind == "rain":
            return "Está lloviendo. Yo tengo paraguas, ¡vos llevá uno!"
        if band == "cold":
            return "Brrr... hay %d°C afuera. ¡Abrigate bien!" % t
        if band == "hot":
            return "¡Qué calor! %d°C. ¡Tomá mucha agua!" % t
        if w.kind == "clear" and w.is_day:
            return "Día lindo, %d°C. ¡Salí a tomar un poco de sol!" % t
        return "Hoy hay %d°C y está %s." % (t, WX_ES.get(w.kind, "variable"))

    def greet(self):
        self.sfx("boot", 1, 2)
        if self.welcome == "first":
            self.say("¡Beep! Soy %s. Pasame el mouse por arriba, hacé clic o arrastrame. Yo exploro solito." % self.name, 8, 2)
            self.spin_t0 = time.monotonic()
            self.spin_until = self.spin_t0 + .9
        elif self.welcome == "back":
            self.say("¡Volviste! Te extrañé un montón.", 6, 2)
            self.fx.hearts(self.px, self.py - 40, 4)
        else:
            self.say("¡Hola de nuevo!", 4, 2)
        self.jump()
