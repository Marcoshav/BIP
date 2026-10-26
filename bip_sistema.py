# -*- coding: utf-8 -*-
"""Datos de la PC (Windows), clasificación de actividad, clima y configuración."""
import sys
import os
import json
import time
import ctypes
import threading
import datetime
import traceback
import urllib.request
import urllib.parse

IS_WIN = sys.platform.startswith("win")
APP_DIR = os.path.join(os.path.expanduser("~"), ".bip")
STATE_FILE = os.path.join(APP_DIR, "estado.json")
LOG_FILE = os.path.join(APP_DIR, "bip.log")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def log(msg):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), msg))
    except Exception:
        pass


def install_excepthook():
    def hook(et, ev, tb):
        log("".join(traceback.format_exception(et, ev, tb)))
    sys.excepthook = hook


DEFAULTS = dict(name="Bip", energy=85.0, affection=70.0, fun=60.0, lat=None, lon=None, city="",
                explore="normal", volume=0.7, bubbles=True, reminders=True, last_seen=None, first_run=True)


def load_state():
    cfg = dict(DEFAULTS)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_state(cfg):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
    except Exception as e:
        log("save_state: %s" % e)


# ------------------------------------------------------------------ Windows
if IS_WIN:
    from ctypes import wintypes
    _u32 = ctypes.windll.user32
    _k32 = ctypes.windll.kernel32
    _k32.GetTickCount.restype = wintypes.DWORD
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                ctypes.POINTER(wintypes.DWORD)]
    _u32.GetForegroundWindow.restype = wintypes.HWND
    _u32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _u32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _u32.IsWindowVisible.argtypes = [wintypes.HWND]
    _u32.IsIconic.argtypes = [wintypes.HWND]
    _u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    _u32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    _EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _u32.EnumWindows.argtypes = [_EnumProc, wintypes.LPARAM]

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                    ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD)]

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]


class SysInfo:
    dpr = 1.0   # Win32 da pixeles físicos; Qt usa lógicos. Se setea al iniciar.

    @staticmethod
    def idle_seconds():
        if not IS_WIN:
            return 0.0
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(lii)
            if _u32.GetLastInputInfo(ctypes.byref(lii)):
                return ((_k32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF) / 1000.0
        except Exception:
            pass
        return 0.0

    @staticmethod
    def foreground():
        """(título, exe, pid, rect lógico (x,y,w,h) o None)"""
        if not IS_WIN:
            return "", "", 0, None
        try:
            hwnd = _u32.GetForegroundWindow()
            if not hwnd:
                return "", "", 0, None
            n = _u32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            _u32.GetWindowTextW(hwnd, buf, n + 1)
            pid = wintypes.DWORD()
            _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            exe = ""
            h = _k32.OpenProcess(0x1000, False, pid.value)
            if h:
                try:
                    size = wintypes.DWORD(520)
                    pbuf = ctypes.create_unicode_buffer(520)
                    if _k32.QueryFullProcessImageNameW(h, 0, pbuf, ctypes.byref(size)):
                        exe = os.path.basename(pbuf.value).lower()
                finally:
                    _k32.CloseHandle(h)
            r = wintypes.RECT()
            rect = None
            if _u32.GetWindowRect(hwnd, ctypes.byref(r)):
                d = SysInfo.dpr or 1.0
                rect = (r.left / d, r.top / d, (r.right - r.left) / d, (r.bottom - r.top) / d)
            return buf.value, exe, pid.value, rect
        except Exception:
            return "", "", 0, None

    @staticmethod
    def windows():
        """Ventanas visibles de otras apps: lista de dict(title,x,y,w,h) en pixeles lógicos."""
        if not IS_WIN:
            return []
        out = []
        mypid = os.getpid()
        d = SysInfo.dpr or 1.0

        def cb(hwnd, lp):
            try:
                if not _u32.IsWindowVisible(hwnd) or _u32.IsIconic(hwnd):
                    return True
                n = _u32.GetWindowTextLengthW(hwnd)
                if n == 0 or _u32.GetWindowLongW(hwnd, -20) & 0x80:
                    return True
                cloaked = wintypes.DWORD(0)
                ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)
                if cloaked.value:
                    return True
                pid = wintypes.DWORD()
                _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == mypid:
                    return True
                r = wintypes.RECT()
                _u32.GetWindowRect(hwnd, ctypes.byref(r))
                w, h = (r.right - r.left) / d, (r.bottom - r.top) / d
                if w < 220 or h < 140:
                    return True
                buf = ctypes.create_unicode_buffer(n + 1)
                _u32.GetWindowTextW(hwnd, buf, n + 1)
                if buf.value == "Program Manager":
                    return True
                out.append(dict(title=buf.value, x=r.left / d, y=r.top / d, w=w, h=h))
            except Exception:
                pass
            return True

        try:
            _u32.EnumWindows(_EnumProc(cb), 0)
        except Exception:
            pass
        return out

    @staticmethod
    def battery():
        if not IS_WIN:
            return None, True
        try:
            sps = SYSTEM_POWER_STATUS()
            if _k32.GetSystemPowerStatus(ctypes.byref(sps)):
                pct = sps.BatteryLifePercent
                return (None if pct == 255 else int(pct)), sps.ACLineStatus == 1
        except Exception:
            pass
        return None, True

    @staticmethod
    def ram_percent():
        if not IS_WIN:
            return 0
        try:
            m = MEMORYSTATUSEX()
            m.dwLength = ctypes.sizeof(m)
            if _k32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return int(m.dwMemoryLoad)
        except Exception:
            pass
        return 0


class CpuMeter:
    """% de CPU usando GetSystemTimes (sin dependencias)."""

    def __init__(self):
        self.last = None

    @staticmethod
    def _ft(f):
        return (f.dwHighDateTime << 32) | f.dwLowDateTime

    def read(self):
        if not IS_WIN:
            return 0.0
        try:
            from ctypes import wintypes as wt
            i, k, u = wt.FILETIME(), wt.FILETIME(), wt.FILETIME()
            if not _k32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u)):
                return 0.0
            cur = (self._ft(i), self._ft(k), self._ft(u))
            if self.last is None:
                self.last = cur
                return 0.0
            di, dk, du = (cur[x] - self.last[x] for x in range(3))
            self.last = cur
            total = dk + du
            return max(0.0, min(100.0, 100.0 * (total - di) / total)) if total > 0 else 0.0
        except Exception:
            return 0.0


# ------------------------------------------------------------ actividad
def classify(title, exe):
    t = (title or "").lower()
    e = (exe or "").lower()

    def has_t(*ks):
        return any(k in t for k in ks)

    def has_e(*ks):
        return any(k in e for k in ks)

    if has_e("zoom", "teams", "webex", "skype") or has_t("zoom meeting", "meet -", "google meet", "videollamada", "microsoft teams"):
        return "meeting"
    if has_e("spotify", "itunes", "musicbee", "foobar", "winamp", "tidal", "deezer") \
            or has_t("spotify", "youtube music", "soundcloud", "deezer", "tidal"):
        return "music"
    if e in ("vlc.exe", "mpv.exe", "wmplayer.exe", "netflix.exe") \
            or has_t("youtube", "netflix", "disney+", "prime video", "twitch", "hbo max", "crunchyroll", "star+"):
        return "video"
    if has_e("steam", "epicgames", "riotclient", "leagueclient", "minecraft", "roblox", "fortnite", "valorant", "javaw") \
            or has_t("league of legends", "minecraft", "roblox", "fortnite", "valorant", "steam"):
        return "game"
    if e in ("code.exe", "devenv.exe", "pycharm64.exe", "idea64.exe", "sublime_text.exe", "notepad++.exe", "cmd.exe",
             "powershell.exe", "pwsh.exe", "windowsterminal.exe", "wt.exe", "python.exe", "cursor.exe",
             "androidstudio64.exe", "claude.exe") or has_t("visual studio", "github", "stack overflow", "powershell"):
        return "code"
    if has_e("photoshop", "illustrator", "figma", "blender", "premiere", "afterfx", "davinci", "gimp", "inkscape",
             "krita", "canva") or has_t("figma", "canva", "photoshop"):
        return "design"
    if e in ("winword.exe", "excel.exe", "powerpnt.exe", "onenote.exe", "acrord32.exe", "acrobat.exe", "soffice.exe",
             "notion.exe", "obsidian.exe") or has_t("google docs", "hojas de cálculo", ".pdf", "docs.google", "chatgpt"):
        return "work"
    if e == "outlook.exe" or has_t("gmail", "outlook", "bandeja de entrada"):
        return "mail"
    if has_e("whatsapp", "telegram", "discord", "slack", "signal") or has_t("whatsapp", "telegram", "discord", "messenger"):
        return "chat"
    if has_t("facebook", "instagram", "tiktok", "twitter", "reddit", "linkedin", "/ x"):
        return "social"
    if has_t("mercadolibre", "mercado libre", "amazon", "aliexpress", "temu", "shein"):
        return "shop"
    if e in ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe"):
        return "browse"
    if e == "explorer.exe":
        return "files"
    return "other"


# --------------------------------------------------------------- clima
WX_ES = {"clear": "despejado", "partly": "algo nublado", "cloudy": "nublado", "fog": "con niebla",
         "rain": "lluvioso", "snow": "con nieve", "storm": "con tormenta"}


def http_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Bip/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wmo_kind(code):
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "cloudy"


class WeatherService:
    def __init__(self, cfg, offline=False):
        self.cfg = cfg
        self.offline = offline
        self.ok = False
        self.temp = self.feels = None
        self.kind = "clear"
        self.is_day = True
        self.city = cfg.get("city", "")
        self.version = 0
        self.message = None
        self._wake = threading.Event()

    def start(self):
        if not self.offline:
            threading.Thread(target=self._loop, daemon=True).start()

    def refresh(self):
        self._wake.set()

    def set_city(self, name):
        def work():
            try:
                if not name:
                    self.cfg["lat"] = self.cfg["lon"] = None
                    self.cfg["city"] = ""
                    self.message = "Listo, detecto tu ubicación por internet."
                else:
                    url = ("https://geocoding-api.open-meteo.com/v1/search?count=1&language=es&name="
                           + urllib.parse.quote(name))
                    res = http_json(url).get("results") or []
                    if not res:
                        self.message = "No encontré esa ciudad."
                        return
                    self.cfg["lat"], self.cfg["lon"] = res[0]["latitude"], res[0]["longitude"]
                    self.cfg["city"] = res[0].get("name", name)
                    self.message = "Ahora miro el clima de %s." % self.cfg["city"]
                self.refresh()
            except Exception as e:
                log("set_city: %s" % e)
                self.message = "No pude buscar esa ciudad. ¿Hay internet?"
        threading.Thread(target=work, daemon=True).start()

    def _loop(self):
        while True:
            wait = 20 * 60
            try:
                self._fetch()
            except Exception as e:
                log("weather: %s" % e)
                wait = 60
            self._wake.wait(wait)
            self._wake.clear()

    def _locate(self):
        c = self.cfg
        if c.get("lat") is not None and c.get("lon") is not None:
            return c["lat"], c["lon"], c.get("city", "")
        for url, parse in (
                ("https://ipapi.co/json/", lambda d: (d["latitude"], d["longitude"], d.get("city", ""))),
                ("https://ipwho.is/", lambda d: (d["latitude"], d["longitude"], d.get("city", ""))),
                ("http://ip-api.com/json/?fields=status,city,lat,lon", lambda d: (d["lat"], d["lon"], d.get("city", "")))):
            try:
                return parse(http_json(url))
            except Exception:
                continue
        raise RuntimeError("no se pudo ubicar por IP")

    def _fetch(self):
        lat, lon, city = self._locate()
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&timezone=auto"
               "&current=temperature_2m,apparent_temperature,weather_code,is_day" % (lat, lon))
        cur = http_json(url)["current"]
        self.temp = cur["temperature_2m"]
        self.feels = cur.get("apparent_temperature", self.temp)
        self.kind = wmo_kind(cur["weather_code"])
        self.is_day = bool(cur.get("is_day", 1))
        self.city = city
        self.ok = True
        self.version += 1


# ------------------------------------------------------- autoinicio
def autostart_enabled():
    if not IS_WIN:
        return False
    try:
        import winreg
        winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY), "Bip")
        return True
    except OSError:
        return False


def set_autostart(on, script):
    if not IS_WIN:
        return
    import winreg
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    if on:
        if getattr(sys, "frozen", False):
            cmd = '"%s"' % sys.executable
        else:
            exe = sys.executable
            pyw = exe.replace("python.exe", "pythonw.exe")
            cmd = '"%s" "%s"' % (pyw if os.path.exists(pyw) else exe, os.path.abspath(script))
        winreg.SetValueEx(k, "Bip", 0, winreg.REG_SZ, cmd)
    else:
        try:
            winreg.DeleteValue(k, "Bip")
        except OSError:
            pass
