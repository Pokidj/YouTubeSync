"""First-run setup with a staged, user-owned OAuth connection."""

import json
import tempfile
import threading
import urllib.request
import webbrowser
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QScrollArea, QStackedWidget, QStyle, QVBoxLayout, QWidget,
)

import youtube_sync_engine as engine


class SetupSignals(QObject):
    connected = Signal(int, object)
    failed = Signal(int, str)


class SetupWizard(QDialog):
    configured = Signal(object)

    GUIDES = [
        ("Crea tu proyecto", "1. Inicia sesion en Google Cloud con tu cuenta.\n"
         "2. Crea un proyecto para tu uso de YouTubeSync.\n3. Selecciona ese proyecto en la barra superior.",
         "Abrir Google Cloud", "https://console.cloud.google.com/projectcreate"),
        ("Activa la API de YouTube", "1. Comprueba que este seleccionado tu proyecto.\n"
         "2. Abre YouTube Data API v3.\n3. Pulsa Habilitar.",
         "Abrir YouTube Data API v3", "https://console.cloud.google.com/apis/library/youtube.googleapis.com"),
        ("Prepara las credenciales", "1. Configura el nombre y los correos de contacto en Google Auth Platform.\n"
         "2. Elige la audiencia adecuada. Si tu proyecto es Externo y esta en Pruebas, anade tu correo como usuario de prueba.\n"
         "3. Crea un ID de cliente OAuth de tipo Aplicacion de escritorio.\n4. Descarga su JSON.",
         "Abrir Credenciales", "https://console.cloud.google.com/apis/credentials"),
    ]

    def __init__(self, store: engine.Store, config: engine.Config, parent=None) -> None:
        super().__init__(parent)
        self.store, self.config = store, replace(config)
        self.channel = None
        self._busy = False
        self._closed = False
        self._generation = 0
        self.session = tempfile.TemporaryDirectory(prefix="setup-", dir=store.base)
        self.staged_token = Path(self.session.name) / "token.json"
        self.signals = SetupSignals(self)
        self.signals.connected.connect(self.connection_ready)
        self.signals.failed.connect(self.connection_failed)
        self.setWindowTitle("Conectar mi canal / YouTubeSync")
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())
        self.resize(780, 660)
        self.setMinimumSize(620, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        self.step = QLabel()
        self.step.setObjectName("Muted")
        layout.addWidget(self.step)
        self.progress = QProgressBar()
        self.progress.setRange(0, 6)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.pages = QStackedWidget()
        scroll.setWidget(self.pages)
        layout.addWidget(scroll, 1)

        welcome = self.page("Conecta tu canal")
        self.paragraph(welcome, "Cuenta de Google / Proyecto propio de Google Cloud")
        existing = QPushButton("Ya tengo mi JSON OAuth")
        existing.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        existing.clicked.connect(lambda: self.go(4))
        welcome.addWidget(existing, alignment=Qt.AlignLeft)
        welcome.addStretch(1)
        for title, body, action, url in self.GUIDES:
            page = self.page(title)
            self.paragraph(page, body)
            button = QPushButton(action)
            button.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
            button.clicked.connect(lambda _checked=False, url=url: webbrowser.open(url))
            page.addWidget(button, alignment=Qt.AlignLeft)
            if title == "Prepara las credenciales":
                audience = QPushButton("Audiencia y usuarios de prueba")
                audience.clicked.connect(lambda: webbrowser.open("https://console.cloud.google.com/auth/audience"))
                page.addWidget(audience, alignment=Qt.AlignLeft)
            page.addStretch(1)

        connection = self.page("Autoriza el acceso")
        self.credential_label = self.paragraph(connection, "Ningun JSON seleccionado")
        self.credential_label.setObjectName("Muted")
        self.import_button = QPushButton("Seleccionar JSON de escritorio")
        self.import_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.import_button.clicked.connect(self.pick_json)
        connection.addWidget(self.import_button, alignment=Qt.AlignLeft)
        self.paragraph(connection, "Autorizacion en el navegador oficial de Google. No se solicita tu contrasena en esta ventana.")
        connection.addStretch(1)

        confirmation = self.page("Confirma tu canal")
        self.avatar = QLabel("YouTube")
        self.avatar.setFixedSize(96, 96)
        self.avatar.setAlignment(Qt.AlignCenter)
        confirmation.addWidget(self.avatar, alignment=Qt.AlignHCenter)
        self.channel_name = self.paragraph(confirmation, "")
        self.channel_name.setObjectName("CardValue")
        self.channel_id = self.paragraph(confirmation, "")
        self.channel_id.setObjectName("Muted")
        self.confirm_channel = QCheckBox("Este es mi canal")
        self.confirm_channel.toggled.connect(self.update_navigation)
        confirmation.addWidget(self.confirm_channel)
        other = QPushButton("Elegir otra cuenta")
        other.clicked.connect(lambda: self.connect_google(force=True))
        confirmation.addWidget(other, alignment=Qt.AlignLeft)
        confirmation.addStretch(1)

        options = self.page("Configura tus subidas")
        self.paragraph(options, "Carpeta de videos")
        folder_row = QHBoxLayout()
        self.folder = QLineEdit(config.watch_folder)
        self.folder.setPlaceholderText("Selecciona una carpeta existente")
        folder_row.addWidget(self.folder, 1)
        pick = QPushButton("Elegir")
        pick.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        pick.clicked.connect(self.pick_folder)
        folder_row.addWidget(pick)
        options.addLayout(folder_row)
        self.recursive = QCheckBox("Incluir subcarpetas")
        self.recursive.setChecked(config.recursive)
        options.addWidget(self.recursive)
        self.paragraph(options, "Privacidad")
        self.privacy = QComboBox()
        for value, label in engine.PRIVACY_LABELS.items():
            self.privacy.addItem(label, value)
        self.privacy.setCurrentIndex(max(0, self.privacy.findData(config.privacy_status)))
        options.addWidget(self.privacy)
        self.paragraph(options, "Lista de reproduccion")
        self.playlist = QComboBox()
        self.playlist.addItem("Sin lista", "")
        options.addWidget(self.playlist)
        self.auto = QCheckBox("Subir automaticamente")
        self.auto.setChecked(False)
        options.addWidget(self.auto)
        options.addStretch(1)

        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.hide()
        layout.addWidget(self.busy)
        self.message = QLabel()
        self.message.setTextFormat(Qt.PlainText)
        self.message.setWordWrap(True)
        self.message.setMinimumWidth(0)
        self.message.setObjectName("Muted")
        layout.addWidget(self.message)
        nav = QHBoxLayout()
        self.later = QPushButton("Configurar mas tarde")
        self.later.clicked.connect(self.reject)
        self.back = QPushButton("Anterior")
        self.back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.back.clicked.connect(lambda: self.go(self.pages.currentIndex() - 1))
        self.next = QPushButton()
        self.next.setObjectName("PrimaryButton")
        self.next.clicked.connect(self.advance)
        nav.addWidget(self.later)
        nav.addStretch(1)
        nav.addWidget(self.back)
        nav.addWidget(self.next)
        layout.addLayout(nav)
        if config.client_secret_path and Path(config.client_secret_path).is_file():
            self.import_file(Path(config.client_secret_path))
        self.go(0)

    def page(self, title: str) -> QVBoxLayout:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(14)
        heading = self.paragraph(layout, title)
        heading.setObjectName("PageTitle")
        self.pages.addWidget(widget)
        return layout

    def paragraph(self, layout, text: str) -> QLabel:
        label = QLabel(text)
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(True)
        label.setMinimumWidth(0)
        layout.addWidget(label)
        return label

    def go(self, index: int) -> None:
        if self._busy:
            return
        self.pages.setCurrentIndex(max(0, min(6, index)))
        self.update_navigation()

    def update_navigation(self) -> None:
        index = self.pages.currentIndex()
        self.step.setText(f"Conexion inicial / {index + 1} de 7")
        self.progress.setValue(index)
        self.back.setEnabled(index > 0 and not self._busy)
        self.import_button.setEnabled(not self._busy)
        self.next.setText({0: "Conectar mi canal", 4: "Conectar con Google", 5: "Configurar carpeta", 6: "Guardar y finalizar"}.get(index, "Siguiente"))
        ready = (bool(self.config.client_secret_path) if index == 4 else
                 bool(self.channel and self.confirm_channel.isChecked()) if index == 5 else True)
        self.next.setEnabled(ready and not self._busy)

    def pick_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona el JSON de Google Cloud", "", "JSON (*.json)")
        if path:
            self.import_file(Path(path))

    def import_file(self, path: Path) -> bool:
        if self._busy:
            return False
        try:
            managed = self.store.import_oauth_json(path)
        except (ValueError, OSError) as exc:
            self.message.setText(str(exc))
            return False
        self.config.client_secret_path = str(managed)
        self.channel = None
        self.confirm_channel.setChecked(False)
        self.staged_token.unlink(missing_ok=True)
        token = self.store.token_path_for(str(managed))
        if token.exists():
            self.staged_token.write_bytes(token.read_bytes())
        self.credential_label.setText("JSON de escritorio preparado / " + managed.name)
        self.message.setText("")
        self.update_navigation()
        return True

    def advance(self) -> None:
        index = self.pages.currentIndex()
        if index == 4:
            self.connect_google()
        elif index == 6:
            self.finish_setup()
        else:
            self.go(index + 1)

    def connect_google(self, force: bool = False) -> None:
        if self._busy or not self.config.client_secret_path:
            return
        self.go(4)
        self._busy = True
        self._generation += 1
        generation = self._generation
        self.busy.show()
        self.message.setText("Esperando autorizacion en Google y comprobando el canal...")
        self.update_navigation()
        threading.Thread(target=self.authorize, args=(generation, force), daemon=True).start()

    def authorize(self, generation: int, force: bool) -> None:
        try:
            if self._closed:
                return
            client = engine.YouTubeClient(self.store, self.config, lambda _text: None, force_authorize=force)
            client.token_path = self.staged_token
            info = client.channel_info()
            if not info.get("id"):
                raise ValueError("Google no ha devuelto un canal valido.")
            warning, playlists, avatar = "", [], b""
            try:
                playlists = client.playlists()
            except Exception:
                warning = "Canal conectado. No se pudieron cargar las listas; puedes reintentarlo en Ajustes."
            if not self._closed and info.get("thumbnail"):
                try:
                    request = urllib.request.Request(info["thumbnail"], headers={"User-Agent": engine.APP_NAME})
                    with urllib.request.urlopen(request, timeout=5) as response:
                        avatar = response.read(2 * 1024 * 1024)
                except Exception:
                    pass
            if not self._closed:
                self.signals.connected.emit(generation, {"info": info, "playlists": playlists, "avatar": avatar, "warning": warning})
        except Exception as exc:
            if not self._closed:
                text = engine.youtube_error_message(exc) if engine.is_youtube_quota_error(exc) else engine.describe_error(exc)
                self.signals.failed.emit(generation, text[:500])
        finally:
            if self._closed:
                self.session.cleanup()

    def connection_ready(self, generation: int, result: dict) -> None:
        if self._closed or generation != self._generation:
            return
        self._busy = False
        self.busy.hide()
        self.channel = result["info"]
        self.channel_name.setText(self.channel.get("title", "Canal de YouTube"))
        self.channel_id.setText(self.channel["id"])
        self.confirm_channel.setChecked(False)
        pixmap = QPixmap()
        self.avatar.clear()
        self.avatar.setText("YouTube")
        if pixmap.loadFromData(result["avatar"]):
            self.avatar.setPixmap(pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.playlist.clear()
        self.playlist.addItem("Sin lista", "")
        for item in result["playlists"]:
            if item.get("id"):
                self.playlist.addItem(item.get("title", "Lista"), item["id"])
        self.playlist.setCurrentIndex(max(0, self.playlist.findData(self.config.playlist_id)))
        self.message.setText(result["warning"])
        self.go(5)

    def connection_failed(self, generation: int, message: str) -> None:
        if self._closed or generation != self._generation:
            return
        self._busy = False
        self.busy.hide()
        self.channel = None
        help_text = ("Puedes configurar mas tarde y reintentar cuando se renueve la cuota."
                     if engine.is_youtube_quota_error(message) else
                     "Revisa que la API este habilitada y tu correo figure como usuario de prueba si el proyecto esta en Pruebas.")
        self.message.setText(message + "\n" + help_text)
        self.update_navigation()

    def finish_setup(self) -> None:
        if not self.channel or not self.confirm_channel.isChecked():
            self.message.setText("Confirma primero el canal conectado.")
            return
        folder = Path(self.folder.text().strip())
        if not self.folder.text().strip() or not folder.is_dir():
            self.message.setText("Selecciona una carpeta existente para los videos.")
            return
        if not self.staged_token.is_file():
            self.message.setText("La autorizacion no se completo. Vuelve a conectar con Google.")
            return
        self.config.watch_folder = str(folder)
        self.config.recursive = self.recursive.isChecked()
        self.config.privacy_status = self.privacy.currentData()
        self.config.playlist_id = self.playlist.currentData() or ""
        self.config.playlist_name = self.playlist.currentText()
        self.config.auto_start_enabled = self.auto.isChecked()
        self.config.connected_channel_id = self.channel["id"]
        self.config.connected_channel_name = self.channel.get("title", "")
        token = self.store.token_path_for(self.config.client_secret_path)
        temporary = None
        try:
            old_token = token.read_bytes() if token.exists() else None
            with tempfile.NamedTemporaryFile(dir=self.store.base, suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                output.write(self.staged_token.read_bytes())
            temporary.replace(token)
            try:
                self.store.save_config(self.config)
            except Exception:
                if old_token is None:
                    token.unlink(missing_ok=True)
                else:
                    token.write_bytes(old_token)
                raise
        except OSError:
            self.message.setText("No se pudo guardar la configuracion. Comprueba los permisos de la carpeta de datos y reintenta.")
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.configured.emit(self.config)
        self.accept()

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Carpeta de videos", self.folder.text())
        if folder:
            self.folder.setText(folder)

    def done(self, result: int) -> None:
        self._closed = True
        if not self._busy:
            self.session.cleanup()
        super().done(result)
