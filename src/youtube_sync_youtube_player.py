"""Isolated official YouTube iframe; no OAuth tokens or native bridge exposed."""

import json
from html import escape
import re
from string import Template
import sys
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QProcess, QTimer, QUrl, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from youtube_sync_manual import youtube_video_id
from youtube_sync_version import APP_ID

PLAYER_ORIGIN = f"https://{APP_ID.lower()}"
EVENT_PREFIX = "YouTubeSyncPlayer:"


def player_html(video_id: str, origin=PLAYER_ORIGIN, title="YouTubeSync", event_route=None, control_route=None, muted=False) -> str:
    video_id = youtube_video_id(video_id)
    url = urlsplit(origin)
    if origin != PLAYER_ORIGIN and not (url.scheme == "http" and url.hostname == "127.0.0.1" and url.port
                                       and not url.username and not url.password and not url.path and not url.query and not url.fragment):
        raise ValueError("Origen de reproducción no permitido")
    for route in (event_route, control_route):
        if route is not None and not re.fullmatch(r"/[A-Za-z0-9_-]+/(event|control)", route):
            raise ValueError("Ruta de reproducción no permitida")
    options = json.dumps({"videoId": video_id, "width": "100%", "height": "100%",
                          "playerVars": {"autoplay": 0 if control_route else 1, "playsinline": 1, "controls": 1,
                                         "origin": origin, "widget_referrer": origin}})
    return Template("""<!doctype html><html><head><meta charset="utf-8"><title>$title</title>
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body,#player{width:100%;height:100%;margin:0;background:#09090b;overflow:hidden}iframe{border:0}</style>
</head><body><div id="player"></div><script>
const id=$video_id, endpoint=$event_route, control=$control_route;
function report(type,value){
 const data={id:id,type:type,value:value};
 console.info($prefix+JSON.stringify(data));
 if(endpoint)fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).catch(()=>{});
}
let stopped=false, playerReady=false, startRequested=false;
function stopPlayback(){
 if(stopped)return;stopped=true;
 try{window.player.mute();window.player.stopVideo();}catch(e){}
 const frame=document.getElementById('player');if(frame&&frame.tagName==='IFRAME')frame.src='about:blank';
}
if(control)setInterval(()=>fetch(control,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();})
 .then(data=>{if(data.stop)stopPlayback();
 else if(data.play&&playerReady&&!startRequested){startRequested=true;window.player.playVideo();}}).catch(stopPlayback),250);
window.addEventListener('pagehide',stopPlayback);
window.onYouTubeIframeAPIReady=function(){
 const options=$options;
 options.events={onReady:e=>{playerReady=true;if($muted)e.target.mute();report('ready',0);},
 onStateChange:e=>report('state',e.data),onError:e=>report('error',e.data),
 onAutoplayBlocked:()=>report('autoplay',0)};
 window.player=new YT.Player('player',options);
};
</script><script src="https://www.youtube.com/iframe_api"></script></body></html>""").substitute(
        title=escape(title), video_id=json.dumps(video_id), prefix=json.dumps(EVENT_PREFIX), options=options,
        event_route=json.dumps(event_route), control_route=json.dumps(control_route), muted=json.dumps(bool(muted)))


def playback_error(code: int) -> str:
    if code == 100:
        return "YouTube no permite acceder al vídeo: puede ser privado, estar eliminado o no estar disponible. Revísalo en el navegador con tu cuenta."
    if code in {101, 150}:
        return "El propietario no permite reproducir este vídeo dentro de otras aplicaciones. Ábrelo en el navegador."
    if code in {152, 153}:
        return f"YouTube ha rechazado el reproductor integrado (error {code}). Puedes comparar el vídeo en el navegador."
    if code == 5:
        return "No se puede reproducir el formato de este vídeo aquí. Puedes verlo en el navegador."
    return f"YouTube no ha podido reproducir este vídeo (error {code}). Reintenta o ábrelo en el navegador."


class EmbeddedYouTubePlayer(QWidget):
    status = Signal(str)
    reviewed = Signal(str)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.view = None
        self.native = None
        self.native_base = None
        self.prefer_native = True
        self.profile = None
        self.probe = None
        self.muted = False
        self.video_id = ""
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timed_out)

    def load_video(self, video_id: str):
        video_id = youtube_video_id(video_id)
        self.release()
        self.video_id = video_id
        from youtube_sync_browser_session import find_browser
        if self.prefer_native and find_browser():
            from youtube_sync_browser_player import NativeBrowserPlayer
            base = self.native_base
            parent = self.parentWidget()
            while base is None and parent is not None:
                if hasattr(parent, "store"):
                    base = parent.store.base
                parent = parent.parentWidget()
            if base is None:
                import youtube_sync_engine as engine
                base = engine.app_dir()
            self.native = NativeBrowserPlayer(base, self)
            self.native.muted = self.muted
            self.native.status.connect(self.status)
            self.native.reviewed.connect(self.reviewed)
            self.native.failed.connect(self.failed)
            self.layout.addWidget(self.native)
            self.native.load_video(video_id)
            return
        # Chromium initialization can fail natively; check it outside the app first.
        self.probe = QProcess(self)
        probe = self.probe
        probe.finished.connect(lambda code, status: self.probe_finished(probe, code, status))
        probe.errorOccurred.connect(lambda _: self.probe_failed(probe))
        arguments = [] if getattr(sys, "frozen", False) else [str(Path(__file__).with_name("youtube_sync_app.py"))]
        self.status.emit("Preparando reproductor de YouTube…")
        probe.start(sys.executable, arguments + ["--probe-youtube-engine"])
        self.timer.start(15000)

    def probe_failed(self, probe):
        if probe is self.probe:
            self.timer.stop()
            self.probe = None
            probe.deleteLater()
            message = "No se puede iniciar el reproductor integrado en este equipo. Puedes comparar el vídeo en el navegador."
            self.status.emit(message)
            self.failed.emit(message)

    def probe_finished(self, probe, code, status):
        if probe is not self.probe:
            return
        if code != 0 or status != QProcess.NormalExit:
            self.probe_failed(probe)
            return
        self.probe = None
        probe.deleteLater()
        self.start_view()

    def start_view(self):
        if not self.video_id:
            return
        try:
            from youtube_sync_youtube_webview import create_webview
            self.view, self.profile = create_webview(self, self.player_event, self.renderer_failed, self.muted)
        except (ImportError, RuntimeError, OSError):
            self.timer.stop()
            message = "Faltan componentes del reproductor integrado. Reintenta o abre el vídeo en el navegador."
            self.status.emit(message)
            self.failed.emit(message)
            return
        self.layout.addWidget(self.view)
        self.status.emit("Cargando vídeo de YouTube…")
        self.view.show()
        self.view.setHtml(player_html(self.video_id), QUrl(PLAYER_ORIGIN + "/"))
        self.timer.start(30000)

    def renderer_failed(self, view):
        if view is self.view:
            self.timed_out()

    def player_event(self, video_id, event, value):
        if not self.view or video_id != self.video_id:
            return
        if event == "ready":
            self.timer.stop()
            self.status.emit("Pulsa reproducir para comparar el vídeo de YouTube.")
        elif event == "state" and value == 1:
            self.timer.stop()
            self.status.emit("Reproduciendo vídeo de YouTube")
            self.reviewed.emit(video_id)
        elif event == "state" and value in {0, 2}:
            self.status.emit("Vídeo de YouTube finalizado" if value == 0 else "Reproducción de YouTube pausada")
        elif event == "error":
            self.timer.stop()
            message = playback_error(value)
            self.status.emit(message)
            self.failed.emit(message)
        elif event == "autoplay":
            self.status.emit("Pulsa reproducir en el vídeo para iniciar la comparación.")

    def timed_out(self):
        if not self.view and not self.probe:
            return
        if self.probe is not None:
            self.release()
        message = "YouTube no ha respondido. Reintenta la carga o usa el navegador para comparar."
        self.status.emit(message)
        self.failed.emit(message)

    def release(self):
        self.timer.stop()
        self.video_id = ""
        if self.native is not None:
            native, self.native = self.native, None
            native.release()
            native.hide()
            self.layout.removeWidget(native)
            native.deleteLater()
        if self.probe is not None:
            probe, self.probe = self.probe, None
            probe.kill()
            probe.waitForFinished(1000)
            probe.deleteLater()
        if self.view is not None:
            view, self.view = self.view, None
            profile, self.profile = self.profile, None
            view.page().setAudioMuted(True)
            view.stop()
            view.setUrl(QUrl("about:blank"))
            view.hide()
            self.layout.removeWidget(view)
            # The profile must outlive its page, including deferred deletion.
            view.page().deleteLater()
            if profile is not None:
                profile.deleteLater()
            view.deleteLater()
