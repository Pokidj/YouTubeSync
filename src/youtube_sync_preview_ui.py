"""Shared details and control sizing for local and YouTube previews."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout

from youtube_sync_i18n_widgets import QLabel, RawLabel
from youtube_sync_icons import app_icon, button_tone


class PreviewInfoPill(QFrame):
    def __init__(self, title, icon, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoPill")
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        heading = QHBoxLayout()
        heading.setSpacing(6)
        self.glyph = QLabel()
        self.glyph.setFixedSize(18, 18)
        self.glyph.setToolTip(title)
        self.glyph.setPixmap(app_icon(icon).pixmap(18, 18))
        self.heading = QLabel(title)
        self.heading.setObjectName("Muted")
        heading.addWidget(self.glyph)
        heading.addWidget(self.heading, 1)
        column.addLayout(heading)
        self.value = RawLabel("-")
        self.value.setTextFormat(Qt.PlainText)
        self.value.setWordWrap(True)
        self.value.setMinimumWidth(0)
        self.value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        column.addWidget(self.value)


def style_player_tool(button, icon):
    button.setIconSize(QSize(20, 20))
    button.setFixedSize(38, 36)
    button.setStyleSheet("padding: 4px; min-height: 20px;")
    button_tone(button, icon=icon)
