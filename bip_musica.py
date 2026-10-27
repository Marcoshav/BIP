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
from bip_gustos import clean_artist

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
            "# o un texto para buscar (por ejemplo: 'mi playlist de rock'). Las líneas con # se ignoran.\n"
            "# Para decirle qué artistas te gustan escribí:  artista: Soda Stereo\n"
            "# (Bip además aprende solo de lo que escuchás: Spotify, YouTube Music, etc.)\n")


def _read_lines():
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


def favorites():
    """Links o búsquedas de tu lista (las líneas 'artista:' no van acá)."""
    return [l for l in _read_lines() if not l.lower().startswith("artista:")]


def fav_artists():
    """Artistas que escribiste en la lista como 'artista: Nombre'."""
    return [l.split(":", 1)[1].strip() for l in _read_lines() if l.lower().startswith("artista:") and l.split(":", 1)[1].strip()]


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


def resolve(query, playlist=True, radio=False):
    """URL de YouTube Music que arranca sola; si algo falla, la búsqueda.
    radio=True: busca el tema y abre su 'radio' (temas parecidos); playlist=True: una playlist/mix."""
    q = urllib.parse.quote_plus(query)
    fallback = "https://music.youtube.com/search?q=" + q
    try:
        if radio:
            html = _fetch("https://www.youtube.com/results?search_query=%s&sp=EgIQAQ%%253D%%253D" % q)
            m = re.search(r'"videoRenderer":\{"videoId":"([\w-]{11})"', html)
            if m:
                vid = m.group(1)
                return "https://music.youtube.com/watch?v=%s&list=RDAMVM%s" % (vid, vid)
        elif playlist:
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


def _taste_pick(pet, g):
    """Elige algo de TUS gustos. Devuelve (label, consulta, tipo, texto_para_mostrar, artista) o None."""
    recent = list(getattr(pet, "dj_recent", []))[-2:]
    if random.random() < .5:
        for _ in range(4):
            song = g.pick_song()
            if song and song.get("artist") not in recent:
                q = ("%s %s" % (song.get("artist", ""), song["title"])).strip()
                return ("parecida a lo que escuchás", q, "radio", "radio de «%s»" % song["title"][:36], song.get("artist", ""))
    artist = g.pick_artist(avoid=recent)
    if artist:
        return ("de lo que escuchás", "Mix - " + artist, "mix", "mix de " + artist, artist)
    return None


def request(pet, mood=None, query=None, mine=False):
    """Busca en segundo plano; deja el resultado en pet.music_result = (label, url, texto).
    Prioridad: pedido explícito > tus gustos (lo que escuchás + 'artista:' de tu lista) > tu lista > estado de ánimo."""
    pet.music_result = None
    g = getattr(pet, "gustos", None)
    if g is not None:
        try:
            nuevos = [a for a in fav_artists() if g.artists.get(clean_artist(a), {}).get("seed", 0) <= 0]
            if nuevos:
                g.seed("\n".join(nuevos))
        except Exception as e:
            log("musica seed: %s" % e)
    kind, disp, chosen = "search", None, None
    taste = None
    if query is None and g is not None and g.has_data() and (mine or (mood is None and random.random() < .85)):
        taste = _taste_pick(pet, g)
    favs = favorites() if (mood is None and query is None and taste is None) else []

    if taste:
        label, query, kind, disp, chosen = taste
    elif query is None and favs and random.random() < .6:
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
    if chosen:
        pet.dj_recent = (list(getattr(pet, "dj_recent", [])) + [chosen])[-4:]

    def work():
        if re.match(r"^https?://", query):
            url = query
        elif kind == "radio":
            url = resolve(query, radio=True)
        elif kind == "mix":
            url = resolve(query, playlist=True)
        else:
            url = resolve(query, playlist=random.random() < .7)
        pet.music_result = (label, url, disp or query)

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
