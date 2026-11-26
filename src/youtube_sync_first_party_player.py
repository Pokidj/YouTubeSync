"""YouTube's top-level player in the dedicated session, controlled over a private pipe."""

import json
import re
import time
from urllib.parse import urlencode, urlsplit

from PySide6.QtCore import QObject, QTimer, Signal

from youtube_sync_browser_pipe import connections_for
from youtube_sync_manual import youtube_video_id
from youtube_sync_player_controls import command, telemetry, player_operation


def owned_target(targets, bootstrap):
    if not isinstance(targets, list):
        return None
    matches = [item for item in targets if isinstance(item, dict) and item.get("type") == "page"
               and item.get("url") == bootstrap and re.fullmatch(r"[A-Za-z0-9_-]{1,200}", str(item.get("targetId", "")))]
    return matches[0]["targetId"] if len(matches) == 1 else None


def media_expression(video_id, action=None, value=None, captions=None):
    video_id = youtube_video_id(video_id)
    operation = ""
    if action is not None:
        operation = player_operation(action, value) + ";"
    if captions is not None and action != "captions":
        operation += "try{" + player_operation("captions", bool(captions)) + ";}catch(e){}"
    return """(()=>{
      if(location.origin!=='https://www.youtube.com'||location.pathname!==%s)return {valid:false};
      const p=document.querySelector('#movie_player');
      const actual=p?.getVideoData?.()?.video_id;
      if(actual&&actual!==%s)return {valid:false};
      if(p&&(p.classList.contains('ad-showing')||p.classList.contains('ad-interrupting')))
        return {valid:true,media:false,advertising:true};
      const error=document.querySelector('.ytp-error-content-wrap');
      if(error&&error.getClientRects().length&&getComputedStyle(error).visibility!=='hidden'&&error.textContent.trim())
        return {valid:true,media:false,error:error.textContent.slice(0,400)};
      const v=document.querySelector('video');
      if(!v||v.readyState===0||!p||typeof p.seekTo!=='function'||typeof p.getPlayerState!=='function')
        return {valid:true,media:false,error:''};
      %s
      const duration=p.getDuration();
      return {valid:true,media:true,position:Math.max(0,p.getCurrentTime()||0),
        duration:Number.isFinite(duration)?Math.max(0,duration):0,volume:p.getVolume(),
        muted:p.isMuted(),playing:p.getPlayerState()===1&&v.readyState>=2};
    })()""" % (json.dumps("/embed/" + video_id), json.dumps(video_id), operation)


class FirstPartyPlayer(QObject):
    status = Signal(str)
    failed = Signal(str)
    telemetry = Signal(object)
    available = Signal(bool)

    def __init__(self, profile, bootstrap, video_id, muted=False, parent=None):
        super().__init__(parent)
        self.profile, self.bootstrap = profile, bootstrap
        self.video_id = youtube_video_id(video_id)
        self.muted = muted
        self.custom_controls = False
        self.captions = None
        self.closed = self.connected = self.connecting = self.ready = False
        self.pipe = None
        self.session_id = ""
        self.started = time.monotonic()
        self.next_id = 0
        self.pending = {}
        self.discovering = set()
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.tick)

    def start(self):
        self.status.emit("Abriendo YouTube con la sesión de reproducción…")
        self.timer.start()
        self.tick()

    def tick(self):
        if self.closed:
            return
        if self.connected:
            if not self.pipe.alive():
                self.on_disconnected()
                return
            if "poll" not in self.pending.values():
                self.send("Runtime.evaluate", {"expression": media_expression(self.video_id, captions=self.captions), "returnByValue": True}, "poll")
            if not self.ready and time.monotonic() - self.started > 65:
                self.abort("YouTube no permite reproducir este vídeo con esta sesión. Revisa la cuenta en Ajustes > Reproducción.")
            return
        if time.monotonic() - self.started > 25:
            self.abort("Cierra las ventanas de la sesión de reproducción y vuelve a abrirla desde Ajustes > Reproducción. No cierres tu navegador habitual.")
            return
        if self.connecting:
            return
        for pipe in connections_for(self.profile):
            if pipe in self.discovering:
                continue
            self.discovering.add(pipe)
            if not pipe.request("Target.getTargets", {}, lambda data, pipe=pipe: self.targets_finished(pipe, data)):
                self.discovering.discard(pipe)

    def targets_finished(self, pipe, data):
        self.discovering.discard(pipe)
        if self.closed or self.connecting or self.connected:
            return
        result = data.get("result") if isinstance(data, dict) else None
        target = owned_target(result.get("targetInfos"), self.bootstrap) if isinstance(result, dict) else None
        if not target:
            return
        self.connecting = True
        if not pipe.request("Target.attachToTarget", {"targetId": target, "flatten": True},
                            lambda answer: self.attached(pipe, answer)):
            self.connecting = False

    def attached(self, pipe, data):
        result = data.get("result") if isinstance(data, dict) else None
        session_id = result.get("sessionId", "") if isinstance(result, dict) else ""
        if self.closed:
            if session_id:
                pipe.request("Target.detachFromTarget", {"sessionId": session_id}, lambda _: None)
            return
        self.connecting = False
        if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", session_id):
            return
        self.pipe, self.session_id = pipe, session_id
        self.connected = True
        query = urlencode({"autoplay": 1, "playsinline": 1, "controls": 0 if self.custom_controls else 1, "fs": 1, "mute": int(self.muted),
                           "enablejsapi": 1, "origin": "https://www.youtube.com"})
        origin = urlsplit(self.bootstrap)
        self.send("Page.navigate", {"url": f"https://www.youtube.com/embed/{self.video_id}?{query}",
                                    "referrer": f"{origin.scheme}://{origin.netloc}/"}, "navigate")

    def send(self, method, params, kind):
        if self.closed or not self.connected or len(self.pending) >= 12:
            return False
        self.next_id += 1
        request_id = self.next_id
        self.pending[request_id] = kind
        def received(data):
            self.on_message(dict(data, id=request_id))
        if not self.pipe.request(method, params, received, self.session_id):
            self.pending.pop(request_id, None)
            return False
        return True

    def on_message(self, message):
        if self.closed:
            return
        try:
            data = json.loads(message) if isinstance(message, str) else message
            if not isinstance(data, dict):
                return
            kind = self.pending.pop(data.get("id"), "")
            if not kind:
                return
            if "error" in data:
                if kind == "navigate":
                    self.abort("No se pudo abrir el vídeo en la sesión de YouTube.")
                return
            result = data.get("result")
            if not isinstance(result, dict):
                return
            if kind == "navigate":
                if result.get("errorText"):
                    self.abort("No se pudo cargar YouTube. Comprueba la conexión y reintenta.")
                return
            evaluation = result.get("result")
            value = evaluation.get("value") if isinstance(evaluation, dict) else None
            if not isinstance(value, dict):
                return
            if not value.get("valid"):
                if self.ready:
                    self.abort("El reproductor ha salido del vídeo seleccionado. Vuelve a cargarlo.")
                return
            if not value.get("media"):
                self.available.emit(False)
                if value.get("advertising"):
                    self.started = time.monotonic()
                if value.get("error"):
                    self.abort("YouTube no da acceso a este vídeo. Inicia sesión con una cuenta autorizada en Ajustes > Reproducción.")
                return
            state = telemetry(value)
            self.ready = True
            self.available.emit(True)
            self.telemetry.emit(state)
        except (ValueError, KeyError, TypeError):
            pass

    def control(self, action, value=None):
        command(action, value)
        accepted = self.ready and self.send("Runtime.evaluate", {"expression": media_expression(self.video_id, action, value),
                                                             "returnByValue": True, "userGesture": True}, "command")
        if accepted and action == "captions":
            self.captions = value
        return accepted

    def on_disconnected(self):
        if not self.closed:
            self.abort("Se ha cerrado la sesión del reproductor. Vuelve a cargar el vídeo.")

    def abort(self, message):
        if not self.closed:
            self.release()
            self.failed.emit(message)

    def release(self):
        if self.closed:
            return
        if self.connected and self.pipe.alive():
            if self.ready:
                self.control("pause")
                self.control("mute", True)
            self.pipe.request("Target.detachFromTarget", {"sessionId": self.session_id}, lambda _: None)
        self.closed = True
        self.available.emit(False)
        self.timer.stop()
        self.pending.clear()
