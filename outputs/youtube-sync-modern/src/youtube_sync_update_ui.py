"""Manual update checks and downloads, independent of YouTube authorization."""

import os
import threading
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QStyle, QTextEdit,
    QVBoxLayout, QWidget,
)

from youtube_sync_updater import DownloadCancelled, ReleaseClient, RELEASES_URL
from youtube_sync_version import APP_VERSION


class UpdateSignals(QObject):
    checked = Signal(object)
    downloaded = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)


class UpdatePanel(QWidget):
    def __init__(self, data_folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("UpdatePanel")
        self.setStyleSheet("#UpdatePanel, #UpdateActions { background: transparent; }")
        self.folder = data_folder / "updates"
        self.client = ReleaseClient()
        self.release = None
        self.downloaded_path = None
        self.closed = False
        self.cancel = threading.Event()
        self.signals = UpdateSignals(self)
        self.signals.checked.connect(self.checked)
        self.signals.downloaded.connect(self.downloaded)
        self.signals.failed.connect(self.failed)
        self.signals.progress.connect(self.show_progress)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        row = QHBoxLayout()
        version = QLabel(f"YouTubeSync {APP_VERSION}")
        version.setObjectName("CardValue")
        row.addWidget(version, 1)
        self.check_button = QPushButton("Buscar actualizaciones")
        self.check_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.check_button.clicked.connect(self.check)
        row.addWidget(self.check_button)
        layout.addLayout(row)
        self.status = QLabel("Sin comprobar")
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        self.status.setObjectName("Muted")
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.actions = QWidget()
        self.actions.setObjectName("UpdateActions")
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(0, 0, 0, 0)
        self.download_button = QPushButton("Descargar")
        self.download_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.download_button.setObjectName("PrimaryButton")
        self.download_button.clicked.connect(self.download)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.cancel_button.clicked.connect(self.cancel.set)
        self.cancel_button.hide()
        self.notes_button = QPushButton("Notas")
        self.notes_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.notes_button.clicked.connect(self.show_notes)
        self.open_button = QPushButton("Abrir carpeta")
        self.open_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.open_button.clicked.connect(self.open_folder)
        self.open_button.hide()
        release_button = QPushButton("GitHub")
        release_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        release_button.clicked.connect(lambda: webbrowser.open(self.release.url if self.release else RELEASES_URL))
        for button in (self.download_button, self.cancel_button, self.notes_button, self.open_button):
            actions.addWidget(button)
        actions.addStretch(1)
        actions.addWidget(release_button)
        layout.addWidget(self.actions)
        self.actions.hide()

    def check(self) -> None:
        if not self.check_button.isEnabled() or self.closed:
            return
        self.release = None
        self.downloaded_path = None
        self.check_button.setEnabled(False)
        self.open_button.hide()
        self.actions.hide()
        self.progress.setRange(0, 0)
        self.progress.show()
        self.status.setText("Consultando Releases de GitHub...")
        threading.Thread(target=self.check_thread, daemon=True).start()

    def check_thread(self) -> None:
        try:
            result = self.client.latest()
            if not self.closed:
                self.signals.checked.emit(result)
        except Exception as exc:
            if not self.closed:
                self.signals.failed.emit(str(exc))

    def checked(self, release) -> None:
        if self.closed:
            return
        self.check_button.setEnabled(True)
        self.progress.hide()
        self.release = release
        if release is None:
            self.actions.show()
            self.download_button.hide()
            self.notes_button.setEnabled(False)
            self.status.setText("No hay una release estable publica disponible.")
            return
        self.actions.show()
        available = release.is_newer()
        self.download_button.setVisible(available)
        self.download_button.setEnabled(available and release.asset is not None)
        self.download_button.setText(f"Descargar {release.version}")
        self.cancel_button.hide()
        self.notes_button.setEnabled(True)
        if not available:
            self.status.setText("No hay una version posterior publicada.")
        elif release.asset is None:
            self.status.setText(f"Version {release.version} publicada / falta el paquete Windows x64.")
        else:
            self.status.setText(f"Disponible {release.version} / {release.asset.size / (1024 * 1024):.1f} MB")

    def download(self) -> None:
        if not self.release or not self.release.asset or not self.download_button.isEnabled() or self.closed:
            return
        self.cancel.clear()
        self.check_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.cancel_button.show()
        self.open_button.hide()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.show()
        self.status.setText("Descargando desde GitHub...")
        threading.Thread(target=self.download_thread, args=(self.release,), daemon=True).start()

    def download_thread(self, release) -> None:
        try:
            path = self.client.download(release, self.folder, self.cancel, self.report_progress)
            if not self.closed:
                self.signals.downloaded.emit(path)
        except DownloadCancelled:
            if not self.closed:
                self.signals.failed.emit("Descarga cancelada. Puedes reintentar.")
        except Exception as exc:
            if not self.closed:
                self.signals.failed.emit(str(exc))

    def report_progress(self, received: int, total: int) -> None:
        if not self.closed:
            self.signals.progress.emit(received, total)

    def show_progress(self, received: int, total: int) -> None:
        self.progress.setValue(round(received * 100 / max(1, total)))
        self.status.setText(f"Descargando / {received / (1024 * 1024):.1f} de {total / (1024 * 1024):.1f} MB")

    def downloaded(self, path: Path) -> None:
        if self.closed:
            return
        self.downloaded_path = path
        self.check_button.setEnabled(True)
        self.download_button.hide()
        self.cancel_button.hide()
        self.open_button.show()
        self.progress.setValue(100)
        self.status.setText(f"Descarga verificada / {path.name}")

    def failed(self, message: str) -> None:
        if self.closed:
            return
        self.check_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress.hide()
        self.download_button.setEnabled(bool(self.release and self.release.asset and self.release.is_newer()))
        self.status.setText(message)

    def show_notes(self) -> None:
        if not self.release:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"YouTubeSync {self.release.version}")
        dialog.resize(640, 480)
        layout = QVBoxLayout(dialog)
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(self.release.notes)
        layout.addWidget(notes)
        close = QPushButton("Cerrar")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def open_folder(self) -> None:
        if self.downloaded_path and self.downloaded_path.is_file():
            os.startfile(str(self.downloaded_path.parent))

    def shutdown(self) -> None:
        self.closed = True
        self.cancel.set()
