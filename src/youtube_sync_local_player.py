"""Local-only Qt media preview. No YouTube player, downloads or network sources."""

import os
from pathlib import Path

from PySide6.QtCore import QEvent, QSignalBlocker, QTimer, Qt, QUrl
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QSizePolicy, QSlider, QStackedWidget, QToolButton, QVBoxLayout, QWidget
from youtube_sync_i18n_widgets import QDialog, QLabel, QMessageBox, QToolButton, QWidget

from youtube_sync_icons import app_icon
from youtube_sync_preview_ui import style_player_tool
from youtube_sync_fullscreen import mark_fullscreen, escape_pressed


def media_time(milliseconds: int) -> str:
    seconds = max(0, milliseconds // 1000)
    minutes, second = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours}:{minute:02}:{second:02}" if hours else f"{minute}:{second:02}"


class LocalPlayerWindow(QDialog):
    def __init__(self, owner):
        super().__init__(owner.window())
        self.owner = owner
        self.screen_hint = owner.window().screen()
        self.setWindowTitle("Reproductor / YouTubeSync")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.escape_shortcut.setAutoRepeat(False)
        self.escape_shortcut.activated.connect(owner.return_inline)
        self.escape_poll = QTimer(self)
        self.escape_poll.setInterval(60)
        self.escape_poll.timeout.connect(self.check_escape)

    def enter_fullscreen(self):
        if self.screen_hint is not None:
            self.setScreen(self.screen_hint)
            self.setGeometry(self.screen_hint.geometry())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        mark_fullscreen(int(self.winId()), True)
        self.escape_poll.start()

    def check_escape(self):
        if escape_pressed(int(self.winId())):
            self.owner.return_inline()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.owner.return_inline()
            event.accept()
        else:
            super().keyPressEvent(event)

    def done(self, result):
        self.escape_poll.stop()
        mark_fullscreen(int(self.winId()), False)
        if self.owner.popup is self:
            self.owner.return_inline(stop=True, close=False)
        super().done(result)
        self.deleteLater()


class LocalVideoPlayer(QWidget):
    def __init__(self, path: str = "", parent=None, *, compact=False, _shared_owner=None):
        super().__init__(parent)
        self.path = Path(path) if path else None
        self.compact = compact
        self.popup = None
        self._shared_owner = _shared_owner
        self.thumbnail_source = QPixmap()
        self.setObjectName("LocalPlayer")
        self.player = _shared_owner.player if _shared_owner is not None else QMediaPlayer(self)
        self.audio = _shared_owner.audio if _shared_owner is not None else QAudioOutput(self)
        if _shared_owner is None:
            self.audio.setVolume(0.65)
            self.player.setAudioOutput(self.audio)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.video = QVideoWidget()
        self.video.setMinimumSize(0, 0 if compact else 170)
        self.video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.player.setVideoOutput(self.video)
        self.surface = QStackedWidget()
        self.surface.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.surface.setObjectName("ChannelMedia")
        self.surface.addWidget(self.video)
        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setMinimumSize(0, 0)
        self.thumbnail.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.thumbnail.setObjectName("ChannelMedia")
        if compact:
            self.thumbnail.setCursor(Qt.PointingHandCursor)
            self.thumbnail.setToolTip("Reproducir local")
            self.thumbnail.installEventFilter(self)
        self.surface.addWidget(self.thumbnail)
        self.surface.setCurrentWidget(self.thumbnail if compact else self.video)
        layout.addWidget(self.surface, 1)
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
        if compact:
            backward = self.tool("Retroceder 10 segundos", "arrow-left")
            backward.clicked.connect(lambda: self.player.setPosition(max(0, self.player.position() - 10000)))
            controls.addWidget(backward)
            forward = self.tool("Avanzar 10 segundos", "arrow-right")
            forward.clicked.connect(lambda: self.player.setPosition(min(self.player.duration(), self.player.position() + 10000)))
            controls.addWidget(forward)
        self.mute_button = self.tool("Silenciar", "volume-2")
        self.mute_button.clicked.connect(lambda: self.audio.setMuted(not self.audio.isMuted()))
        controls.addWidget(self.mute_button)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setObjectName("PlayerVolume")
        self.volume.setMinimumWidth(36)
        self.volume.setMaximumWidth(90)
        self.volume.setRange(0, 100)
        self.volume.setValue(round(self.audio.volume() * 100))
        self.volume.setToolTip("Ajusta el volumen de la vista previa local.")
        self.volume.valueChanged.connect(lambda value: self.audio.setVolume(value / 100))
        controls.addWidget(self.volume)
        controls.addStretch(1)
        external = self.tool("Ver local fuera", "external-link")
        external.clicked.connect(self.open_external)
        controls.addWidget(external)
        self.fullscreen_button = self.tool("Pantalla completa", "monitor")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        controls.addWidget(self.fullscreen_button)
        layout.addLayout(controls)
        self.player.playbackStateChanged.connect(self.playback_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.errorOccurred.connect(self.media_error)
        self.audio.mutedChanged.connect(self.mute_changed)
        self.audio.volumeChanged.connect(self.volume_changed)
        if compact:
            self.status.hide()
        if not path:
            self.set_file("")
        if _shared_owner is not None:
            self.surface.setCurrentWidget(self.video)
            self.duration_changed(self.player.duration())
            self.playback_changed(self.player.playbackState())
            self.mute_changed(self.audio.isMuted())
            self.fullscreen_button.setIcon(app_icon("arrow-left"))
            self.fullscreen_button.setToolTip("Volver al panel")
            self.fullscreen_button.setAccessibleName("Volver al panel")

    def set_file(self, path: str):
        self.release()
        self.path = Path(path) if path else None
        self.thumbnail_source = QPixmap()
        self.thumbnail.clear()
        if self.compact and path:
            self.thumbnail.setPixmap(app_icon("play", "#a7adb8").pixmap(48, 48))
        self.setEnabled(bool(path))
        self.seek.setRange(0, 0)
        self.clock.setText("0:00 / 0:00")
        self.status.setText("Preparando archivo local…" if path else "Selecciona un archivo para previsualizarlo.")

    def set_thumbnail(self, path: str):
        self.thumbnail_source = QPixmap(path)
        self.update_thumbnail()

    def update_thumbnail(self):
        if not self.thumbnail_source.isNull():
            self.thumbnail.setPixmap(self.thumbnail_source.scaled(self.surface.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.compact and self.popup is None and self._shared_owner is None:
            self.surface.setFixedHeight(max(120, round(event.size().width() * 9 / 16)))
        self.update_thumbnail()

    def eventFilter(self, watched, event):
        if watched is self.thumbnail and event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            self.play_file()
            return True
        return super().eventFilter(watched, event)

    def tool(self, name: str, icon: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(app_icon(icon))
        button.setAccessibleName(name)
        button.setToolTip(name)
        style_player_tool(button, icon)
        return button

    def play_file(self):
        if self.path is None or not self.path.is_file():
            self.status.setText("El archivo local ya no está disponible.")
            return
        source = QUrl.fromLocalFile(str(self.path.resolve()))
        if self.player.source() != source:
            self.status.setText("Cargando vídeo local…")
            self.player.setSource(source)
        if self.player.duration() and self.player.position() >= self.player.duration():
            self.player.setPosition(0)
        self.surface.setCurrentWidget(self.video)
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

    def volume_changed(self, volume):
        with QSignalBlocker(self.volume):
            self.volume.setValue(round(volume * 100))

    def media_error(self, error, message):
        if error != QMediaPlayer.NoError:
            self.status.setText(f"No se puede reproducir aquí: {message}. Puedes abrirlo en el reproductor externo.")
            self.status.show()

    def open_external(self):
        self.player.pause()
        try:
            if self.path is None or not self.path.is_file():
                raise OSError("El archivo local ya no está disponible.")
            os.startfile(str(self.path))
        except OSError as exc:
            QMessageBox.warning(self, "Archivo local", str(exc))

    def pause(self):
        self.player.pause()

    def toggle_fullscreen(self):
        if self._shared_owner is not None:
            self._shared_owner.return_inline()
            return
        if self.popup is not None:
            self.return_inline()
            return
        if self.path is None or not self.path.is_file():
            self.play_file()
            return
        if self.player.source().isEmpty():
            self.play_file()
        window = LocalPlayerWindow(self)
        self.popup = window
        # Keep native video widgets in their original windows; only switch the
        # shared media player's output, without reopening the file or audio.
        window.view = LocalVideoPlayer(str(self.path), window, compact=True, _shared_owner=self)
        window.layout().addWidget(window.view, 1)
        window.enter_fullscreen()

    def return_inline(self, *, stop=False, close=True):
        window = self.popup
        if window is None:
            return
        self.popup = None
        self.player.setVideoOutput(self.video)
        if stop:
            self.release()
        if close:
            window.close()

    def release(self):
        if self._shared_owner is not None:
            self._shared_owner.release()
            return
        self.return_inline()
        self.player.stop()
        self.player.setSource(QUrl())
        if self.compact:
            self.surface.setCurrentWidget(self.thumbnail)
