# -*- coding: utf-8 -*-
"""Estado, interacción, emociones, sonido y menú de Bip."""
import os
import math
import random
import time
import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMenu, QInputDialog

import bip_cara as C
from bip_fx import Overlay, clamp
from bip_apps import APPS
import bip_musica as M
from bip_sonido import Sfx
from bip_sistema import (APP_DIR, load_state, save_state, log, WeatherService, CpuMeter, WX_ES,
                         autostart_enabled, set_autostart, IS_WIN)


class PetBrain:
    def init_brain(self, offline=False, script=__file__):
        self.script = script
        self.cfg = load_state()
        self.name = self.cfg.get("name", "Bip")
        away_h = 0.0
        if self.cfg.get("last_seen"):
            away_h = max(0.0, (time.time() - float(self.cfg["last_seen"])) / 3600.0)
        self.energy = clamp(float(self.cfg["energy"]) + min(away_h * 25, 100), 0, 100)
        self.affection = clamp(float(self.cfg["affection"]) - min(away_h * 6, 45), 5, 100)
        self.fun = clamp(float(self.cfg.get("fun", 60)) - min(away_h * 8, 50), 0, 100)
        self.welcome = "first" if self.cfg.get("first_run") else ("back" if away_h > 2 else "hi")
        self.sfx_ = Sfx(os.path.join(APP_DIR, "sonidos"), float(self.cfg.get("volume", .7)), QApplication.instance())
        self.fx = Overlay()
        self.weather = WeatherService(self.cfg, offline)
        self.weather.start()
        self.cpu = CpuMeter()
        self.debug = False
        # control
        self.task = None
        self.task_wait = 0.0
        self.mode = "free"
        self.next_action = time.monotonic() + 9
        self.home = None
        self.home_t = 0.0
        # ánimo
        self.override_mood = None
        self.override_until = 0.0
        self.love_until = 0.0
        self.sleeping = False
        self.sleep_reason = ""
        self.begging = False
        self.beg_next = 0.0
        self.last_petted = time.monotonic()
        self.last_spont = 0.0
        self.clicks = []
        self.startle_cd = 0.0
        # actividad / sistema
        self.activity = "other"
        self.busy_hist = []
        self.fullscreen = False
        self.last_title = None
        self.switches = []
        self.dizzy_cd = 0.0
        self.active_secs = 0.0
        self.reminder_idx = 0
        self.last_reminder = 0.0
        self.act_since = time.monotonic()
        self.act_long_said = set()
        self.batt_warned = False
        self.cpu_hot = 0.0
        self.cpu_said = 0.0
        self.fired = set()
        self.last_chime = -1
        self.weather_sig = None
        self.episode_until = 0.0
        self.next_episode = time.monotonic() + 120
        self.pomo = None
        self.pending_msg = None
        self.music_result = None
        self.dj_pending = None
        self.dj_last = 0.0
        self.hide_until = 0.0
        self.hide_side, self.hide_y, self.hide_g = 1, 400.0, None
        self.user_busy = False
        self.app = None
        self.song = None
        self.unread_n = 0
        self.app_talk_next = 0.0
        self.paused_said = 0.0
        # timers
        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.tick)
        self.think_timer = QTimer(self)
        self.think_timer.timeout.connect(self.think)
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.save)

    def start_timers(self):
        self.tick_timer.start(25)
        self.think_timer.start(500)
        self.save_timer.start(60000)

    def save(self):
        self.cfg.update(name=self.name, energy=round(self.energy, 1), affection=round(self.affection, 1),
                        fun=round(self.fun, 1), last_seen=time.time(), first_run=False)
        save_state(self.cfg)

    # ---------------------------------------------------------------- tareas
    def run_task(self, dt):
        if self.task is None:
            return
        if self.task_wait > 0:
            self.task_wait -= dt
            return
        try:
            w = next(self.task)
            self.task_wait = float(w or 0)
        except StopIteration:
            self.task = None
            self.after_task()
        except Exception:
            if self.debug:
                raise
            import traceback
            log("task: " + traceback.format_exc())
            self.task = None
            self.after_task()

    def after_task(self):
        self.reset_task_state()
        level = self.cfg.get("explore", "normal")
        lo, hi = {"high": (6, 14), "normal": (14, 32), "calm": (40, 90), "off": (9999, 9999)}.get(level, (14, 32))
        self.next_action = time.monotonic() + random.uniform(lo, hi) * (1.8 if self.energy < 35 else 1.0)

    def set_mode(self, m):
        if m == self.mode:
            return
        self.mode = m
        self.stop()
        self.sc_t = {"free": 1.0, "perch": .85, "dock": .6, "hide": .8, "sleep": .75}[m]
        if m == "free":
            self.next_action = time.monotonic() + random.uniform(3, 8)
        else:
            self.start(self.b_station())

    def anchor(self):
        now = time.monotonic()
        if self.home and now - self.home_t < 1800:
            return self.home
        g = QApplication.primaryScreen().availableGeometry()
        if self.mode in ("dock", "sleep"):
            return (g.right() - 95, g.bottom() - 75)
        return (g.right() - 130, g.bottom() - 110)

    def run_behavior(self, key):
        if self.sleeping:
            self.wake("")
        self.mode = "free"
        self.sc_t = 1.0
        self.manual_until = time.monotonic() + 45
        self.hide_until = 0.0
        self.start(self.BEHAVIORS[key](self))

    def run_dj(self, mood=None, query=None):
        if self.sleeping:
            self.wake("")
        self.mode = "free"
        self.sc_t = 1.0
        self.manual_until = time.monotonic() + 45
        self.hide_until = 0.0
        self.start(self.b_dj(mood, query))

    def hide_for(self, minutes):
        self.hide_until = time.monotonic() + minutes * 60
        self.manual_until = 0.0
        self.say("Me escondo un ratito. Tocame si me necesitás.", 4, 2)
        self.sfx("whistle", .5, 2)

    def on_bump(self, speed):
        if self.every("bump", .6):
            self.sfx("boop", .45)
            self.fx.sparkles(self.px, self.py, 4, (255, 255, 255), 70)
            self.sq_bump = True

    # ------------------------------------------------------- sonido y globos
    @property
    def quiet(self):
        return (self.mode == "dock" or self.activity in ("music", "video", "game", "meeting")
                or (self.pomo is not None and self.pomo["phase"] == "work"))

    def sfx(self, name, vol=1.0, prio=0):
        if self.activity == "meeting" and prio < 2:
            return
        if self.quiet and prio < 1:
            return
        if self.sleeping and prio < 1 and name != "snore":
            return
        self.sfx_.play(name, vol)

    def say(self, text, dur=None, prio=0, silent=False):
        now = time.monotonic()
        if self.bubble and now < self.bubble["until"] and prio < self.bubble["prio"]:
            return False
        if self.activity == "meeting" and prio < 2:
            return False
        if self.quiet and prio < 1:
            return False
        if self.sleeping and prio < 1:
            return False
        if prio == 0:
            if now - self.last_spont < 35:
                return False
            self.last_spont = now
        dur = dur or clamp(2.8 + len(text) * 0.06, 3, 8)
        self.bubble = dict(text=text, t0=now, until=now + dur, prio=prio)
        n = len(text)
        if silent:
            return True
        self.sfx("babble_%d" % (0 if n < 14 else 1 if n < 26 else 2 if n < 40 else 3 if n < 60 else 4 if n < 80 else 5), .6, prio)
        return True

    def mood(self, name, secs, snd=True):
        self.override_mood = name
        self.override_until = time.monotonic() + secs
        if snd and name in C.FACE_SND:
            self.sfx(C.FACE_SND[name], .9)

    def prop_for(self, name, secs):
        self.prop_override = name
        self.prop_until = time.monotonic() + secs
        self.prop_since = time.monotonic()

    def hover_text(self):
        t = datetime.datetime.now().strftime("%H:%M")
        w = self.weather
        if w.ok:
            t += "  ·  %s %d°C, %s" % (w.city or "", round(w.temp), WX_ES.get(w.kind, ""))
        return t

    def bubble_below(self):
        return self.py < self.cur_geo().top() + 190

    def led_color(self):
        if self.sleeping:
            return (90, 140, 255)
        if self.batt_warned:
            return (255, 80, 80)
        if self.pomo:
            return (255, 150, 90)
        if self.quiet:
            return (255, 210, 90)
        return (90, 255, 140)

    # --------------------------------------------------------------- caras
    def choose_face(self, now):
        if self.dragging:
            return "surprised" if math.hypot(self.vx, self.vy) < 300 else "joy"
        if now < self.love_until:
            return "love"
        if now < self.override_until and self.override_mood:
            return self.override_mood
        if self.sleeping:
            return "sleep"
        if self.begging:
            return "beg"
        w = self.weather
        if w.ok and now < self.episode_until:
            if w.kind == "storm":
                return "scared"
            band = self.weather_band()
            if band in ("cold", "hot"):
                return band
        if self.cpu_hot > 8:
            return "hot"
        if self.energy < 25:
            return "sleepy"
        info = APPS.get(self.app) if self.app else None
        if info and info.get("face") and self.activity not in ("away",):
            if self.app in ("ytmusic", "spotify") and not self.song:
                return "curious"
            return info["face"]
        faces = {"music": "music", "video": "watch", "game": "game", "code": "focus", "work": "focus", "mail": "focus",
                 "design": "curious", "chat": "happy", "meeting": "mute", "social": "suspicious", "shop": "curious",
                 "browse": "neutral"}
        if self.activity in faces:
            return faces[self.activity]
        if self.fun < 20:
            return "bored"
        if self.affection > 65 and self.energy > 45:
            return "happy"
        if self.affection < 28:
            return "sad"
        return "neutral"

    def weather_band(self):
        f = self.weather.feels
        if f is None:
            return "mild"
        return "cold" if f <= 13 else ("hot" if f >= 30 else "mild")

    # --------------------------------------------------------- interacciones
    def on_drag_start(self):
        self.stop()
        if self.sleeping and self.sleep_reason != "manual":
            self.wake("¡Uy! ¿Adónde me llevás?")
        self.sfx("surprise", .7, 2)

    def on_drag_end(self):
        self.home = (self.px, self.py)
        self.home_t = time.monotonic()
        self.tx, self.ty = self.px, self.py
        self.next_action = time.monotonic() + 10
        if self.mode in ("hide", "dock"):
            # si lo agarraste es porque lo querés en otro lado: se queda donde lo soltaste un buen rato
            self.set_mode("free")
            self.manual_until = time.monotonic() + 120
        elif self.mode != "free":
            self.start(self.b_station())
        self.sfx("happy", .7, 2)

    def on_click(self):
        now = time.monotonic()
        if self.dj_pending:
            self.dj_pending = None
            self.say("Listo, no pongo nada.", 2.5, 2)
            return
        if self.hide_until:
            self.hide_until = 0.0
            self.say("¡Acá estoy!", 2.5, 2)
        if self.sleeping:
            self.wake("¡Uaaah! Me despertaste... pero está bien.")
            self.affection = clamp(self.affection + 3, 0, 100)
            return
        self.clicks = [c for c in self.clicks if now - c < 4] + [now]
        self.last_petted = now
        gp = self.prev_cursor
        if gp is not None:
            d = max(1.0, math.hypot(self.px - gp.x(), self.py - gp.y()))
            self.vx += (self.px - gp.x()) / d * 90
            self.vy += (self.py - gp.y()) / d * 90
        if len(self.clicks) >= 7:
            self.clicks = []
            self.mood("dizzy", 3.2)
            self.say("¡Mareo! ¡Basta de toquetear!", 3.5, 2)
            self.affection = clamp(self.affection - 3, 0, 100)
        elif len(self.clicks) >= 4:
            self.mood("angry", 1.6)
            self.say("¡Ey! ¡No tan fuerte!", 2.2, 2)
        else:
            self.mood("happy", 1.2, snd=False)
            self.sfx("boop", 1, 2)
            self.fx.hearts(self.px, self.py - 50, 2)
            self.jump(.7)
            self.affection = clamp(self.affection + 6, 0, 100)
            self.fun = clamp(self.fun + 3, 0, 100)
            if self.begging and self.affection > 55:
                self.begging = False
                self.say("¡Gracias por el mimo!", 3, 2)

    def on_double(self):
        if self.sleeping:
            return
        self.spin_t0 = time.monotonic()
        self.spin_until = self.spin_t0 + .9
        self.mood("joy", 1.5, snd=False)
        self.sfx("joy", 1, 2)
        self.fx.hearts(self.px, self.py - 40, 5)
        self.affection = clamp(self.affection + 4, 0, 100)

    def stroke_tick(self, dt, now):
        if self.sleeping:
            self.wake("Mmm... qué rico.")
        self.love_until = now + 1.6
        self.last_petted = now
        self.affection = clamp(self.affection + 16 * dt, 0, 100)
        if self.every("stroke_heart", .3):
            self.fx.hearts(self.px, self.py - 50, 1)
        if self.every("purr", 1.2, .1):
            self.sfx("purr", .7, 2)
        if self.begging and self.affection > 50:
            self.begging = False

    def startle(self, gp):
        now = time.monotonic()
        if now < self.startle_cd or self.sleeping:
            return
        self.startle_cd = now + 8
        d = max(1.0, math.hypot(self.px - gp.x(), self.py - gp.y()))
        self.vx += (self.px - gp.x()) / d * 500
        self.vy += (self.py - gp.y()) / d * 500
        self.mood("scared", 1.0)

    # ---------------------------------------------------------- dormir / menú
    def go_sleep(self, reason):
        if self.sleeping:
            return
        self.sleeping = True
        self.sleep_reason = reason
        self.begging = False
        self.say({"manual": "Buenas noches... zzz", "idle": "Te fuiste... me hago una siestita.",
                  "night": "Ya es tarde... zzz", "tired": "No doy más... zzz"}.get(reason, "zzz"), 3.5, 1)
        self.sfx("powerdown", .7, 1)
        self.set_mode("sleep")

    def wake(self, msg=""):
        if not self.sleeping:
            return
        self.sleeping = False
        self.mood("surprised", .8, snd=False)
        self.sfx("wake", 1, 1)
        if msg:
            self.say(msg, 3.5, 1)
        self.set_mode("free")

    def build_menu(self):
        m = QMenu(self)

        def add(menu, text, fn, checked=None):
            a = QAction(text, menu)
            if checked is not None:
                a.setCheckable(True)
                a.setChecked(bool(checked))
                a.toggled.connect(lambda v, f=fn: f(v))
            else:
                a.triggered.connect(lambda _=False, f=fn: f())
            menu.addAction(a)
            return a

        info = add(m, "%s · Energía %d%% · Cariño %d%% · Diversión %d%%" % (self.name, self.energy, self.affection, self.fun), lambda: None)
        info.setEnabled(False)
        m.addSeparator()
        add(m, "Darle mimos", self.menu_pet)
        for text, key in (("Jugar con la pelota", "ball"), ("Dibujar o escribir algo", "doodle"), ("Sacar una foto", "photo"),
                          ("Escanear una ventana", "scan"), ("Visitar una ventana", "visit"), ("Bailar", "dance"),
                          ("Carrera loca", "race"), ("Ver todas mis emociones", "demo")):
            add(m, text, lambda k=key: self.run_behavior(k))
        add(m, "A la mancha (atrapame)", lambda: self.run_behavior("tag"))
        add(m, "Escondite (buscame)", lambda: self.run_behavior("hideseek"))
        add(m, "Que juegue con mi mouse", lambda: self.run_behavior("mouse"))
        add(m, "Esconderse un rato (10 min)", lambda: self.hide_for(10))
        mm = m.addMenu("Música")
        add(mm, "Que Bip elija algo", lambda: self.run_dj())
        for key, (lab, _q) in M.MOODS.items():
            add(mm, "Música %s" % lab, lambda k=key: self.run_dj(k))
        mm.addSeparator()
        for text, k in (("Play / Pausa", "playpause"), ("Siguiente", "next"), ("Anterior", "prev"),
                        ("Subir volumen", "volup"), ("Bajar volumen", "voldown"), ("Silenciar", "mute")):
            add(mm, text, lambda kk=k: M.media_key(kk, 3 if kk in ("volup", "voldown") else 1))
        add(mm, "Editar mi lista de música", M.open_favorites)
        add(m, "Reproductor fijo en pantalla", lambda v: (setattr(self, "card_pin", bool(v)), self.cfg.__setitem__("card_pin", bool(v))), self.card_pin)
        add(m, "Ofrecerme música al abrir YouTube Music", lambda v: self.cfg.__setitem__("dj_auto", bool(v)), self.cfg.get("dj_auto", True))
        add(m, "¿Qué hora y clima hay?", self.menu_status)
        add(m, "Despertar" if self.sleeping else "Mandar a dormir", self.menu_sleep)
        add(m, "Parar Pomodoro" if self.pomo else "Iniciar Pomodoro (25/5)", self.toggle_pomo)
        m.addSeparator()
        sm = m.addMenu("Sonido")
        for text, v in (("Silencio", 0.0), ("Bajo", .35), ("Medio", .7), ("Alto", 1.0)):
            a = add(sm, text, lambda val=v: self.set_volume(val))
            a.setCheckable(True)
            a.setChecked(abs(float(self.cfg.get("volume", .7)) - v) < .01)
        em = m.addMenu("Explorar la pantalla")
        for text, v in (("Mucho", "high"), ("Normal", "normal"), ("Tranquilo", "calm"), ("No explorar", "off")):
            a = add(em, text, lambda val=v: self.cfg.__setitem__("explore", val))
            a.setCheckable(True)
            a.setChecked(self.cfg.get("explore", "normal") == v)
        add(m, "Globos de texto", lambda v: self.cfg.__setitem__("bubbles", bool(v)), self.cfg.get("bubbles", True))
        add(m, "Recordatorios (agua, descanso)", lambda v: self.cfg.__setitem__("reminders", bool(v)), self.cfg.get("reminders", True))
        add(m, "Cambiar nombre...", self.menu_rename)
        add(m, "Cambiar ciudad del clima...", self.menu_city)
        if IS_WIN:
            add(m, "Iniciar con Windows", lambda v: set_autostart(bool(v), self.script), autostart_enabled())
        m.addSeparator()
        add(m, "Salir", self.quit_app)
        return m

    def set_volume(self, v):
        self.cfg["volume"] = v
        self.sfx_.volume = v
        self.sfx_.play("happy")

    def menu_pet(self):
        if self.sleeping:
            self.wake("Mmm... qué rico.")
        self.love_until = time.monotonic() + 4
        self.affection = clamp(self.affection + 15, 0, 100)
        self.begging = False
        self.sfx("love", 1, 2)
        self.fx.hearts(self.px, self.py - 50, 5)

    def menu_sleep(self):
        self.wake("¡Buen día! ...o buenas tardes.") if self.sleeping else self.go_sleep("manual")

    def menu_status(self):
        d = datetime.datetime.now()
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                 "noviembre", "diciembre"]
        txt = "Son las %s del %s %d de %s." % (d.strftime("%H:%M"), dias[d.weekday()], d.day, meses[d.month - 1])
        w = self.weather
        if w.ok:
            txt += " En %s hay %d°C (sensación %d°C), %s." % (w.city or "tu zona", round(w.temp), round(w.feels), WX_ES[w.kind])
            self.episode_until = time.monotonic() + 8
        else:
            txt += " Todavía no pude ver el clima... ¿tenés internet?"
            w.refresh()
        if self.sleeping:
            self.wake("")
        self.say(txt, 8, 2)

    def ask_text(self, title, label, text=""):
        from PyQt6.QtCore import Qt
        dlg = QInputDialog()
        dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setTextValue(text)
        return (dlg.textValue().strip(), True) if dlg.exec() else ("", False)

    def menu_rename(self):
        txt, ok = self.ask_text("Nombre", "¿Cómo se llama tu robot?", self.name)
        if ok and txt:
            self.name = txt[:20]
            self.say("¡Me encanta! Ahora soy %s." % self.name, 4, 2)

    def menu_city(self):
        txt, ok = self.ask_text("Ciudad", "Ciudad para el clima (vacío = detectar por internet):", self.cfg.get("city", ""))
        if ok:
            self.weather.set_city(txt)

    def toggle_pomo(self):
        if self.pomo:
            self.pomo = None
            self.say("Pomodoro cancelado.", 3, 2)
            return
        self.pomo = dict(phase="work", t0=time.monotonic(), end=time.monotonic() + 25 * 60)
        self.say("¡Pomodoro! 25 minutos de foco. Yo me quedo quietito.", 5, 2)
        self.sfx("ding", 1, 2)

    def pomo_progress(self):
        p = self.pomo
        return (time.monotonic() - p["t0"]) / max(1.0, p["end"] - p["t0"])

    def quit_app(self):
        self.save()
        QApplication.quit()
