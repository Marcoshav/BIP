# -*- coding: utf-8 -*-
"""Reconocimiento de aplicaciones concretas y su 'personalidad' en Bip."""
import re

# key: dict(nombre, cat, exe=[...], title=[...], prop, face, enter=[...], talk=[...])
APPS = {}


def A(key, nombre, cat, exe=(), title=(), prop=None, face=None, enter=(), talk=()):
    APPS[key] = dict(key=key, nombre=nombre, cat=cat, exe=tuple(exe), title=tuple(t.lower() for t in title),
                     prop=prop, face=face, enter=list(enter), talk=list(talk))


# --- orden importante: lo más específico primero
A("meeting", "Videollamada", "meeting", ["zoom.exe", "teams.exe", "ms-teams.exe", "webex.exe", "skype.exe"],
  ["zoom meeting", "google meet", "meet -", "microsoft teams", "videollamada"],
  enter=["Reunión: me callo y me hago chiquito."])
A("ytmusic", "YouTube Music", "music", [], ["youtube music"], prop="music", face="music",
  enter=["¡YouTube Music! Yo puedo elegirte algo si querés.", "Música a la vista. ¿Pongo una playlist?"],
  talk=["Buena banda sonora para el día.", "Si querés, elijo yo la próxima: clic derecho > Música."])
A("spotify", "Spotify", "music", ["spotify.exe"], ["spotify"], prop="music", face="music",
  enter=["¡Spotify! Siempre hay un tema para cada momento.", "Dale play que yo bailo."],
  talk=["Qué buena playlist.", "¿Subimos el volumen? Yo bailo igual."])
A("music_other", "Reproductor", "music", ["itunes.exe", "musicbee.exe", "foobar2000.exe", "winamp.exe", "tidal.exe", "deezer.exe"],
  ["soundcloud", "deezer", "tidal"], prop="music", face="music", enter=["♪ Música en marcha."])
A("youtube", "YouTube", "video", [], [" - youtube", "youtube"], prop="popcorn", face="watch",
  enter=["YouTube. Yo me traje pochoclo.", "A mirar videos. No me spoilees."],
  talk=["Cuidado: un video más y se hacen las 3 de la mañana."])
A("streaming", "Streaming", "video", ["netflix.exe", "vlc.exe", "mpv.exe", "wmplayer.exe"],
  ["netflix", "disney+", "prime video", "twitch", "hbo max", "max -", "crunchyroll", "star+"], prop="popcorn", face="watch",
  enter=["¡Función de cine! Apago las luces."], talk=["Shhh, que viene la mejor parte."])
A("game", "Juego", "game", ["steam.exe", "epicgameslauncher.exe", "riotclientservices.exe", "leagueclient.exe",
                             "minecraft.exe", "javaw.exe", "robloxplayerbeta.exe", "fortniteclient-win64-shipping.exe",
                             "valorant.exe", "gta5.exe"],
  ["league of legends", "minecraft", "roblox", "fortnite", "valorant", "steam"], prop="gamepad", face="game",
  enter=["¡Modo gamer! Yo te alieno desde el costado.", "A jugar. Prometo no distraerte."],
  talk=["¡Dale que ganás!", "Cuidado con ese jefe..."])
A("word", "Word", "work", ["winword.exe"], [" - word", "google docs", "documentos de google", "docs.google.com/document"],
  prop="word", face="focus", enter=["Word: a escribir. Yo corrijo con la mirada.", "Hoja en blanco... ¡qué miedo y qué ganas!"],
  talk=["¿Guardaste el documento? Ctrl+G, por las dudas.", "Tantas palabras lindas.", "Ojo con las tildes."])
A("excel", "Excel", "work", ["excel.exe"], [" - excel", "hojas de cálculo", "google sheets", "docs.google.com/spreadsheets"],
  prop="sheet", face="calc", enter=["Excel: números por todos lados. ¡Me encanta!", "Celdas, fórmulas... yo calculo con vos."],
  talk=["Yo en las sumas soy buenísimo: 1+1=2.", "¿Chequeaste que las fórmulas apunten bien?", "#¡REF! da miedo."])
A("powerpoint", "PowerPoint", "work", ["powerpnt.exe"], [" - powerpoint", "presentaciones de google", "google slides", "docs.google.com/presentation"],
  prop="slides", face="focus", enter=["Presentación en camino. ¡Que salga genial!", "Diapositivas: yo aplaudo al final."],
  talk=["Menos texto, más imágenes.", "Ensayá en voz alta, funciona."])
A("pdf", "Lector PDF", "work", ["acrord32.exe", "acrobat.exe", "sumatrapdf.exe", "foxitreader.exe"], [".pdf"], prop="doc",
  face="focus", enter=["Leyendo un PDF. ¡A concentrarse!"])
A("notes", "Notas", "work", ["onenote.exe", "notion.exe", "obsidian.exe", "notepad.exe"], ["notion", "obsidian", "onenote"],
  prop="doc", face="focus", enter=["Tomando notas. Yo no espío."])
A("outlook", "Correo", "mail", ["outlook.exe", "olk.exe"], ["gmail", "outlook", "bandeja de entrada"], prop="doc",
  face="focus", enter=["Mails... ¡ánimo con la bandeja de entrada!"], talk=["Inbox cero es un mito, pero se puede intentar."])
A("discord", "Discord", "chat", ["discord.exe"], [" - discord", "| discord", "discord |", "discord"], prop="discord",
  face="happy", enter=["¡Discord! ¿Con quién jugamos hoy?", "Saludá a la banda de mi parte."],
  talk=["Las charlas de voz son lo mejor.", "Silenciá el micrófono si no hablás."])
A("whatsapp", "WhatsApp", "chat", ["whatsapp.exe", "whatsapp.root.exe"], ["whatsapp"], prop="chat", face="happy",
  enter=["WhatsApp. No leo nada, lo juro."], talk=["¿Respondiste ese audio de 4 minutos?"])
A("telegram", "Telegram", "chat", ["telegram.exe"], ["telegram"], prop="chat", face="happy", enter=["Telegram. ¡Mandame un sticker!"])
A("ai", "IA", "work", [], ["chatgpt", "claude", "gemini", "copilot", "perplexity"], prop="bulb", face="curious",
  enter=["Hablando con otra IA... ¡saludala de mi parte, somos colegas!"], talk=["Preguntá lo que quieras, yo no me ofendo."])
A("vscode", "VS Code", "code", ["code.exe", "cursor.exe"], ["visual studio code"], prop="code", face="focus",
  enter=["VS Code: yo vigilo los bugs.", "A programar. Yo te acompaño."], talk=["¿Hiciste commit?", "Si no anda, reiniciá. Siempre funciona."])
A("terminal", "Terminal", "code", ["cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe", "wt.exe", "python.exe"],
  ["powershell", "símbolo del sistema"], prop="code", face="focus", enter=["La terminal... qué poderío hacker."],
  talk=["sudo hacerme un mate."])
A("ide", "IDE", "code", ["devenv.exe", "pycharm64.exe", "idea64.exe", "androidstudio64.exe", "sublime_text.exe", "notepad++.exe"],
  ["visual studio", "github", "stack overflow"], prop="code", face="focus", enter=["Código en pantalla. ¡Vos podés!"])
A("photoshop", "Photoshop", "design", ["photoshop.exe"], ["photoshop"], prop="brush", face="curious",
  enter=["Photoshop: ¡a retocar con estilo!"], talk=["Capas sobre capas..."])
A("figma", "Figma", "design", ["figma.exe"], ["figma"], prop="brush", face="curious", enter=["Figma: diseñando cosas lindas."])
A("design", "Diseño", "design", ["illustrator.exe", "blender.exe", "premiere pro.exe", "afterfx.exe", "resolve.exe", "gimp-2.10.exe",
                                  "inkscape.exe", "krita.exe", "mspaint.exe"], ["canva", "blender"], prop="brush", face="curious",
  enter=["Modo creativo. Me encanta ver cómo trabajás."])
A("facebook", "Redes sociales", "social", [], ["facebook", "instagram", "tiktok", "twitter", "reddit", "linkedin"], face="suspicious",
  enter=["Hmm... redes sociales. Yo te vigilo.", "¿Otro ratito de scroll? Dale, pero poquito."], talk=["Ya van varias vueltas de scroll..."])
A("shop", "Compras", "shop", [], ["mercadolibre", "mercado libre", "amazon", "aliexpress", "temu", "shein"], face="curious",
  enter=["¿Comprando algo? Mirá bien el precio.", "Carrito de compras... ¡cuidado con la billetera!"])
A("taskmgr", "Administrador de tareas", "other", ["taskmgr.exe"], ["administrador de tareas"], face="scared",
  enter=["¿Todo bien con la PC? Me asusté."])
A("calculator", "Calculadora", "work", ["calculator.exe", "calc.exe", "calculatorapp.exe"], ["calculadora"], prop="sheet", face="calc",
  enter=["Calculadora: yo ya sé que 2+2=4."])
A("settings", "Configuración", "other", ["systemsettings.exe"], ["configuración"], face="curious", enter=["Tocando configuraciones... con cuidado."])
A("brave", "Brave", "browse", ["brave.exe"], [" - brave"], face="neutral",
  enter=["Brave: escudos arriba, anuncios afuera.", "Navegando con Brave. ¡Qué valiente!"], talk=["Brave bloquea un montón de cosas por vos."])
A("opera", "Opera", "browse", ["opera.exe", "opera_gx.exe"], [" - opera"], face="neutral",
  enter=["Opera: ¿vamos al modo GX?", "Navegando con Opera."], talk=["Tu Opera tiene más funciones que yo."])
A("firefox", "Firefox", "browse", ["firefox.exe"], ["mozilla firefox"], face="neutral", enter=["Firefox: el zorrito rojo, qué buen compañero."])
A("edge", "Edge", "browse", ["msedge.exe"], [" - microsoft edge"], face="neutral", enter=["Edge, el vecino de Windows."])
A("chrome", "Chrome", "browse", ["chrome.exe"], ["google chrome"], face="neutral", enter=["Chrome: ¡cuántas pestañas abiertas!"])
A("browser", "Navegador", "browse", ["vivaldi.exe", "iexplore.exe"], [], face="neutral", enter=["Mirá cuánto internet hay."])
A("explorer", "Archivos", "files", ["explorer.exe"], [], enter=["Ordenando archivitos, ¿eh?"])


def identify(title, exe):
    """Devuelve la clave de la app o None."""
    t = (title or "").lower()
    e = (exe or "").lower()
    # primero por título (webs dentro de navegadores) y exe específico
    for key, a in APPS.items():
        if e and e in a["exe"] and key not in ("brave", "opera", "firefox", "edge", "chrome", "browser"):
            return key
    for key, a in APPS.items():
        if key in ("brave", "opera", "firefox", "edge", "chrome", "browser", "explorer"):
            continue
        if any(s in t for s in a["title"]):
            if key == "youtube" and "youtube music" in t:
                continue
            return key
    for key in ("brave", "opera", "firefox", "edge", "chrome", "browser", "explorer"):
        if e in APPS[key]["exe"] and e:
            return key
    return None


_PLAY_SUFFIX = re.compile(r"\s+-\s+(youtube music|youtube|brave|opera.*|google chrome|microsoft.? edge|mozilla firefox)\s*$", re.I)
SPOTIFY_IDLE = ("spotify", "spotify free", "spotify premium")


def now_playing(key, title):
    """Título de la canción actual (o None si está en pausa / no se sabe)."""
    t = (title or "").strip()
    if key == "spotify":
        return None if t.lower() in SPOTIFY_IDLE or not t else t
    if key == "ytmusic":
        s = t
        for _ in range(3):
            s2 = _PLAY_SUFFIX.sub("", s)
            if s2 == s:
                break
            s = s2
        s = re.sub(r"^\(\d+\)\s*", "", s).strip()
        return s if s and s.lower() != "youtube music" else None
    return None


def unread(title):
    m = re.match(r"^\s*[\(\[](\d+)[\)\]]", title or "")
    return int(m.group(1)) if m else 0


def category(key):
    return APPS[key]["cat"] if key in APPS else None
