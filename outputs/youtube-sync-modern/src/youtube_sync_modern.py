import os
import queue
import sys
import threading
import urllib.request
import webbrowser
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QEvent, QRect, QSize, QTimer, Qt, Signal, QObject
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "YouTubeSync"
APP_VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[1]


import youtube_sync_engine as engine


def asset_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", ROOT))
    return base / "assets" / name


def table_item(text: str, color: str = "") -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    if color:
        item.setForeground(QColor(color))
    return item


class PreviewThumbnail(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._source = QPixmap()
        self._placeholder = "Sin miniatura"
        self.setObjectName("PreviewThumb")
        self.setMinimumSize(0, 96)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return max(96, round(width * 9 / 16))

    def sizeHint(self) -> QSize:
        return QSize(320, 180)

    def set_image(self, data: bytes) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self._source = pixmap
        if pixmap.isNull():
            self.clear_image("Sin imagen")
            return
        self.update()

    def clear_image(self, text: str = "Sin miniatura") -> None:
        self._source = QPixmap()
        self._placeholder = text
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0b0b0c"))
        if self._source.isNull():
            painter.setPen(QColor("#a7adb8"))
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder)
            return
        size = self._source.size().scaled(self.size(), Qt.KeepAspectRatio)
        target = QRect(0, 0, size.width(), size.height())
        target.moveCenter(self.rect().center())
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(target, self._source)


class ChannelLoader(QObject):
    finished = Signal(object, object)
    failed = Signal(str)
    cached = Signal(str)

    def __init__(self, store, config) -> None:
        super().__init__()
        self.store = store
        self.config = config

    def start(self) -> None:
        threading.Thread(target=self.run, daemon=True).start()

    def run(self) -> None:
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda _text: None)
            videos, playlists = client.channel_gallery()
            self.finished.emit(videos, playlists)
        except Exception as exc:
            if engine.is_youtube_quota_error(exc):
                snapshot = self.store.service_cache(engine.api_scope(self.config.client_secret_path), "gallery")
                if snapshot:
                    self.finished.emit(snapshot["data"]["videos"], snapshot["data"]["playlists"])
                    self.cached.emit(snapshot["checked_at"])
                    return
            self.failed.emit(engine.describe_error(exc))


class OAuthWizard(QDialog):
    json_selected = Signal(str)

    STEPS = [
        {
            "title": "1 de 4 - Crea un proyecto en Google",
            "body": (
                "Necesitas un proyecto en Google Cloud para dar acceso a la API de YouTube.\n\n"
                "1. Abre Google Cloud Console.\n"
                "2. Inicia sesion con la cuenta del canal.\n"
                "3. Crea un proyecto nuevo con cualquier nombre.\n"
                "4. Cuando lo tengas, pulsa Siguiente."
            ),
            "button": "Abrir Google Cloud Console",
            "url": "https://console.cloud.google.com/projectcreate",
        },
        {
            "title": "2 de 4 - Activa YouTube Data API v3",
            "body": (
                "Ahora activa la API de YouTube en ese proyecto.\n\n"
                "1. Asegurate de tener seleccionado tu proyecto arriba.\n"
                "2. Pulsa el boton azul Habilitar.\n"
                "3. Cuando este activada, pulsa Siguiente."
            ),
            "button": "Activar YouTube Data API v3",
            "url": "https://console.cloud.google.com/apis/library/youtube.googleapis.com",
        },
        {
            "title": "3 de 4 - Crea las credenciales",
            "body": (
                "Crea un ID de cliente OAuth.\n\n"
                "1. Ve a Crear credenciales.\n"
                "2. Elige ID de cliente OAuth.\n"
                "3. Si pide pantalla de consentimiento, usa Externo y completa lo basico.\n"
                "4. Tipo de aplicacion: Aplicacion de escritorio.\n"
                "5. Descarga el JSON."
            ),
            "button": "Ir a Credenciales",
            "url": "https://console.cloud.google.com/apis/credentials",
        },
        {
            "title": "4 de 4 - Selecciona el JSON",
            "body": (
                "Selecciona el archivo JSON descargado.\n\n"
                "La primera vez que conectes YouTube se abrira el navegador para autorizar la app."
            ),
            "button": "Seleccionar archivo JSON",
            "url": "",
        },
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.index = 0
        self.setWindowTitle("Asistente JSON OAuth")
        self.setWindowIcon(QIcon(str(asset_path("youtube-sync.ico"))))
        self.setMinimumSize(620, 430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.title = QLabel()
        self.title.setObjectName("PageTitle")
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setObjectName("WizardBody")
        self.main_button = QPushButton()
        self.main_button.setObjectName("PrimaryButton")
        self.main_button.clicked.connect(self.primary_action)
        nav = QHBoxLayout()
        self.prev_button = QPushButton("Anterior")
        self.next_button = QPushButton("Siguiente")
        close_button = QPushButton("Cerrar")
        self.prev_button.clicked.connect(self.previous_step)
        self.next_button.clicked.connect(self.next_step)
        close_button.clicked.connect(self.close)
        nav.addWidget(self.prev_button)
        nav.addStretch(1)
        nav.addWidget(self.next_button)
        nav.addWidget(close_button)
        layout.addWidget(self.title)
        layout.addWidget(self.body, 1)
        layout.addWidget(self.main_button)
        layout.addLayout(nav)
        self.render()

    def render(self) -> None:
        step = self.STEPS[self.index]
        self.title.setText(step["title"])
        self.body.setText(step["body"])
        self.main_button.setText(step["button"])
        self.prev_button.setEnabled(self.index > 0)
        self.next_button.setText("Finalizar" if self.index == len(self.STEPS) - 1 else "Siguiente")

    def primary_action(self) -> None:
        step = self.STEPS[self.index]
        if step["url"]:
            webbrowser.open(step["url"])
            return
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona JSON OAuth", "", "JSON (*.json)")
        if path:
            self.json_selected.emit(path)
            self.close()

    def previous_step(self) -> None:
        self.index = max(0, self.index - 1)
        self.render()

    def next_step(self) -> None:
        if self.index == len(self.STEPS) - 1:
            self.close()
            return
        self.index += 1
        self.render()


class SettingsDialog(QWidget):
    saved = Signal()

    def __init__(self, store, config, parent=None) -> None:
        super().__init__(parent, Qt.Window)
        self.store = store
        self.config = config
        self.playlists_by_label = {config.playlist_name or "Ninguna": config.playlist_id}
        self.setWindowTitle("Ajustes")
        self.setWindowIcon(QIcon(str(asset_path("youtube-sync.ico"))))
        self.build_settings(config)

    def build_settings(self, config) -> None:
        self.resize(1040, 760)
        self.setMinimumSize(900, 650)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(14)

        title = QLabel("Ajustes")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Opciones organizadas por area. Todo se guarda al pulsar Guardar.")
        subtitle.setObjectName("Muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.settings_search = QLineEdit()
        self.settings_search.setPlaceholderText("Buscar ajuste: carpeta, privacidad, lista, auto, limpieza...")
        layout.addWidget(self.settings_search)

        self.settings_sections = []
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        def tab_page(name: str) -> tuple[QWidget, QVBoxLayout]:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(12, 12, 12, 12)
            page_layout.setSpacing(14)
            tabs.addTab(page, name)
            return page, page_layout

        def tracked_section(parent_layout: QVBoxLayout, title_text: str, terms: str) -> QFrame:
            frame = self.section(title_text)
            parent_layout.addWidget(frame)
            self.settings_sections.append((frame, tabs.count() - 1, f"{title_text} {terms}".casefold()))
            return frame

        general_page, general_layout = tab_page("General")
        youtube_page, youtube_tab_layout = tab_page("YouTube")
        automation_page, automation_tab_layout = tab_page("Automatizacion")
        cleanup_page, cleanup_tab_layout = tab_page("Limpieza")

        app_section = tracked_section(general_layout, "Aplicacion", "version actualizacion updater")
        app_layout = app_section.layout()
        version_row = QHBoxLayout()
        version_label = QLabel(f"{APP_NAME} {APP_VERSION}")
        version_label.setObjectName("CardValue")
        updater_button = QPushButton("Buscar actualizaciones")
        updater_button.setEnabled(False)
        updater_button.setToolTip("Preparado para activar el actualizador en una version futura.")
        version_row.addWidget(version_label, 1)
        version_row.addWidget(updater_button, 0)
        app_layout.addLayout(version_row)
        updater_hint = QLabel("Actualizador preparado para una proxima version.")
        updater_hint.setObjectName("Muted")
        app_layout.addWidget(updater_hint)

        folder = tracked_section(general_layout, "Carpeta", "videos extensiones subcarpetas ruta")
        folder_layout = folder.layout()
        self.folder = self.path_row(folder_layout, "Carpeta de videos", config.watch_folder, self.pick_folder)
        self.extensions = QLineEdit(config.extensions)
        folder_layout.addLayout(self.field_row("Extensiones", self.extensions))
        self.recursive = QCheckBox("Incluir subcarpetas")
        self.recursive.setChecked(bool(config.recursive))
        folder_layout.addWidget(self.recursive)
        general_layout.addStretch(1)

        youtube = tracked_section(youtube_tab_layout, "YouTube / OAuth", "json oauth credenciales privacidad categoria")
        youtube_layout = youtube.layout()
        self.oauth = self.path_row(youtube_layout, "JSON OAuth", config.client_secret_path, self.pick_json)
        oauth_tools = QHBoxLayout()
        wizard_button = QPushButton("Asistente JSON")
        wizard_button.clicked.connect(self.open_oauth_wizard)
        oauth_tools.addStretch(1)
        oauth_tools.addWidget(wizard_button)
        youtube_layout.addLayout(oauth_tools)

        self.privacy = QComboBox()
        self.privacy.addItems(["Privado", "Oculto", "Publico"])
        privacy_label = {"private": "Privado", "unlisted": "Oculto", "public": "Publico"}.get(config.privacy_status, "Privado")
        self.privacy.setCurrentText(privacy_label)
        youtube_layout.addLayout(self.field_row("Privacidad", self.privacy))

        self.category = QComboBox()
        self.category.addItems(list(engine.CATEGORIES.keys()))
        self.category.setCurrentText(engine.CATEGORY_NAMES_BY_ID.get(config.category_id, "Gente y blogs"))
        youtube_layout.addLayout(self.field_row("Categoria", self.category))

        playlist = tracked_section(youtube_tab_layout, "Lista de reproduccion", "playlist lista cargar crear")
        playlist_layout = playlist.layout()
        playlist_row = QHBoxLayout()
        self.playlist_combo = QComboBox()
        self.playlist_combo.addItems(list(self.playlists_by_label.keys()) or ["Ninguna"])
        self.playlist_combo.setCurrentText(config.playlist_name or "Ninguna")
        load_playlists = QPushButton("Cargar listas")
        create_playlist = QPushButton("Crear lista")
        load_playlists.clicked.connect(self.load_playlists)
        create_playlist.clicked.connect(self.create_playlist)
        playlist_row.addWidget(QLabel("Lista"), 0)
        playlist_row.addWidget(self.playlist_combo, 1)
        playlist_row.addWidget(load_playlists, 0)
        playlist_row.addWidget(create_playlist, 0)
        playlist_layout.addLayout(playlist_row)
        youtube_tab_layout.addStretch(1)

        automation = tracked_section(automation_tab_layout, "Automatizacion", "auto on inicio windows minimizada revisar estabilidad")
        automation_layout = automation.layout()
        self.auto_start = QCheckBox("Arrancar con Auto ON")
        self.auto_start.setChecked(bool(config.auto_start_enabled))
        automation_layout.addWidget(self.auto_start)
        self.start_minimized = QCheckBox("Arrancar minimizada")
        self.start_minimized.setChecked(bool(config.start_minimized))
        automation_layout.addWidget(self.start_minimized)
        self.close_to_tray = QCheckBox("Al cerrar, dejar en bandeja")
        self.close_to_tray.setChecked(bool(getattr(config, "close_to_tray", True)))
        automation_layout.addWidget(self.close_to_tray)
        self.run_at_startup = QCheckBox("Iniciar con Windows")
        self.run_at_startup.setChecked(bool(config.run_at_startup))
        automation_layout.addWidget(self.run_at_startup)
        self.scan_interval = QSpinBox()
        self.scan_interval.setRange(2, 3600)
        self.scan_interval.setValue(int(config.scan_interval_seconds))
        automation_layout.addLayout(self.field_row("Revisar cada (segundos)", self.scan_interval))
        self.stable_wait = QSpinBox()
        self.stable_wait.setRange(2, 600)
        self.stable_wait.setValue(int(config.stable_wait_seconds))
        automation_layout.addLayout(self.field_row("Esperar estabilidad (segundos)", self.stable_wait))
        automation_tab_layout.addStretch(1)

        cleanup = tracked_section(cleanup_tab_layout, "Limpieza local", "borrar eliminar locales subidos minutos horas dias")
        cleanup_layout = cleanup.layout()
        self.auto_delete = QCheckBox("Borrar automaticamente archivos locales ya subidos")
        self.auto_delete.setChecked(bool(config.auto_delete_uploaded))
        cleanup_layout.addWidget(self.auto_delete)
        cleanup_row = QHBoxLayout()
        self.cleanup_delay = QSpinBox()
        self.cleanup_delay.setRange(1, 525600)
        self.cleanup_delay.setValue(int(config.auto_delete_after_hours))
        self.cleanup_unit = QComboBox()
        self.cleanup_unit.addItems(["minutos", "horas", "dias"])
        self.cleanup_unit.setCurrentText(config.auto_delete_after_unit if config.auto_delete_after_unit in {"minutos", "horas", "dias"} else "horas")
        cleanup_row.addWidget(QLabel("Borrar tras"), 0)
        cleanup_row.addWidget(self.cleanup_delay, 1)
        cleanup_row.addWidget(self.cleanup_unit, 1)
        cleanup_layout.addLayout(cleanup_row)
        cleanup_tab_layout.addStretch(1)
        self.settings_search.textChanged.connect(lambda text, tabs=tabs: self.filter_settings_sections(text, tabs))

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancelar")
        save = QPushButton("Guardar")
        save.setObjectName("PrimaryButton")
        cancel.clicked.connect(self.close)
        save.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def section(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("SettingsSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        label = QLabel(title.upper())
        label.setObjectName("SectionTitle")
        layout.addWidget(label)
        return frame

    def filter_settings_sections(self, query: str, tabs: QTabWidget) -> None:
        text = query.strip().casefold()
        first_match = None
        for frame, tab_index, terms in getattr(self, "settings_sections", []):
            visible = not text or text in terms
            frame.setVisible(visible)
            if visible and first_match is None:
                first_match = tab_index
        if text and first_match is not None and tabs.currentIndex() != first_match:
            tabs.setCurrentIndex(first_match)

    def path_row(self, parent: QVBoxLayout, label: str, value: str, callback) -> QLineEdit:
        edit = QLineEdit(value)
        button = QPushButton("Elegir")
        button.clicked.connect(callback)
        row = QHBoxLayout()
        row.addWidget(QLabel(label), 0)
        row.addWidget(edit, 1)
        row.addWidget(button, 0)
        parent.addLayout(row)
        return edit

    def field_row(self, label: str, widget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label), 0)
        row.addWidget(widget, 1)
        return row

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecciona carpeta", self.folder.text())
        if folder:
            self.folder.setText(folder)

    def pick_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona JSON OAuth", "", "JSON (*.json)")
        if path:
            self.oauth.setText(path)

    def open_oauth_wizard(self) -> None:
        wizard = OAuthWizard(self)
        wizard.json_selected.connect(self.oauth.setText)
        wizard.exec()

    def load_playlists(self) -> None:
        path = self.oauth.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "Listas", "Selecciona primero un JSON OAuth valido.")
            return
        try:
            temp_config = replace(self.config)
            temp_config.client_secret_path = path
            client = engine.YouTubeClient(self.store, temp_config, lambda _text: None)
            self.set_playlist_options(client.playlists(), selected_id=self.config.playlist_id)
        except Exception as exc:
            QMessageBox.warning(self, "Listas", f"No se pudieron cargar las listas:\n\n{engine.describe_error(exc)}")

    def set_playlist_options(self, playlists: list[dict], selected_id: str = "") -> None:
        self.playlists_by_label = {}
        labels = []
        used = set()
        for item in playlists:
            label = item.get("title", "Lista sin nombre")
            playlist_id = item.get("id", "")
            if label in used:
                label = f"{label} / {playlist_id[-6:]}"
            used.add(label)
            labels.append(label)
            self.playlists_by_label[label] = playlist_id
        self.playlist_combo.clear()
        self.playlist_combo.addItems(labels or ["Ninguna"])
        for label, playlist_id in self.playlists_by_label.items():
            if playlist_id == selected_id:
                self.playlist_combo.setCurrentText(label)
                break

    def create_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "Crear lista", "Nombre de la lista:")
        if not ok or not name.strip():
            return
        path = self.oauth.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "Crear lista", "Selecciona primero un JSON OAuth valido.")
            return
        try:
            temp_config = replace(self.config)
            temp_config.client_secret_path = path
            temp_config.privacy_status = {"Privado": "private", "Oculto": "unlisted", "Publico": "public"}[self.privacy.currentText()]
            client = engine.YouTubeClient(self.store, temp_config, lambda _text: None)
            created = client.create_playlist(name.strip(), temp_config.privacy_status)
            playlists = client.playlists()
            self.set_playlist_options(playlists, selected_id=created["id"])
            QMessageBox.information(self, "Crear lista", "Lista creada correctamente.")
        except Exception as exc:
            QMessageBox.warning(self, "Crear lista", f"No se pudo crear la lista:\n\n{engine.describe_error(exc)}")

    def save(self) -> None:
        privacy = {"Privado": "private", "Oculto": "unlisted", "Publico": "public"}[self.privacy.currentText()]
        self.config.watch_folder = self.folder.text().strip()
        self.config.client_secret_path = self.oauth.text().strip()
        self.config.privacy_status = privacy
        self.config.category_id = engine.CATEGORIES.get(self.category.currentText(), "22")
        playlist_label = self.playlist_combo.currentText() or "Ninguna"
        self.config.playlist_id = self.playlists_by_label.get(playlist_label, "")
        self.config.playlist_name = playlist_label
        self.config.extensions = self.extensions.text().strip()
        self.config.recursive = self.recursive.isChecked()
        self.config.auto_start_enabled = self.auto_start.isChecked()
        self.config.start_minimized = self.start_minimized.isChecked()
        self.config.close_to_tray = self.close_to_tray.isChecked()
        self.config.run_at_startup = self.run_at_startup.isChecked()
        self.config.scan_interval_seconds = int(self.scan_interval.value())
        self.config.stable_wait_seconds = int(self.stable_wait.value())
        self.config.auto_delete_uploaded = self.auto_delete.isChecked()
        self.config.auto_delete_after_hours = int(self.cleanup_delay.value())
        self.config.auto_delete_after_unit = self.cleanup_unit.currentText()
        self.store.save_config(self.config)
        try:
            engine.set_run_at_startup(self.config.run_at_startup)
        except Exception:
            pass
        self.saved.emit()
        self.close()


class Card(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        self.title = QLabel(title.upper())
        self.title.setObjectName("CardTitle")
        self.value = QLabel("-")
        self.value.setObjectName("CardValue")
        self.detail = QLabel("")
        self.detail.setObjectName("CardDetail")
        self.detail.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set(self, value: str, detail: str = "") -> None:
        self.value.setText(value)
        self.detail.setText(detail)


class MainWindow(QMainWindow):
    thumbnail_loaded = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self.store = engine.Store()
        self.config = self.store.load_config()
        self.events = queue.Queue()
        self.worker = None
        self._allow_exit = False
        self.settings_dialog = None
        self.auto_enabled = bool(self.config.auto_start_enabled)
        self.channel_loader = None
        self.youtube_check_running = False
        self.api_pause_state = None
        self._closing = False
        self.thumbnail_jobs = queue.Queue()
        self.thumbnail_pool_started = False
        self.video_rows: dict[int, dict] = {}
        self.channel_videos: list[dict] = []
        self.channel_rows_by_id: dict[int, dict] = {}
        self.channel_playlists_by_label: dict[str, str] = {"Ninguna": ""}
        self.channel_filter_playlists_by_label: dict[str, str | None] = {"Todas": None, "Sin lista": ""}
        self.thumbnail_cache: dict[str, bytes] = {}
        self.thumbnail_pending: set[str] = set()
        self.thumbnail_labels: dict[str, list[QLabel]] = {}
        self.channel_render_pending: list[dict] = []
        self.channel_render_total = 0
        self.thumbnail_loaded.connect(self.apply_thumbnail)
        self.channel_render_timer = QTimer(self)
        self.channel_render_timer.timeout.connect(self.append_channel_render_batch)
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.timeout.connect(self.adjust_channel_layout)
        self.folder_refresh_timer = QTimer(self)
        self.folder_refresh_timer.setSingleShot(True)
        self.folder_refresh_timer.timeout.connect(self.refresh_folder)
        self.verification_timer = QTimer(self)
        self.verification_timer.timeout.connect(lambda: self.check_youtube(full=False))
        self.verification_timer.start(60000)
        self.quota_timer = QTimer(self)
        self.quota_timer.timeout.connect(self.update_quota_status)
        self.quota_timer.start(1000)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(asset_path("youtube-sync.ico"))))
        self.resize(1280, 780)
        self.setMinimumSize(940, 620)

        self.build_ui()
        self.build_tray()
        self.refresh_all(light=True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_events)
        self.timer.start(80)

    def action_button(self, text: str, icon: QStyle.StandardPixmap | QIcon | None = None, danger: bool = False, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setToolTip(text)
        button.setAccessibleName(text)
        if icon is not None:
            button.setIcon(icon if isinstance(icon, QIcon) else self.style().standardIcon(icon))
            button.setIconSize(QSize(22, 22))
        if danger:
            button.setObjectName("DangerButton")
        elif primary:
            button.setObjectName("PrimaryButton")
        return button

    def icon_button(self, tooltip: str, icon: QStyle.StandardPixmap | QIcon, danger: bool = False, primary: bool = False) -> QPushButton:
        button = self.action_button("", icon, danger=danger, primary=primary)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setMinimumWidth(46)
        button.setMaximumWidth(54)
        return button

    def symbol_icon(self, codepoint: int, color: str = "#ffffff") -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(color))
        font = QFont("Segoe UI Symbol", 20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, chr(codepoint))
        painter.end()
        return QIcon(pixmap)

    def polish_header_tool(self, button: QToolButton, icon: QStyle.StandardPixmap | QIcon) -> None:
        button.setObjectName("HeaderTool")
        button.setIcon(icon if isinstance(icon, QIcon) else self.style().standardIcon(icon))
        button.setIconSize(QSize(22, 22))
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)

    def build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        self.main_layout = main
        main.setContentsMargins(22, 20, 22, 20)
        main.setSpacing(18)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QIcon(str(asset_path("youtube-sync-logo.png"))).pixmap(58, 58))
        header.addWidget(logo)
        title_box = QVBoxLayout()
        title = QLabel("YouTubeSync")
        title.setObjectName("AppTitle")
        self.status = QLabel("Preparado")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.status.setMinimumWidth(0)
        title_box.addWidget(title)
        title_box.addWidget(self.status)
        header.addLayout(title_box, 1)

        self.auto_btn = QPushButton()
        self.auto_btn.clicked.connect(self.toggle_auto)
        self.upload_btn = QToolButton()
        self.upload_btn.setText("")
        self.upload_btn.setToolTip("Subir pendientes")
        self.polish_header_tool(self.upload_btn, self.symbol_icon(0x2191))
        self.upload_btn.clicked.connect(self.upload_pending)
        self.cancel_btn = QToolButton()
        self.cancel_btn.setText("")
        self.cancel_btn.setToolTip("Cancelar subida actual")
        self.polish_header_tool(self.cancel_btn, self.symbol_icon(0x25A0))
        self.cancel_btn.clicked.connect(self.cancel_upload)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("")
        self.refresh_btn.setToolTip("Actualizar")
        self.polish_header_tool(self.refresh_btn, self.symbol_icon(0x21BB))
        self.refresh_btn.clicked.connect(self.request_remote_refresh)
        self.settings_btn = QToolButton()
        self.settings_btn.setText("")
        self.settings_btn.setToolTip("Ajustes")
        self.polish_header_tool(self.settings_btn, self.symbol_icon(0x2699))
        self.settings_btn.clicked.connect(self.open_settings)
        for button in (self.auto_btn, self.upload_btn, self.cancel_btn, self.refresh_btn, self.settings_btn):
            header.addWidget(button)
        main.addLayout(header)

        cards = QGridLayout()
        self.state_card = Card("Estado")
        self.config_card = Card("Configuracion")
        self.upload_card = Card("Subida actual")
        cards.addWidget(self.state_card, 0, 0)
        cards.addWidget(self.config_card, 0, 1)
        cards.addWidget(self.upload_card, 0, 2)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)
        cards.setColumnStretch(2, 1)
        main.addLayout(cards)

        progress_frame = QFrame()
        progress_frame.setObjectName("Card")
        progress_layout = QVBoxLayout(progress_frame)
        self.progress_layout = progress_layout
        progress_layout.setDirection(QVBoxLayout.LeftToRight)
        progress_layout.addWidget(QLabel("Subida"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        progress_layout.addWidget(self.progress, 1)
        main.addWidget(progress_frame)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_videos_page(), "Videos")
        self.tabs.addTab(self.build_channel_page(), "Canal")
        self.tabs.addTab(self.build_console_page(), "Consola")
        self.tabs.currentChanged.connect(self.tab_changed)
        main.addWidget(self.tabs, 1)
        self.update_auto_button()

    def build_videos_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        toolbar = QHBoxLayout()
        title = QLabel("Biblioteca de videos")
        title.setObjectName("PageTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        upload_one = self.action_button("Subir", self.symbol_icon(0x2191), primary=True)
        upload_one.clicked.connect(self.upload_selected_video)
        open_local = self.icon_button("Abrir local", QStyle.SP_DirOpenIcon)
        open_local.clicked.connect(self.open_selected_local_video)
        retry = self.icon_button("Reintentar", self.symbol_icon(0x21BA, "#3ea6ff"))
        retry.clicked.connect(self.retry_selected_video)
        delete_local = self.icon_button("Borrar local verificado", QStyle.SP_TrashIcon, danger=True)
        delete_local.clicked.connect(self.delete_selected_local_verified)
        cleanup = self.action_button("Limpieza", self.symbol_icon(0x2728, "#22c55e"))
        cleanup.clicked.connect(self.run_configured_cleanup)
        reload_btn = self.icon_button("Actualizar carpeta", self.symbol_icon(0x21BB, "#3ea6ff"))
        reload_btn.clicked.connect(self.refresh_folder)
        toolbar.addWidget(upload_one)
        toolbar.addWidget(open_local)
        toolbar.addWidget(retry)
        toolbar.addWidget(delete_local)
        toolbar.addWidget(cleanup)
        toolbar.addWidget(reload_btn)
        layout.addLayout(toolbar)
        self.video_summary = QLabel("Sin revisar")
        self.video_summary.setObjectName("Muted")
        self.video_summary.setWordWrap(True)
        layout.addWidget(self.video_summary)
        self.video_table = QTableWidget(0, 6)
        self.video_table.setHorizontalHeaderLabels(["Archivo", "Titulo", "Tamaño", "Creado", "Estado", "Ruta"])
        self.setup_table(self.video_table)
        layout.addWidget(self.video_table, 1)
        return page

    def build_channel_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        toolbar = QVBoxLayout()
        header = QHBoxLayout()
        title = QLabel("Canal de YouTube")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.channel_loader_bar = QProgressBar()
        self.channel_loader_bar.setRange(0, 0)
        self.channel_loader_bar.hide()
        header.addWidget(self.channel_loader_bar)
        toolbar.addLayout(header)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        reload_btn = self.action_button("Cargar canal", QStyle.SP_BrowserReload)
        reload_btn.clicked.connect(self.refresh_channel)
        youtube_btn = self.action_button("YouTube", QStyle.SP_ComputerIcon, primary=True)
        youtube_btn.clicked.connect(lambda: webbrowser.open("https://www.youtube.com"))
        open_btn = self.action_button("Abrir", QStyle.SP_DialogOpenButton)
        open_btn.clicked.connect(self.open_selected_channel_video)
        share_btn = self.action_button("Compartir", QStyle.SP_FileLinkIcon)
        share_btn.clicked.connect(self.share_selected_channel_video)
        privacy_btn = self.action_button("Privacidad", QStyle.SP_DialogYesButton)
        privacy_btn.clicked.connect(self.change_selected_channel_privacy)
        duplicates_btn = self.action_button("Duplicados", QStyle.SP_FileDialogListView)
        duplicates_btn.clicked.connect(self.find_channel_duplicates)
        delete_btn = self.action_button("Borrar", QStyle.SP_TrashIcon, danger=True)
        delete_btn.clicked.connect(self.delete_selected_channel_videos)
        for button in (reload_btn, youtube_btn):
            actions.addWidget(button)
        actions.addSpacing(12)
        for button in (open_btn, share_btn, privacy_btn, duplicates_btn):
            actions.addWidget(button)
        actions.addStretch(1)
        actions.addWidget(delete_btn)
        toolbar.addLayout(actions)
        layout.addLayout(toolbar)
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.channel_search = QLineEdit()
        self.channel_search.setPlaceholderText("Buscar por titulo, lista o enlace")
        self.channel_search.textChanged.connect(self.filter_channel_table)
        self.channel_privacy_filter = QComboBox()
        self.channel_privacy_filter.addItems(["Todas", "Publico", "Oculto", "Privado"])
        self.channel_privacy_filter.currentTextChanged.connect(self.filter_channel_table)
        self.channel_playlist_filter = QComboBox()
        self.channel_playlist_filter.addItems(["Todas", "Sin lista"])
        self.channel_playlist_filter.currentTextChanged.connect(self.filter_channel_table)
        self.channel_date_filter = QLineEdit()
        self.channel_date_filter.setPlaceholderText("Fecha: 2026, 2026-06...")
        self.channel_date_filter.textChanged.connect(self.filter_channel_table)
        filter_label = QLabel("Filtros")
        filter_label.setObjectName("Muted")
        filters.addWidget(filter_label, 0)
        filters.addWidget(self.channel_search, 2)
        filters.addWidget(self.channel_privacy_filter, 1)
        filters.addWidget(self.channel_playlist_filter, 1)
        filters.addWidget(self.channel_date_filter, 1)
        layout.addLayout(filters)
        playlist_bar = QHBoxLayout()
        playlist_bar.setSpacing(8)
        self.channel_playlist_combo = QComboBox()
        self.channel_playlist_combo.addItems(["Ninguna"])
        move_playlist = self.action_button("Mover a lista", QStyle.SP_ArrowRight)
        move_playlist.clicked.connect(self.change_selected_channel_playlist)
        playlist_bar.addWidget(QLabel("Lista destino"), 0)
        playlist_bar.addWidget(self.channel_playlist_combo, 1)
        playlist_bar.addWidget(move_playlist, 0)
        layout.addLayout(playlist_bar)
        self.channel_summary = QLabel("Pulsa Cargar canal o abre esta pestana para consultar YouTube.")
        self.channel_summary.setObjectName("Muted")
        layout.addWidget(self.channel_summary)

        content = QSplitter(Qt.Horizontal)
        content.setObjectName("ChannelSplitter")
        content.setChildrenCollapsible(False)
        content.setHandleWidth(10)
        self.channel_splitter = content
        self.channel_table = QTableWidget(0, 7)
        self.channel_table.setHorizontalHeaderLabels(["Miniatura", "Titulo", "Duracion", "Privacidad", "Listas", "Publicado", "YouTube"])
        self.setup_table(self.channel_table)
        self.configure_channel_table_columns()
        self.channel_table.setIconSize(self.channel_table.iconSize())
        self.channel_table.itemSelectionChanged.connect(self.update_channel_preview)
        self.channel_table.setMinimumWidth(360)
        content.addWidget(self.channel_table)

        preview = QFrame()
        preview.setObjectName("PreviewPanel")
        preview.setMinimumWidth(0)
        self.channel_preview_panel = preview
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(10)
        self.channel_preview_title = QLabel("Selecciona un video")
        self.channel_preview_title.setObjectName("CardValue")
        self.channel_preview_title.setWordWrap(True)
        self.channel_preview_meta = QLabel("Aqui veras la miniatura, datos y acciones rapidas.")
        self.channel_preview_meta.setObjectName("Muted")
        self.channel_preview_meta.setWordWrap(True)
        self.channel_preview_thumb = PreviewThumbnail()
        preview_layout.addWidget(self.channel_preview_title)
        preview_layout.addWidget(self.channel_preview_meta)
        preview_layout.addWidget(self.channel_preview_thumb)
        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        self.channel_info_grid = info_grid
        self.channel_preview_duration = QLabel("Duracion\n-")
        self.channel_preview_privacy = QLabel("Privacidad\n-")
        self.channel_preview_date = QLabel("Publicado\n-")
        self.channel_preview_playlist = QLabel("Lista\n-")
        self.channel_info_pills = [
            self.channel_preview_duration,
            self.channel_preview_privacy,
            self.channel_preview_date,
            self.channel_preview_playlist,
        ]
        for label in (
            self.channel_preview_duration,
            self.channel_preview_privacy,
            self.channel_preview_date,
            self.channel_preview_playlist,
        ):
            label.setObjectName("InfoPill")
            label.setWordWrap(True)
        self.layout_channel_info_pills(two_columns=True)
        preview_layout.addLayout(info_grid)
        preview_layout.addStretch(1)
        player_actions = QHBoxLayout()
        player_actions.setSpacing(8)
        browser_btn = self.action_button("Reproducir", QStyle.SP_MediaPlay, primary=True)
        browser_btn.setToolTip("Abrir el video seleccionado en el navegador")
        browser_btn.clicked.connect(self.open_selected_channel_video)
        player_actions.addStretch(1)
        player_actions.addWidget(browser_btn)
        preview_layout.addLayout(player_actions)
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setFrameShape(QFrame.NoFrame)
        preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        preview_scroll.setMinimumWidth(280)
        preview_scroll.setWidget(preview)
        self.channel_preview_scroll = preview_scroll
        preview_scroll.viewport().installEventFilter(self)
        content.addWidget(preview_scroll)
        content.setStretchFactor(0, 3)
        content.setStretchFactor(1, 1)
        content.setSizes([860, 380])
        content.splitterMoved.connect(lambda _pos, _index: self.layout_timer.start(30))
        layout.addWidget(content, 1)
        return page

    def build_console_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        title = QLabel("Consola")
        title.setObjectName("PageTitle")
        bar.addWidget(title)
        bar.addStretch(1)
        clear = self.action_button("Limpiar", QStyle.SP_TrashIcon)
        clear.clicked.connect(lambda: self.console.clear())
        bar.addWidget(clear)
        layout.addLayout(bar)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.document().setMaximumBlockCount(2000)
        layout.addWidget(self.console, 1)
        return page

    def setup_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setResizeContentsPrecision(100)

    def configure_channel_table_columns(self) -> None:
        header = self.channel_table.horizontalHeader()
        header.setMinimumSectionSize(72)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for column in (2, 3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.channel_table.setColumnWidth(0, 128)
        self.channel_table.setColumnHidden(6, True)

    def build_tray(self) -> None:
        self.tray = QSystemTrayIcon(QIcon(str(asset_path("youtube-sync.ico"))), self)
        show_action = QAction("Mostrar", self)
        show_action.setIcon(self.symbol_icon(0x25A3))
        show_action.triggered.connect(self.show_from_tray)
        self.tray_auto_action = QAction("Auto ON" if self.auto_enabled else "Auto OFF", self)
        self.tray_auto_action.setIcon(self.symbol_icon(0x25CF, "#22c55e" if self.auto_enabled else "#ef4444"))
        self.tray_auto_action.triggered.connect(self.toggle_auto)
        upload_action = QAction("Subir pendientes", self)
        upload_action.setIcon(self.symbol_icon(0x2191))
        upload_action.triggered.connect(self.upload_pending)
        cancel_action = QAction("Cancelar subida", self)
        cancel_action.setIcon(self.symbol_icon(0x25A0))
        cancel_action.triggered.connect(self.cancel_upload)
        refresh_action = QAction("Actualizar", self)
        refresh_action.setIcon(self.symbol_icon(0x21BB, "#3ea6ff"))
        refresh_action.triggered.connect(lambda: self.refresh_all(light=False))
        settings_action = QAction("Ajustes", self)
        settings_action.setIcon(self.symbol_icon(0x2699))
        settings_action.triggered.connect(self.open_settings)
        quit_action = QAction("Salir", self)
        quit_action.setIcon(self.symbol_icon(0x2715, "#ef4444"))
        quit_action.triggered.connect(self.request_quit)
        menu = self.tray.contextMenu() or None
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(self.tray_auto_action)
        menu.addAction(upload_action)
        menu.addAction(cancel_action)
        menu.addAction(refresh_action)
        menu.addSeparator()
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_from_tray() if reason == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()

    def closeEvent(self, event) -> None:
        if self._allow_exit:
            self.stop_background_work()
            event.accept()
            return
        if not bool(getattr(self.config, "close_to_tray", True)):
            if self.confirm_quit():
                self.stop_background_work()
                self._allow_exit = True
                event.accept()
                QTimer.singleShot(0, QApplication.quit)
            else:
                event.ignore()
            return
        event.ignore()
        self.hide()
        self.tray.showMessage(APP_NAME, "La app sigue funcionando en la bandeja.", QSystemTrayIcon.Information, 1800)

    def confirm_quit(self) -> bool:
        return (
            QMessageBox.question(
                self,
                "Salir de YouTubeSync",
                "Esto cerrara YouTubeSync por completo y detendra la vigilancia de la carpeta.\n\nQuieres salir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    def request_quit(self) -> None:
        if not self.confirm_quit():
            return
        self._allow_exit = True
        self.stop_background_work()
        if hasattr(self, "tray"):
            self.tray.hide()
        QApplication.quit()

    def stop_background_work(self) -> None:
        self._closing = True
        if self.worker:
            self.worker.stop()
        for timer in (self.timer, self.verification_timer, self.quota_timer, self.channel_render_timer,
                      self.folder_refresh_timer, self.layout_timer):
            timer.stop()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "layout_timer"):
            self.layout_timer.start(30)

    def eventFilter(self, watched, event) -> bool:
        if (event.type() == QEvent.Resize
                and hasattr(self, "channel_preview_scroll")
                and watched is self.channel_preview_scroll.viewport()):
            self.layout_timer.start(30)
        return super().eventFilter(watched, event)

    def adjust_channel_layout(self) -> None:
        if not hasattr(self, "channel_splitter"):
            return
        compact = self.height() < 820
        if getattr(self, "_compact_layout", None) != compact:
            self._compact_layout = compact
            self.main_layout.setContentsMargins(*((12, 10, 12, 10) if compact else (22, 20, 22, 20)))
            self.main_layout.setSpacing(8 if compact else 18)
            self.progress_layout.setContentsMargins(10, 6 if compact else 10, 10, 6 if compact else 10)
            for card in (self.state_card, self.config_card, self.upload_card):
                card.layout().setContentsMargins(*((12, 8, 12, 8) if compact else (18, 16, 18, 16)))
                card.layout().setSpacing(4 if compact else 6)
        if hasattr(self, "channel_preview_panel"):
            self.layout_channel_info_pills(two_columns=self.channel_preview_panel.width() >= 420)
            width = max(1, self.channel_preview_panel.width() - 32)
            self.channel_preview_thumb.setFixedHeight(self.channel_preview_thumb.heightForWidth(width))

    def layout_channel_info_pills(self, two_columns: bool) -> None:
        if not hasattr(self, "channel_info_grid"):
            return
        if getattr(self, "_pills_two_columns", None) == two_columns:
            return
        self._pills_two_columns = two_columns
        for index, label in enumerate(self.channel_info_pills):
            self.channel_info_grid.removeWidget(label)
            if two_columns:
                self.channel_info_grid.addWidget(label, index // 2, index % 2)
            else:
                self.channel_info_grid.addWidget(label, index, 0)

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def update_auto_button(self) -> None:
        self.auto_btn.setText("ON" if self.auto_enabled else "OFF")
        self.auto_btn.setToolTip("Automatizacion activa" if self.auto_enabled else "Automatizacion parada")
        self.auto_btn.setObjectName("AutoOn" if self.auto_enabled else "AutoOff")
        self.auto_btn.style().unpolish(self.auto_btn)
        self.auto_btn.style().polish(self.auto_btn)
        if hasattr(self, "tray_auto_action"):
            self.tray_auto_action.setText("Auto ON" if self.auto_enabled else "Auto OFF")
            self.tray_auto_action.setIcon(self.symbol_icon(0x25CF, "#22c55e" if self.auto_enabled else "#ef4444"))

    def start_worker(self, manual_path: Path | None = None) -> None:
        if self.worker and self.worker.is_alive():
            if manual_path is not None:
                self.worker.upload_path(manual_path)
            self.worker.set_enabled(self.auto_enabled)
            self.worker.refresh()
            return
        self.worker = engine.SyncWorker(self.store, lambda: self.config, self.events)
        if manual_path is not None:
            self.worker.upload_path(manual_path)
        self.worker.set_enabled(self.auto_enabled)
        self.worker.start()

    def toggle_auto(self) -> None:
        self.auto_enabled = not self.auto_enabled
        self.update_auto_button()
        self.start_worker()
        if self.worker:
            self.worker.set_enabled(self.auto_enabled)
        self.status.setText("Modo automatico activo" if self.auto_enabled else "Modo automatico pausado")

    def upload_pending(self) -> None:
        self.auto_enabled = True
        self.update_auto_button()
        self.start_worker()
        if self.worker:
            self.worker.set_enabled(True)
            self.worker.refresh()
        self.log("Subida de pendientes solicitada.")

    def cancel_upload(self) -> None:
        self.auto_enabled = False
        self.update_auto_button()
        if self.worker:
            self.worker.cancel_upload()
            self.worker.set_enabled(False)
        self.upload_card.set("Cancelando", "Deteniendo la subida actual")
        self.status.setText("Subida cancelada / Auto OFF")
        self.log("Cancelacion solicitada. Auto queda pausado.")

    def refresh_all(self, light: bool = False) -> None:
        self.config = self.store.load_config()
        self.refresh_config_card()
        self.refresh_folder()
        if not light:
            self.check_youtube()

    def request_remote_refresh(self) -> None:
        scope = engine.api_scope(self.config.client_secret_path)
        pause = self.store.api_pause(scope) or self.store.api_pause(scope, "upload")
        if pause:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Cuota de YouTube")
            dialog.setIcon(QMessageBox.Information)
            dialog.setText("Google ha agotado la cuota. Los archivos y los estados anteriores se conservan.")
            dialog.setInformativeText("Reintentar comprueba si Google ya ha renovado o ampliado la cuota; no reinicia su contador.")
            quotas = dialog.addButton("Ver cuota", QMessageBox.ActionRole)
            extension = dialog.addButton("Solicitar ampliacion", QMessageBox.ActionRole)
            retry = dialog.addButton("Reintentar conexion", QMessageBox.AcceptRole)
            close = dialog.addButton(QMessageBox.Close)
            dialog.setDefaultButton(close)
            dialog.exec()
            clicked = dialog.clickedButton()
            if clicked == quotas:
                webbrowser.open("https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas")
                return
            if clicked == extension:
                webbrowser.open("https://support.google.com/youtube/contact/yt_api_form")
                return
            if clicked != retry:
                return
            self.store.clear_api_pause(scope)
            self.api_pause_state = None
            if self.worker:
                self.worker.refresh()
        self.refresh_all(light=False)

    def refresh_config_card(self) -> None:
        folder = self.config.watch_folder or "Sin carpeta"
        category = engine.CATEGORY_NAMES_BY_ID.get(self.config.category_id, self.config.category_id)
        playlist = self.config.playlist_name if self.config.playlist_id else "Sin lista"
        self.config_card.set("Listo" if self.config.watch_folder else "Pendiente", f"{folder}\n{category} / {playlist}")

    def refresh_folder(self) -> None:
        folder = Path(self.config.watch_folder) if self.config.watch_folder else None
        self.video_table.setSortingEnabled(False)
        self.video_table.setRowCount(0)
        self.video_rows = {}
        if not folder or not folder.exists():
            self.video_summary.setText("Configura una carpeta valida.")
            self.state_card.set("Sin carpeta", "Abre ajustes para configurarla.")
            self.video_table.setSortingEnabled(True)
            return
        pattern = "**/*" if self.config.recursive else "*"
        paths = []
        extensions = self.config.extension_set
        for path in folder.glob(pattern):
            try:
                if path.suffix.lower() in extensions and path.is_file():
                    paths.append((path.stat().st_ctime, path))
            except OSError:
                continue
        registry_by_signature, _ = self.store.registry_index()
        statuses_by_signature, _ = self.store.upload_status_index()
        counts = {"Pendiente": 0, "Subido": 0, "Incidencia": 0, "En curso": 0, "En espera": 0, "Por verificar": 0}
        for _, path in sorted(paths, key=lambda item: item[0]):
            try:
                signature = engine.file_signature(path)
                title = engine.creation_title(path)
                size = engine.human_size(path.stat().st_size)
                created = engine.datetime.fromtimestamp(path.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            except OSError:
                continue
            registry_row = registry_by_signature.get(signature)
            status_row = statuses_by_signature.get(signature)
            if registry_row and registry_row[3] and registry_row[4] in {"uploaded", "youtube_title_exists"}:
                status = "Subido"
            elif registry_row and registry_row[3] and registry_row[4] == "processing":
                status = "En curso"
            elif status_row and (status_row[3] == "waiting_quota" or
                                 (status_row[3] == "error" and engine.is_youtube_quota_error(status_row[4] or ""))):
                status = "En espera"
            elif status_row and (status_row[3] == "verification_pending" or
                                 (status_row[3] == "error" and any(
                                     text in (status_row[4] or "").lower() for text in ("datos suficientes", "no hay huella")))):
                status = "Por verificar"
            elif status_row and status_row[3] in {"error", "cancelled"}:
                status = "Incidencia"
            elif status_row and status_row[3] in {"uploading", "processing"}:
                status = "En curso"
            else:
                status = "Pendiente"
            counts[status] += 1
            row = self.video_table.rowCount()
            self.video_table.insertRow(row)
            values = [path.name, title, size, created, status, str(path)]
            status_colors = {
                "Pendiente": "#3ea6ff",
                "Subido": "#22c55e",
                "Incidencia": "#f59e0b",
                "En curso": "#c084fc",
                "En espera": "#a7adb8",
                "Por verificar": "#eab308",
            }
            for column, value in enumerate(values):
                self.video_table.setItem(row, column, table_item(value, status_colors.get(status, "") if column == 4 else ""))
            if status_row and status_row[4]:
                self.video_table.item(row, 4).setToolTip(status_row[4])
            if status == "Subido" and registry_row:
                self.video_table.item(row, 4).setToolTip(
                    f"Ultima confirmacion: {registry_row[5]}\nhttps://youtu.be/{registry_row[3]}\nSe conserva aunque el archivo siga en la carpeta.")
            self.video_rows[row] = {
                "path": str(path),
                "signature": signature,
                "title": title,
                "status": status,
                "youtube_id": registry_row[3] if registry_row else "",
            }
        self.video_table.setSortingEnabled(True)
        self.video_summary.setText(
            f"Total {len(paths)} / Pendientes {counts['Pendiente']} / En curso {counts['En curso']} / En espera {counts['En espera']} / Por verificar {counts['Por verificar']} / Subidos {counts['Subido']} / Incidencias {counts['Incidencia']}"
        )
        self.state_card.set("Preparado", f"{len(paths)} videos en la carpeta")

    def selected_video_row(self) -> dict | None:
        selected = self.video_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, APP_NAME, "Selecciona primero un video de la tabla.")
            return None
        row = selected[0].row()
        path = self.video_table.item(row, 5).text() if self.video_table.item(row, 5) else ""
        signature = ""
        youtube_id = ""
        for data in self.video_rows.values():
            if data.get("path") == path:
                signature = data.get("signature", "")
                youtube_id = data.get("youtube_id", "")
                break
        return {
            "path": path,
            "signature": signature,
            "youtube_id": youtube_id,
            "title": self.video_table.item(row, 1).text() if self.video_table.item(row, 1) else "",
            "status": self.video_table.item(row, 4).text() if self.video_table.item(row, 4) else "",
        }

    def upload_selected_video(self) -> None:
        item = self.selected_video_row()
        if not item:
            return
        self.queue_video(item)

    def queue_video(self, item: dict) -> None:
        path = Path(item["path"])
        if not path.exists():
            QMessageBox.warning(self, APP_NAME, "El archivo seleccionado ya no existe.")
            self.refresh_folder()
            return
        if item["status"] == "Subido":
            QMessageBox.information(self, APP_NAME, "Este video ya aparece como subido en el registro.")
            return
        self.start_worker(manual_path=path)
        self.upload_card.set("En cola", path.name)
        self.log(f"Subida manual solicitada para {path.name}.")

    def retry_selected_video(self) -> None:
        item = self.selected_video_row()
        if not item:
            return
        if item["status"] == "Subido":
            self.queue_video(item)
            return
        if item["signature"]:
            self.store.clear_upload_incident(item["signature"])
        self.refresh_folder()
        self.queue_video(item)

    def open_selected_local_video(self) -> None:
        item = self.selected_video_row()
        if not item:
            return
        path = Path(item["path"])
        if not path.exists():
            QMessageBox.warning(self, APP_NAME, "El archivo seleccionado ya no existe.")
            return
        os.startfile(str(path))

    def delete_selected_local_verified(self) -> None:
        item = self.selected_video_row()
        if not item:
            return
        if item["status"] != "Subido":
            QMessageBox.information(self, APP_NAME, "Solo se puede borrar localmente un video marcado como subido.")
            return
        if QMessageBox.question(
            self,
            "Borrar archivo local",
            "Se comprobara YouTube antes de borrar el archivo local.\n\nContinuar?",
        ) != QMessageBox.StandardButton.Yes:
            return
        threading.Thread(target=self._delete_local_verified_thread, args=([item],), daemon=True).start()

    def run_configured_cleanup(self) -> None:
        older_than = engine.datetime.now() - self.config.auto_delete_delay
        rows = [row for row in self.store.uploaded_before(older_than, 2000) if Path(row[4]).exists()]
        if not rows:
            QMessageBox.information(self, "Limpieza", "No hay archivos locales subidos que cumplan el tiempo configurado.")
            return
        if QMessageBox.question(
            self,
            "Limpieza configurada",
            f"Se comprobaran {len(rows)} archivo(s) con YouTube antes de borrar localmente.\n\nContinuar?",
        ) != QMessageBox.StandardButton.Yes:
            return
        items = [{"signature": row[0], "title": row[3], "path": row[4], "youtube_id": row[5] or ""} for row in rows]
        threading.Thread(target=self._delete_local_verified_thread, args=(items,), daemon=True).start()

    def _delete_local_verified_thread(self, items: list[dict]) -> None:
        deleted = 0
        errors = []
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            client.uploaded_video_index(force=True)
        except Exception as exc:
            self.events.put(("local_delete_result", {"deleted": 0, "errors": [f"No se pudo comprobar YouTube: {engine.describe_error(exc)}"]}))
            return
        for item in items:
            path = Path(item["path"])
            try:
                if not path.exists():
                    self.store.mark_local_deleted(item["signature"])
                    deleted += 1
                    continue
                if engine.file_signature(path) != item["signature"]:
                    errors.append(f"{path.name}: el archivo local ha cambiado desde la subida")
                    continue
                confirmed, resolved_id, reason, remote_state = client.verify_local_file(path, item["title"], item.get("youtube_id", ""))
                if not confirmed or remote_state != "processed":
                    errors.append(f"{path.name}: {reason or 'YouTube no confirma el video procesado'}")
                    continue
                path.unlink()
                if resolved_id and not item.get("youtube_id"):
                    self.store.update_registry_youtube_id(item["signature"], resolved_id)
                self.store.mark_local_deleted(item["signature"])
                deleted += 1
            except Exception as exc:
                errors.append(f"{path.name}: {engine.describe_error(exc)}")
        self.events.put(("local_delete_result", {"deleted": deleted, "errors": errors}))

    def check_youtube(self, full: bool = True) -> None:
        if self.youtube_check_running:
            return
        if not self.config.client_secret_path or not Path(self.config.client_secret_path).exists():
            self.state_card.set("Sin OAuth", "Configura el JSON de YouTube.")
            return
        pause = self.store.api_pause(engine.api_scope(self.config.client_secret_path))
        if pause:
            self.api_pause_state = pause
            self.update_quota_status()
            return
        self.youtube_check_running = True
        self.status.setText("Comprobando videos con YouTube...")
        threading.Thread(target=self._check_youtube_thread, args=(full,), daemon=True).start()

    def _check_youtube_thread(self, full: bool = True) -> None:
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            info = client.channel_info()
            changed = engine.reconcile_local_uploads(
                self.store, self.config, client, full=full,
                is_active=lambda path: bool(self.worker and self.worker.active_path == path),
            )
            if changed:
                self.events.put(("folder_refresh", False))
                self.events.put(("log", f"Comprobacion de YouTube: {changed} estado(s) actualizado(s)."))
            self.events.put(("youtube", info))
        except Exception as exc:
            if engine.is_youtube_quota_error(exc) and not engine.is_youtube_channel_upload_limit(exc):
                state = exc.state if isinstance(exc, engine.ApiQuotaUnavailable) else (
                    self.store.api_pause(client.scope) or self.store.defer_api(client.scope, exc))
                self.events.put(("api_quota", state))
                self.events.put(("youtube_check_done", None))
            else:
                self.events.put(("youtube_error", engine.describe_error(exc)))

    def update_quota_status(self) -> None:
        if not self.api_pause_state:
            return
        retry = engine.datetime.fromisoformat(self.api_pause_state["retry_at"]).astimezone()
        if retry <= engine.datetime.now().astimezone():
            self.api_pause_state = None
            self.check_youtube(full=True)
            if self.worker:
                self.worker.refresh()
            return
        remaining = engine.remaining_text(retry)
        self.status.setText(f"Sin cuota API / Proxima comprobacion {retry:%d/%m %H:%M} / {remaining}")
        if self.api_pause_state.get("bucket") != "upload":
            self.state_card.set("Consulta local", "Sin cuota API / estados conservados")

    def channel_cache_loaded(self, checked_at: str) -> None:
        stamp = engine.datetime.fromisoformat(checked_at).astimezone()
        self.channel_summary.setText(f"Copia local del canal / ultima consulta {stamp:%d/%m %H:%M} / sin verificacion en directo")

    def tab_changed(self, index: int) -> None:
        if self.tabs.tabText(index) == "Canal" and self.channel_table.rowCount() == 0:
            self.refresh_channel()

    def refresh_channel(self) -> None:
        if self.channel_loader is not None:
            return
        if not self.config.client_secret_path or not Path(self.config.client_secret_path).exists():
            QMessageBox.warning(self, APP_NAME, "Configura primero el JSON OAuth.")
            return
        self.channel_summary.setText("Cargando canal desde YouTube...")
        self.channel_loader_bar.show()
        self.channel_loader = ChannelLoader(self.store, self.config)
        self.channel_loader.finished.connect(self.apply_channel_rows)
        self.channel_loader.failed.connect(self.channel_failed)
        self.channel_loader.cached.connect(self.channel_cache_loaded)
        self.channel_loader.start()

    def apply_channel_rows(self, videos, playlists) -> None:
        self.channel_loader_bar.hide()
        self.channel_loader = None
        self.channel_videos = list(videos)
        self.set_channel_playlist_options(list(playlists or []))
        self.render_channel_rows(self.channel_videos)

    def set_channel_playlist_options(self, playlists: list[dict]) -> None:
        self.channel_playlists_by_label = {"Ninguna": ""}
        self.channel_filter_playlists_by_label = {"Todas": None, "Sin lista": ""}
        used = {"Ninguna", "Todas", "Sin lista"}
        for playlist in playlists:
            playlist_id = playlist.get("id", "")
            if not playlist_id:
                continue
            base = playlist.get("title", "Lista sin nombre")
            label = base if base not in used else f"{base} / {playlist_id[-6:]}"
            used.add(label)
            self.channel_playlists_by_label[label] = playlist_id
            self.channel_filter_playlists_by_label[label] = playlist_id
        current_filter = self.channel_playlist_filter.currentText() if hasattr(self, "channel_playlist_filter") else "Todas"
        self.channel_playlist_filter.clear()
        self.channel_playlist_filter.addItems(list(self.channel_filter_playlists_by_label.keys()))
        self.channel_playlist_filter.setCurrentText(current_filter if current_filter in self.channel_filter_playlists_by_label else "Todas")
        current_target = self.channel_playlist_combo.currentText() if hasattr(self, "channel_playlist_combo") else "Ninguna"
        self.channel_playlist_combo.clear()
        self.channel_playlist_combo.addItems(list(self.channel_playlists_by_label.keys()))
        self.channel_playlist_combo.setCurrentText(current_target if current_target in self.channel_playlists_by_label else "Ninguna")

    def render_channel_rows(self, videos: list[dict]) -> None:
        self.channel_render_timer.stop()
        self.channel_table.setSortingEnabled(False)
        self.channel_table.setRowCount(0)
        self.channel_rows_by_id = {}
        self.thumbnail_labels = {}
        self.channel_render_pending = list(videos)
        self.channel_render_total = len(self.channel_render_pending)
        if not self.channel_render_pending:
            self.channel_table.setSortingEnabled(True)
            self.update_channel_preview()
            return
        self.channel_summary.setText(f"Pintando canal... 0 de {self.channel_render_total}")
        self.channel_render_timer.start(1)

    def append_channel_render_batch(self) -> None:
        privacy_labels = {"private": "Privado", "unlisted": "Oculto", "public": "Publico"}
        batch = self.channel_render_pending[:35]
        self.channel_render_pending = self.channel_render_pending[35:]
        for video in batch:
            row = self.channel_table.rowCount()
            self.channel_table.insertRow(row)
            self.channel_table.setRowHeight(row, 74)
            memberships = video.get("memberships", [])
            playlists = ", ".join(item.get("playlist_title", "") for item in memberships if item.get("playlist_title")) or "Sin lista"
            values = [
                "",
                video.get("title", "Sin titulo"),
                video.get("duration", "-"),
                privacy_labels.get(video.get("privacy", ""), video.get("privacy", "")),
                playlists,
                video.get("published_at", "")[:10],
                f"https://youtu.be/{video.get('id', '')}",
            ]
            thumb = self.thumbnail_label(video, fetch_now=row < 80)
            self.channel_table.setCellWidget(row, 0, thumb)
            for column, value in enumerate(values):
                color = ""
                if column == 3:
                    color = {"public": "#22c55e", "unlisted": "#3ea6ff", "private": "#f59e0b"}.get(video.get("privacy", ""), "")
                self.channel_table.setItem(row, column, table_item(value, color))
            self.channel_rows_by_id[row] = video
        rendered = self.channel_table.rowCount()
        self.channel_summary.setText(f"Pintando canal... {rendered} de {self.channel_render_total}")
        if self.channel_render_pending:
            return
        self.channel_render_timer.stop()
        self.channel_table.setColumnHidden(6, True)
        self.channel_table.setSortingEnabled(True)
        self.channel_summary.setText(f"{self.channel_render_total} videos cargados del canal.")
        self.update_channel_preview()

    def thumbnail_url(self, video: dict | str) -> str:
        if isinstance(video, dict):
            return video.get("thumbnail") or f"https://i.ytimg.com/vi/{video.get('id', '')}/mqdefault.jpg"
        return f"https://i.ytimg.com/vi/{video}/mqdefault.jpg"

    def thumbnail_label(self, video: dict, fetch_now: bool = True) -> QLabel:
        video_id = video.get("id", "")
        label = QLabel("Cargando...")
        label.setObjectName("ThumbCell")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumSize(116, 64)
        label.setMaximumSize(128, 72)
        if video_id:
            self.thumbnail_labels.setdefault(video_id, []).append(label)
            if video_id in self.thumbnail_cache:
                self.set_thumbnail_pixmap(label, self.thumbnail_cache[video_id], 128, 72)
            elif fetch_now:
                self.fetch_thumbnail(video)
            else:
                label.setText("Miniatura")
        return label

    def fetch_thumbnail(self, video: dict | str) -> None:
        video_id = video.get("id", "") if isinstance(video, dict) else str(video)
        if not video_id or video_id in self.thumbnail_pending:
            return
        self.thumbnail_pending.add(video_id)
        self.thumbnail_jobs.put((video_id, self.thumbnail_url(video)))
        if not self.thumbnail_pool_started:
            self.thumbnail_pool_started = True
            for _ in range(6):
                threading.Thread(target=self.load_thumbnail_jobs, daemon=True).start()

    def load_thumbnail_jobs(self) -> None:
        while not self._closing:
            try:
                video_id, url = self.thumbnail_jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                request = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
                with urllib.request.urlopen(request, timeout=12) as response:
                    data = response.read()
            except Exception:
                data = b""
            if not self._closing:
                self.thumbnail_loaded.emit(video_id, data)

    def apply_thumbnail(self, video_id: str, data: object) -> None:
        self.thumbnail_pending.discard(video_id)
        if not isinstance(data, (bytes, bytearray)) or not data:
            for label in self.thumbnail_labels.get(video_id, []):
                label.setText("Sin imagen")
            return
        self.thumbnail_cache[video_id] = bytes(data)
        for label in self.thumbnail_labels.get(video_id, []):
            self.set_thumbnail_pixmap(label, self.thumbnail_cache[video_id], 128, 72)
        selected = self.current_channel_video()
        if selected and selected.get("id") == video_id:
            self.repaint_channel_preview_thumbnail()

    def set_thumbnail_pixmap(self, label: QLabel, data: bytes, width: int, height: int) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if pixmap.isNull():
            label.setText("Sin imagen")
            return
        label.setText("")
        label.setPixmap(pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def repaint_channel_preview_thumbnail(self) -> None:
        if not hasattr(self, "channel_preview_thumb"):
            return
        video = self.current_channel_video()
        video_id = video.get("id", "") if video else ""
        data = self.thumbnail_cache.get(video_id)
        if not data:
            return
        self.channel_preview_thumb.set_image(data)

    def current_channel_video(self) -> dict | None:
        selected = self.channel_table.selectionModel().selectedRows() if hasattr(self, "channel_table") else []
        if not selected:
            return None
        url_item = self.channel_table.item(selected[0].row(), 6)
        if not url_item:
            return None
        video_id = url_item.text().rsplit("/", 1)[-1]
        return next((video for video in self.channel_videos if video.get("id") == video_id), None)

    def update_channel_preview(self) -> None:
        if not hasattr(self, "channel_preview_title"):
            return
        video = self.current_channel_video()
        if not video:
            self.channel_preview_title.setText("Selecciona un video")
            self.channel_preview_meta.setText("Miniatura, datos y acciones rapidas.")
            self.channel_preview_thumb.clear_image("Sin miniatura")
            self.channel_preview_duration.setText("Duracion\n-")
            self.channel_preview_privacy.setText("Privacidad\n-")
            self.channel_preview_date.setText("Publicado\n-")
            self.channel_preview_playlist.setText("Lista\n-")
            return
        memberships = video.get("memberships", [])
        playlists = ", ".join(item.get("playlist_title", "") for item in memberships if item.get("playlist_title")) or "Sin lista"
        privacy_labels = {"private": "Privado", "unlisted": "Oculto", "public": "Publico"}
        self.channel_preview_title.setText(video.get("title", "Sin titulo"))
        video_id = video.get("id", "")
        privacy_text = privacy_labels.get(video.get("privacy", ""), video.get("privacy", "-") or "-")
        published = video.get("published_at", "")[:10] or "Sin fecha"
        self.channel_preview_meta.setText(f"https://youtu.be/{video_id}")
        self.channel_preview_duration.setText(f"Duracion\n{video.get('duration', '-')}")
        self.channel_preview_privacy.setText(f"Privacidad\n{privacy_text}")
        self.channel_preview_date.setText(f"Publicado\n{published}")
        self.channel_preview_playlist.setText(f"Lista\n{playlists}")
        if video_id in self.thumbnail_cache:
            self.repaint_channel_preview_thumbnail()
        else:
            self.channel_preview_thumb.clear_image("Cargando miniatura...")
            self.fetch_thumbnail(video)

    def filter_channel_table(self) -> None:
        query = self.channel_search.text().strip().casefold() if hasattr(self, "channel_search") else ""
        privacy_label = self.channel_privacy_filter.currentText() if hasattr(self, "channel_privacy_filter") else "Todas"
        privacy = {"Publico": "public", "Oculto": "unlisted", "Privado": "private"}.get(privacy_label)
        playlist_filter = self.channel_filter_playlists_by_label.get(self.channel_playlist_filter.currentText()) if hasattr(self, "channel_playlist_filter") else None
        date_query = self.channel_date_filter.text().strip() if hasattr(self, "channel_date_filter") else ""
        filtered = []
        for video in self.channel_videos:
            memberships = video.get("memberships", [])
            playlist_ids = {item.get("playlist_id", "") for item in memberships}
            playlists = " ".join(item.get("playlist_title", "") for item in memberships)
            text = f"{video.get('title', '')} {video.get('id', '')} {playlists}".casefold()
            published = video.get("published_at", "")
            if query and query not in text:
                continue
            if privacy and video.get("privacy") != privacy:
                continue
            if playlist_filter == "" and memberships:
                continue
            if playlist_filter not in (None, "") and playlist_filter not in playlist_ids:
                continue
            if date_query and date_query not in published and date_query not in video.get("title", ""):
                continue
            filtered.append(video)
        self.render_channel_rows(filtered)
        self.channel_summary.setText(f"{len(filtered)} de {len(self.channel_videos)} videos")

    def selected_channel_videos(self) -> list[dict]:
        selected = self.channel_table.selectionModel().selectedRows()
        videos = []
        for index in selected:
            url_item = self.channel_table.item(index.row(), 6)
            if not url_item:
                continue
            video_id = url_item.text().rsplit("/", 1)[-1]
            match = next((video for video in self.channel_videos if video.get("id") == video_id), None)
            if match:
                videos.append(match)
        if not videos:
            QMessageBox.information(self, APP_NAME, "Selecciona primero uno o varios videos del canal.")
        return videos

    def open_selected_channel_video(self) -> None:
        videos = self.selected_channel_videos()
        if videos:
            webbrowser.open(f"https://youtu.be/{videos[0]['id']}")

    def share_selected_channel_video(self) -> None:
        videos = self.selected_channel_videos()
        if not videos:
            return
        video = videos[0]
        if QMessageBox.question(
            self, "Compartir video",
            f"Se pondra como Oculto y se copiara el enlace:\n\n{video.get('title', '')}"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.channel_summary.setText("Preparando enlace compartido...")
        threading.Thread(target=self._share_channel_video_thread, args=(video,), daemon=True).start()

    def _share_channel_video_thread(self, video: dict) -> None:
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            client.set_video_unlisted(video["id"])
            self.events.put(("channel_shared", video))
        except Exception as exc:
            self.events.put(("channel_error", f"No se pudo compartir el video: {engine.describe_error(exc)}"))

    def change_selected_channel_privacy(self) -> None:
        videos = self.selected_channel_videos()
        if not videos:
            return
        label, ok = QInputDialog.getItem(
            self, "Cambiar privacidad", f"Privacidad para {len(videos)} video(s):",
            ["Privado", "Oculto", "Publico"], 1, False
        )
        if not ok:
            return
        privacy = {"Privado": "private", "Oculto": "unlisted", "Publico": "public"}[label]
        threading.Thread(target=self._change_channel_privacy_thread, args=(videos, privacy), daemon=True).start()

    def _change_channel_privacy_thread(self, videos: list[dict], privacy: str) -> None:
        updated = []
        errors = []
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            for video in videos:
                try:
                    client.set_video_privacy(video["id"], privacy)
                    video["privacy"] = privacy
                    updated.append(video)
                except Exception as exc:
                    errors.append(f"{video.get('title', video.get('id', ''))}: {engine.describe_error(exc)}")
            self.events.put(("channel_privacy_changed", {"updated": updated, "errors": errors}))
        except Exception as exc:
            self.events.put(("channel_error", f"No se pudo cambiar privacidad: {engine.describe_error(exc)}"))

    def delete_selected_channel_videos(self) -> None:
        videos = self.selected_channel_videos()
        if not videos:
            return
        if QMessageBox.question(
            self, "Borrar del canal",
            f"Se borraran {len(videos)} video(s) de YouTube.\n\nNo se tocara ningun archivo local."
        ) != QMessageBox.StandardButton.Yes:
            return
        threading.Thread(target=self._delete_channel_videos_thread, args=(videos,), daemon=True).start()

    def _delete_channel_videos_thread(self, videos: list[dict]) -> None:
        deleted = []
        errors = []
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            for video in videos:
                try:
                    client.delete_video(video["id"])
                    deleted.append(video)
                except Exception as exc:
                    errors.append(f"{video.get('title', video.get('id', ''))}: {engine.describe_error(exc)}")
            self.events.put(("channel_deleted", {"deleted": deleted, "errors": errors}))
        except Exception as exc:
            self.events.put(("channel_error", f"No se pudo borrar del canal: {engine.describe_error(exc)}"))

    def change_selected_channel_playlist(self) -> None:
        videos = self.selected_channel_videos()
        if not videos:
            return
        if len(videos) > 1:
            QMessageBox.information(self, APP_NAME, "Selecciona un solo video para moverlo de lista.")
            return
        label = self.channel_playlist_combo.currentText()
        target_id = self.channel_playlists_by_label.get(label, "")
        video = videos[0]
        if QMessageBox.question(
            self,
            "Cambiar lista",
            f"Mover este video a '{label}'?\n\n{video.get('title', '')}",
        ) != QMessageBox.StandardButton.Yes:
            return
        threading.Thread(target=self._change_channel_playlist_thread, args=(video, target_id), daemon=True).start()

    def _change_channel_playlist_thread(self, video: dict, target_id: str) -> None:
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            client.replace_video_playlist(video["id"], video.get("memberships", []), target_id)
            self.events.put(("channel_playlist_changed", "Lista actualizada correctamente."))
        except Exception as exc:
            self.events.put(("channel_error", f"No se pudo cambiar la lista: {engine.describe_error(exc)}"))

    def channel_duplicate_key(self, video: dict) -> tuple | None:
        title = " ".join(str(video.get("title", "")).split()).casefold()
        if not title:
            return None
        fingerprint = str(video.get("fingerprint", "") or "").strip()
        if fingerprint:
            return ("fingerprint", fingerprint)
        filename = Path(str(video.get("filename", "") or "")).name.casefold()
        raw_duration = str(video.get("raw_duration", "") or video.get("duration", "") or "").strip()
        try:
            size = int(video.get("size", 0) or 0)
        except (TypeError, ValueError):
            size = 0
        if filename and size > 0 and raw_duration:
            return ("file", title, filename, size, raw_duration)
        return None

    def find_channel_duplicates(self) -> None:
        groups: dict[tuple, list[dict]] = {}
        skipped = 0
        for video in self.channel_videos:
            key = self.channel_duplicate_key(video)
            if key:
                groups.setdefault(key, []).append(video)
            else:
                skipped += 1
        duplicate_ids = {video["id"] for values in groups.values() if len(values) > 1 for video in values}
        if not duplicate_ids:
            detail = "No se encontraron duplicados fiables en el canal cargado."
            if skipped:
                detail += f"\n\n{skipped} video(s) no tienen metadatos suficientes para compararlos con seguridad."
            QMessageBox.information(self, "Duplicados", detail)
            return
        filtered = [video for video in self.channel_videos if video.get("id") in duplicate_ids]
        self.render_channel_rows(filtered)
        self.channel_summary.setText(
            f"{len(filtered)} videos en {sum(1 for values in groups.values() if len(values) > 1)} grupo(s) duplicado(s) fiables"
        )

    def channel_failed(self, message: str) -> None:
        self.channel_loader_bar.hide()
        self.channel_loader = None
        self.channel_summary.setText(f"No se pudo cargar el canal: {message}")
        if engine.is_youtube_quota_error(message):
            scope = engine.api_scope(self.config.client_secret_path)
            self.api_pause_state = self.store.api_pause(scope) or self.store.api_pause(scope, "upload")
            self.update_quota_status()
        else:
            QMessageBox.warning(self, APP_NAME, self.channel_summary.text())

    def open_settings(self) -> None:
        if self.settings_dialog is not None:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return
        dialog = SettingsDialog(self.store, self.config, self)
        self.settings_dialog = dialog
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.destroyed.connect(lambda: setattr(self, "settings_dialog", None))
        dialog.saved.connect(lambda: self.refresh_all(light=False))
        dialog.show()

    def process_events(self) -> None:
        for _ in range(100):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                return
            if kind == "log":
                self.log(value)
            elif kind == "progress":
                percent = int(value.get("percent", 0))
                filename = value.get("filename", "")
                self.progress.setValue(percent)
                self.upload_card.set(f"{percent}%" if filename else "Sin actividad", filename or "Esperando videos")
            elif kind == "busy":
                if not self.api_pause_state:
                    self.status.setText("Trabajando..." if value else "Preparado")
            elif kind == "upload_completed":
                self.folder_refresh_timer.start(0)
                self.check_youtube(full=False)
            elif kind == "folder_refresh":
                self.folder_refresh_timer.start(150)
            elif kind == "upload_limited":
                self.auto_enabled = False
                self.update_auto_button()
                self.upload_card.set("Limite YouTube", value.get("message", "Reintento mas tarde"))
            elif kind == "api_quota":
                self.api_pause_state = value
                self.upload_card.set("En espera", "Cuota API / archivos conservados")
                self.update_quota_status()
            elif kind == "youtube_check_done":
                self.youtube_check_running = False
            elif kind == "youtube":
                self.youtube_check_running = False
                self.state_card.set("Conectado", value.get("title", "Canal conectado"))
                self.status.setText("Videos comprobados con YouTube")
            elif kind == "youtube_error":
                self.youtube_check_running = False
                self.state_card.set("Sin conexion", value)
                self.log(f"No se pudieron actualizar los estados: {value}")
            elif kind == "channel_shared":
                value["privacy"] = "unlisted"
                url = f"https://youtu.be/{value['id']}"
                QApplication.clipboard().setText(url)
                self.filter_channel_table()
                self.channel_summary.setText("Video en Oculto / enlace copiado")
            elif kind == "channel_privacy_changed":
                updated = len(value.get("updated", []))
                errors = value.get("errors", [])
                self.filter_channel_table()
                self.channel_summary.setText(f"{updated} video(s) actualizado(s)")
                if errors:
                    QMessageBox.warning(self, APP_NAME, "\n".join(errors[:6]))
            elif kind == "channel_deleted":
                deleted_ids = {video.get("id") for video in value.get("deleted", [])}
                self.channel_videos = [video for video in self.channel_videos if video.get("id") not in deleted_ids]
                self.filter_channel_table()
                errors = value.get("errors", [])
                self.channel_summary.setText(f"{len(deleted_ids)} video(s) borrado(s) del canal")
                if errors:
                    QMessageBox.warning(self, APP_NAME, "\n".join(errors[:6]))
            elif kind == "channel_error":
                self.channel_summary.setText(value)
                QMessageBox.warning(self, APP_NAME, value)
            elif kind == "channel_playlist_changed":
                self.channel_summary.setText(value)
                self.refresh_channel()
            elif kind == "local_delete_result":
                self.refresh_folder()
                deleted = int(value.get("deleted", 0))
                errors = value.get("errors", [])
                message = f"{deleted} archivo(s) local(es) borrado(s)."
                if errors:
                    message += "\n\nNo borrados:\n" + "\n".join(errors[:8])
                    QMessageBox.warning(self, "Limpieza", message)
                else:
                    QMessageBox.information(self, "Limpieza", message)

    def log(self, text: str) -> None:
        self.console.append(text)


def apply_style(app: QApplication) -> None:
    app.setStyleSheet(
        """
        QWidget {
            background: #0f0f10;
            color: #f6f7f9;
            font-family: Segoe UI;
            font-size: 10pt;
        }
        QLabel {
            background: transparent;
            border: none;
        }
        QCheckBox {
            background: transparent;
            spacing: 8px;
        }
        #AppTitle {
            background: transparent;
            font-size: 20pt;
            font-weight: 800;
        }
        #PageTitle {
            background: transparent;
            font-size: 15pt;
            font-weight: 800;
        }
        #Muted, #CardDetail {
            background: transparent;
            color: #a7adb8;
        }
        #Card {
            background: #18181b;
            border: 1px solid #2a2b31;
            border-radius: 16px;
        }
        #CardTitle {
            background: transparent;
            color: #a7adb8;
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 0;
        }
        #CardValue {
            background: transparent;
            font-size: 15pt;
            font-weight: 800;
        }
        #SettingsSection {
            background: #18181b;
            border: 1px solid #2a2b31;
            border-radius: 16px;
        }
        #PreviewPanel {
            background: #18181b;
            border: 1px solid #2a2b31;
            border-radius: 16px;
        }
        #PreviewThumb, #ThumbCell {
            background: #0b0b0c;
            border: 1px solid #2a2b31;
            border-radius: 12px;
            color: #6f7684;
        }
        #PreviewThumb {
            padding: 0px;
        }
        #InfoPill {
            background: #101114;
            border: 1px solid #30313a;
            border-radius: 14px;
            padding: 9px 11px;
            color: #f6f7f9;
            font-weight: 800;
        }
        QSplitter::handle {
            background: transparent;
            width: 12px;
        }
        #SectionTitle {
            background: transparent;
            color: #ff3157;
            font-size: 9pt;
            font-weight: 800;
            letter-spacing: 0;
        }
        QPushButton, QToolButton {
            background: #24252b;
            border: 1px solid #30313a;
            border-radius: 14px;
            padding: 10px 16px;
            font-weight: 700;
            min-height: 22px;
        }
        QPushButton:hover, QToolButton:hover {
            background: #31323b;
            border-color: #5b5d6a;
        }
        QPushButton:disabled, QToolButton:disabled {
            color: #757b87;
            background: #1c1d21;
            border-color: #282a30;
        }
        QPushButton:focus, QToolButton:focus, QLineEdit:focus, QComboBox:focus {
            border-color: #ff3157;
        }
        QPushButton:pressed, QToolButton:pressed {
            background: #444652;
            border-color: #ff3157;
            padding-top: 12px;
            padding-bottom: 8px;
        }
        #HeaderTool {
            min-width: 38px;
            max-width: 38px;
            min-height: 38px;
            max-height: 38px;
            border-radius: 12px;
            padding: 0px;
        }
        #AutoOn {
            background: #16a34a;
            border-color: #22c55e;
        }
        #AutoOff, #PrimaryButton {
            background: #ff0033;
            border-color: #ff3157;
        }
        #PrimaryButton:hover {
            background: #ff3157;
        }
        #DangerButton {
            background: #991b1b;
            border-color: #ef4444;
        }
        #DangerButton:hover {
            background: #b91c1c;
        }
        QTabWidget::pane {
            border: 1px solid #2a2b31;
            border-radius: 16px;
            top: -1px;
        }
        QTabBar::tab {
            background: #18181b;
            color: #a7adb8;
            padding: 12px 22px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            margin-right: 4px;
        }
        QTabBar::tab:selected {
            background: #ff0033;
            color: white;
        }
        QTableWidget {
            background: #121214;
            alternate-background-color: #17171a;
            border: none;
            gridline-color: #25262d;
            selection-background-color: #3a1420;
        }
        QHeaderView::section {
            background: #24252b;
            color: #f6f7f9;
            border: none;
            padding: 9px;
            font-weight: 800;
        }
        QLineEdit, QComboBox, QTextEdit {
            background: #121214;
            border: 1px solid #30313a;
            border-radius: 10px;
            padding: 9px;
        }
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollBar:vertical {
            background: #111114;
            width: 10px;
            margin: 2px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #3a3b44;
            min-height: 34px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #555762;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QProgressBar {
            background: #24252b;
            border: none;
            border-radius: 8px;
            height: 10px;
            text-align: center;
        }
        QProgressBar::chunk {
            background: #ff0033;
            border-radius: 8px;
        }
        """
    )


def main() -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_style(app)
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        import json
        import ssl
        ssl.create_default_context()
        preview = QWidget()
        preview.show()
        app.processEvents()
        preview.close()
        Path(sys.argv[2]).write_text(json.dumps({"ok": True, "ui": "qt", "ssl": True}), encoding="utf-8")
        return
    window = MainWindow()
    if window.config.start_minimized and QSystemTrayIcon.isSystemTrayAvailable():
        window.hide()
    else:
        window.show()
    window.check_youtube()
    if window.auto_enabled:
        window.start_worker()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
