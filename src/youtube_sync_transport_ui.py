"""The same playback controls for the sidebar and detached player window."""

from PySide6.QtCore import Qt, QSignalBlocker, QTimer, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QSlider

from youtube_sync_i18n_widgets import QLabel, QPushButton, QWidget
from youtube_sync_i18n import t
from youtube_sync_icons import app_icon
from youtube_sync_preview_ui import style_player_tool
from youtube_sync_local_player import media_time
from youtube_sync_player_controls import telemetry


def transport_button(name, icon, callback):
    button = QPushButton(app_icon(icon), "")
    button.setToolTip(name)
    button.setAccessibleName(name)
    button.setAutoDefault(False)
    style_player_tool(button, icon)
    button.clicked.connect(callback)
    return button


class TransportControls(QWidget):
    problem = Signal(str)
    captions_changed = Signal(bool)
    start_requested = Signal()
    fullscreen_requested = Signal()

    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewControls")
        self.player = player
        self.active = False
        self.startable = False
        self.available_now = False
        self.ready = False
        self.last_data = None
        self.captions_enabled = False
        self.seek_timer = QTimer(self)
        self.seek_timer.setSingleShot(True)
        self.seek_timer.timeout.connect(self.commit_seek)
        self.volume_timer = QTimer(self)
        self.volume_timer.setSingleShot(True)
        self.volume_timer.timeout.connect(self.commit_volume)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setObjectName("PlayerSeek")
        self.seek.setRange(0, 1000)
        self.seek.setAccessibleName(t("Posición del vídeo"))
        self.seek.setToolTip(t("Ir a un punto del vídeo"))
        self.seek.valueChanged.connect(lambda: self.seek_timer.start(150) if not self.seek.isSliderDown() else None)
        self.seek.sliderReleased.connect(self.commit_seek)
        self.time = QLabel("0:00 / 0:00")
        self.time.setMinimumWidth(98)
        self.time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.seek, 0, 0)
        layout.addWidget(self.time, 0, 1)
        tools = QHBoxLayout()
        tools.setSpacing(6)
        self.back = transport_button("Retroceder 10 segundos", "arrow-left", lambda: self.send("relative", -10))
        self.toggle = transport_button("Reanudar vídeo", "play", self.toggle_play)
        self.forward = transport_button("Avanzar 10 segundos", "arrow-right", lambda: self.send("relative", 10))
        self.mute = transport_button("Silenciar vídeo", "volume-2", self.toggle_mute)
        self.captions = transport_button("Subtítulos", "captions", self.toggle_captions)
        self.captions.setCheckable(True)
        self.fullscreen = transport_button("Pantalla completa", "monitor", self.fullscreen_requested.emit)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setObjectName("PlayerVolume")
        self.volume.setRange(0, 100)
        self.volume.setValue(100)
        self.volume.setMinimumWidth(36)
        self.volume.setMaximumWidth(90)
        self.volume.setAccessibleName(t("Volumen del vídeo"))
        self.volume.setToolTip(t("Volumen del vídeo"))
        self.volume.valueChanged.connect(lambda: self.volume_timer.start(150) if not self.volume.isSliderDown() else None)
        self.volume.sliderReleased.connect(self.commit_volume)
        for button in (self.toggle, self.back, self.forward, self.mute):
            tools.addWidget(button)
        tools.addWidget(self.volume)
        tools.addStretch(1)
        tools.addWidget(self.captions)
        tools.addWidget(self.fullscreen)
        layout.addLayout(tools, 1, 0, 1, 2)
        layout.setColumnStretch(0, 1)
        player.telemetry.connect(self.update_data)
        player.available.connect(self.set_available)
        self.set_active(False)

    def set_active(self, active):
        self.active = active
        if not active:
            self.captions_enabled = False
            self.captions.setChecked(False)
            self.seek_timer.stop()
            self.volume_timer.stop()
            self.last_data = None
            self.available_now = False
            self.time.setText("0:00 / 0:00")
            with QSignalBlocker(self.seek):
                self.seek.setValue(0)
            self.toggle.setIcon(app_icon("play"))
            self.toggle.setToolTip("Reproducir")
            self.toggle.setAccessibleName("Reproducir")
        self.update_enabled()

    def set_startable(self, startable):
        self.startable = bool(startable)
        self.update_enabled()

    def update_enabled(self):
        self.ready = bool(self.active and self.last_data and self.available_now)
        self.setEnabled(self.ready or self.startable)
        self.toggle.setEnabled(self.ready or (self.startable and not self.active))
        self.fullscreen.setEnabled(self.ready or self.startable)
        for control in (self.seek, self.back, self.forward, self.mute, self.captions, self.volume):
            control.setEnabled(self.ready)
        if self.ready:
            for control in (self.seek, self.back, self.forward):
                control.setEnabled(self.last_data["duration"] > 0)

    def update_data(self, value):
        if not self.active:
            return
        try:
            data = telemetry(value)
        except ValueError:
            return
        self.last_data = data
        self.available_now = True
        self.update_enabled()
        if not self.seek.isSliderDown():
            with QSignalBlocker(self.seek):
                self.seek.setValue(round(data["position"] / data["duration"] * 1000) if data["duration"] else 0)
            self.time.setText(media_time(round(data["position"] * 1000)) + " / " + media_time(round(data["duration"] * 1000)))
        if not self.volume.isSliderDown():
            with QSignalBlocker(self.volume):
                self.volume.setValue(round(data["volume"]))
        self.toggle.setIcon(app_icon("pause" if data["playing"] else "play"))
        name = "Pausar vídeo" if data["playing"] else "Reanudar vídeo"
        self.toggle.setToolTip(name)
        self.toggle.setAccessibleName(name)
        self.mute.setIcon(app_icon("volume-x" if data["muted"] else "volume-2"))
        name = "Activar sonido del vídeo" if data["muted"] else "Silenciar vídeo"
        self.mute.setToolTip(name)
        self.mute.setAccessibleName(name)

    def set_available(self, available):
        self.available_now = bool(available)
        self.update_enabled()
        if not available:
            self.seek_timer.stop()
            self.volume_timer.stop()

    def send(self, action, value=None):
        if self.ready and not self.player.control(action, value):
            self.problem.emit("El reproductor aún no está disponible. Reintenta la carga del vídeo.")

    def toggle_play(self):
        if self.ready:
            self.send("pause" if self.last_data["playing"] else "play")
        elif self.startable and not self.active:
            self.start_requested.emit()

    def toggle_mute(self):
        if self.last_data:
            self.send("mute", not self.last_data["muted"])

    def toggle_captions(self):
        wanted = not self.captions_enabled
        if self.ready and self.player.control("captions", wanted):
            self.captions_enabled = wanted
            self.captions_changed.emit(wanted)
        self.captions.setChecked(self.captions_enabled)

    def commit_seek(self):
        self.seek_timer.stop()
        if self.last_data and self.last_data["duration"]:
            self.send("seek", self.last_data["duration"] * self.seek.value() / 1000)

    def commit_volume(self):
        self.volume_timer.stop()
        self.send("volume", self.volume.value())
        if self.volume.value() > 0:
            self.send("mute", False)
