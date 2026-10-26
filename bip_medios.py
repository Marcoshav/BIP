# -*- coding: utf-8 -*-
"""Lee qué está sonando (título, artista, portada, estado) desde los controles multimedia de Windows
(los mismos de la barra de volumen) y permite controlarlo. Funciona con YouTube Music en Brave/Opera/
Chrome/Edge/Firefox, Spotify, etc. Si falta el paquete 'winrt', Bip usa el título de la ventana."""
import asyncio
import threading
import time

from bip_sistema import IS_WIN, log

AVAILABLE = False
_err = ""
if IS_WIN:
    try:
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as _Manager
        from winrt.windows.storage.streams import Buffer, InputStreamOptions, DataReader
        AVAILABLE = True
    except Exception as e:  # paquete no instalado
        _err = str(e)
        log("medios: sin winrt (%s)" % e)


class MediaWatcher:
    def __init__(self):
        self.available = AVAILABLE
        self.state = None          # dict con la sesión elegida, o None
        self._cmds = []
        self._run = False
        self._sess = None
        self._thumbs = {}
        self._thumb_tries = {}

    def start(self):
        if not self.available:
            return
        self._run = True
        threading.Thread(target=self._thread, daemon=True).start()

    def stop(self):
        self._run = False

    def command(self, name):
        """name: playpause | next | prev. Devuelve True si se pudo encolar."""
        if not self.available or self.state is None:
            return False
        self._cmds.append(name)
        return True

    # ------------------------------------------------------------ hilo
    def _thread(self):
        try:
            asyncio.run(self._main())
        except Exception:
            import traceback
            log("medios hilo: " + traceback.format_exc())
            self.state = None

    async def _main(self):
        mgr = await _Manager.request_async()
        last = 0.0
        while self._run:
            try:
                if self._cmds:
                    await self._do(self._cmds.pop(0))
                    last = 0.0
                    await asyncio.sleep(0.25)
                if time.monotonic() - last >= 1.0:
                    last = time.monotonic()
                    await self._refresh(mgr)
            except Exception as e:
                log("medios ciclo: %s" % e)
            await asyncio.sleep(0.15)

    def seek(self, secs):
        """Salta a `secs` segundos desde el inicio de la canción."""
        if not self.available or self.state is None:
            return False
        self._cmds.append(("seek", float(secs)))
        return True

    async def _do(self, cmd):
        s = self._sess
        if s is None:
            return
        try:
            if isinstance(cmd, tuple):
                start = (self.state or {}).get("start", 0.0)
                ticks = int(round((start + cmd[1]) * 10_000_000))     # unidades de 100 ns
                ok = await s.try_change_playback_position_async(ticks)
                if not ok:
                    log("medios: el reproductor rechazó el salto")
            elif cmd == "playpause":
                await s.try_toggle_play_pause_async()
            elif cmd == "next":
                await s.try_skip_next_async()
            elif cmd == "prev":
                await s.try_skip_previous_async()
        except Exception as e:
            log("medios cmd %s: %s" % (cmd, e))

    @staticmethod
    def _playing(sess):
        try:
            return int(sess.get_playback_info().playback_status) == 4     # 4 = Playing, 5 = Paused
        except Exception:
            return False

    def _choose(self, mgr):
        sessions = []
        try:
            sessions = [s for s in mgr.get_sessions()]
        except Exception:
            pass
        cur = None
        try:
            cur = mgr.get_current_session()
        except Exception:
            pass
        if not sessions and cur is not None:
            sessions = [cur]
        playing = [s for s in sessions if self._playing(s)]
        if cur is not None and cur in playing:
            return cur
        if playing:
            return playing[0]
        return cur or (sessions[0] if sessions else None)

    async def _refresh(self, mgr):
        s = self._choose(mgr)
        self._sess = s
        if s is None:
            self.state = None
            return
        info = await s.try_get_media_properties_async()
        title, artist, album = (info.title or ""), (info.artist or ""), (info.album_title or "")
        if not title:
            self.state = None
            return
        key = "%s|%s|%s" % (title, artist, album)
        pos = dur = start = 0.0
        try:
            tl = s.get_timeline_properties()
            start = tl.start_time.total_seconds()
            pos = tl.position.total_seconds() - start
            dur = (tl.end_time - tl.start_time).total_seconds()
        except Exception:
            pass
        can_next = can_prev = True
        can_seek = True
        try:
            c = s.get_playback_info().controls
            can_next, can_prev = bool(c.is_next_enabled), bool(c.is_previous_enabled)
            can_seek = bool(c.is_playback_position_enabled)
        except Exception:
            pass
        thumb = self._thumbs.get(key)
        if thumb is None and self._thumb_tries.get(key, 0) < 4 and info.thumbnail is not None:
            self._thumb_tries[key] = self._thumb_tries.get(key, 0) + 1
            thumb = await self._read_thumb(info.thumbnail)
            if thumb:
                self._thumbs[key] = thumb
                if len(self._thumbs) > 12:
                    self._thumbs.pop(next(iter(self._thumbs)))
        try:
            app = s.source_app_user_model_id or ""
        except Exception:
            app = ""
        self.state = dict(app=app, title=title, artist=artist, album=album, key=key, playing=self._playing(s),
                          pos=pos, dur=dur, start=start, stamp=time.monotonic(), thumb=thumb, can_next=can_next,
                          can_prev=can_prev, can_seek=can_seek)

    async def _read_thumb(self, ref):
        try:
            stream = await ref.open_read_async()
            size = int(stream.size)
            if size <= 0 or size > 8_000_000:
                return None
            buf = Buffer(size)
            res = await stream.read_async(buf, size, InputStreamOptions.READ_AHEAD)
            try:
                return bytes(memoryview(res))
            except Exception:
                reader = DataReader.from_buffer(res)
                data = bytearray(res.length)
                reader.read_bytes(data)
                return bytes(data)
        except Exception as e:
            log("medios portada: %s" % e)
            return None
