"""Chromium's Windows CDP pipe, restricted to inherited process handles.

There is no debugger TCP listener. Reads and writes never block the Qt thread.
"""

import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

_connections = []
_launch_lock = threading.Lock()


class BrowserPipe(QObject):
    received = Signal(object)
    disconnected = Signal()

    def __init__(self, arguments, profile, parent=None):
        super().__init__(parent)
        if os.name != "nt":
            raise OSError("La sesión integrada requiere Windows.")
        import msvcrt
        self.profile = Path(profile).resolve()
        self.closed = False
        self.sequence = 0
        self.callbacks = {}
        self.outgoing = queue.Queue(maxsize=64)
        self.received.connect(self.dispatch)
        self.disconnected.connect(self.mark_closed)
        child_read, self.write_fd = os.pipe()
        self.read_fd, child_write = os.pipe()
        handles = [msvcrt.get_osfhandle(child_read), msvcrt.get_osfhandle(child_write)]
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {"handle_list": handles}
        try:
            for fd in (child_read, child_write):
                os.set_inheritable(fd, True)
            args = list(arguments) + ["--remote-debugging-pipe", f"--remote-debugging-io-pipes={handles[0]},{handles[1]}"]
            self.process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL, close_fds=True, startupinfo=startup)
        except Exception:
            os.close(self.read_fd)
            os.close(self.write_fd)
            self.closed = True
            raise
        finally:
            os.close(child_read)
            os.close(child_write)
        self.expiry = QTimer(self)
        self.expiry.setInterval(1000)
        self.expiry.timeout.connect(self.expire_requests)
        self.expiry.start()
        threading.Thread(target=self.read_messages, daemon=True).start()
        threading.Thread(target=self.write_messages, daemon=True).start()

    def alive(self):
        return not self.closed and self.process.poll() is None

    def request(self, method, params, callback, session_id=None):
        allowed = {"Page.navigate", "Runtime.evaluate"} if session_id else {
            "Target.getTargets", "Target.attachToTarget", "Target.detachFromTarget"}
        if method not in allowed:
            return False
        if not self.alive() or len(self.callbacks) >= 32:
            return False
        self.sequence += 1
        message = {"id": self.sequence, "method": method, "params": params}
        if session_id:
            message["sessionId"] = session_id
        self.callbacks[self.sequence] = (time.monotonic(), callback)
        try:
            self.outgoing.put_nowait(json.dumps(message).encode("utf-8") + b"\0")
            return True
        except queue.Full:
            self.callbacks.pop(self.sequence, None)
            return False

    def read_messages(self):
        buffer = b""
        try:
            while not self.closed:
                data = os.read(self.read_fd, 65536)
                if not data:
                    break
                buffer += data
                if len(buffer) > 2 * 1024 * 1024:
                    break
                while b"\0" in buffer:
                    message, buffer = buffer.split(b"\0", 1)
                    try:
                        value = json.loads(message)
                    except (ValueError, UnicodeError):
                        continue
                    if isinstance(value, dict) and not self.closed:
                        self.received.emit(value)
        except OSError:
            pass
        finally:
            os.close(self.read_fd)
        if not self.closed:
            self.disconnected.emit()

    def write_messages(self):
        try:
            while not self.closed:
                try:
                    data = self.outgoing.get(timeout=0.5)
                except queue.Empty:
                    continue
                while data and not self.closed:
                    written = os.write(self.write_fd, data)
                    if written <= 0:
                        raise OSError("Closed player pipe")
                    data = data[written:]
        except OSError:
            if not self.closed:
                self.disconnected.emit()
        finally:
            os.close(self.write_fd)

    def dispatch(self, data):
        pending = self.callbacks.pop(data.get("id"), None)
        if pending is not None and not self.closed:
            pending[1](data)

    def expire_requests(self):
        expired = [key for key, (started, _) in self.callbacks.items() if time.monotonic() - started > 10]
        for key in expired:
            _, callback = self.callbacks.pop(key)
            callback({"id": key, "error": {"message": "Player request timed out"}})

    def mark_closed(self):
        if self.closed:
            return
        self.closed = True
        self.expiry.stop()
        self.callbacks.clear()


def launch_browser(arguments, profile):
    # Handles are inheritable only during this serialized Popen call.
    with _launch_lock:
        for previous in list(_connections):
            if previous.closed:
                _connections.remove(previous)
                previous.deleteLater()
        connection = BrowserPipe(arguments, profile, QApplication.instance())
        _connections.append(connection)
    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(connection.mark_closed)
    return connection.process


def connections_for(profile):
    profile = Path(profile).resolve()
    return [connection for connection in _connections if connection.profile == profile and connection.alive()]
