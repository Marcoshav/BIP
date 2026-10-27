# -*- coding: utf-8 -*-
"""La charla de Bip (v2): comentarios según la app, el navegador y la pestaña; el 'repertorio' de una página,
comandos escritos, curiosidades y el aprendizaje de tus gustos de música.

Sólo lee el TÍTULO de la ventana activa (nunca el contenido de la página ni lo que escribís)."""
import os
import time
import random
import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

import bip_sitios as S
from bip_apps import APPS, identify
from bip_fx import clamp
from bip_gustos import Gustos
from bip_sistema import SysInfo, IS_WIN, log

# cada cuántos segundos comenta sola mientras seguís en el mismo sitio (mín, máx)
LEVELS = {"high": (90, 180), "normal": (200, 420), "low": (600, 1000)}
LEVEL_NAMES = (("Mucho", "high"), ("Normal", "normal"), ("Poco", "low"), ("Nada", "off"))
ENTER_COOLDOWN = 20.0       # entre comentarios al cambiar de pestaña (para no marearte)
SAME_SITE_COOLDOWN = 120.0  # si volvés al mismo sitio enseguida, no repite el saludo
BROWSER_APPS = ("brave", "opera", "firefox", "edge", "chrome", "browser")

BEHAVIOR_WORDS = {
    "bailar": "dance", "baila": "dance", "baile": "dance", "pelota": "ball", "jugar": "ball", "dibujar": "doodle",
    "dibuja": "doodle", "foto": "photo", "escanear": "scan", "escanea": "scan", "carrera": "race", "mancha": "tag",
    "escondite": "hideseek", "cantar": "sing", "canta": "sing", "mouse": "mouse", "visitar": "visit", "emociones": "demo",
    "estrellas": "stargaze", "meteoro": "meteor", "tesoro": "treasure",
}
AYUDA = (
    "Escribí una de estas palabras (con o sin /):\n\n"
    "  youtube, netflix, github, mercado libre...   Bip suelta su repertorio de comentarios de esa página\n"
    "  hablar            comentarios de lo que estás viendo ahora (página o app)\n"
    "  musica            elige algo de lo que VOS escuchás      ·  musica <artista o tema>: busca eso\n"
    "  gustos            qué aprendió de tu música     ·  olvidar musica: borra lo aprendido\n"
    "  contame           una curiosidad o un chiste\n"
    "  charla mucho / normal / poco / nada       cuánto comenta solo\n"
    "  bailar, jugar, foto, escanear, carrera, mancha, escondite, cantar, dibujar...\n"
    "  clima, dormir, pomodoro, mimos\n\n"
    "Tus propias páginas: Menú > Charla > Mis sitios y comentarios.")


class PetCharla:
    def init_charla(self):
        self.gustos = Gustos()
        self.dj_recent = []
        self.site = None            # sitio detectado en la pestaña activa (dict) o None
        self.browser = None         # clave del navegador activo (brave, operagx, chrome...) o None
        self.site_key = None
        self.site_talk_next = 0.0
        self.site_enter_cd = 0.0
        self.site_said = {}
        self.site_recent = []
        self.last_ctx = None
        S.ensure_user_file()

    # ------------------------------------------------------------ utilidades
    def charla_range(self):
        return LEVELS.get(self.cfg.get("charla", "normal"))      # None si está en "off"

    def pick_line(self, pool):
        """Una frase al azar sin repetir las últimas 8."""
        fresh = [p for p in pool if p not in self.site_recent] or list(pool)
        line = random.choice(fresh)
        self.site_recent = (self.site_recent + [line])[-8:]
        return line

    def say_site(self, text):
        """Globo de un comentario automático. Pasa el modo silencioso (video/música/juegos) pero sin sonidito."""
        if self.sleeping or self.fullscreen or self.activity == "meeting":
            return False
        return self.say(text, None, 1, silent=self.quiet)

    def pseudo_app(self, site):
        """Registra el sitio como 'app' para que Bip le ponga la cara y el objeto que corresponden."""
        key = "site:" + site["key"]
        if key not in APPS:
            APPS[key] = dict(key=key, nombre=site["nombre"], cat=site["cat"], exe=(), title=(), prop=site.get("prop"),
                             face=site.get("face"), enter=[], talk=[])
        return key

    # ------------------------------------------------- qué hay en pantalla
    def site_update(self, now, title, exe, pid, app):
        """Se llama desde el cerebro lento. Devuelve (app, dueño): si dueño es True, esta capa se encarga de
        los comentarios de la ventana y los viejos de bip_apps no se repiten."""
        try:
            e = (exe or "").lower()
            path = SysInfo.exe_info(pid)[1] if e == "opera.exe" else ""
            b = S.detect_browser(e, title, path)
            if not b:
                self.browser = self.site = self.site_key = None
                if app in APPS:
                    self.last_ctx = dict(site=None, browser=None, app=app, t=now)
                return app, False
            site = S.site_of(S.strip_browser(title))
            self.browser, self.site = b, site
            if site and (app is None or app in BROWSER_APPS):
                app = self.pseudo_app(site)
            self.last_ctx = dict(site=site, browser=b, app=app, t=now)
            key = (b, site["key"] if site else None)
            if key != self.site_key:
                prev_b = self.site_key[0] if self.site_key else None
                self.site_key = key
                rng = self.charla_range()
                self.site_talk_next = now + (random.uniform(*rng) if rng else 600)
                self.site_enter(now, site, b, prev_b != b)
            elif now >= self.site_talk_next:
                self.site_talk(now, site, b)
            return app, True
        except Exception as ex:
            log("site_update: %s" % ex)
            return app, False

    def site_enter(self, now, site, b, browser_changed):
        if not self.charla_range() or now < self.site_enter_cd:
            return
        name = site["key"] if site else "b:" + b
        if now - self.site_said.get(name, -9999) < SAME_SITE_COOLDOWN:
            return
        if site:
            pool, p = site["enter"], .8
        else:
            pool, p = S.browser_lines(b, "enter"), (.5 if browser_changed else 0.0)
        if not pool or random.random() > p:
            return
        if self.say_site(self.pick_line(pool)):
            self.site_enter_cd = now + ENTER_COOLDOWN
            self.site_said[name] = now

    def site_talk(self, now, site, b):
        rng = self.charla_range()
        self.site_talk_next = now + (random.uniform(*rng) if rng else 600)
        if not rng or (self.user_busy and random.random() < .6):
            return
        pool = list(site["talk"]) if site else []
        if site and site.get("late") and datetime.datetime.now().hour < 5 and random.random() < .6:
            pool = list(site["late"])
        if not pool or random.random() < .2:
            pool = S.browser_lines(b) or pool
        if pool:
            self.say_site(self.pick_line(pool))

    def current_context(self):
        """Lo que Bip ve ahora (o hace menos de 10 min): (sitio, navegador, app)."""
        c = self.last_ctx
        if c and time.monotonic() - c["t"] < 600:
            return c["site"], c["browser"], c["app"]
        return None, None, self.app

    def scan_comment(self, w):
        """Comentario del escaneo de una ventana, según su app o su pestaña. None si no hay nada específico."""
        title, exe = w.get("title", ""), (w.get("exe") or "").lower()
        path = SysInfo.exe_info(w.get("pid"))[1] if exe == "opera.exe" and w.get("pid") else ""
        b = S.detect_browser(exe, title, path)
        if b:
            site = S.site_of(S.strip_browser(title))
            if site and (site["talk"] or site["enter"]):
                return "%s: %s" % (site["nombre"], self.pick_line(site["talk"] or site["enter"]))
            lines = S.browser_lines(b)
            if lines:
                return "%s: %s" % (S.BROWSERS[b]["nombre"], self.pick_line(lines))
            return None
        app = identify(title, exe)
        info = APPS.get(app) if app else None
        if info and (info["talk"] or info["enter"]):
            return "%s: %s" % (info["nombre"], self.pick_line(info["talk"] or info["enter"]))
        return None

    # --------------------------------------------------------- repertorio
    def run_repertorio(self, site=None, browser=None):
        if self.sleeping:
            self.wake("")
        self.mode = "free"
        self.sc_t = 1.0
        self.manual_until = time.monotonic() + 60
        self.hide_until = 0.0
        self.start(self.b_repertorio(site, browser))

    def b_repertorio(self, site=None, browser=None, n=5):
        """Bip suelta un comentario detrás de otro sobre una página o app."""
        if site is None:
            site, browser, app = self.current_context()
            if site is None and app in APPS and (APPS[app]["enter"] or APPS[app]["talk"]):
                info = APPS[app]
                site = dict(nombre=info["nombre"], enter=info["enter"], talk=info["talk"], late=[], face=info.get("face"))
        lines = S.repertorio(site, n, browser) if site else []
        if not lines:
            lines = ["No sé nada de esta página todavía.",
                     "Podés enseñarme: Menú > Charla > Mis sitios y comentarios.",
                     "Probá decirme 'youtube', 'netflix' o 'github' en Comando."]
            name = None
        else:
            name = site["nombre"]
        self.mood("excited", 1.6)
        self.sfx("happy", .8, 2)
        self.jump(.5)
        self.say(("Hablemos de %s..." % name) if name else "Mmm...", 2.4, 2)
        yield 2.7
        for line in lines:
            self.mood(random.choice(("happy", "curious", "proud", "excited")), 2.6, snd=False)
            dur = clamp(2.8 + len(line) * 0.06, 3, 8)
            self.say(line, dur, 2)
            self.jump(.35)
            yield dur + .5
        self.mood("joy", 2)
        self.fx.sparkles(self.px, self.py - 30, 6, (255, 255, 255), 60)
        yield 1.6

    # ----------------------------------------------------------- comandos
    def ask_box(self, title, text):
        box = QMessageBox()
        box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        box.setWindowTitle(title)
        box.setText(text)
        box.exec()

    def menu_comando(self):
        txt, ok = self.ask_text("Comando", "Escribí un comando o una página (youtube, netflix, música, bailar...). 'ayuda' lista todo:", "")
        if ok and txt:
            self.run_comando(txt)

    def comando_ayuda(self):
        self.ask_box("Comandos de Bip", AYUDA)

    def run_comando(self, txt):
        orig = txt.strip().lstrip("/!").strip()
        t = S.norm(orig)
        if not t:
            return
        words = t.split()
        verb, rest = words[0], " ".join(words[1:])
        rest_orig = " ".join(orig.split()[1:])
        if verb in ("ayuda", "help", "?", "comandos"):
            return self.comando_ayuda()
        if verb in ("hablar", "habla", "comentar", "comenta", "sitio", "pagina", "repertorio", "decime", "dime", "charlar"):
            if not rest:
                return self.run_repertorio()
            s = S.find_site(rest)
            if s:
                return self.run_repertorio(s)
            return self.say("No conozco '%s' todavía. Agregalo en Menú > Charla > Mis sitios." % rest_orig[:24], 6, 2)
        if verb in ("musica", "dj", "pone", "pon", "poneme", "ponete"):
            if not rest or rest in ("mia", "mio", "mis gustos", "lo mio", "lo que escucho"):
                return self.run_dj(mine=True)
            return self.run_dj(query=rest_orig)
        if verb in ("gustos", "artistas"):
            return self.menu_gustos_ver()
        if verb in ("olvidar", "borrar") and rest.startswith("musica"):
            return self.menu_gustos_borrar()
        if verb in ("contame", "cuentame", "chiste", "curiosidad", "dato", "sorprendeme"):
            return self.contar_algo()
        if verb == "charla" and rest:
            lvl = {"mucho": "high", "alta": "high", "normal": "normal", "poco": "low", "baja": "low", "nada": "off", "no": "off"}.get(rest)
            if lvl:
                return self.set_charla(lvl)
        if verb in ("silencio", "callate", "calla"):
            return self.set_charla("off")
        if verb in ("clima", "hora"):
            return self.menu_status()
        if verb in ("dormir", "duerme", "sueno"):
            return self.go_sleep("manual") if not self.sleeping else None
        if verb in ("pomodoro", "pomo"):
            return self.toggle_pomo()
        if verb in ("mimos", "mimo", "cariño", "carino"):
            return self.menu_pet()
        if verb in BEHAVIOR_WORDS and BEHAVIOR_WORDS[verb] in self.BEHAVIORS:
            return self.run_behavior(BEHAVIOR_WORDS[verb])
        s = S.find_site(t)
        if s:
            return self.run_repertorio(s)
        self.say("No entendí '%s'. Escribí 'ayuda' para ver qué sé hacer." % orig[:22], 5, 2)

    def contar_algo(self):
        if self.sleeping:
            self.wake("")
        self.mood("curious", 3)
        line = self.pick_line(S.CURIOSIDADES)
        self.say(line, clamp(3.5 + len(line) * 0.06, 5, 10), 2)
        self.jump(.4)

    # ------------------------------------------------------------- menú
    def set_charla(self, level):
        self.cfg["charla"] = level
        self.site_talk_next = time.monotonic() + 30
        txt = {"high": "¡Voy a hablar bastante! Aviso si es mucho.", "normal": "Charla normal: comento de vez en cuando.",
               "low": "Charla tranquila: hablo poquito.", "off": "Silencio. Sólo hablo si me lo pedís."}[level]
        self.say(txt, 4, 2)

    def menu_sitios(self):
        S.ensure_user_file()
        try:
            if IS_WIN:
                os.startfile(S.USER_FILE)
        except Exception as e:
            log("abrir sitios: %s" % e)

    # -------------------------------------------------------- tu música
    def menu_gustos_artistas(self):
        cur = self.gustos.summary(6)
        txt, ok = self.ask_text("Mis artistas", "Artistas que escuchás (separados por coma). Bip los suma a lo que aprende solo:", cur)
        if ok and txt:
            n = self.gustos.seed(txt)
            if n:
                self.say("¡Anotado! Voy a elegir música de %s." % (txt if len(txt) < 38 else txt[:35] + "..."), 5, 2)
                self.sfx("happy", 1, 2)

    def menu_gustos_ver(self):
        s = self.gustos.summary(6)
        if s:
            self.say("Lo que más escuchás: %s. Eso uso cuando elijo música." % s, 8, 2)
        else:
            self.say("Todavía no aprendí qué escuchás. Poné música un rato, o decime tus artistas.", 7, 2)

    def menu_gustos_borrar(self):
        self.gustos.forget()
        self.dj_recent = []
        self.say("Listo, olvidé tus gustos de música. Empiezo de cero.", 5, 2)
