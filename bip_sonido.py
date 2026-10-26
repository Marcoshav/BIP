# -*- coding: utf-8 -*-
"""Sonidos sintetizados de Bip (ruiditos tipo robot). Sin archivos externos."""
import os
import math
import wave
import array
import random

try:
    from PyQt6.QtCore import QUrl
    from PyQt6.QtMultimedia import QSoundEffect
except Exception:  # sin multimedia: queda en silencio o winsound
    QSoundEffect = None
    QUrl = None

SR = 22050
VERSION = "v1"


def _wave(kind, ph):
    if kind == "sine":
        return math.sin(ph)
    if kind == "tri":
        return 2 / math.pi * math.asin(math.sin(ph))
    if kind == "sq":
        return 0.5 if math.sin(ph) >= 0 else -0.5
    if kind == "saw":
        return (((ph / (2 * math.pi)) % 1.0) * 2 - 1) * 0.6
    return random.uniform(-1, 1)  # noise


def synth(notes, shape="sine", vol=0.5, vib=0.0, am=0.0):
    """notes: lista de (f0, f1, dur[, vol]); f0=None es silencio."""
    out = array.array("h")
    ph = 0.0
    for n in notes:
        f0, f1, dur = n[0], n[1], n[2]
        N = max(1, int(SR * dur))
        if f0 is None:
            out.extend([0] * N)
            continue
        v = n[3] if len(n) > 3 else 1.0
        for i in range(N):
            f = f0 + (f1 - f0) * i / N
            if vib:
                f *= 1 + vib * math.sin(6.2832 * 6 * i / SR)
            ph += 6.2831853 * f / SR
            s = _wave(shape, ph)
            if am:
                s *= 0.65 + 0.35 * math.sin(6.2832 * am * i / SR)
            env = min(1.0, i / (SR * 0.006), (N - i) / (SR * 0.025))
            out.append(int(32767 * vol * v * env * s))
    return out


def N(f0, f1, d, v=1.0):
    return (f0, f1, d, v)


def R(d):
    return (None, None, d)


def babble(count, seed):
    rnd = random.Random(seed)
    scale = [523, 587, 659, 784, 880, 988, 1175, 1319, 1568]
    notes = []
    for _ in range(count):
        f = rnd.choice(scale)
        notes.append(N(f, f * rnd.uniform(0.9, 1.3), rnd.uniform(0.04, 0.09)))
        if rnd.random() < 0.3:
            notes.append(R(0.03))
    return notes


# nombre: (notas, forma, volumen, vibrato, am)
SOUNDS = {
    "boot": ([N(400, 400, .08), N(600, 600, .08), N(800, 800, .08), N(1200, 1500, .2)], "sine", .5, 0, 0),
    "happy": ([N(600, 1000, .09), N(900, 1400, .13)], "sine", .5, 0, 0),
    "joy": ([N(700, 1100, .07), R(.03), N(900, 1500, .07), R(.03), N(1200, 1800, .15)], "sine", .5, 0, 0),
    "yay": ([N(500, 700, .08), N(700, 900, .08), N(900, 1200, .08), N(1200, 1900, .2)], "tri", .5, .02, 0),
    "love": ([N(880, 880, .12), N(1100, 1100, .12), N(1320, 1320, .3)], "sine", .45, .02, 0),
    "sad": ([N(700, 400, .25), N(500, 250, .4)], "sine", .5, .01, 0),
    "surprise": ([N(500, 1500, .08), N(1500, 1500, .1)], "sine", .5, 0, 0),
    "scared": ([N(900, 1300, .04), N(1300, 900, .04)] * 6, "tri", .45, 0, 0),
    "angry": ([N(200, 160, .15), R(.04), N(200, 150, .22)], "saw", .4, 0, 0),
    "yawn": ([N(600, 280, .55)], "sine", .45, .03, 0),
    "snore": ([N(110, 90, .35), R(.25), N(120, 95, .4)], "sine", .35, 0, 0),
    "purr": ([N(140, 140, 1.0)], "tri", .4, 0, 22),
    "giggle": ([N(900, 1100, .05), R(.04), N(1000, 1200, .05), R(.04), N(1100, 1300, .05), R(.04), N(1200, 1400, .06)], "sine", .45, 0, 0),
    "curious": ([N(500, 700, .12), N(700, 650, .14)], "sine", .45, 0, 0),
    "dizzy": ([N(500, 800, .15), N(800, 450, .15), N(450, 750, .15)], "sine", .45, .06, 0),
    "sigh": ([N(900, 500, .35)], "sine", .4, 0, 0),
    "cold": ([N(900, 900, .03), R(.03)] * 8, "tri", .4, 0, 0),
    "wink": ([N(1500, 2200, .08)], "sine", .45, 0, 0),
    "think": ([N(700, 700, .06), R(.05), N(800, 800, .06), R(.05), N(650, 650, .09)], "sine", .4, 0, 0),
    "boop": ([N(800, 200, .08)], "sine", .55, 0, 0),
    "click": ([N(1500, 1500, .015)], "sq", .3, 0, 0),
    "fly": ([N(400, 750, .22, .7)], "sine", .3, 0, 0),
    "scan": ([N(400, 1600, .5), N(1600, 400, .5)], "sq", .2, 0, 0),
    "shutter": ([N(1, 1, .04), R(.03), N(1, 1, .07)], "noise", .5, 0, 0),
    "alert": ([N(1000, 1000, .08), R(.05), N(1000, 1000, .08), R(.05), N(1400, 1400, .16)], "sine", .5, 0, 0),
    "ring": ([N(880, 880, .15), N(1100, 1100, .15), N(1320, 1320, .3), R(.1), N(880, 880, .15), N(1100, 1100, .15), N(1320, 1320, .35)], "sine", .5, .01, 0),
    "beat": ([N(200, 120, .08), R(.12), N(300, 200, .08), R(.12)] * 2, "sine", .4, 0, 0),
    "whistle": ([N(1500, 2000, .2), N(2000, 1700, .2), N(1700, 2300, .3)], "sine", .4, .03, 0),
    "hiccup": ([N(1200, 600, .06), R(.05), N(1300, 700, .06)], "sine", .4, 0, 0),
    "wake": ([N(300, 600, .1), N(600, 1000, .12)], "sine", .5, 0, 0),
    "powerdown": ([N(1000, 300, .5)], "sine", .4, 0, 0),
    "ding": ([N(1500, 1500, .25)], "sine", .4, 0, 0),
}
for _i, _n in enumerate((4, 6, 8, 10, 12, 14)):
    SOUNDS["babble_%d" % _i] = (babble(_n, _i + 7), "sine", .35, 0, 0)


def _write(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(samples.tobytes())


class Sfx:
    def __init__(self, folder, volume=0.7, parent=None):
        self.volume = volume
        self.paths = {}
        self.effects = {}
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        for name, (notes, shape, vol, vib, am) in SOUNDS.items():
            path = os.path.join(folder, "%s_%s.wav" % (VERSION, name))
            if not os.path.exists(path):
                try:
                    _write(path, synth(notes, shape, vol, vib, am))
                except Exception:
                    continue
            self.paths[name] = path
            if QSoundEffect is not None:
                try:
                    e = QSoundEffect(parent)
                    e.setSource(QUrl.fromLocalFile(path))
                    self.effects[name] = e
                except Exception:
                    pass

    def play(self, name, vol=1.0):
        if self.volume <= 0 or name not in self.paths:
            return
        e = self.effects.get(name)
        if e is not None:
            e.setVolume(max(0.0, min(1.0, self.volume * vol)))
            e.play()
            return
        try:
            import winsound
            winsound.PlaySound(self.paths[name], winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception:
            pass
