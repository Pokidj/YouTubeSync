"""Channel identity, cached gallery totals and a single movable playback surface."""

import webbrowser

from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QShortcut, QKeySequence
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QSizePolicy, QStackedWidget, QVBoxLayout

from youtube_sync_i18n import t
from youtube_sync_i18n_widgets import QDialog, QLabel, QPushButton, RawLabel, QWidget
from youtube_sync_icons import app_icon, button_tone
from youtube_sync_youtube_player import EmbeddedYouTubePlayer
from youtube_sync_transport_ui import TransportControls
from youtube_sync_fullscreen import mark_fullscreen, escape_pressed


class ChannelAvatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtGui import QPixmap
        self.source = QPixmap()
        self.setFixedSize(64, 64)

    def set_image(self, data=b""):
        self.source.loadFromData(data)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addEllipse(self.rect())
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor("#252930"))
        if self.source.isNull():
            app_icon("user-round", "#b4bdcb").paint(painter, self.rect().adjusted(15, 15, -15, -15))
        else:
            scaled = self.source.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap((self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled)


class ChannelOverview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 4, 0, 12)
        self.grid.setHorizontalSpacing(24)
        self.identity = QWidget()
        identity = QHBoxLayout(self.identity)
        identity.setContentsMargins(0, 0, 0, 0)
        identity.setSpacing(14)
        self.avatar = ChannelAvatar()
        identity.addWidget(self.avatar)
        text = QVBoxLayout()
        text.setSpacing(3)
        self.name = RawLabel()
        self.name.setTextFormat(Qt.PlainText)
        self.name.setObjectName("ChannelName")
        self.name.setMinimumWidth(0)
        self.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.name.setWordWrap(True)
        self.connection = QLabel("Canal sin confirmar")
        self.connection.setObjectName("Muted")
        self.connection.setWordWrap(True)
        text.addWidget(self.name)
        text.addWidget(self.connection)
        identity.addLayout(text, 1)
        self.stats = QWidget()
        stats = QHBoxLayout(self.stats)
        stats.setContentsMargins(0, 0, 0, 0)
        stats.setSpacing(20)
        self.counts = {}
        for key, label, icon, color in (("total", "Vídeos", "list-video", "#f5f6f8"),
                                        ("public", "Públicos", "globe", "#4ade80"),
                                        ("private", "Privados", "lock", "#ff7c94"),
                                        ("unlisted", "Ocultos", "eye-off", "#64baff")):
            column = QVBoxLayout()
            column.setSpacing(3)
            heading = QHBoxLayout()
            glyph = QLabel()
            glyph.setFixedSize(16, 16)
            glyph.setPixmap(app_icon(icon, color).pixmap(16, 16))
            heading.addWidget(glyph)
            heading.addWidget(QLabel(label))
            heading.addStretch(1)
            value = RawLabel("—")
            value.setObjectName("ChannelCount")
            value.setStyleSheet(f"color: {color};")
            value.setAccessibleName(label)
            column.addLayout(heading)
            column.addWidget(value)
            stats.addLayout(column, 1)
            self.counts[key] = value
        self.note = QLabel("Sin cargar")
        self.note.setObjectName("Muted")
        self.note.setWordWrap(True)
        text.addWidget(self.note)
        self.grid.addWidget(self.identity, 0, 0)
        self.grid.addWidget(self.stats, 0, 1)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self._compact = None

    def set_identity(self, name, channel_id=""):
        self.name.setText(name or t("Tu canal de YouTube"))
        self.name.setToolTip(name)
        self.connection.setText("Canal vinculado" if channel_id else "Canal sin confirmar")

    def set_videos(self, videos=None, checked_at="", cached=False, unavailable_count=0):
        if videos is None:
            for value in self.counts.values():
                value.setText("—")
            self.note.setText("Sin cargar")
            return
        unique = {video["id"]: video for video in videos if video.get("id")}
        totals = {key: 0 for key in self.counts}
        totals["total"] = len(unique)
        for video in unique.values():
            if video.get("privacy") in totals and video["privacy"] != "total":
                totals[video["privacy"]] += 1
        for key, value in self.counts.items():
            value.setText(f"{totals[key]:,}".replace(",", " "))
        note = t("Copia guardada") if cached else t("Canal actualizado")
        if checked_at:
            note += " · " + checked_at
        unknown = totals["total"] - sum(totals[key] for key in ("public", "private", "unlisted"))
        if unknown:
            note += " · " + t("{count} sin clasificar".format(count=unknown))
        if unavailable_count:
            note += "\n" + t("{count} referencias no disponibles (fuera del total)".format(count=unavailable_count))
        self.note.setRawText(note)

    def resizeEvent(self, event):
        compact = event.size().width() < 820
        if self._compact != compact:
            self._compact = compact
            self.grid.removeWidget(self.stats)
            self.grid.addWidget(self.stats, 1 if compact else 0, 0 if compact else 1, 1, 2 if compact else 1)
        super().resizeEvent(event)


class PlayerWindow(QDialog):
    def __init__(self, owner):
        super().__init__(owner.window())
        self.owner = owner
        self.setWindowTitle("Reproductor / YouTubeSync")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setMinimumSize(480, 340)
        self.resize(960, 620)
        layout = QVBoxLayout(self)
        self.video_layout = QVBoxLayout()
        layout.addLayout(self.video_layout, 1)
        self.transport = TransportControls(owner.player, self)
        self.transport.problem.connect(owner.show_status)
        self.transport.captions_changed.connect(owner.set_captions_state)
        self.transport.captions_enabled = owner.transport.captions_enabled
        self.transport.captions.setChecked(self.transport.captions_enabled)
        self.transport.set_active(bool(owner.active_id))
        if owner.transport.last_data:
            self.transport.update_data(owner.transport.last_data)
            self.transport.set_available(owner.transport.ready)
        layout.addWidget(self.transport)
        self.notice = QLabel()
        self.notice.setObjectName("Muted")
        self.notice.setWordWrap(True)
        self.notice.hide()
        layout.addWidget(self.notice)
        tools = QHBoxLayout()
        self.back = owner.button("Volver al panel", "arrow-left", owner.return_inline)
        tools.addWidget(self.back)
        tools.addStretch(1)
        self.fullscreen = self.transport.fullscreen
        self.transport.fullscreen_requested.connect(self.toggle_fullscreen)
        self.browser = owner.button("Abrir en YouTube", "external-link", owner.open_external)
        self.share_here = owner.button("Compartir desde aquí", "share-2", owner.share_from_position)
        self.share_here.setEnabled(owner.can_share_position())
        self.stop_button = owner.button("Detener reproducción", "square", owner.stop)
        for button in (self.share_here, self.browser, self.stop_button):
            tools.addWidget(button)
        layout.addLayout(tools)
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.escape_shortcut.setAutoRepeat(False)
        self.escape_shortcut.activated.connect(owner.return_inline)
        self.escape_poll = QTimer(self)
        self.escape_poll.setInterval(60)
        self.escape_poll.timeout.connect(self.check_native_escape)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.owner.return_inline()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        screen = self.owner.window().screen()
        if screen is not None:
            self.setScreen(screen)
            self.setGeometry(screen.geometry())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        mark_fullscreen(int(self.winId()), True)
        self.escape_poll.start()
        self.fullscreen.setToolTip(t("Salir de pantalla completa"))
        self.fullscreen.setAccessibleName(t("Salir de pantalla completa"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.owner.return_inline()
        elif event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def check_native_escape(self):
        if self.isFullScreen() and escape_pressed(int(self.winId())):
            self.owner.return_inline()

    def closeEvent(self, event):
        self.escape_poll.stop()
        mark_fullscreen(int(self.winId()), False)
        super().closeEvent(event)

    def done(self, result):
        if self.owner.popup is self:
            self.owner.restore_inline(stop=True, close=False)
        super().done(result)
        self.deleteLater()


class ChannelPlayback(QWidget):
    settings_requested = Signal()
    share_requested = Signal(str, int)
    share_video_requested = Signal()

    def __init__(self, thumbnail, base, parent=None):
        super().__init__(parent)
        self.video_id = ""
        self.private_mode = False
        self.active_id = ""
        self.popup = None
        self.share_busy = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.media = QStackedWidget()
        self.media.setObjectName("ChannelMedia")
        self.media.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.thumbnail = thumbnail
        self.player = EmbeddedYouTubePlayer(self)
        self.player.custom_controls = True
        self.player.captions_off = True
        self.player.native_base = base
        self.player.setMinimumSize(0, 0)
        self.media.addWidget(thumbnail)
        self.media.addWidget(self.player)
        layout.addWidget(self.media)
        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.status.hide()
        self.controls_widget = QWidget()
        self.controls_widget.setObjectName("PreviewControls")
        self.controls = QGridLayout(self.controls_widget)
        self.controls.setContentsMargins(0, 0, 0, 0)
        self.controls.setSpacing(6)
        layout.addWidget(self.status)
        self.transport = TransportControls(self.player)
        self.transport.problem.connect(self.show_status)
        self.transport.captions_changed.connect(self.set_captions_state)
        self.transport.start_requested.connect(self.start)
        self.transport.fullscreen_requested.connect(self.open_popup)
        layout.addWidget(self.transport)
        self.stop_button = self.button("Detener reproducción", "square", self.stop)
        self.popout = self.transport.fullscreen
        self.browser = self.button("Abrir en YouTube", "external-link", self.open_external)
        self.share_here = self.button("Compartir", "share-2", self.share_selected)
        self.access_settings = self.button("Revisar acceso en Ajustes", "settings", self.settings_requested.emit)
        self.access_settings.hide()
        self.controls.setColumnStretch(0, 1)
        for index, button in enumerate((self.stop_button, self.browser, self.share_here), 1):
            self.controls.addWidget(button, 2, index)
        self.controls.addWidget(self.access_settings, 3, 1, 1, 3, Qt.AlignRight)
        layout.addWidget(self.controls_widget)
        self.player.status.connect(self.show_status)
        self.player.failed.connect(self.playback_failed)
        self.player.telemetry.connect(self.refresh_share_action)
        self.player.available.connect(self.refresh_share_action)
        self.stop_button.setEnabled(False)
        self.select_video("")
        self.refresh_share_action()

    @staticmethod
    def button(name, icon, callback, text=False):
        button = QPushButton(app_icon(icon), name if text else "")
        button.setIconSize(QSize(20, 20))
        button.setToolTip(name)
        button.setAccessibleName(name)
        button.setAutoDefault(False)
        button_tone(button, icon=icon)
        if not text:
            button.setFixedWidth(42)
        button.clicked.connect(callback)
        return button

    def select_video(self, video_id, privacy=""):
        private = privacy == "private"
        if video_id != self.video_id or private != self.private_mode:
            self.stop()
            self.video_id = video_id
            self.private_mode = private
            self.player.first_party = private
        self.transport.set_startable(bool(video_id))
        for button in (self.popout, self.browser):
            button.setEnabled(bool(video_id))
        self.refresh_share_action()

    def resize_media(self, width):
        self.media.setFixedHeight(max(96, round(width * 9 / 16)))

    def start(self):
        if not self.video_id:
            return
        if self.popup is not None:
            self.popup.show()
            self.popup.raise_()
            self.popup.activateWindow()
            return
        if self.active_id == self.video_id:
            self.player.control("play")
            return
        self.media.setCurrentWidget(self.player)
        self.active_id = self.video_id
        self.transport.set_active(True)
        self.stop_button.setEnabled(True)
        self.show_status(t("Cargando vídeo de YouTube…"))
        try:
            self.player.load_video(self.video_id)
        except (OSError, ValueError, RuntimeError) as exc:
            self.playback_failed(str(exc))

    def playback_failed(self, message):
        self.stop()
        self.show_status(message)
        self.access_settings.setVisible(self.private_mode)

    def show_status(self, message):
        self.status.setText(message)
        self.status.setVisible(bool(message))
        if self.popup is not None:
            self.popup.notice.setText(message)
            self.popup.notice.setVisible(bool(message))

    def stop(self):
        if self.popup is not None:
            self.restore_inline(stop=True)
            return
        self.player.release()
        self.active_id = ""
        self.access_settings.hide()
        self.transport.set_active(False)
        self.transport.set_startable(bool(self.video_id))
        self.refresh_share_action()
        self.media.setCurrentWidget(self.thumbnail)
        self.stop_button.setEnabled(False)
        self.show_status("")

    def can_share_position(self):
        data = self.transport.last_data
        return bool(not self.share_busy and self.active_id and self.active_id == self.video_id
                    and self.transport.ready and data and data["duration"] > 0
                    and data["position"] <= data["duration"])

    def refresh_share_action(self, *_):
        enabled = self.can_share_position()
        self.share_here.setEnabled(bool(self.video_id and not self.share_busy))
        if self.popup is not None:
            self.popup.share_here.setEnabled(enabled)

    def set_share_busy(self, busy):
        self.share_busy = bool(busy)
        self.refresh_share_action()

    def set_captions_state(self, enabled):
        for controls in (self.transport, self.popup.transport if self.popup else None):
            if controls is not None:
                controls.captions_enabled = enabled
                controls.captions.setChecked(enabled)

    def share_from_position(self):
        if self.can_share_position():
            self.share_requested.emit(self.video_id, int(self.transport.last_data["position"]))

    def share_selected(self):
        if self.can_share_position():
            self.share_from_position()
        elif self.video_id and not self.share_busy:
            self.share_video_requested.emit()

    def open_popup(self):
        if not self.video_id:
            return
        if self.popup is not None:
            self.popup.enter_fullscreen()
            self.popup.raise_()
            self.popup.activateWindow()
            return
        if not self.active_id:
            self.start()
        if not self.active_id:
            return
        window = PlayerWindow(self)
        self.popup = window
        # Move the existing surface, never start a second audio/video stream.
        self.media.removeWidget(self.player)
        window.video_layout.addWidget(self.player)
        self.player.show()
        self.show_status(t("Reproduciendo en ventana"))
        window.enter_fullscreen()

    def return_inline(self):
        self.restore_inline(stop=False)

    def restore_inline(self, stop, close=True):
        window, self.popup = self.popup, None
        if window is None:
            return
        window.video_layout.removeWidget(self.player)
        window.transport.set_active(False)
        self.media.addWidget(self.player)
        self.media.setCurrentWidget(self.player)
        if stop:
            self.stop()
        else:
            self.show_status("")
        if close:
            window.close()

    def open_external(self):
        if self.video_id:
            webbrowser.open(f"https://www.youtube.com/watch?v={self.video_id}")

    def hideEvent(self, event):
        self.stop()
        super().hideEvent(event)
