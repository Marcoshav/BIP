# -*- coding: utf-8 -*-
"""DJ Bip: elige música de YouTube Music según el momento y controla la reproducción."""
import os
import re
import random
import threading
import datetime
import urllib.parse
import urllib.request
import webbrowser

from bip_sistema import APP_DIR, IS_WIN, log

FAV_FILE = os.path.join(APP_DIR, "musica.txt")

MOODS = {
    "concentracion": ("para concentrarte", ["lofi hip hop para concentrarse", "música instrumental para estudiar", "jazz suave para trabajar"]),
    "energia": ("con energía", ["música para entrenar", "rock nacional clásicos", "pop rock hits"]),
    "relax": ("para relajarse", ["música relajante", "bossa nova", "acústico chill"]),
    "lluvia": ("para un día de lluvia", ["jazz lluvioso", "lofi lluvia", "piano lluvia"]),
    "fiesta": ("para festejar", ["reggaeton hits", "cumbia mix", "pop latino hits"]),
    "noche": ("para la noche", ["lofi para dormir", "piano relajante noche", "música tranquila"]),
    "despertar": ("para arrancar el día", ["música positiva mañana", "pop alegre para empezar el día", "folk acústico mañana"]),
    "nostalgia": ("para recordar", ["rock nacional argentino clásicos", "éxitos 90s", "baladas clásicas"]),
}

FAV_HELP = ("# Tu lista de música para Bip. Una por línea: un link (YouTube / YouTube Music / playlist)\n"
            "# o un texto para buscar (por ejemplo: 'mi playlist de rock'). Las líneas con # se ignoran.\n")


def favorites():
    try:
        if not os.path.exists(FAV_FILE):
            os.makedirs(APP_DIR, exist_ok=True)
            with open(FAV_FILE, "w", encoding="utf-8") as f:
                f.write(FAV_HELP)
            return []
        with open(FAV_FILE, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    except Exception:
        return []


def pick_mood(pet):
    """Elige un ánimo según hora, clima y lo que está haciendo el usuario."""
    h = datetime.datetime.now().hour
    w = pet.weather
    if w.ok and w.kind in ("rain", "storm"):
        return "lluvia"
    if pet.activity in ("code", "work", "mail", "design") or getattr(pet, "pomo", None):
        return "concentracion"
    if h >= 23 or h < 5:
        return "noche"
    if 5 <= h < 11:
        return "despertar"
    if 18 <= h < 23 and random.random() < .4:
        return "fiesta"
    return random.choice(["energia", "relax", "nostalgia", "fiesta"])


def _fetch(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "es-AR,es;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def resolve(query, playlist=True):
    """URL de YouTube Music que arranca sola; si algo falla, la búsqueda."""
    q = urllib.parse.quote_plus(query)
    fallback = "https://music.youtube.com/search?q=" + q
    try:
        if playlist:
            html = _fetch("https://www.youtube.com/results?search_query=%s&sp=EgIQAw%%253D%%253D" % q)
            m = re.search(r'"playlistId":"((?:PL|RD|OL)[\w-]{10,})"', html)
            if m:
                return "https://music.youtube.com/watch?list=" + m.group(1)
        html = _fetch("https://www.youtube.com/results?search_query=" + q)
        m = re.search(r'"videoRenderer":\{"videoId":"([\w-]{11})"', html)
        if m:
            return "https://music.youtube.com/watch?v=" + m.group(1)
    except Exception as e:
        log("musica resolve: %s" % e)
    return fallback


def request(pet, mood=None, query=None):
    """Busca en segundo plano; deja el resultado en pet.music_result = (label, url)."""
    pet.music_result = None
    favs = favorites() if mood is None and query is None else []
    if query is None and favs and random.random() < .6:
        query = random.choice(favs)
        label = "algo de tu lista"
    elif query is None:
        mood = mood or pick_mood(pet)
        label_mood, queries = MOODS[mood]
        query = random.choice(queries)
        label = label_mood
    else:
        label = "tu pedido"

    pet.music_pending = (label, query)

    def work():
        if re.match(r"^https?://", query):
            url = query
        else:
            url = resolve(query, playlist=random.random() < .7)
        pet.music_result = (label, url, query)

    threading.Thread(target=work, daemon=True).start()


def open_url(url):
    try:
        webbrowser.open(url, new=1)
    except Exception as e:
        log("abrir música: %s" % e)


def open_favorites():
    favorites()
    try:
        if IS_WIN:
            os.startfile(FAV_FILE)
    except Exception as e:
        log("abrir lista: %s" % e)


# ---- teclas multimedia (Windows)
VK = {"playpause": 0xB3, "next": 0xB0, "prev": 0xB1, "volup": 0xAF, "voldown": 0xAE, "mute": 0xAD}


def media_key(name, times=1):
    if not IS_WIN or name not in VK:
        return False
    try:
        import ctypes
        u = ctypes.windll.user32
        for _ in range(times):
            u.keybd_event(VK[name], 0, 0, 0)
            u.keybd_event(VK[name], 0, 2, 0)
        return True
    except Exception as e:
        log("media_key: %s" % e)
        return False
