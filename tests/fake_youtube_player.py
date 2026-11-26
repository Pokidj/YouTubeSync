"""No network or Chromium subprocesses in wizard interaction tests."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class FakeYouTubePlayer(QWidget):
    status = Signal(str)
    reviewed = Signal(str)
    failed = Signal(str)
    telemetry = Signal(object)
    available = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auto_review = True
        self.video_id = ""
        self.commands = []
        self.setMinimumSize(200, 200)

    def load_video(self, video_id):
        self.video_id = video_id
        self.status.emit("Vídeo de prueba")
        if self.auto_review:
            self.reviewed.emit(video_id)

    def release(self):
        self.video_id = ""

    def control(self, action, value=None):
        self.commands.append((action, value))
        return bool(self.video_id)
