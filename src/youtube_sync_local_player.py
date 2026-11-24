"""Local-only Qt media preview. No YouTube player, downloads or network sources."""

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QSlider, QToolButton, QVBoxLayout, QWidget
from youtube_sync_i18n_widgets import QLabel, QMessageBox, QToolButton, QWidget

from youtube_sync_icons import app_icon


def media_time(milliseconds: int) -> str:
    seconds = max(0, milliseconds // 1000)
    minutes, second = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours}:{minute:02}:{second:02}" if hours else f"{minute}:{second:02}"


class LocalVideoPlayer(QWidget):
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.65)
        self.player.setAudioOutput(self.audio)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.video = QVideoWidget()
        self.video.setMinimumSize(0, 170)
        self.video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.player.setVideoOutput(self.video)
        layout.addWidget(self.video, 1)
        self.status = QLabel("Preparando archivo local…")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        self.status.setObjectName("Muted")
        layout.addWidget(self.status)
        timeline = QHBoxLayout()
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setObjectName("PlayerSeek")
        self.seek.setRange(0, 0)
        self.seek.setToolTip("Desplaza la posición de reproducción del archivo local.")
        self.seek.sliderMoved.connect(self.player.setPosition)
        self.seek.sliderReleased.connect(lambda: self.player.setPosition(self.seek.value()))
        timeline.addWidget(self.seek, 1)
        self.clock = QLabel("0:00 / 0:00")
        self.clock.setMinimumWidth(98)
        self.clock.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        timeline.addWidget(self.clock)
        layout.addLayout(timeline)
        controls = QHBoxLayout()
        self.play_button = self.tool("Reproducir local", "play")
        self.play_button.clicked.connect(self.toggle_playback)
        controls.addWidget(self.play_button)
        self.mute_button = self.tool("Silenciar", "volume-2")
        self.mute_button.clicked.connect(lambda: self.audio.setMuted(not self.audio.isMuted()))
        controls.addWidget(self.mute_button)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setObjectName("PlayerVolume")
        self.volume.setFixedWidth(90)
        self.volume.setRange(0, 100)
        self.volume.setValue(65)
        self.volume.setToolTip("Ajusta el volumen de la vista previa local.")
        self.volume.valueChanged.connect(lambda value: self.audio.setVolume(value / 100))
        controls.addWidget(self.volume)
        controls.addStretch(1)
        external = self.tool("Ver local fuera", "external-link")
        external.clicked.connect(self.open_external)
        controls.addWidget(external)
        layout.addLayout(controls)
        self.player.playbackStateChanged.connect(self.playback_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.errorOccurred.connect(self.media_error)
        self.audio.mutedChanged.connect(self.mute_changed)

    def tool(self, name: str, icon: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(app_icon(icon))
        button.setIconSize(QSize(20, 20))
        button.setStyleSheet("QToolButton { padding: 4px; min-height: 20px; }")
        button.setAccessibleName(name)
        button.setToolTip(name)
        button.setFixedSize(38, 36)
        return button

    def play_file(self):
        if not self.path.is_file():
            self.status.setText("El archivo local ya no está disponible.")
            return
        source = QUrl.fromLocalFile(str(self.path.resolve()))
        if self.player.source() != source:
            self.status.setText("Cargando vídeo local…")
            self.player.setSource(source)
        if self.player.duration() and self.player.position() >= self.player.duration():
            self.player.setPosition(0)
        self.player.play()

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.play_file()

    def playback_changed(self, state):
        playing = state == QMediaPlayer.PlayingState
        self.play_button.setIcon(app_icon("pause" if playing else "play"))
        name = "Pausar local" if playing else "Reproducir local"
        self.play_button.setAccessibleName(name)
        self.play_button.setToolTip(name)
        if playing:
            self.status.setText("Reproduciendo archivo local")
        elif state == QMediaPlayer.PausedState:
            self.status.setText("Reproducción local pausada")

    def position_changed(self, position):
        if not self.seek.isSliderDown():
            self.seek.setValue(position)
        self.clock.setText(f"{media_time(position)} / {media_time(self.player.duration())}")

    def duration_changed(self, duration):
        self.seek.setRange(0, max(0, duration))
        self.position_changed(self.player.position())

    def mute_changed(self, muted):
        self.mute_button.setIcon(app_icon("volume-x" if muted else "volume-2"))
        name = "Activar sonido" if muted else "Silenciar"
        self.mute_button.setToolTip(name)
        self.mute_button.setAccessibleName(name)

    def media_error(self, error, message):
        if error != QMediaPlayer.NoError:
            self.status.setText(f"No se puede reproducir aquí: {message}. Puedes abrirlo en el reproductor externo.")

    def open_external(self):
        self.player.pause()
        try:
            if not self.path.is_file():
                raise OSError("El archivo local ya no está disponible.")
            os.startfile(str(self.path))
        except OSError as exc:
            QMessageBox.warning(self, "Archivo local", str(exc))

    def pause(self):
        self.player.pause()

    def release(self):
        self.player.stop()
        self.player.setSource(QUrl())
