from collections import deque
from dataclasses import dataclass
from datetime import datetime
import platform
import re
from urllib.parse import urlsplit, urlunsplit

from PySide6.QtCore import QObject, QIODevice, QSaveFile, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from youtube_sync_icons import app_icon
from youtube_sync_version import APP_VERSION
from youtube_sync_i18n import t
from youtube_sync_i18n_widgets import QCheckBox, QComboBox, QFileDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QWidget


def redact_secrets(text: str) -> str:
    text = re.sub(r"(?im)^(\s*(?:authorization|cookie|set-cookie)\s*:\s*).+$", lambda match: match[1] + "[OCULTO]", text)
    text = re.sub(r"(?i)\bBearer\s+[^\s\"']+", "Bearer [OCULTO]", text)
    text = re.sub(r'''(?i)(["']?(?:access_token|refresh_token|client_secret|id_token|authorization|cookie|password|code_verifier)["']?\s*[:=]\s*)(["'])(.*?)\2''',
                  lambda match: match[1] + match[2] + "[OCULTO]" + match[2], text)
    text = re.sub(r'''(?i)((?:[?&]|\b)(?:access_token|refresh_token|client_secret|id_token|upload_id|key|code|password|code_verifier)=)[^&\s"']+''',
                  lambda match: match[1] + "[OCULTO]", text)

    def redact_url(match):
        try:
            parsed = urlsplit(match[0])
            if "@" in parsed.netloc:
                return urlunsplit(parsed._replace(netloc="[OCULTO]@" + parsed.netloc.rsplit("@", 1)[1]))
        except ValueError:
            pass
        return match[0]

    return re.sub(r'''https?://[^\s<>"']+''', redact_url, text)


@dataclass(frozen=True)
class DiagnosticEntry:
    timestamp: str
    level: str
    source: str
    message: str

    def text(self) -> str:
        message = t(self.message).replace("\n", "\n    ")
        return f"{self.timestamp} [{self.level}] [{t(self.source)}] {message}"


class DiagnosticBuffer(QObject):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.entries = deque(maxlen=2000)

    def append(self, message: str, source: str = "Servicio", level: str | None = None) -> None:
        message = redact_secrets(str(message))
        message = re.sub(r"^\[\d{2}:\d{2}:\d{2}\]\s*", "", message)
        if level is None:
            lower = message.casefold()
            level = "ERROR" if any(word in lower for word in ("error", "exception", "traceback", "no se pudo", "no se pudieron", "fallo", "denegad")) else (
                "WARNING" if any(word in lower for word in ("cuota", "limite", "cancelad", "por verificar", "sin confirmar", "no hay datos suficientes", "no se sube ni se borra")) else "INFO")
        self.entries.append(DiagnosticEntry(datetime.now().astimezone().isoformat(timespec="seconds"), level, source, message))
        self.changed.emit()

    def clear(self) -> None:
        self.entries.clear()
        self.changed.emit()

    def report(self, entries=None) -> str:
        selected = list(self.entries if entries is None else entries)
        header = f"YouTubeSync {APP_VERSION}\n{t('Fecha')}: {datetime.now().astimezone().isoformat(timespec='seconds')}\n{t('Sistema')}: {platform.system()} {platform.release()} / Python {platform.python_version()}\n"
        return header + "\n" + "\n".join(entry.text() for entry in selected)


class DiagnosticHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        for marker, color in (("[ERROR]", "#ff8b98"), ("[WARNING]", "#efc26d")):
            if marker in text:
                style = QTextCharFormat()
                style.setForeground(QColor(color))
                self.setFormat(0, len(text), style)
                break


class DiagnosticWindow(QWidget):
    def __init__(self, buffer: DiagnosticBuffer, parent=None) -> None:
        super().__init__(parent, Qt.Window)
        self.buffer = buffer
        self.setWindowTitle("Consola / YouTubeSync")
        self.setWindowIcon(app_icon("terminal"))
        self.resize(1060, 680)
        self.setMinimumSize(760, 440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        heading = QHBoxLayout()
        title = QLabel("Consola")
        title.setObjectName("PageTitle")
        heading.addWidget(title)
        heading.addStretch(1)
        for label, name, callback in (("Copiar errores", "circle-exclamation-point", self.copy_errors),
                                      ("Copiar informe", "copy", self.copy_report), ("", "download", self.export_report),
                                      ("", "trash", self.buffer.clear)):
            button = QPushButton(label)
            button.setIcon(app_icon(name))
            tooltip = label or ("Guardar informe" if name == "download" else "Limpiar registro temporal")
            button.setToolTip("Copiar avisos y errores" if label == "Copiar errores" else tooltip)
            button.setAccessibleName(tooltip)
            button.clicked.connect(callback)
            heading.addWidget(button)
        layout.addLayout(heading)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar mensaje, archivo o codigo de error")
        self.search.addAction(app_icon("search"), QLineEdit.LeadingPosition)
        self.level_filter = QComboBox()
        self.level_filter.addItems(["Todo", "Avisos y errores", "Solo errores"])
        self.source_filter = QComboBox()
        self.source_filter.addItem("Todos los origenes")
        self.follow = QCheckBox("Seguir")
        self.follow.setChecked(True)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.level_filter)
        filters.addWidget(self.source_filter)
        filters.addWidget(self.follow)
        layout.addLayout(filters)
        self.viewer = QPlainTextEdit()
        self.viewer.setObjectName("DiagnosticText")
        self.viewer.setReadOnly(True)
        self.viewer.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.highlighter = DiagnosticHighlighter(self.viewer.document())
        layout.addWidget(self.viewer, 1)
        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        layout.addWidget(self.summary)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render)
        buffer.changed.connect(self.schedule_render)
        for signal in (self.search.textChanged, self.level_filter.currentTextChanged, self.source_filter.currentTextChanged):
            signal.connect(self.filter_changed)
        self.viewer.selectionChanged.connect(self.schedule_render)
        self.render()

    def schedule_render(self, *_args) -> None:
        if self.isVisible() and not self.render_timer.isActive():
            self.render_timer.start(80)

    def filter_changed(self, *_args) -> None:
        cursor = self.viewer.textCursor()
        cursor.clearSelection()
        self.viewer.setTextCursor(cursor)
        self.schedule_render()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        cursor = self.viewer.textCursor()
        cursor.clearSelection()
        self.viewer.setTextCursor(cursor)
        self.render()

    def filtered_entries(self) -> list[DiagnosticEntry]:
        query = self.search.text().casefold().strip()
        level, source = self.level_filter.currentIndex(), self.source_filter.currentText()
        return [entry for entry in self.buffer.entries
                if (not query or query in entry.text().casefold())
                and (not level or entry.level in ({"ERROR", "WARNING"} if level == 1 else {"ERROR"}))
                and (source == "Todos los origenes" or entry.source == source)]

    def render(self) -> None:
        if self.viewer.textCursor().hasSelection() and self.buffer.entries:
            return
        sources = ["Todos los origenes"] + sorted({entry.source for entry in self.buffer.entries})
        current = self.source_filter.currentText()
        if sources != [self.source_filter.itemText(index) for index in range(self.source_filter.count())]:
            self.source_filter.blockSignals(True)
            self.source_filter.clear()
            self.source_filter.addItems(sources)
            self.source_filter.setCurrentText(current if current in sources else sources[0])
            self.source_filter.blockSignals(False)
        visible = self.filtered_entries()
        scrollbar = self.viewer.verticalScrollBar()
        position = scrollbar.value()
        self.viewer.blockSignals(True)
        self.viewer.setPlainText("\n".join(entry.text() for entry in visible))
        self.viewer.blockSignals(False)
        scrollbar.setValue(scrollbar.maximum() if self.follow.isChecked() else position)
        errors = sum(entry.level == "ERROR" for entry in self.buffer.entries)
        warnings = sum(entry.level == "WARNING" for entry in self.buffer.entries)
        self.summary.setText(f"{len(visible)} de {len(self.buffer.entries)} mensajes / {errors} errores / {warnings} avisos")

    def copy_report(self) -> None:
        QApplication.clipboard().setText(self.buffer.report())

    def copy_errors(self) -> None:
        QApplication.clipboard().setText(self.buffer.report(entry for entry in self.buffer.entries if entry.level in {"ERROR", "WARNING"}))

    def export_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Guardar diagnostico", "YouTubeSync-diagnostico.log", "Registro (*.log)")
        if not path:
            return
        output = QSaveFile(path)
        if not output.open(QIODevice.WriteOnly):
            self.buffer.append("No se pudo exportar el informe: " + output.errorString(), "Consola", "ERROR")
            QMessageBox.warning(self, "Consola", output.errorString())
            return
        data = self.buffer.report().encode("utf-8")
        if output.write(data) != len(data) or not output.commit():
            output.cancelWriting()
            QMessageBox.warning(self, "Consola", "No se pudo guardar el informe completo.")
