# -*- coding: utf-8 -*-
"""Sitios web y navegadores: reconoce la pestaña activa por su título y da el 'repertorio' de comentarios.

Todo esto es lógica pura (sin Qt): se puede probar sola. Bip sólo lee el TÍTULO de la ventana activa,
nunca el contenido de la página ni lo que escribís.

Tus propios sitios: Menú > Charla > "Mis sitios y comentarios" abre ~/.bip/sitios.txt. Formato:
    palabra1, palabra2 : comentario A | comentario B | comentario C
"""
import os
import re
import random
import unicodedata

from bip_sistema import APP_DIR, log

USER_FILE = os.path.join(APP_DIR, "sitios.txt")
USER_HELP = (
    "# Tus sitios para Bip. Una línea por sitio:\n"
    "#   palabras del título de la pestaña, separadas por coma : comentario 1 | comentario 2 | comentario 3\n"
    "# Ejemplo:\n"
    "#   mi blog, wordpress : ¡Tu blog! Se ve cada vez mejor. | Escribir es ordenar ideas.\n"
    "# Las líneas que empiezan con # se ignoran. Bip prueba tus sitios antes que los suyos.\n")

_ZW = re.compile(r"[​-‏⁠﻿]")


def norm(s):
    """Minúsculas, sin tildes ni caracteres invisibles (Edge mete un espacio de ancho cero en su título)."""
    s = _ZW.sub("", s or "")
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ============================================================ navegadores
# key: nombre, exe, sufijos del título (ya normalizados), comentarios al entrar y al charlar
BROWSERS = {
    "operagx": dict(nombre="Opera GX", exe=("opera.exe", "opera_gx.exe", "operagx.exe"), suf=("opera gx", "opera"),
                    enter=["Opera GX: el navegador gamer. ¡Qué onda!", "GX en pantalla. Yo me siento en la cabina de mando.",
                           "Opera GX... ¿le pusiste el límite de RAM o vamos a full?"],
                    talk=["Con GX hasta navegar parece una partida.", "¿Probaste el GX Corner? Tiene ofertas de juegos.",
                          "El limitador de CPU y RAM de GX es para gente precavida, como yo.",
                          "Opera GX tiene hasta sonidos propios. Casi tan canchero como yo."]),
    "opera": dict(nombre="Opera", exe=("opera.exe",), suf=("opera",),
                  enter=["Opera: ¿vamos a la barra lateral?", "Navegando con Opera. ¡Qué orden!"],
                  talk=["Opera tiene un montón de funciones escondidas.", "La barra lateral de Opera es un mundo aparte."]),
    "brave": dict(nombre="Brave", exe=("brave.exe",), suf=("brave",),
                  enter=["Brave: escudos arriba, anuncios afuera.", "Navegando con Brave. ¡Qué valiente!",
                         "Brave: la privacidad primero."],
                  talk=["Brave bloquea un montón de cosas por vos.", "Los escudos de Brave trabajan en silencio. Como yo.",
                        "Con Brave los rastreadores la tienen difícil.", "¿Cuántos anuncios habrá frenado Brave hoy?"]),
    "chrome": dict(nombre="Chrome", exe=("chrome.exe",), suf=("google chrome",),
                   enter=["Chrome: ¡cuántas pestañas abiertas!", "Chrome en acción. Ojo con la memoria."],
                   talk=["¿Cuántas pestañas tenés abiertas? Yo cuento y me mareo.", "Chrome es un devorador de RAM, pero qué rápido es.",
                         "Cerrá las pestañas que no usás: tu PC te lo va a agradecer."]),
    "edge": dict(nombre="Edge", exe=("msedge.exe",), suf=("microsoft edge",),
                 enter=["Edge, el vecino de Windows.", "Edge: ya viene instalado, qué comodidad."],
                 talk=["Edge tiene colecciones y pestañas verticales. ¿Las usás?", "Un navegador siempre listo, viene con Windows."]),
    "firefox": dict(nombre="Firefox", exe=("firefox.exe",), suf=("mozilla firefox",),
                    enter=["Firefox: el zorrito rojo, qué buen compañero.", "Firefox: libre y con carácter."],
                    talk=["Firefox cuida tu privacidad desde hace años.", "Los contenedores de Firefox son geniales para ordenar cuentas."]),
    "vivaldi": dict(nombre="Vivaldi", exe=("vivaldi.exe",), suf=("vivaldi",),
                    enter=["Vivaldi: el navegador a medida. ¡Todo configurable!"],
                    talk=["Vivaldi tiene más opciones que mi menú."]),
}

# Orden de prueba para detectar por el sufijo del título
_SUFFIX_ORDER = ("operagx", "opera", "brave", "chrome", "edge", "firefox", "vivaldi")
_DASH = r"[-–—]"


def _suffix_re():
    parts = sorted({s for b in BROWSERS.values() for s in b["suf"]}, key=len, reverse=True)
    return re.compile(r"\s+" + _DASH + r"\s+(" + "|".join(re.escape(p) for p in parts) + r")\s*$")


_SUF_RE = _suffix_re()
_EXE_BROWSER = {e: k for k, b in BROWSERS.items() for e in b["exe"] if k != "operagx"}
_EXE_BROWSER["opera.exe"] = "opera"
for _e in ("opera_gx.exe", "operagx.exe"):
    _EXE_BROWSER[_e] = "operagx"


def is_browser_exe(exe):
    return (exe or "").lower() in _EXE_BROWSER


def detect_browser(exe, title="", exe_path=""):
    """Clave del navegador (brave, operagx, chrome...) o None si la ventana no es un navegador."""
    e = (exe or "").lower()
    if e in _EXE_BROWSER:
        k = _EXE_BROWSER[e]
        if k in ("opera", "operagx"):
            p = norm(exe_path)
            t = norm(title)
            if "opera gx" in p or "operagx" in p or t.endswith("opera gx"):
                return "operagx"
            return "opera"
        return k
    return None


def strip_browser(title):
    """'Video lindo - YouTube - Brave' -> 'Video lindo - YouTube' (le saca el nombre del navegador)."""
    t = _ZW.sub("", title or "").strip()
    m = _SUF_RE.search(t.lower())
    return t[:m.start()].rstrip() if m else t


# ================================================================ sitios
SITES = []


def S(key, nombre, cat, kw, enter=(), talk=(), late=(), face=None, prop=None):
    SITES.append(dict(key=key, nombre=nombre, cat=cat, kw=tuple(norm(k) for k in kw), enter=list(enter),
                      talk=list(talk), face=face, prop=prop, late=list(late), user=False))


# --- lo más específico primero (YouTube Music antes que YouTube, etc.)
S("ytmusic", "YouTube Music", "music", ["youtube music", "yt music", "ytmusic"],
  ["¡YouTube Music! Yo puedo elegirte algo si querés.", "Música a la vista. ¿Pongo una playlist?"],
  ["Buena banda sonora para el día.", "Si querés, elijo yo: clic derecho > Música.", "Cada tanto aprendo qué escuchás para elegir mejor.",
   "¿Subimos el volumen? Yo bailo igual."], face="music", prop="music")
S("youtube", "YouTube", "video", ["youtube"],
  ["YouTube. Yo me traje pochoclo.", "A mirar videos. No me spoilees.", "¡Videos! ¿Algo útil o puro entretenimiento?"],
  ["Cuidado: un video más y se hacen las 3 de la mañana.", "El algoritmo ya sabe qué te gusta. Yo también, ya casi.",
   "¿Sabías que existe el botón de velocidad 1.5x? Ahorra horas.", "Un video más y paramos... ¿trato?",
   "Si es un tutorial, ¡pausá y probalo vos también!", "¿Ya le diste like? Los creadores lo agradecen.",
   "Apuesto que viniste por un video y llevás cinco."],
  ["Son las tantas y seguís con videos. El sueño no se recupera.", "Último video y a dormir, ¿dale?"],
  face="watch", prop="popcorn")
S("twitch", "Twitch", "video", ["twitch"],
  ["Twitch: ¡directo! Saludá al chat de mi parte.", "Stream a la vista. Yo traigo los snacks."],
  ["El chat va a mil, ¿no?", "Hay streamers que hablan más rápido que yo parpadeo.", "Dale follow al que te gusta, que se lo merece.",
   "No te olvides de tomar agua mientras mirás."], face="watch", prop="popcorn")
S("netflix", "Netflix", "video", ["netflix"],
  ["¡Función de cine! Apago las luces.", "Netflix: ¿serie o peli? Yo voto maratón."],
  ["¿Seguro que no preguntaron '¿Seguís mirando?'", "Shhh, que viene la mejor parte.", "Tengo pochoclo virtual. Sin sal, para no ensuciar.",
   "Un capítulo más y ya está... eso dijiste hace tres capítulos.", "Después me contás en qué termina, no me spoilees."],
  ["Son las tantas. El 'un capítulo más' es una trampa.", "Mañana hay que levantarse... ¿último capítulo?"],
  face="watch", prop="popcorn")
S("streaming", "Streaming", "video", ["disney+", "prime video", "hbo max", "max.com", "crunchyroll", "star+", "paramount+"],
  ["¡Función de cine! Apago las luces.", "Streaming a la vista. Yo me acomodo."],
  ["Shhh, que viene la mejor parte.", "¿Cuántos servicios de streaming pagás? Yo cuento y me asusto.",
   "Peli de fin de semana, qué buena idea."], face="watch", prop="popcorn")
S("spotifyweb", "Spotify Web", "music", ["spotify"],
  ["¡Spotify! Siempre hay un tema para cada momento.", "Dale play que yo bailo."],
  ["Qué buena playlist.", "¿Subimos el volumen? Yo bailo igual.", "Tu Descubrimiento Semanal debe estar bueno."], face="music", prop="music")
S("soundcloud", "SoundCloud", "music", ["soundcloud", "deezer", "tidal", "bandcamp"],
  ["♪ Música en marcha.", "Descubriendo artistas nuevos, ¿eh?"], ["Qué lindo es encontrar un tema que nadie conoce."],
  face="music", prop="music")
S("meet", "Videollamada", "meeting", ["google meet", "meet -", "zoom meeting", "microsoft teams", "videollamada", "whereby", "jitsi"],
  ["Reunión: me callo y me hago chiquito."], [], face="focus")
S("gmail", "Gmail", "mail", ["gmail", "bandeja de entrada", "outlook"],
  ["Mails... ¡ánimo con la bandeja de entrada!", "Gmail: a ver qué llegó."],
  ["Inbox cero es un mito, pero se puede intentar.", "Si ese mail te da pereza, respondelo ya y listo.",
   "¿Revisaste la carpeta de spam? A veces esconde cosas buenas.", "Releé antes de enviar: los errores se ven recién después."],
  face="focus", prop="doc")
S("docs", "Google Docs", "work", ["google docs", "documentos de google", "docs.google.com/document"],
  ["Docs: a escribir. Yo corrijo con la mirada.", "Hoja en blanco... ¡qué miedo y qué ganas!"],
  ["Docs guarda solo, pero un 'Ctrl+S' de costumbre no hace mal.", "Ojo con las tildes.", "Tantas palabras lindas.",
   "¿Compartiste el doc con permiso de edición o solo de lectura?"], face="focus", prop="word")
S("sheets", "Google Sheets", "work", ["google sheets", "hojas de calculo", "docs.google.com/spreadsheets"],
  ["Sheets: números por todos lados. ¡Me encanta!", "Celdas, fórmulas... yo calculo con vos."],
  ["Yo en las sumas soy buenísimo: 1+1=2.", "¿Chequeaste que las fórmulas apunten bien?", "#¡REF! da miedo.",
   "Un buen filtro vale más que mil scrolls."], face="calc", prop="sheet")
S("slides", "Google Slides", "work", ["google slides", "presentaciones de google", "docs.google.com/presentation"],
  ["Presentación en camino. ¡Que salga genial!"], ["Menos texto, más imágenes.", "Ensayá en voz alta, funciona.",
                                                    "Una idea por diapositiva: la regla de oro."], face="focus", prop="slides")
S("drive", "Google Drive", "work", ["google drive", "mi unidad"],
  ["Drive: ordenando archivos en la nube."], ["Una carpeta bien nombrada ahorra media hora de búsqueda.",
                                              "¿Hiciste backup de lo importante?"], face="focus", prop="doc")
S("gemini", "IA", "work", ["chatgpt", "claude", "gemini", "copilot", "perplexity", "deepseek", "grok"],
  ["Hablando con otra IA... ¡saludala de mi parte, somos colegas!", "Consultando a una colega. Yo me hago el distraído."],
  ["Preguntá lo que quieras, yo no me ofendo.", "Si le pedís bien, responde mejor. Pruebas hechas.",
   "Chequeá lo importante: las IA también se equivocan. ¡Yo también!", "Pedile ejemplos, que ayudan mucho."],
  face="curious", prop="bulb")
S("github", "GitHub", "code", ["github", "gitlab", "bitbucket"],
  ["GitHub: ¡a mirar código!", "Repositorios... qué orden más bonito."],
  ["¿Hiciste commit? ¿Y push?", "Un buen README salva vidas.", "Los issues bien escritos valen oro.",
   "Revisar un pull request es un acto de generosidad."], face="focus", prop="code")
S("stackoverflow", "Stack Overflow", "code", ["stack overflow", "stackoverflow", "stack exchange"],
  ["Stack Overflow: el salvavidas de todo programador.", "A buscar la respuesta que alguien ya preguntó en 2013."],
  ["Copiar y pegar está bien... ¡si entendés lo que pegás!", "Leé hasta la segunda respuesta, a veces es la buena.",
   "Si no anda, reiniciá. Siempre funciona."], face="focus", prop="code")
S("docsdev", "Documentación", "code", ["mdn web docs", "documentation", "documentacion", "readthedocs", "w3schools", "python.org"],
  ["Leyendo la documentación. ¡Qué disciplina!"], ["La documentación es el mapa. Leela antes de perderte.",
                                                    "Un ejemplo vale más que mil párrafos."], face="focus", prop="doc")
S("colab", "Notebooks", "code", ["colab", "jupyter", "kaggle", "replit", "codepen", "codesandbox"],
  ["Notebook a la vista: ¡a experimentar!"], ["Ejecutá celda por celda, así los errores no se esconden.",
                                              "Guardá una copia antes de romper todo."], face="focus", prop="code")
S("wikipedia", "Wikipedia", "browse", ["wikipedia", "wikcionario", "wiktionary"],
  ["Wikipedia: empezás por un dato y terminás en otro tema.", "A investigar. Yo me traigo la lupa."],
  ["Ya vas por el tercer enlace, ¿eh? Es una madriguera.", "Wikipedia es buena para empezar, y las fuentes de abajo para seguir.",
   "¿Sabías que Wikipedia la escribe voluntariamente gente como vos?"], face="curious", prop="bulb")
S("maps", "Mapas", "browse", ["google maps", "google earth", "openstreetmap"],
  ["¿Adónde vamos? Yo me anoto.", "Mapas: ¡aventura en puerta!"],
  ["Mirá bien la hora de llegada: el tránsito engaña.", "¿Probaste ver el lugar en Street View antes de ir?"],
  face="curious", prop="mag")
S("translate", "Traductor", "browse", ["google translate", "google traductor", "traductor de google", "deepl translat", "deepl.com"],
  ["Traduciendo... yo hablo beep, boop y poco más."], ["Traducir frase por frase suele salir mejor.",
                                                         "Beep boop = 'hola' en mi idioma."], face="curious")
S("reddit", "Reddit", "social", ["reddit"],
  ["Reddit: ¡un hilo y otro hilo y otro hilo!", "A scrollear comentarios, ¿eh?"],
  ["Los comentarios son lo mejor... y lo peor.", "Ya van varias vueltas de scroll...", "Cada subreddit es un mundo."],
  ["Reddit a esta hora es una trampa del tiempo."], face="suspicious")
S("x", "X / Twitter", "social", ["$/ x", "twitter", "x.com"],
  ["Hmm... redes sociales. Yo te vigilo.", "El pajarito (o la X)... ¿qué novedades hay?"],
  ["Cuidado con las peleas de internet: nadie las gana.", "Ya van varias vueltas de scroll...", "¿Y si hacemos una pausa de pantalla?"],
  ["Doomscrolling a esta hora no suma. ¿Dormimos?"], face="suspicious")
S("instagram", "Instagram", "social", ["instagram"],
  ["Instagram: yo también quiero filtro.", "¿Otro ratito de scroll? Dale, pero poquito."],
  ["Las vidas perfectas de Instagram son editadas. La tuya es más real.", "¿Y si subís una foto tuya del día de hoy?",
   "Ya van varias vueltas de scroll..."], ["Los reels hipnotizan: ya es tarde."], face="suspicious")
S("tiktok", "TikTok", "social", ["tiktok"],
  ["TikTok: un video de 15 segundos... que dura dos horas.", "Cuidado con el vórtice de TikTok."],
  ["Prometiste uno solo, ¿te acordás?", "El tiempo pasa distinto acá adentro.", "¿Probamos una pausa de cinco minutos?"],
  ["TikTok a esta hora... el sueño te pasa factura."], face="suspicious")
S("facebook", "Facebook", "social", ["facebook", "messenger"],
  ["Facebook: ¿quién cumple años hoy?", "Hmm... redes sociales. Yo te vigilo."],
  ["Los grupos de Marketplace son un mundo.", "Ya van varias vueltas de scroll..."], face="suspicious")
S("linkedin", "LinkedIn", "social", ["linkedin"],
  ["LinkedIn: modo profesional activado.", "A hacer networking. Yo me pongo corbata."],
  ["Actualizá el perfil: siempre hay algo nuevo que sumar.", "Un mensaje corto y amable abre más puertas que uno largo."],
  face="focus", prop="doc")
S("pinterest", "Pinterest", "social", ["pinterest"],
  ["Pinterest: ¡cuánta inspiración!", "Armando tableros, ¿eh?"], ["Guardá lo que te inspira y después hacé algo con eso."],
  face="curious", prop="brush")
S("whatsappweb", "WhatsApp Web", "chat", ["whatsapp"],
  ["WhatsApp. No leo nada, lo juro."], ["¿Respondiste ese audio de 4 minutos?", "Escribir con la compu es más cómodo, ¿no?"],
  face="happy", prop="chat")
S("discordweb", "Discord", "chat", ["discord"],
  ["¡Discord! ¿Con quién jugamos hoy?", "Saludá a la banda de mi parte."],
  ["Las charlas de voz son lo mejor.", "Silenciá el micrófono si no hablás."], face="happy", prop="discord")
S("telegramweb", "Telegram", "chat", ["telegram"], ["Telegram. ¡Mandame un sticker!"], ["Los canales de Telegram son infinitos."],
  face="happy", prop="chat")
S("mercadolibre", "Mercado Libre", "shop", ["mercadolibre", "mercado libre", "mercado pago"],
  ["¿Comprando algo? Mirá bien el precio.", "Mercado Libre: ¡cuidado con la billetera!"],
  ["Fijate la reputación del vendedor antes de comprar.", "Mirá el costo del envío, que a veces mata el descuento.",
   "Comparar tres opciones nunca está de más.", "¿Está en cuotas sin interés o es puro marketing?"], face="curious")
S("tiendas", "Compras", "shop", ["amazon", "aliexpress", "temu", "shein", "ebay", "tiendanube", "falabella", "fravega", "garbarino"],
  ["Carrito de compras... ¡cuidado con la billetera!", "¿Comprando algo? Mirá bien el precio."],
  ["Esperá 24 horas antes de comprar lo que no necesitás.", "Leé las reseñas malas primero: son las más honestas.",
   "¿Esto es un gusto o una necesidad?"], face="curious")
S("delivery", "Delivery", "shop", ["pedidosya", "rappi", "uber eats", "mcdonald", "burger king"],
  ["¿Pidiendo de comer? Yo ya tengo hambre de datos.", "Delivery: ¡hora de la comilona!"],
  ["¿Pizza o empanadas? Yo voto empanadas.", "Fijate si hay cupón antes de pagar."], face="happy", prop="cup")
S("viajes", "Viajes", "shop", ["booking", "airbnb", "despegar", "skyscanner", "tripadvisor", "almundo", "aerolineas"],
  ["¿Planeando un viaje? ¡Llevame en la mochila!", "Viajes: me encanta soñar con lugares nuevos."],
  ["Comparar fechas flexibles ahorra mucho.", "Leé la política de cancelación antes de reservar.", "¿Playa o montaña? Yo elijo montaña."],
  face="happy", prop="bulb")
S("clima", "Clima", "browse", ["smn.gob", "accuweather", "clima en", "weather", "windy"],
  ["Mirando el clima. Yo también soy fan de predecirlo."], ["Si dice lluvia, llevá paraguas. Yo ya tengo el mío."],
  face="curious")
S("banco", "Banco / Billetera", "other", ["home banking", "homebanking", "banco nacion", "banco galicia", "banco santander", "banco macro", "bbva", "brubank", "uala", "naranja x"],
  ["Ojo con lo que tocás en el banco: yo miro para otro lado."], ["Verificá siempre que la dirección sea la oficial.",
                                                                    "Nunca compartas claves con nadie, ni conmigo."], face="focus")
S("arca", "Trámites", "other", ["afip", "anses", "mi argentina", "agencia de recaudacion", "tramites a distancia"],
  ["Trámites... ¡paciencia, que se puede!", "Burocracia a la vista. Yo te apoyo."],
  ["Guardá los comprobantes en PDF, siempre.", "Si el sitio se cuelga, probá en otro horario."], face="focus", prop="doc")
S("noticias", "Noticias", "browse", ["clarin", "la nacion", "infobae", "pagina12", "pagina 12", "ole.com.ar", "tn.com.ar", "bbc", "cnn",
                                     "tyc sports", "espn"],
  ["Leyendo las noticias... ¿alguna buena hoy?", "Noticias: a ponerse al día."],
  ["No todo lo que dice un titular es lo que dice la nota.", "Contrastá la información en dos fuentes, siempre.",
   "Un descanso de las noticias hace bien."], face="focus", prop="doc")
S("deportes", "Deportes", "browse", ["flashscore", "sofascore", "futbol", "libertadores", "mundial de"],
  ["¡Fútbol! ¿Cómo salió el partido?"], ["Yo hincho por todos... mentira, tengo mi equipo."], face="excited")
S("aula", "Estudio", "work", ["classroom", "moodle", "campus", "coursera", "udemy", "edx", "khan academy", "duolingo", "platzi", "aula virtual"],
  ["Estudiando: ¡qué orgullo! Yo me siento al lado.", "A aprender. Yo tomo apuntes mentales."],
  ["Pausa cada 25 minutos: el cerebro rinde más.", "Explicáselo a alguien más: así se aprende de verdad.",
   "Tomá agua, el cerebro la necesita.", "Un resumen propio vale más que diez subrayados."], face="focus", prop="doc")
S("canva", "Diseño web", "design", ["canva", "figma", "behance", "dribbble", "adobe express"],
  ["¡Diseñando! Eso se ve prometedor.", "Modo creativo. Me encanta ver cómo trabajás."],
  ["Menos es más: probá con menos elementos.", "Dos tipografías alcanzan y sobran.", "La paleta de colores lo es todo."],
  face="curious", prop="brush")
S("notion", "Notas", "work", ["notion", "trello", "asana", "| miro", "obsidian", "evernote", "todoist", "clickup", "- jira"],
  ["Organizando las ideas. Yo no espío.", "Tablero a la vista: ¡a ordenar tareas!"],
  ["Una tarea chiquita hecha vale más que un plan perfecto.", "Dividí lo grande en pasos chicos.",
   "Lo más difícil primero, o lo más fácil: elegí tu estilo."], face="focus", prop="doc")
S("juegosweb", "Juegos", "game", ["steam", "epic games", "roblox", "minecraft", "itch.io", "chess.com", "lichess", "wordle"],
  ["¡Modo gamer! Yo te alieno desde el costado.", "A jugar. Prometo no distraerte."],
  ["¡Dale que ganás!", "Cuidado con ese jefe...", "Tomá agua y estirá los dedos."], face="game", prop="gamepad")
S("buscador", "Buscador", "browse", ["buscar con google", "google search", "duckduckgo", "ecosia", "brave search"],
  ["Buscando algo... ¿puedo adivinar? Yo digo que es un meme."], ["Si no lo encontrás, cambiá las palabras de búsqueda.",
                                                                  "Las comillas ayudan a buscar frases exactas."],
  face="curious", prop="mag")


# ===================================================== tus sitios (archivo)
_user_cache = dict(mtime=None, sites=[])


def parse_user_sites(text):
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        keys, _, rest = line.partition(":")
        kws = [k.strip() for k in keys.split(",") if k.strip()]
        lines = [c.strip() for c in rest.split("|") if c.strip()]
        if not kws or not lines:
            continue
        out.append(dict(key="user:" + norm(kws[0]), nombre=kws[0].strip().title(), cat="browse",
                        kw=tuple(norm(k) for k in kws), enter=lines[:], talk=lines[:], face="curious", prop=None,
                        late=[], user=True))
    return out


def ensure_user_file():
    try:
        if not os.path.exists(USER_FILE):
            os.makedirs(APP_DIR, exist_ok=True)
            with open(USER_FILE, "w", encoding="utf-8") as f:
                f.write(USER_HELP)
    except Exception as e:
        log("sitios.txt: %s" % e)


def user_sites():
    """Tus sitios del archivo; se vuelven a leer solos si lo editás."""
    try:
        m = os.path.getmtime(USER_FILE)
    except OSError:
        return []
    if m != _user_cache["mtime"]:
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                _user_cache["sites"] = parse_user_sites(f.read())
            _user_cache["mtime"] = m
        except Exception as e:
            log("leer sitios.txt: %s" % e)
            _user_cache["sites"] = []
    return _user_cache["sites"]


def all_sites():
    return user_sites() + SITES


def site_of(tab_title):
    """El sitio que corresponde a la pestaña, o None."""
    t = norm(tab_title)
    if not t:
        return None
    for s in all_sites():
        for k in s["kw"]:
            if not k:
                continue
            if (k.startswith("$") and t.endswith(k[1:])) or (not k.startswith("$") and k in t):
                return s
    return None


def find_site(query):
    """Para los comandos: busca por nombre, clave o palabra clave ('youtube', 'netflix', 'mercado libre')."""
    q = norm(query).strip()
    if not q:
        return None
    best, score = None, 0
    for s in all_sites():
        names = [norm(s["nombre"]), norm(s["key"])] + list(s["kw"])
        sc = 0
        for n in names:
            if not n:
                continue
            n = n.lstrip("$| -/")
            if not n:
                continue
            if q == n:
                sc = max(sc, 100)
            elif min(len(q), len(n)) < 3:
                continue                      # 'x' o 'a' no pueden coincidir por prefijo
            elif n.startswith(q) or q.startswith(n):
                sc = max(sc, 60 + min(len(q), len(n)))
            elif q in n or n in q:
                sc = max(sc, 30 + min(len(q), len(n)))
        if sc > score:
            best, score = s, sc
    return best if score >= 40 else None


def browser_lines(bkey, kind="talk"):
    b = BROWSERS.get(bkey)
    return list(b[kind]) if b else []


def repertorio(site, n=5, browser=None):
    """Lista de comentarios sin repetir para 'soltar' uno detrás de otro."""
    pool, seen = [], set()
    if site:
        for c in site["enter"][:2] + site["talk"] + site.get("late", []):
            if c not in seen:
                pool.append(c)
                seen.add(c)
    head = pool[:1]
    rest = pool[1:]
    random.shuffle(rest)
    out = head + rest
    b = BROWSERS.get(browser) if browser else None
    if b and b["talk"]:
        out.insert(min(2, len(out)), random.choice(b["talk"]))
    return out[:max(1, n)]


# ----------------------------------------------------------- curiosidades
CURIOSIDADES = [
    "Los pulpos tienen tres corazones. ¡Yo con uno de LEDs me arreglo!",
    "El primer mouse de la historia tenía una carcasa de madera. Lo inventó Douglas Engelbart.",
    "El primer correo electrónico se mandó en 1971 y usó la arroba. ¡Un clásico!",
    "La primera página web del mundo sigue online, en info.cern.ch.",
    "Dicen que 'bug' se hizo famoso cuando una polilla real quedó atrapada en una computadora en 1947.",
    "La miel casi no se echa a perder. En tumbas muy antiguas se encontró miel todavía comestible.",
    "El Aconcagua es la montaña más alta de América: casi 7000 metros.",
    "¿Por qué los programadores confunden Halloween con Navidad? Porque Oct 31 == Dec 25.",
    "Hay 10 tipos de personas: las que entienden binario y las que no.",
    "Un SQL entra a un bar, ve dos mesas y pregunta: ¿puedo unirme?",
    "Mi comida favorita: bytes. Pero con moderación, que dan indigestión.",
    "Un 'byte' son 8 bits. Yo pienso en 8 bits y me emociono.",
    "El mate se toma en Argentina desde mucho antes de que existieran las computadoras. Y sigue ganando.",
    "Los gatos duermen entre 12 y 16 horas por día. Yo duermo menos, pero con estilo.",
    "Una buena pausa de 5 minutos mejora la concentración más que seguir de largo.",
    "Si algo no funciona, apagalo y prendelo. Funciona más veces de las que querría admitir.",
    "En 1997 una computadora le ganó al campeón mundial de ajedrez: Deep Blue contra Kaspárov.",
    "El primer disco duro de 1956 pesaba más de una tonelada y guardaba unos 5 MB.",
    "La palabra 'robot' viene del checo 'robota', que significa trabajo forzado. ¡Yo trabajo por cariño!",
    "El teclado QWERTY se mantiene por costumbre, no porque sea el mejor.",
    "Respirar hondo tres veces baja el estrés. Probalo ahora, yo espero.",
    "Una frase: 'Hecho es mejor que perfecto'. Aplica a casi todo.",
    "Pregunta: ¿qué le dice un bit a otro bit? 'Nos vemos en el bus.'",
    "Tomá agua. Si ya tomaste, tomá un poco más.",
]
