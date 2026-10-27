# -*- coding: utf-8 -*-
"""Gustos musicales de Bip: aprende qué escuchás de verdad (artistas y temas) para elegir música tuya.

Todo queda en tu PC, en ~/.bip/gustos.json. Sólo guarda artista, título y cuántas veces lo escuchaste.
Un tema cuenta como 'escuchado' cuando suena de corrido más de 35 segundos (los que salteás enseguida no suman).
Los gustos recientes pesan más que los viejos (la importancia se reduce a la mitad cada 45 días).
"""
import os
import re
import json
import time
import random

from bip_sistema import APP_DIR, log

FILE = os.path.join(APP_DIR, "gustos.json")
LISTEN_SECS = 35.0        # segundos sonando para contar una escucha
HALF_LIFE_DAYS = 45.0     # cada cuántos días un gusto viejo pesa la mitad
SEED_WEIGHT = 3.0         # cuánto pesa un artista que vos le dijiste a Bip
MAX_SONGS = 120

_TOPIC = re.compile(r"\s*-\s*topic\s*$", re.I)
_SPLIT = re.compile(r"\s*(?:,|;|\bfeat\.?|\bft\.?)\s+", re.I)


def clean_artist(name):
    """'Soda Stereo - Topic' -> 'Soda Stereo'; 'Tini, Lola Índigo' -> 'Tini'."""
    a = _TOPIC.sub("", (name or "").strip())
    first = _SPLIT.split(a)[0].strip(" -·•|")
    return (first or a)[:60]


def split_title(title, artist):
    """Si no hay artista (sólo el título de la ventana), intenta 'Artista - Tema'."""
    t = (title or "").strip()
    a = clean_artist(artist)
    if a:
        return a, t
    if " - " in t:
        left, right = t.split(" - ", 1)
        if 1 <= len(left) <= 50 and right:
            return clean_artist(left), right.strip()
    return "", t


def _key(artist, title):
    return ("%s|%s" % (artist, title)).lower()


class Gustos:
    def __init__(self, path=FILE):
        self.path = path
        self.artists = {}     # nombre -> dict(n=escuchas, seed=peso fijo, last=timestamp)
        self.songs = {}       # clave -> dict(artist, title, n, last)
        self._dirty = False
        self._cur = None      # clave del tema actual
        self._played = 0.0
        self._counted = False
        self.load()

    # ---------------------------------------------------------------- disco
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.artists = d.get("artists", {}) or {}
            self.songs = d.get("songs", {}) or {}
        except FileNotFoundError:
            pass
        except Exception as e:
            log("gustos: no pude leer (%s)" % e)

    def flush(self):
        if not self._dirty:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dict(artists=self.artists, songs=self.songs), f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
            self._dirty = False
        except Exception as e:
            log("gustos: no pude guardar (%s)" % e)

    # ------------------------------------------------------------ aprender
    def observe(self, title, artist, playing, dt, now=None):
        """Llamar seguido (cada tick). Cuenta la escucha cuando el mismo tema suena `LISTEN_SECS` seguidos."""
        a, t = split_title(title, artist)
        if not t:
            self._cur = None
            return
        k = _key(a, t)
        if k != self._cur:
            self._cur, self._played, self._counted = k, 0.0, False
        if playing and not self._counted:
            self._played += dt
            if self._played >= LISTEN_SECS:
                self._counted = True
                self.add_listen(a, t, now)

    def add_listen(self, artist, title, now=None):
        now = now or time.time()
        if artist:
            e = self.artists.setdefault(artist, dict(n=0.0, seed=0.0, last=now))
            e["n"] = float(e.get("n", 0)) + 1.0
            e["last"] = now
        k = _key(artist, title)
        s = self.songs.setdefault(k, dict(artist=artist, title=title, n=0.0, last=now))
        s["n"] = float(s.get("n", 0)) + 1.0
        s["last"] = now
        if len(self.songs) > MAX_SONGS:      # tira los más viejos y menos escuchados
            worst = sorted(self.songs.items(), key=lambda kv: (kv[1].get("n", 0), kv[1].get("last", 0)))[:len(self.songs) - MAX_SONGS]
            for kk, _ in worst:
                self.songs.pop(kk, None)
        self._dirty = True

    def seed(self, names):
        """Artistas que le decís vos a Bip (ej: 'Soda Stereo, Charly García')."""
        now = time.time()
        added = 0
        for raw in re.split(r"[,;\n]", names or ""):
            a = clean_artist(raw)
            if not a:
                continue
            e = self.artists.setdefault(a, dict(n=0.0, seed=0.0, last=now))
            e["seed"] = SEED_WEIGHT
            e["last"] = max(float(e.get("last", 0)), now)
            added += 1
        if added:
            self._dirty = True
            self.flush()
        return added

    def forget(self):
        self.artists, self.songs = {}, {}
        self._cur, self._played, self._counted = None, 0.0, False
        self._dirty = True
        self.flush()

    # ------------------------------------------------------------- elegir
    @staticmethod
    def _decay(last, now):
        age = max(0.0, (now - float(last or now)) / 86400.0)
        return 0.5 ** (age / HALF_LIFE_DAYS)

    def weights(self, now=None):
        now = now or time.time()
        out = {}
        for name, e in self.artists.items():
            w = float(e.get("n", 0)) * self._decay(e.get("last"), now) + float(e.get("seed", 0))
            if w > 0.05:
                out[name] = w
        return out

    def has_data(self):
        return sum(self.weights().values()) >= 2.0

    def top_artists(self, k=8):
        return sorted(self.weights().items(), key=lambda kv: -kv[1])[:k]

    def pick_artist(self, avoid=()):
        w = self.weights()
        for a in avoid:
            if len(w) > 1:
                w.pop(a, None)
        if not w:
            return None
        names = list(w)
        return random.choices(names, weights=[w[n] for n in names], k=1)[0]

    def pick_song(self, avoid=()):
        now = time.time()
        pool = [(s, float(s.get("n", 0)) * self._decay(s.get("last"), now)) for s in self.songs.values()
                if s.get("title") and _key(s.get("artist", ""), s["title"]) not in avoid]
        pool = [(s, w) for s, w in pool if w > 0.05]
        if not pool:
            return None
        return random.choices([s for s, _ in pool], weights=[w for _, w in pool], k=1)[0]

    def summary(self, k=5):
        top = self.top_artists(k)
        if not top:
            return ""
        return ", ".join(a for a, _ in top)
