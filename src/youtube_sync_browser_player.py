"""Real-browser hosting with a token-protected, loopback-only player document."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import queue
import secrets
import socketserver
import threading
import time

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from youtube_sync_browser_session import BrowserWindow, start_browser, find_browser, playback_profile
from youtube_sync_manual import youtube_video_id
from youtube_sync_player_controls import command, telemetry


class LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = "127.0.0.1", self.server_address[1]


class PlayerDocument:
    def __init__(self, video_id: str, muted=False, custom_controls=False, captions_off=False):
        from youtube_sync_youtube_player import player_html
        self.video_id = youtube_video_id(video_id)
        self.token = secrets.token_urlsafe(24)
        self.title = "YouTubeSync-" + secrets.token_hex(16)
        self.events = queue.Queue(maxsize=100)
        self.commands = queue.Queue(maxsize=32)
        self.stopping = threading.Event()
        self.attached = threading.Event()
        self.closed = False
        owner = self
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def reply(self, status, data=b"", kind="application/json"):
                self.send_response(status)
                self.send_header("Content-Type", kind + "; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
                self.send_header("Content-Security-Policy", "frame-ancestors 'none'; object-src 'none'")
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def allowed(self):
                return self.headers.get("Host") == owner.host

            def do_GET(self):
                if not self.allowed():
                    self.reply(403)
                elif self.path == owner.route:
                    self.reply(200, owner.html, "text/html")
                elif self.path == owner.route + "/control":
                    commands = []
                    while not owner.commands.empty():
                        try:
                            commands.append(owner.commands.get_nowait())
                        except queue.Empty:
                            break
                    self.reply(200, json.dumps({"stop": owner.stopping.is_set(), "play": owner.attached.is_set(), "commands": commands}).encode())
                else:
                    self.reply(404)

            def do_POST(self):
                if not self.allowed() or self.headers.get("Origin") != owner.origin or self.path != owner.route + "/event":
                    self.close_connection = True
                    self.reply(403)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 1024:
                        raise ValueError("Invalid size")
                    event = json.loads(self.rfile.read(length))
                    progress = event.get("type") == "progress"
                    if (event.get("id") != owner.video_id or event.get("type") not in {"ready", "state", "error", "autoplay", "progress"}
                            or (not progress and type(event.get("value")) is not int)):
                        raise ValueError("Invalid event")
                    if progress:
                        event["value"] = telemetry(event["value"])
                    if not owner.stopping.is_set():
                        try:
                            owner.events.put_nowait(event)
                        except queue.Full:
                            pass
                    self.reply(204)
                except (ValueError, TypeError, AttributeError):
                    self.close_connection = True
                    self.reply(400)
        self.server = LoopbackServer(("127.0.0.1", 0), Handler)
        self.host = f"127.0.0.1:{self.server.server_port}"
        self.origin = "http://" + self.host
        self.route = "/" + self.token
        self.url = self.origin + self.route
        self.html = player_html(self.video_id, origin=self.origin, title=self.title,
                                event_route=self.route + "/event", control_route=self.route + "/control", muted=muted,
                                custom_controls=custom_controls, captions_off=captions_off).encode("utf-8")
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.05), daemon=True)
        self.thread.start()

    def control(self, action, value=None):
        data = command(action, value)
        if self.closed:
            return False
        try:
            self.commands.put_nowait(data)
            return True
        except queue.Full:
            return False

    def close(self, grace=0.6):
        if self.closed:
            return
        self.closed = True
        self.stopping.set()
        def shutdown():
            self.server.shutdown()
            self.server.server_close()
        timer = threading.Timer(grace, shutdown)
        timer.daemon = True
        timer.start()


class BrowserViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.container = None
        self.caption = 0

    def fit(self, caption=None):
        if type(caption) is int and 0 <= caption <= 80:
            self.caption = caption
        if self.container is not None:
            self.container.setGeometry(0, -self.caption, self.width(), self.height() + self.caption)

    def resizeEvent(self, event):
        self.fit()
        super().resizeEvent(event)


class NativeBrowserPlayer(QWidget):
    status = Signal(str)
    reviewed = Signal(str)
    failed = Signal(str)
    telemetry = Signal(object)
    available = Signal(bool)

    def __init__(self, base: Path, parent=None):
        super().__init__(parent)
        self.base = Path(base)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.document = self.window = self.container = self.foreign = self.process = None
        self.video_id = ""
        self.first_party = False
        self.custom_controls = False
        self.captions_off = False
        self.bridge = self.viewport = None
        self.frame_checked_at = 0
        self.muted = False
        self.last_status = ""
        self.started = 0
        self.playing = False
        self.load_deadline = True
        self.poll = QTimer(self)
        self.poll.setInterval(150)
        self.poll.timeout.connect(self.check)
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.release)

    def load_video(self, video_id):
        self.release()
        browser = find_browser()
        if browser is None:
            raise OSError("Se necesita Chrome o Microsoft Edge para reproducir con tu sesión.")
        self.video_id = youtube_video_id(video_id)
        try:
            self.document = PlayerDocument(self.video_id, self.muted, self.custom_controls, self.captions_off)
            if self.first_party:
                self.document.html = ("<!doctype html><title>" + self.document.title
                                      + "</title><body style='background:#09090b'></body>").encode()
            self.window = BrowserWindow(self.document.title, browser)
            self.process = start_browser(self.base, browser, ["--window-position=-10000,-10000", "--app=" + self.document.url])
            self.started = time.monotonic()
            self.load_deadline = True
            self.status.emit("Abriendo reproductor con la sesión de YouTubeSync…")
            self.poll.start()
        except Exception:
            self.release()
            raise

    def check(self):
        if not self.document:
            return
        if self.container is None:
            hwnd = self.window.find()
            if hwnd:
                if not self.window.pin_identity():
                    self.abort("Windows no ha permitido identificar la ventana del reproductor.")
                    return
                self.foreign = QWindow.fromWinId(hwnd)
                if self.foreign is None:
                    self.abort("Windows no ha permitido alojar el reproductor.")
                    return
                self.foreign.setFlags(Qt.ForeignWindow | Qt.FramelessWindowHint)
                self.viewport = BrowserViewport(self)
                self.container = QWidget.createWindowContainer(self.foreign, self.viewport)
                self.viewport.container = self.container
                self.layout.addWidget(self.viewport, 1)
                self.container.show()
                self.layout.activate()
                self.refresh_frame()
                self.status.emit("Cargando vídeo de YouTube…")
                if self.first_party:
                    from youtube_sync_first_party_player import FirstPartyPlayer
                    self.bridge = FirstPartyPlayer(playback_profile(self.base, self.window.browser), self.document.url,
                                                   self.video_id, self.muted, self)
                    self.bridge.custom_controls = self.custom_controls
                    self.bridge.captions = False if self.captions_off else None
                    self.bridge.status.connect(self.status)
                    self.bridge.failed.connect(self.failed)
                    self.bridge.telemetry.connect(self.apply_telemetry)
                    self.bridge.available.connect(self.available)
                    self.bridge.start()
            elif self.process.poll() not in (None, 0):
                self.abort("El navegador no ha podido iniciar el reproductor. Revisa la sesión en Ajustes > Reproducción.")
                return
            elif time.monotonic() - self.started > 30:
                self.abort("El navegador no ha abierto el reproductor. Revisa la sesión en Ajustes > Reproducción y reintenta.")
                return
        elif not self.window.owned():
            self.abort("Se ha cerrado la ventana de reproducción. Puedes volver a cargar el vídeo.")
            return
        if self.container is None:
            return
        if time.monotonic() - self.frame_checked_at >= 0.8:
            self.refresh_frame()
        if self.isVisible() and not self.topLevelWidget().isMinimized():
            self.document.attached.set()
        else:
            self.document.attached.clear()
        while self.document and not self.document.events.empty():
            event = self.document.events.get_nowait()
            if event["type"] == "progress":
                self.apply_telemetry(event["value"])
            elif event["type"] == "ready":
                self.load_deadline = False
                self.status.emit("Pulsa reproducir para comparar el vídeo de YouTube.")
            elif event["type"] == "state" and event["value"] == 1:
                self.load_deadline = False
                self.playing = True
                self.status.emit("Reproduciendo vídeo de YouTube")
                self.reviewed.emit(self.video_id)
            elif event["type"] == "state" and event["value"] in {0, 2}:
                self.status.emit("Vídeo de YouTube finalizado" if event["value"] == 0 else "Reproducción de YouTube pausada")
            elif event["type"] == "error":
                self.load_deadline = False
                message = ("El vídeo requiere acceso. Revisa la cuenta en Ajustes > Reproducción > Gestionar sesión y vuelve a cargarlo."
                           if event["value"] == 100 else self.error_message(event["value"]))
                self.status.emit(message)
                self.failed.emit(message)
            elif event["type"] == "autoplay":
                self.status.emit("Pulsa reproducir en el vídeo para iniciar la comparación.")
        if not self.first_party and self.load_deadline and time.monotonic() - self.started > 45:
            self.load_deadline = False
            self.status.emit("YouTube no ha respondido. Revisa la conexión y vuelve a cargar el vídeo.")

    def refresh_frame(self):
        self.frame_checked_at = time.monotonic()
        self.window.strip_frame()
        if self.viewport is not None:
            caption = self.window.caption_height()
            if type(caption) is int:
                self.viewport.fit(round(caption / self.devicePixelRatioF()))

    def apply_telemetry(self, data):
        try:
            data = telemetry(data)
        except ValueError:
            return
        self.telemetry.emit(data)
        self.available.emit(True)
        if self.first_party:
            self.load_deadline = False
            if data["playing"] and not self.playing:
                self.reviewed.emit(self.video_id)
            self.playing = data["playing"]
            message = "Reproduciendo vídeo de YouTube" if self.playing else "Reproducción de YouTube pausada"
            if message != self.last_status:
                self.last_status = message
                self.status.emit(message)

    def control(self, action, value=None):
        command(action, value)
        if self.bridge is not None:
            return self.bridge.control(action, value)
        return self.document.control(action, value) if self.document is not None else False

    @staticmethod
    def error_message(code):
        from youtube_sync_youtube_player import playback_error
        return playback_error(code)

    def abort(self, message):
        self.release()
        self.status.emit(message)
        self.failed.emit(message)

    def release(self):
        self.poll.stop()
        self.available.emit(False)
        if self.bridge is not None:
            bridge, self.bridge = self.bridge, None
            bridge.release()
            bridge.deleteLater()
        if self.document:
            self.document.close()
            self.document = None
        if self.window:
            self.window.close()
            self.window = None
        if self.container:
            self.container.hide()
            self.layout.removeWidget(self.container)
            self.container.deleteLater()
        if self.viewport is not None:
            self.layout.removeWidget(self.viewport)
            self.viewport.deleteLater()
            self.viewport = None
        self.container = self.foreign = self.process = None
        self.video_id = ""
        self.playing = False
        self.last_status = ""
