"""Selection-driven preview and commands for one local video."""

from pathlib import Path
from math import isfinite

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QSizePolicy, QVBoxLayout
from youtube_sync_i18n import t
from youtube_sync_i18n_widgets import QPushButton, RawLabel
from youtube_sync_icons import app_icon, button_tone
from youtube_sync_library import STATUS_ICONS
from youtube_sync_local_player import LocalVideoPlayer, media_time
from youtube_sync_preview_ui import PreviewInfoPill


class LocalPreview(QFrame):
    action_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewContent")
        self.identity = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.title = RawLabel()
        self.title.setObjectName("CardValue")
        self.title.setWordWrap(True)
        self.title.setMinimumWidth(0)
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title.setTextFormat(Qt.PlainText)
        layout.addWidget(self.title)
        self.path = RawLabel()
        self.path.setObjectName("Muted")
        self.path.setWordWrap(True)
        self.path.setMinimumWidth(0)
        self.path.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.path.setTextFormat(Qt.PlainText)
        self.path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.path)
        self.player = LocalVideoPlayer(compact=True)
        self.player.player.durationChanged.connect(
            lambda duration: self.set_media({"seconds": duration / 1000}) if duration > 0 else None)
        layout.addWidget(self.player)
        self.fields = {}
        self.pills = []
        self.info_grid = QGridLayout()
        self.info_grid.setSpacing(8)
        self._two_columns = None
        for key, name, icon in (("status", "Estado", "circle-check"), ("size", "Tamaño", "layers"),
                                ("created", "Creado", "calendar"), ("duration", "Duracion", "clock")):
            pill = PreviewInfoPill(name, icon)
            self.fields[key] = (pill.glyph, pill.value)
            self.pills.append(pill)
        self.layout_pills(False)
        layout.addLayout(self.info_grid)
        self.actions_widget = QFrame(self)
        self.actions_widget.setObjectName("ProfileField")
        self.actions_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.actions_grid = QGridLayout(self.actions_widget)
        self.actions_grid.setContentsMargins(0, 0, 0, 0)
        self.actions_grid.setSpacing(6)
        self.actions_grid.setColumnStretch(0, 1)
        self.action_columns = 6
        self.buttons = {}
        commands = (("upload_file", "Subir seleccionado", "arrow-up"),
                    ("retry_video", "Reintentar", "rotate-ccw"),
                    ("review_video", "Revisar", "circle-question-mark"),
                    ("manual_verify", "Confirmar coincidencia", "circle-check"),
                    ("check_video", "Comprobar este vídeo", "refresh-cw"),
                    ("open_video", "Ver YouTube", "external-link"),
                    ("locate_file", "Mostrar archivo en Windows", "search"),
                    ("copy_detail", "Copiar detalle", "copy"),
                    ("delete_local", "Borrar archivo local", "trash"))
        for action, name, icon in commands:
            button = self.button(name, icon, lambda _checked=False, action=action: self.request_action(action))
            button.hide()
            self.buttons[action] = button
        self.verify = self.buttons["manual_verify"]
        self.youtube = self.buttons["open_video"]
        layout.addStretch(1)
        self.select(None)

    def button(self, name, icon, callback):
        button = QPushButton(app_icon(icon), "", self.actions_widget)
        button.setIconSize(QSize(20, 20))
        button.setMinimumWidth(0)
        button.setFixedSize(42, 40)
        button.setToolTip(name)
        button.setAccessibleName(name)
        button.setAutoDefault(False)
        button_tone(button, icon=icon)
        button.clicked.connect(callback)
        return button

    def request_action(self, action):
        if self.identity and action in self.visible_actions:
            self.action_requested.emit(action, self.identity[0])

    def set_actions(self, item, actions=()):
        allowed = list(dict.fromkeys(action for _label, action in actions if action in self.buttons))
        if item:
            if item.get("status") == "Pendiente":
                allowed = [action for action in allowed if action != "manual_verify"]
            if item.get("status") in {"Pendiente", "En espera", "Incidencia"} and not any(
                    action in allowed for action in ("upload_file", "retry_video", "review_video")):
                allowed.insert(0, "retry_video" if item["status"] == "Incidencia" else "upload_file")
            if item.get("youtube_id") and "open_video" not in allowed:
                allowed.append("open_video")
            if item.get("status") not in {"Subido", "En curso", "Pendiente"} and "manual_verify" not in allowed:
                allowed.append("manual_verify")
            allowed.append("locate_file")
            if item.get("error"):
                allowed.append("copy_detail")
            if "delete_local" not in allowed:
                allowed.append("delete_local")
        self.visible_actions = list(dict.fromkeys(allowed))
        self.layout_actions()
        self.actions_widget.setVisible(bool(item))

    def layout_actions(self):
        for button in self.buttons.values():
            self.actions_grid.removeWidget(button)
            button.hide()
        for index, action in enumerate(self.visible_actions):
            self.actions_grid.addWidget(self.buttons[action], index // self.action_columns, 1 + index % self.action_columns)
            self.buttons[action].show()
        self.actions_widget.setFixedHeight(((len(self.visible_actions) + self.action_columns - 1) // self.action_columns) * 46 - 6 if self.visible_actions else 0)

    def select(self, item, size="", created=""):
        identity = (item["path"], item.get("signature", "")) if item else None
        if identity != self.identity:
            self.player.set_file(item["path"] if item else "")
            self.identity = identity
            self.fields["duration"][1].setText("-")
        self.title.setText(Path(item["path"]).name if item else t("Selecciona un archivo"))
        self.player.setVisible(bool(item))
        self.path.setVisible(bool(item))
        self.title.setToolTip(item["path"] if item else "")
        self.path.setText(item["path"] if item else "")
        self.path.setToolTip(item["path"] if item else "")
        for pill in self.pills:
            pill.setVisible(bool(item))
        status = item.get("status", "") if item else ""
        for key, value in (("status", t(status)), ("size", size), ("created", created)):
            glyph, label = self.fields[key]
            glyph.setVisible(bool(value))
            label.setVisible(bool(value))
            label.setText(value)
            label.setToolTip(item.get("error", "") if item and key == "status" else value)
        icon, color = STATUS_ICONS.get(status, ("circle-question-mark", "#a7adb8"))
        self.fields["status"][0].setPixmap(app_icon(icon, color).pixmap(18, 18))
        self.fields["status"][1].setStyleSheet(f"color: {color};")
        if not item:
            self.set_actions(None)

    def set_media(self, data):
        seconds = data.get("seconds")
        if isinstance(seconds, (float, int)) and isfinite(seconds) and seconds >= 0:
            self.fields["duration"][1].setText(media_time(round(seconds * 1000)))

    def layout_pills(self, two_columns):
        if self._two_columns == two_columns:
            return
        self._two_columns = two_columns
        columns = 2 if two_columns else 1
        for index, pill in enumerate(self.pills):
            self.info_grid.removeWidget(pill)
            self.info_grid.addWidget(pill, index // columns, index % columns)
        self.info_grid.setColumnStretch(0, 1)
        self.info_grid.setColumnStretch(1, 1 if two_columns else 0)

    def resizeEvent(self, event):
        self.layout_pills(event.size().width() >= 420)
        super().resizeEvent(event)

    def release(self):
        self.player.release()
