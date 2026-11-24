import os
import queue
import sys
import threading
import urllib.request
import webbrowser
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QEvent, QRect, QSize, QTimer, Qt, Signal, QObject
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
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
    QLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "YouTubeSync"
ROOT = Path(__file__).resolve().parents[1]


import youtube_sync_engine as engine
from youtube_sync_setup import SetupWizard
from youtube_sync_update_ui import UpdatePanel
from youtube_sync_version import APP_ID, APP_VERSION
from youtube_sync_icons import app_icon, standard_icon, decorate_buttons
from youtube_sync_diagnostics import DiagnosticBuffer, DiagnosticWindow, redact_secrets
from youtube_sync_manual import quota_console_url
from youtube_sync_manual_ui import ManualConfirmationDialog
from youtube_sync_help import install_button_help
from youtube_sync_browser_session import find_browser, open_playback_session
from youtube_sync_library import (LIBRARY_COLUMNS, DEFAULT_LIBRARY_COLUMNS, MEDIA_COLUMNS, STATUS_ICONS,
                                  normalize_library_columns, media_cells)
from youtube_sync_local_media import LocalMediaLoader
from youtube_sync_cleanup import scan_short_videos, delete_short_videos, delete_local_files
from youtube_sync_i18n import LANGUAGES, set_language, t
from youtube_sync_i18n_widgets import (
    QAction, QCheckBox, QComboBox, QDialog, QFileDialog, QInputDialog, QLabel,
    QLineEdit, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
    QStyledItemDelegate, QTableWidget, QTableWidgetItem, QTabWidget, QToolButton, QWidget, RawLabel,
)


def asset_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", ROOT))
    return base / "assets" / name


def table_item(text: str, color: str = "") -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    if color:
        item.setForeground(QColor(color))
    return item


class NumericTableItem(QTableWidgetItem):
    def __init__(self, text: str, value: float):
        super().__init__(text)
        self.setTextAlignment(Qt.AlignCenter)
        self.setData(Qt.UserRole, value)

    def __lt__(self, other):
        value = other.data(Qt.UserRole)
        if isinstance(value, (int, float)):
            return self.data(Qt.UserRole) < value
        return super().__lt__(other)


class LibraryItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.decorationSize = QSize(96, 54) if index.column() == 7 else QSize(18, 18)


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
            painter.drawText(self.rect(), Qt.AlignCenter, t(self._placeholder))
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


class SettingsDialog(QWidget):
    saved = Signal()
    setup_requested = Signal()
    problem = Signal(str)
    console_requested = Signal()

    def __init__(self, store, config, parent=None) -> None:
        super().__init__(parent, Qt.Window)
        self.store = store
        self.config = replace(config)
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
        layout.addWidget(title)

        self.settings_search = QLineEdit()
        self.settings_search.setPlaceholderText("Buscar ajuste: carpeta, columnas, privacidad, auto, limpieza...")
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
            translated_terms = t(title_text) + " " + " ".join(t(term) for term in terms.split())
            self.settings_sections.append((frame, tabs.indexOf(parent_layout.parentWidget()), f"{title_text} {terms} {translated_terms}".casefold()))
            return frame

        general_page, general_layout = tab_page("General")
        youtube_page, youtube_tab_layout = tab_page("YouTube")
        playback_page, playback_layout = tab_page("Reproducción")
        automation_page, automation_tab_layout = tab_page("Automatizacion")
        cleanup_page, cleanup_tab_layout = tab_page("Limpieza")
        library_page, library_layout = tab_page("Biblioteca")

        columns = tracked_section(library_layout, "Columnas de la biblioteca",
                                  "archivo titulo tamaño creado estado ruta columnas orden miniatura calidad resolucion resolución duracion duración fps")
        column_row = QHBoxLayout()
        self.library_columns = QListWidget()
        self.library_columns.setIconSize(QSize(20, 20))
        self.library_columns.setMinimumHeight(292)
        self.library_columns.setDragDropMode(QAbstractItemView.InternalMove)
        self.library_columns.setDefaultDropAction(Qt.MoveAction)
        self.library_columns.setSelectionMode(QAbstractItemView.SingleSelection)
        self.fill_library_columns(config.library_columns)
        column_row.addWidget(self.library_columns, 1)
        column_tools = QVBoxLayout()
        for delta, icon, label in ((-1, "chevron-up", "Mover columna arriba"), (1, "chevron-down", "Mover columna abajo")):
            button = QPushButton(app_icon(icon), "")
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.clicked.connect(lambda _checked=False, delta=delta: self.move_library_column(delta))
            column_tools.addWidget(button)
        column_tools.addStretch(1)
        column_row.addLayout(column_tools)
        columns.layout().addLayout(column_row, 1)
        reset_columns = QPushButton(app_icon("rotate-ccw"), "Predeterminadas")
        reset_columns.clicked.connect(lambda: self.fill_library_columns(list(DEFAULT_LIBRARY_COLUMNS)))
        columns.layout().addWidget(reset_columns, 0, Qt.AlignRight)
        library_layout.setStretch(0, 1)

        app_section = tracked_section(general_layout, "Aplicacion", "version actualizacion updater consola diagnostico errores registro logs copiar informe idioma language español english")
        app_layout = app_section.layout()
        self.update_panel = UpdatePanel(self.store.base, self)
        app_layout.addWidget(self.update_panel)
        console_row = QHBoxLayout()
        console_row.addWidget(QLabel("Idioma"))
        self.language_combo = QComboBox()
        self.language_combo.setProperty("translatedItemCount", 0)
        for code, name in LANGUAGES:
            self.language_combo.addItem(name, code)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(config.language)))
        self.language_combo.setMinimumWidth(150)
        self.language_combo.setToolTip("Se aplica al volver a abrir YouTubeSync.")
        console_row.addWidget(self.language_combo)
        restart_hint = QLabel("Tras reiniciar")
        restart_hint.setObjectName("Muted")
        console_row.addWidget(restart_hint)
        console_row.addStretch(1)
        console_button = QPushButton("Consola")
        console_button.clicked.connect(self.console_requested.emit)
        console_row.addWidget(console_button)
        app_layout.addLayout(console_row)

        folder = tracked_section(general_layout, "Carpeta", "videos extensiones subcarpetas ruta")
        folder_layout = folder.layout()
        self.folder = self.path_row(folder_layout, "Carpeta de videos", config.watch_folder, self.pick_folder)
        self.extensions = QLineEdit(config.extensions)
        folder_layout.addLayout(self.field_row("Extensiones", self.extensions))
        self.recursive = QCheckBox("Incluir subcarpetas")
        self.recursive.setChecked(bool(config.recursive))
        folder_layout.addWidget(self.recursive)
        general_layout.addStretch(1)

        youtube = tracked_section(youtube_tab_layout, "YouTube / OAuth", "json oauth credenciales privacidad categoria canal conexion conectar asistente")
        youtube_layout = youtube.layout()
        self.oauth = self.path_row(youtube_layout, "JSON OAuth", config.client_secret_path, self.pick_json)
        oauth_tools = QHBoxLayout()
        wizard_button = QPushButton("Conectar mi canal")
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
        self.playlist_combo.setProperty("translatedItemCount", int(not config.playlist_id))
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
        session = tracked_section(playback_layout, "Sesión de reproducción", "sesion sesión iniciar login cuenta privados reproducción chrome edge navegador")
        session_row = QHBoxLayout()
        browser = find_browser()
        self.playback_session_status = QLabel(("Chrome" if browser and browser.stem.lower() == "chrome" else "Microsoft Edge") + " · Cuenta independiente de OAuth"
                                             if browser else "Se necesita Chrome o Microsoft Edge")
        self.playback_session_status.setObjectName("Muted")
        self.playback_session_status.setWordWrap(True)
        session_row.addWidget(self.playback_session_status, 1)
        self.playback_login = QPushButton(app_icon("user-round"), "Gestionar sesión")
        self.playback_login.setAccessibleName("Gestionar sesión de reproducción")
        self.playback_login.setToolTip("Gestionar sesión de reproducción")
        self.playback_login.clicked.connect(self.open_playback_login)
        session_row.addWidget(self.playback_login)
        session.layout().addLayout(session_row)
        playback_layout.addStretch(1)
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
        for kind in (QLineEdit, QComboBox, QSpinBox):
            for control in self.findChildren(kind):
                if not (kind is QLineEdit and isinstance(control.parentWidget(), QSpinBox)):
                    control.setMinimumHeight(38)
        for frame, _index, _terms in self.settings_sections:
            frame.layout().setSizeConstraint(QLayout.SetMinimumSize)
        decorate_buttons(self)

    def open_playback_login(self) -> None:
        try:
            open_playback_session(self.store.base)
            self.playback_session_status.setText("Ventana de sesión abierta. Comprueba la cuenta con acceso a tus vídeos privados.")
        except OSError as exc:
            QMessageBox.warning(self, "Sesión de reproducción", str(exc))

    def fill_library_columns(self, visible: list[str]) -> None:
        self.library_columns.clear()
        visible = normalize_library_columns(visible)
        definitions = {key: (label, icon) for key, label, icon in LIBRARY_COLUMNS}
        for key in visible + [key for key in definitions if key not in visible]:
            label, icon = definitions[key]
            item = QListWidgetItem(app_icon(icon), label)
            item.setData(Qt.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            item.setCheckState(Qt.Checked if key in visible else Qt.Unchecked)
            item.setSizeHint(QSize(0, 28))
            if key == "resolution":
                item.setToolTip("Dimensiones reales del archivo, leidas por Windows.")
            elif key == "thumbnail":
                item.setToolTip("Miniatura del Explorador de Windows, si el formato dispone de ella.")
            self.library_columns.addItem(item)
        self.library_columns.setCurrentRow(0)

    def move_library_column(self, delta: int) -> None:
        row = self.library_columns.currentRow()
        target = row + delta
        if row >= 0 and 0 <= target < self.library_columns.count():
            self.library_columns.insertItem(target, self.library_columns.takeItem(row))
            self.library_columns.setCurrentRow(target)

    def selected_library_columns(self) -> list[str]:
        return [self.library_columns.item(row).data(Qt.UserRole) for row in range(self.library_columns.count())
                if self.library_columns.item(row).checkState() == Qt.Checked]

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

    def closeEvent(self, event) -> None:
        self.update_panel.shutdown()
        super().closeEvent(event)

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
            try:
                self.oauth.setText(str(self.store.import_oauth_json(Path(path))))
            except (OSError, ValueError) as exc:
                self.problem.emit(engine.describe_error(exc))
                QMessageBox.warning(self, "JSON OAuth", str(exc))

    def open_oauth_wizard(self) -> None:
        self.setup_requested.emit()

    def apply_connection(self, config: engine.Config) -> None:
        self.config = replace(config)
        self.oauth.setText(config.client_secret_path)
        self.folder.setText(config.watch_folder)
        self.recursive.setChecked(config.recursive)
        self.auto_start.setChecked(config.auto_start_enabled)
        self.privacy.setCurrentIndex(self.privacy.findText({"private": "Privado", "unlisted": "Oculto", "public": "Publico"}[config.privacy_status]))
        self.set_playlist_options([{"id": "", "title": "Ninguna"},
                                   {"id": config.playlist_id, "title": config.playlist_name}] if config.playlist_id
                                  else [{"id": "", "title": "Ninguna"}], config.playlist_id)

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
            self.problem.emit(engine.describe_error(exc))
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
        for index, label in enumerate(labels):
            self.playlist_combo.setItemData(index, not bool(self.playlists_by_label[label]), Qt.UserRole + 57)
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
            self.problem.emit(engine.describe_error(exc))
            QMessageBox.warning(self, "Crear lista", f"No se pudo crear la lista:\n\n{engine.describe_error(exc)}")

    def save(self) -> None:
        columns = self.selected_library_columns()
        if not columns:
            QMessageBox.warning(self, "Biblioteca", "Selecciona al menos una columna para la biblioteca.")
            return
        oauth = self.oauth.text().strip()
        if oauth:
            try:
                oauth = str(self.store.import_oauth_json(Path(oauth)))
            except (OSError, ValueError) as exc:
                self.problem.emit(engine.describe_error(exc))
                QMessageBox.warning(self, "JSON OAuth", str(exc))
                return
        privacy = {"Privado": "private", "Oculto": "unlisted", "Publico": "public"}[self.privacy.currentText()]
        self.config.watch_folder = self.folder.text().strip()
        self.config.client_secret_path = oauth
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
        self.config.library_columns = columns
        self.config.language = self.language_combo.currentData() or "es"
        try:
            self.store.save_config(self.config)
        except OSError as exc:
            self.problem.emit(engine.describe_error(exc))
            QMessageBox.warning(self, "Ajustes", "No se pudieron guardar los ajustes. Comprueba los permisos de la carpeta de datos.")
            return
        try:
            engine.set_run_at_startup(self.config.run_at_startup)
        except Exception:
            pass
        self.saved.emit()
        self.close()


@dataclass(frozen=True)
class Guidance:
    title: str
    detail: str
    level: str = "info"
    actions: tuple[tuple[str, str], ...] = ()
    target: str = ""
    diagnostic: str = ""


def problem_guidance(message: str, context: str = "Operacion", target: str = "") -> Guidance:
    text = message.casefold()
    if (target or context == "Subida") and any(word in text for word in ("cancelad", "cancelled", "canceled")):
        return Guidance("Subida cancelada", "El archivo se conserva. No se iniciara otra transferencia sin tu autorizacion.",
                        "info", (("Reintentar video", "retry_video"), ("Consola", "console")) if target else (("Videos", "videos"),), target)
    if any(word in text for word in ("oauth", "invalid_grant", "invalid_scope", "unauthorized", "401", "credencial", "autorizacion")):
        return Guidance("Revisa la conexion", "Autoriza de nuevo tu canal con Google o revisa el JSON OAuth en Ajustes.",
                        "error", (("Conectar canal", "connect"), ("Ajustes", "youtube_settings")))
    if any(word in text for word in ("accessnotconfigured", "servicedisabled", "api has not been used", "api is disabled")):
        return Guidance("Activa la API de YouTube", "Activa YouTube Data API v3 en el proyecto del JSON y vuelve a comprobar la conexion.",
                        "error", (("Activar API", "enable_api"), ("Comprobar", "refresh")))
    if any(word in text for word in ("forbidden", "403", "insufficientpermission", "permission", "permiso", "access denied", "acceso denegado", "read-only", "winerror 5")):
        return Guidance("Faltan permisos", "Comprueba los permisos, el canal autorizado y el acceso al archivo. No se ha confirmado la operacion.",
                        "error", (("Ajustes", "settings"), ("Consola", "console")))
    if any(word in text for word in ("timeout", "timed out", "connection", "conexion", "network", "ssl", "certificate", "dns")):
        return Guidance("Fallo de conexion", "Revisa Internet, VPN o proxy antes de reintentar. Los archivos se conservan.",
                        "warning", (("Reintentar video", "retry_video") if target else ("Comprobar", "refresh"), ("Consola", "console")), target)
    if any(word in text for word in ("carpeta", "ruta", "file not found", "no such file", "no existe el archivo")):
        return Guidance("Revisa carpeta o archivo", "La ruta no esta disponible. Comprueba que la unidad este conectada y que la carpeta elegida exista.",
                        "error", (("Carpeta", "folder_settings"), ("Videos", "videos")), target)
    detail = "Revisa el motivo en Consola. El archivo no se volvera a subir por si solo." if target else "Consulta el detalle en Consola y revisa los ajustes antes de repetir la accion."
    return Guidance(f"{context}: necesita revision", detail, "warning",
                    (("Revisar video", "videos") if target else ("Ajustes", "settings"), ("Consola", "console")), target)


class Card(QFrame):
    def __init__(self, title: str, with_detail: bool = True) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        self.title = QLabel(title.upper())
        self.title.setObjectName("CardTitle")
        self.value = QLabel("-")
        self.value.setObjectName("CardValue")
        self.value.setWordWrap(True)
        self.value.setMinimumWidth(0)
        self.detail = QLabel("") if with_detail else None
        if self.detail is not None:
            self.detail.setObjectName("CardDetail")
            self.detail.setWordWrap(True)
            self.detail.setMinimumWidth(0)
            self.detail.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        for label in (self.title, self.value):
            label.setTextFormat(Qt.PlainText)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        if self.detail is not None:
            self.detail.setTextFormat(Qt.PlainText)
            layout.addWidget(self.detail)

    def set(self, value: str, detail: str = "") -> None:
        self.value.setText(value)
        if self.detail is not None:
            self.detail.setText(detail)


class ElidedLabel(RawLabel):
    def __init__(self) -> None:
        super().__init__()
        self.full_text = ""
        self.setMinimumWidth(0)
        self.setTextFormat(Qt.PlainText)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def set_value(self, text: str, tooltip: str = "") -> None:
        self.full_text = text
        self.setToolTip(tooltip or text)
        self.update_text()

    def update_text(self) -> None:
        self.setText(self.fontMetrics().elidedText(self.full_text, Qt.ElideMiddle, max(24, self.width())))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_text()


class TransferStrip(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TransferStrip")
        self.setFixedHeight(44)
        self.phase = "idle"
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(10)
        self.icon = QLabel()
        self.icon.setFixedSize(20, 20)
        self.status_label = QLabel()
        self.status_label.setObjectName("TransferStatus")
        self.status_label.setFixedWidth(100)
        self.filename = ElidedLabel()
        self.filename.setObjectName("CardDetail")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setMinimumWidth(140)
        self.progress.setMaximumWidth(220)
        self.percent_label = QLabel()
        self.percent_label.setFixedWidth(36)
        self.percent_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.icon)
        row.addWidget(self.status_label)
        row.addWidget(self.filename, 1)
        row.addWidget(self.progress, 1)
        row.addWidget(self.percent_label)
        self.hide()

    def show_state(self, phase: str, filename: str, percent: int) -> None:
        self.phase = phase
        self.setVisible(phase != "idle")
        if phase == "idle":
            self.filename.set_value("")
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            return
        label, icon, color = {
            "queued": ("Preparando", "clock", "#a8b2c5"),
            "uploading": ("Subiendo", "arrow-up", "#ff4c68"),
            "paused": ("En pausa", "clock", "#efc26d"),
            "processing": ("Procesando", "clock", "#56b6ff"),
            "canceling": ("Cancelando", "square", "#efc26d"),
        }[phase]
        self.status_label.setText(label)
        self.icon.setPixmap(app_icon(icon, color).pixmap(20, 20))
        self.icon.setToolTip(label)
        self.filename.set_value(filename)
        indeterminate = phase in {"queued", "processing"}
        self.progress.setRange(0, 0 if indeterminate else 100)
        if not indeterminate:
            self.progress.setValue(percent)
        self.percent_label.setVisible(not indeterminate)
        self.percent_label.setText(f"{percent}%")
        self.setProperty("phase", phase)
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    thumbnail_loaded = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self.store = engine.Store()
        self.config = self.store.load_config()
        set_language(self.config.language)
        self.events = queue.Queue()
        self.worker = None
        self.local_delete_running = False
        self.manual_confirmation_running = False
        self.single_verifications = set()
        self._allow_exit = False
        self.settings_dialog = None
        self.diagnostic_buffer = DiagnosticBuffer(self)
        self.diagnostic_window = None
        self.setup_dialog = None
        self._resume_after_setup_check = False
        self.auto_enabled = bool(self.config.auto_start_enabled)
        self.channel_loader = None
        self.youtube_check_running = False
        self.api_pause_state = None
        self.last_quota_diagnostic = None
        self.channel_limit_state = None
        self.guidance_notices: dict[str, Guidance] = {}
        self.guidance_selected = None
        self.guidance_browsing = False
        self.transfer_filename = ""
        self.transfer_percent = 0
        self.transfer_candidates = 0
        self.processing_files: list[str] = []
        self.connection_value = "Preparado"
        self.connection_channel = self.config.connected_channel_name
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
            button.setIcon(standard_icon(icon))
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

    def polish_header_tool(self, button: QToolButton, icon: QStyle.StandardPixmap | QIcon) -> None:
        button.setObjectName("HeaderTool")
        button.setIcon(standard_icon(icon))
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
        self.polish_header_tool(self.upload_btn, app_icon("arrow-up"))
        self.upload_btn.clicked.connect(self.upload_pending)
        self.cancel_btn = QToolButton()
        self.cancel_btn.setText("")
        self.cancel_btn.setToolTip("Cancelar subida actual")
        self.polish_header_tool(self.cancel_btn, app_icon("square"))
        self.cancel_btn.clicked.connect(self.cancel_upload)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("")
        self.refresh_btn.setToolTip("Actualizar")
        self.polish_header_tool(self.refresh_btn, app_icon("refresh-cw"))
        self.refresh_btn.clicked.connect(self.request_remote_refresh)
        self.settings_btn = QToolButton()
        self.settings_btn.setText("")
        self.settings_btn.setToolTip("Ajustes")
        self.polish_header_tool(self.settings_btn, app_icon("settings"))
        self.settings_btn.clicked.connect(self.open_settings)
        for button in (self.auto_btn, self.upload_btn, self.cancel_btn, self.refresh_btn, self.settings_btn):
            header.addWidget(button)
        main.addLayout(header)

        cards = QGridLayout()
        self.state_card = Card("Canal y carpeta", with_detail=False)
        self.state_connection_icon = QLabel()
        self.state_connection_icon.setFixedSize(18, 18)
        self.state_card.layout().removeWidget(self.state_card.value)
        connection_row = QHBoxLayout()
        connection_row.setSpacing(8)
        connection_row.addWidget(self.state_connection_icon)
        connection_row.addWidget(self.state_card.value, 1)
        self.state_card.layout().insertLayout(1, connection_row)
        self.profile_fields = []
        profile_grid = QGridLayout()
        profile_grid.setHorizontalSpacing(18)
        profile_grid.setVerticalSpacing(8)
        profile_grid.setColumnStretch(0, 1)
        profile_grid.setColumnStretch(1, 1)
        self.state_card.layout().addLayout(profile_grid)

        def profile_field(name: str, icon: str, color: str, grid_row: int, column: int, span: int = 1) -> ElidedLabel:
            field = QWidget()
            field.setObjectName("ProfileField")
            field_layout = QHBoxLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(8)
            glyph = QLabel()
            glyph.setPixmap(app_icon(icon, color).pixmap(16, 16))
            glyph.setFixedSize(16, 16)
            glyph.setToolTip(name)
            value = ElidedLabel()
            value.icon_label = glyph
            value.setAccessibleName(name)
            value.setObjectName("ProfileValue")
            field_layout.addWidget(glyph)
            field_layout.addWidget(value, 1)
            profile_grid.addWidget(field, grid_row, column, 1, span)
            self.profile_fields.append(value)
            return value

        self.profile_channel = profile_field("Canal", "user-round", "#ff4c68", 0, 0)
        self.profile_privacy = profile_field("Privacidad", "lock", "#a8b2c5", 0, 1)
        self.profile_folder = profile_field("Carpeta", "folder-open", "#56b6ff", 1, 0, 2)
        self.profile_category = profile_field("Categoria", "tag", "#e8b85b", 2, 0)
        self.profile_playlist = profile_field("Lista", "list-video", "#5bd8b7", 2, 1)
        self.guidance_card = Card("Ahora")
        self.guidance_card.setObjectName("GuidanceCard")
        self.guidance_card.value.setObjectName("GuidanceValue")
        self.guidance_target = QLabel()
        self.guidance_target.setObjectName("CardDetail")
        self.guidance_target.setMinimumWidth(0)
        self.guidance_target.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.guidance_target.setTextFormat(Qt.PlainText)
        self.guidance_card.layout().insertWidget(2, self.guidance_target)
        guidance_tools = QHBoxLayout()
        self.guidance_buttons = []
        for index in range(5):
            button = self.action_button("")
            button.setObjectName("GuidanceAction")
            if index > 0:
                button.setObjectName("GuidanceTool")
                button.setFixedWidth(38)
            button.clicked.connect(lambda checked=False, slot=index: self.run_guidance_action(slot))
            guidance_tools.addWidget(button)
            self.guidance_buttons.append(button)
        guidance_tools.addStretch(1)
        self.guidance_previous = self.icon_button("Aviso anterior", app_icon("arrow-left"))
        self.guidance_previous.setObjectName("GuidanceTool")
        self.guidance_previous.setFixedWidth(38)
        self.guidance_previous.clicked.connect(lambda: self.next_guidance(-1))
        guidance_tools.addWidget(self.guidance_previous)
        self.guidance_next = self.icon_button("Siguiente aviso", app_icon("arrow-right"))
        self.guidance_next.setObjectName("GuidanceTool")
        self.guidance_next.setFixedWidth(38)
        self.guidance_next.clicked.connect(lambda: self.next_guidance())
        guidance_tools.addWidget(self.guidance_next)
        self.guidance_card.layout().addLayout(guidance_tools)
        cards.addWidget(self.state_card, 0, 0)
        cards.addWidget(self.guidance_card, 0, 1)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)
        main.addLayout(cards)

        self.transfer_strip = TransferStrip()
        self.progress = self.transfer_strip.progress
        main.addWidget(self.transfer_strip)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_videos_page(), "Videos")
        self.tabs.addTab(self.build_channel_page(), "Canal")
        self.tabs.setTabIcon(0, app_icon("file-video-camera"))
        self.tabs.setTabIcon(1, app_icon("user-round"))
        self.tabs.currentChanged.connect(self.tab_changed)
        main.addWidget(self.tabs, 1)
        self.update_auto_button()
        self.render_guidance()

    def set_guidance(self, source: str, notice: Guidance | None) -> None:
        if self.guidance_notices.get(source) == notice:
            return
        if notice is None:
            self.guidance_notices.pop(source, None)
        else:
            self.guidance_notices[source] = notice
        self.render_guidance()

    def render_guidance(self) -> None:
        priorities = {"configuration": 100, "quota": 95, "channel_limit": 94, "connection": 90, "settings": 85,
                      "manual_confirmation": 84, "verification": 83, "selection": 82, "review": 81,
                      "upload": 80, "channel": 75, "cleanup": 70, "library": 60, "activity": 10}
        sources = sorted((source for source in self.guidance_notices if source != "activity"),
                         key=lambda key: priorities.get(key, 50), reverse=True)
        if not sources and "activity" in self.guidance_notices:
            sources = ["activity"]
        self.guidance_order = sources
        if not self.guidance_browsing or self.guidance_selected not in sources:
            self.guidance_browsing = False
            self.guidance_selected = sources[0] if sources else None
        notice = self.guidance_notices.get(self.guidance_selected) or Guidance(
            "Esperando archivos" if self.auto_enabled else "Sin transferencia activa",
            "Automatico ON" if self.auto_enabled else "Automatico OFF")
        actions = list(notice.actions)
        row = next((row for row in self.video_rows.values() if row.get("path") == notice.target), None)
        extras = []
        if row:
            if row.get("youtube_id"):
                extras.append(("Ver YouTube", "open_video"))
            extras.append(("Ver local", "open_local"))
            if row.get("status") in {"Por verificar", "Subido (manual)"}:
                extras.append(("Confirmar coincidencia", "manual_verify"))
            else:
                extras.append(("Borrar local", "delete_local"))
        elif notice.level in {"warning", "error"}:
            extras.append(("Consola", "console"))
            if notice.diagnostic:
                extras.append(("Copiar detalle", "copy_detail"))
        for label, action in extras:
            if action not in {action for _label, action in actions} and len(actions) < 5:
                actions.append((label, action))
        notice = replace(notice, actions=tuple(actions))
        self.active_guidance = notice
        self.guidance_card.set(notice.title, notice.detail)
        self.guidance_card.setToolTip(notice.diagnostic or notice.detail)
        self.guidance_target.setVisible(bool(notice.target))
        self.guidance_target.setToolTip(notice.target)
        self.guidance_target.setText(self.guidance_target.fontMetrics().elidedText(
            Path(notice.target).name if notice.target else "", Qt.ElideMiddle, max(80, self.guidance_card.width() - 28)))
        self.guidance_card.title.setText(f"AHORA / {sources.index(self.guidance_selected) + 1} DE {len(sources)}" if len(sources) > 1 else "AHORA")
        self.guidance_card.setProperty("level", notice.level)
        self.guidance_card.style().unpolish(self.guidance_card)
        self.guidance_card.style().polish(self.guidance_card)
        icons = {"connect": "key-round", "settings": "settings", "youtube_settings": "settings",
                 "folder_settings": "folder-open", "refresh": "refresh-cw", "retry_video": "rotate-ccw",
                 "console": "terminal", "videos": "layers", "channel": "user-round", "quota": "monitor",
                 "enable_api": "external-link", "open_video": "play", "review_video": "circle-question-mark",
                 "open_local": "folder-open", "delete_local": "trash", "manual_verify": "circle-check",
                 "check_video": "refresh-cw", "studio": "external-link", "channel_limits": "circle-exclamation-point",
                 "quota_request": "external-link", "copy_detail": "copy", "upload_file": "arrow-up", "cancel_upload": "square"}
        for index, button in enumerate(self.guidance_buttons):
            button.setVisible(index < len(notice.actions))
            if index < len(notice.actions):
                label, action = notice.actions[index]
                short_labels = {"Reintentar video": "Reintentar", "Revisar videos": "Revisar", "Conectar canal": "Conectar"}
                button.setText(short_labels.get(label, label) if index == 0 else "")
                button.setToolTip("Comprobar con API" if action == "check_video" else label)
                button.setAccessibleName(label)
                button.setIcon(app_icon(icons.get(action, "circle-question-mark"),
                                       "#5bd8b7" if action == "manual_verify" else "#ff6b7a" if action == "delete_local" else "#e5e7eb"))
                button.setEnabled(not (action == "manual_verify" and self.manual_confirmation_running))
        self.guidance_next.setVisible(len(sources) > 1)
        self.guidance_previous.setVisible(len(sources) > 1)
        self.guidance_next.setToolTip(f"Siguiente aviso / {len(sources)} avisos")
        self.sync_status_hint()

    def sync_status_hint(self) -> None:
        levels = {notice.level for notice in self.guidance_notices.values()}
        hint = "Requiere atencion" if "error" in levels else "Hay avisos pendientes" if "warning" in levels else "Trabajando" if "activity" in self.guidance_notices else "Preparado"
        if self.status.text() != t(hint):
            self.status.setText(hint)

    def next_guidance(self, step: int = 1) -> None:
        sources = self.guidance_order
        if sources:
            index = sources.index(self.guidance_selected) if self.guidance_selected in sources else -1
            self.guidance_selected = sources[(index + step) % len(sources)]
            self.guidance_browsing = True
            self.render_guidance()

    def set_transfer_state(self, phase: str, filename: str | None = None, percent: int | None = None) -> None:
        if phase == "idle":
            self.transfer_filename = ""
            self.transfer_percent = 0
        if filename is not None:
            self.transfer_filename = filename
        if percent is not None:
            self.transfer_percent = max(0, min(100, percent))
        display = Path(self.transfer_filename).name if self.transfer_filename else (
            f"{self.transfer_candidates} en cola" if self.transfer_candidates else "")
        self.transfer_strip.show_state(phase, display, self.transfer_percent)
        self.layout_timer.start(0)

    def refresh_transfer_state(self, cycle_finished: bool = False) -> None:
        phase = self.transfer_strip.phase
        active = bool(self.worker and self.worker.active_path)
        if phase in {"uploading", "canceling"} and (active or not cycle_finished):
            return
        if phase == "queued" and not cycle_finished and not self.api_pause_state:
            return
        if phase == "processing" and cycle_finished:
            return
        if phase == "paused" and cycle_finished and self.auto_enabled and self.api_pause_state:
            return
        if self.processing_files:
            name = self.transfer_filename if Path(self.transfer_filename).name in self.processing_files else self.processing_files[0]
            blocked = self.api_pause_state and self.api_pause_state.get("bucket") != "upload"
            self.set_transfer_state("paused" if blocked else "processing", name, 100)
        elif self.auto_enabled and self.transfer_candidates and self.api_pause_state:
            self.set_transfer_state("paused", "", 0)
        else:
            self.set_transfer_state("idle")

    def pause_transfer_state(self) -> None:
        if self.transfer_strip.phase == "processing" and self.api_pause_state and self.api_pause_state.get("bucket") == "upload":
            return
        if self.transfer_strip.phase != "idle" or (self.auto_enabled and self.transfer_candidates):
            self.set_transfer_state("paused")

    def focus_video(self, path: str = "") -> bool:
        self.tabs.setCurrentIndex(0)
        for row in range(self.video_table.rowCount()):
            item = self.video_table.item(row, 5)
            if item and (item.text() == path or (not path and self.video_table.item(row, 4).text() in {"Revisar", "Incidencia", "Por verificar", "En espera"})):
                self.video_table.selectRow(row)
                self.video_table.scrollToItem(item)
                return True
        return False

    def run_guidance_action(self, index: int) -> None:
        notice = self.active_guidance
        if index >= len(notice.actions):
            return
        action = notice.actions[index][1]
        if action == "connect":
            self.open_setup()
        elif action in {"settings", "youtube_settings", "folder_settings"}:
            self.open_settings()
            if action != "settings":
                self.settings_dialog.settings_search.setText("Carpeta" if action == "folder_settings" else "OAuth")
        elif action == "refresh":
            self.request_remote_refresh()
        elif action == "quota":
            webbrowser.open(quota_console_url(self.config.client_secret_path))
        elif action == "quota_request":
            webbrowser.open("https://support.google.com/youtube/contact/yt_api_form")
        elif action == "studio":
            webbrowser.open("https://studio.youtube.com/")
        elif action == "channel_limits":
            self.show_channel_limits_info()
        elif action == "copy_detail":
            QApplication.clipboard().setText(redact_secrets(notice.diagnostic or notice.detail))
        elif action == "cancel_upload":
            if self.worker and self.worker.active_path == Path(notice.target):
                self.cancel_upload()
            else:
                self.refresh_folder()
        elif action == "enable_api":
            webbrowser.open("https://console.cloud.google.com/apis/library/youtube.googleapis.com")
        elif action == "console":
            self.open_console()
        elif action == "channel":
            self.tabs.setCurrentIndex(1)
        elif action == "channel_reload":
            self.refresh_channel()
        elif action in {"videos", "retry_video", "open_video", "review_video", "open_local", "manual_verify", "check_video", "delete_local", "upload_file"}:
            found = self.focus_video(notice.target)
            if action == "upload_file" and found:
                self.upload_selected_video()
            elif action == "manual_verify" and found:
                self.confirm_video_manually()
            elif action == "check_video" and found:
                self.check_selected_video()
            elif action == "delete_local" and found:
                self.delete_selected_local_video()
            elif action == "review_video" and found:
                self.review_selected_video()
            elif action == "open_local" and found:
                self.open_selected_local_video()
            elif action == "retry_video" and found:
                self.retry_selected_video()
            elif action == "open_video" and found:
                selected = self.selected_video_row()
                if selected and selected.get("youtube_id"):
                    webbrowser.open(f"https://youtu.be/{selected['youtube_id']}")

    def report_problem(self, message: str, source: str = "connection", target: str = "", operation: str = "", diagnostic: str = "") -> None:
        context = {"upload": "Subida", "connection": "Conexion", "channel": "Canal", "settings": "Ajustes", "cleanup": "Limpieza", "configuration": "Configuracion",
                   "manual_confirmation": "Confirmación manual", "verification": "Comprobación"}.get(source, "Operacion")
        details = message + (f"\nOperacion: {operation}" if operation else "") + (f"\nArchivo: {target}" if target else "")
        if diagnostic:
            details += "\n" + diagnostic
        self.log(details, source=context, level="INFO" if "cancelad" in message.casefold() else "ERROR")
        if engine.is_youtube_quota_error(message):
            scope = engine.api_scope(self.config.client_secret_path)
            pause = self.store.api_pause(scope) or self.store.api_pause(scope, "upload")
            if pause:
                self.api_pause_state = pause
                self.update_quota_status()
                return
            self.set_guidance("quota", Guidance("Google ha limitado esta operacion", "Consulta la cuota del proyecto antes de reintentar. Los archivos y sus confirmaciones se conservan.",
                                               "warning", (("Ver cuota", "quota"), ("Consola", "console"))))
            return
        notice = problem_guidance(message, context, target)
        if source == "channel":
            notice = replace(notice, actions=tuple(("Cargar canal", "channel_reload") if action == "refresh" else (label, action)
                                                   for label, action in notice.actions))
        self.set_guidance(source, replace(notice, diagnostic=message, target=target or notice.target))

    def build_videos_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        toolbar = QHBoxLayout()
        title = QLabel("Biblioteca de videos")
        title.setObjectName("PageTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        upload_one = self.action_button("Subir", app_icon("arrow-up"), primary=True)
        upload_one.clicked.connect(self.upload_selected_video)
        open_local = self.icon_button("Abrir local", QStyle.SP_DirOpenIcon)
        open_local.clicked.connect(self.open_selected_local_video)
        retry = self.icon_button("Reintentar", app_icon("rotate-ccw", "#56b6ff"))
        retry.clicked.connect(self.retry_selected_video)
        delete_local = self.icon_button("Borrar archivo local", QStyle.SP_TrashIcon, danger=True)
        delete_local.clicked.connect(lambda: self.delete_selected_local_video())
        cleanup = self.action_button("Limpieza", app_icon("brush", "#5bd8b7"))
        cleanup_menu = QMenu(cleanup)
        configured_cleanup = cleanup_menu.addAction(app_icon("calendar"), "Según tiempo de conservación")
        configured_cleanup.triggered.connect(self.run_configured_cleanup)
        self.short_cleanup_action = cleanup_menu.addAction(app_icon("clock"), "Vídeos de menos de 30 segundos")
        self.short_cleanup_action.triggered.connect(self.run_short_video_cleanup)
        cleanup.setMenu(cleanup_menu)
        cleanup.setToolTip("Opciones de limpieza local")
        self.short_cleanup_scanning = False
        reload_btn = self.icon_button("Actualizar carpeta", app_icon("refresh-cw", "#56b6ff"))
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
        self.video_table = QTableWidget(0, len(LIBRARY_COLUMNS))
        self.video_table.setProperty("translatedColumns", [4, 6, 7, 8, 9])
        self.video_table.itemSelectionChanged.connect(self.user_video_selection_changed)
        self.video_table.setHorizontalHeaderLabels([label for _key, label, _icon in LIBRARY_COLUMNS])
        for column, (_key, label, icon) in enumerate(LIBRARY_COLUMNS):
            item = self.video_table.horizontalHeaderItem(column)
            item.setIcon(app_icon(icon))
            item.setToolTip(label)
        self.setup_table(self.video_table)
        self.video_table.setItemDelegate(LibraryItemDelegate(self.video_table))
        self.local_media = LocalMediaLoader(self.store.base / "cache" / "library-media", self)
        self.local_media.ready.connect(self.apply_local_media)
        self.local_media_timer = QTimer(self)
        self.local_media_timer.setSingleShot(True)
        self.local_media_timer.timeout.connect(self.load_visible_local_media)
        self.video_table.verticalScrollBar().valueChanged.connect(lambda: self.local_media_timer.start(80))
        self.video_table.horizontalHeader().sortIndicatorChanged.connect(lambda: self.local_media_timer.start(80))
        self.video_table.viewport().installEventFilter(self)
        self.configure_library_columns()
        layout.addWidget(self.video_table, 1)
        return page

    def configure_library_columns(self) -> None:
        visible = normalize_library_columns(self.config.library_columns)
        header = self.video_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(76)
        header.setIconSize(QSize(18, 18))
        keys = [key for key, _label, _icon in LIBRARY_COLUMNS]
        for position, key in enumerate(visible + [key for key in keys if key not in visible]):
            logical = keys.index(key)
            header.moveSection(header.visualIndex(logical), position)
            self.video_table.setColumnHidden(logical, key not in visible)
            header.setSectionResizeMode(logical, QHeaderView.ResizeToContents)
        elastic = next((key for key in ("file", "title", "path") if key in visible), visible[0])
        header.setSectionResizeMode(keys.index(elastic), QHeaderView.Stretch)
        if "thumbnail" in visible:
            header.setSectionResizeMode(7, QHeaderView.Fixed)
            self.video_table.setColumnWidth(7, 112)
        self.video_table.setIconSize(QSize(96, 54) if "thumbnail" in visible else QSize(18, 18))
        self.video_table.verticalHeader().setDefaultSectionSize(64 if "thumbnail" in visible else 34)

    def load_visible_local_media(self) -> None:
        if self._closing or not self.video_table.isVisible() or not MEDIA_COLUMNS.intersection(self.config.library_columns):
            return
        first = max(0, self.video_table.rowAt(0))
        last = self.video_table.rowAt(self.video_table.viewport().height() - 1)
        last = min(self.video_table.rowCount() - 1, last if last >= 0 else first + 24)
        thumbnail = "thumbnail" in self.config.library_columns
        sort_column = self.video_table.horizontalHeader().sortIndicatorSection()
        sort_media = sort_column in (6, 8, 9) and not self.video_table.isColumnHidden(sort_column)
        rows = range(self.video_table.rowCount()) if sort_media else range(first, last + 1)
        for row in rows:
            if self.local_media.jobs.full():
                break
            identity = self.video_table.item(row, 5)
            if identity is None or identity.data(Qt.UserRole + 1) == thumbnail:
                continue
            path, signature = identity.text(), identity.data(Qt.UserRole)
            if not signature:
                continue
            data = self.local_media.request(path, signature, thumbnail)
            if data is not None:
                self.apply_local_media(path, signature, data)

    def apply_local_media(self, path: str, signature: str, data: dict) -> None:
        if self._closing or not MEDIA_COLUMNS.intersection(self.config.library_columns):
            return
        try:
            if engine.file_signature(Path(path)) != signature:
                return
        except OSError:
            return
        thumbnail = "thumbnail" in self.config.library_columns
        for row in range(self.video_table.rowCount()):
            identity = self.video_table.item(row, 5)
            if identity is None or identity.text() != path or identity.data(Qt.UserRole) != signature:
                continue
            sorting = self.video_table.isSortingEnabled()
            self.video_table.setSortingEnabled(False)
            for column, (text, number) in enumerate(media_cells(data), 6):
                item = NumericTableItem(text, number)
                item.setToolTip(text if column != 7 else "Miniatura del Explorador de Windows")
                if column == 7 and data.get("thumbnail"):
                    item.setIcon(QIcon(data["thumbnail"]))
                self.video_table.setItem(row, column, item)
            identity.setData(Qt.UserRole + 1, thumbnail if not thumbnail or data.get("thumbnail_checked") else None)
            self.video_table.setSortingEnabled(sorting)
            break
        self.local_media_timer.start(100)

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
        youtube_btn.setToolTip("Abrir YouTube")
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
        self.channel_playlist_filter.setProperty("translatedItemCount", 2)
        self.channel_playlist_filter.addItems(["Todas", "Sin lista"])
        self.channel_playlist_filter.currentTextChanged.connect(self.filter_channel_table)
        self.channel_date_filter = QLineEdit()
        self.channel_date_filter.setPlaceholderText("Fecha: 2026, 2026-06...")
        self.channel_date_filter.addAction(app_icon("calendar"), QLineEdit.LeadingPosition)
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
        self.channel_playlist_combo.setProperty("translatedItemCount", 1)
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
        self.channel_table.setProperty("translatedColumns", [3])
        self.channel_table.setHorizontalHeaderLabels(["Miniatura", "Titulo", "Duracion", "Privacidad", "Listas", "Publicado", "YouTube"])
        self.channel_table.horizontalHeaderItem(2).setIcon(app_icon("clock"))
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
        show_action.setIcon(app_icon("monitor"))
        show_action.triggered.connect(self.show_from_tray)
        self.tray_auto_action = QAction("Auto ON" if self.auto_enabled else "Auto OFF", self)
        self.tray_auto_action.setIcon(app_icon("power", "#22c55e" if self.auto_enabled else "#ef4444"))
        self.tray_auto_action.triggered.connect(self.toggle_auto)
        upload_action = QAction("Subir pendientes", self)
        upload_action.setIcon(app_icon("arrow-up"))
        upload_action.triggered.connect(self.upload_pending)
        cancel_action = QAction("Cancelar subida", self)
        cancel_action.setIcon(app_icon("square"))
        cancel_action.triggered.connect(self.cancel_upload)
        refresh_action = QAction("Actualizar", self)
        refresh_action.setIcon(app_icon("refresh-cw", "#56b6ff"))
        refresh_action.triggered.connect(lambda: self.refresh_all(light=False))
        settings_action = QAction("Ajustes", self)
        settings_action.setIcon(app_icon("settings"))
        settings_action.triggered.connect(self.open_settings)
        quit_action = QAction("Salir", self)
        quit_action.setIcon(app_icon("log-out", "#ef4444"))
        quit_action.triggered.connect(self.request_quit)
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
        self.tray.showMessage(APP_NAME, t("La app sigue funcionando en la bandeja."), QSystemTrayIcon.Information, 1800)

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
        self.local_media.shutdown()
        self.local_media_timer.stop()
        if self.settings_dialog is not None:
            self.settings_dialog.update_panel.shutdown()
        if self.diagnostic_window is not None:
            self.diagnostic_window.render_timer.stop()
            self.diagnostic_window.close()
        if self.setup_dialog is not None:
            self.setup_dialog.reject()
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
        if (hasattr(self, "video_table") and watched is self.video_table.viewport()
                and event.type() in (QEvent.Resize, QEvent.Show)):
            self.local_media_timer.start(80)
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
            self.main_layout.setSpacing(6 if compact else 18)
            for card in (self.state_card, self.guidance_card):
                card.layout().setContentsMargins(*((12, 6, 12, 6) if compact else (18, 16, 18, 16)))
                card.layout().setSpacing(3 if compact else 6)
        for field in self.profile_fields:
            field.update_text()
        self.guidance_target.setText(self.guidance_target.fontMetrics().elidedText(
            Path(self.active_guidance.target).name if self.active_guidance.target else "", Qt.ElideMiddle,
            max(80, self.guidance_card.width() - 28)))
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
        if hasattr(self, "guidance_card"):
            self.render_guidance()
        if hasattr(self, "tray_auto_action"):
            self.tray_auto_action.setText("Auto ON" if self.auto_enabled else "Auto OFF")
            self.tray_auto_action.setIcon(app_icon("power", "#22c55e" if self.auto_enabled else "#ef4444"))

    def start_worker(self, manual_path: Path | None = None) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
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

    def initialize_session(self) -> None:
        if (not self.config.client_secret_path or not Path(self.config.client_secret_path).is_file()
                or not self.config.watch_folder or not Path(self.config.watch_folder).is_dir()):
            self.auto_enabled = False
            self.update_auto_button()
            self.show()
            self.open_setup()
            return
        self.check_youtube()
        if self.auto_enabled:
            self.start_worker()

    def open_setup(self) -> None:
        if self.setup_dialog is not None:
            self.setup_dialog.raise_()
            self.setup_dialog.activateWindow()
            return
        if self.youtube_check_running or self.channel_loader is not None or (self.worker and self.worker.busy_event.is_set()):
            QMessageBox.information(self, APP_NAME, "Espera a que termine la comprobacion o la subida actual. Puedes cancelar la subida antes de cambiar la conexion.")
            return
        self.auto_enabled = False
        self.update_auto_button()
        if self.worker:
            self.worker.pause_after_current()
        self.setup_dialog = SetupWizard(self.store, self.store.load_config(), self)
        self.setup_dialog.setWindowModality(Qt.ApplicationModal)
        self.setup_dialog.configured.connect(self.setup_configured)
        self.setup_dialog.finished.connect(self.setup_finished)
        self.setup_dialog.show()

    def setup_configured(self, config: engine.Config) -> None:
        self.config = config
        self.auto_enabled = config.auto_start_enabled
        self._resume_after_setup_check = self.auto_enabled
        self.update_auto_button()
        if self.settings_dialog is not None:
            self.settings_dialog.apply_connection(config)
        self.channel_videos = []
        self.channel_table.setRowCount(0)
        self.refresh_all(light=True)
        self.connection_value = "Canal confirmado"
        self.connection_channel = config.connected_channel_name
        self.refresh_connection_card()
        self.set_guidance("connection", None)

    def setup_finished(self, result: int) -> None:
        dialog = self.setup_dialog
        self.setup_dialog = None
        if dialog is not None:
            dialog.deleteLater()
        if result == QDialog.Accepted:
            self.check_youtube()
        else:
            self.status.setText("Configuracion aplazada / Auto OFF")

    def toggle_auto(self) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
        self.auto_enabled = not self.auto_enabled
        self.update_auto_button()
        self.start_worker()
        if self.worker:
            self.worker.set_enabled(self.auto_enabled)
        self.status.setText("Modo automatico activo" if self.auto_enabled else "Modo automatico pausado")
        self.render_guidance()
        self.refresh_transfer_state(cycle_finished=True)

    def upload_pending(self) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
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
        if self.transfer_strip.phase != "idle":
            self.set_transfer_state("canceling")
        self.status.setText("Subida cancelada / Auto OFF")
        self.log("Cancelacion solicitada. Auto queda pausado.")

    def refresh_all(self, light: bool = False) -> None:
        self.config = self.store.load_config()
        self.refresh_connection_card()
        self.refresh_folder()
        scope = engine.api_scope(self.config.client_secret_path)
        self.api_pause_state = self.store.api_pause(scope) or self.store.api_pause(scope, "upload")
        if self.api_pause_state:
            self.update_quota_status()
        else:
            self.set_guidance("quota", None)
        channel_limit = self.store.get_upload_limit()
        if isinstance(channel_limit, dict):
            self.channel_limit_state = channel_limit
            self.show_channel_limit()
        if not light:
            self.check_youtube()

    def request_remote_refresh(self) -> None:
        scope = engine.api_scope(self.config.client_secret_path)
        pause = self.store.api_pause(scope) or self.store.api_pause(scope, "upload")
        if pause:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Cuota de YouTube")
            dialog.setIcon(QMessageBox.Information)
            dialog.setText(("YouTube ha limitado temporalmente las peticiones." if pause.get("kind") == "api"
                            else "Google ha agotado la cuota diaria.") + " Los archivos y los estados se conservan.")
            dialog.setInformativeText("Reintentar comprueba si Google ya ha renovado o ampliado la cuota; no reinicia su contador.")
            quotas = dialog.addButton("Ver cuota", QMessageBox.ActionRole)
            extension = dialog.addButton("Solicitar ampliacion", QMessageBox.ActionRole)
            retry = dialog.addButton("Reintentar conexion", QMessageBox.AcceptRole)
            close = dialog.addButton(QMessageBox.Close)
            dialog.setDefaultButton(close)
            dialog.exec()
            clicked = dialog.clickedButton()
            if clicked == quotas:
                webbrowser.open(quota_console_url(self.config.client_secret_path))
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

    def refresh_connection_card(self) -> None:
        folder = self.config.watch_folder or t("Sin carpeta")
        category = engine.CATEGORY_NAMES_BY_ID.get(self.config.category_id, self.config.category_id)
        playlist = self.config.playlist_name if self.config.playlist_id else t("Sin lista")
        privacy = {"private": "Privado", "unlisted": "Oculto", "public": "Publico"}.get(self.config.privacy_status, "Privado")
        self.state_card.set(self.connection_value)
        if self.state_card.detail is not None:
            self.state_card.detail.setRawText(self.connection_channel or self.config.connected_channel_name or t("Canal sin confirmar"))
        color = "#4ade80" if self.connection_value in {"Conectado", "Canal confirmado"} else "#f87171" if self.connection_value == "Sin conexion" else "#f6f7f9"
        self.state_card.value.setStyleSheet(f"color: {color};")
        self.state_connection_icon.setPixmap(app_icon("circle-check" if self.connection_value in {"Conectado", "Canal confirmado"}
                                                     else "circle-exclamation-point" if self.connection_value == "Sin conexion" else "circle-question-mark", color).pixmap(18, 18))
        self.profile_channel.set_value(self.connection_channel or self.config.connected_channel_name or t("Sin confirmar"), "Canal de YouTube")
        self.profile_folder.set_value(folder)
        self.profile_privacy.set_value(t(privacy), f"Privacidad: {t(privacy)}")
        self.profile_privacy.icon_label.setPixmap(app_icon({"private": "lock", "unlisted": "eye-off", "public": "globe"}.get(self.config.privacy_status, "lock"), "#a8b2c5").pixmap(16, 16))
        self.profile_category.set_value(t(category), f"Categoria: {t(category)}")
        self.profile_playlist.set_value(playlist, f"Lista de reproduccion: {playlist}")
        self.layout_timer.start(0)
        if not self.config.watch_folder or not Path(self.config.watch_folder).is_dir():
            self.set_guidance("configuration", Guidance("Falta una carpeta disponible", "Elige la carpeta de videos o conecta la unidad donde esta guardada.",
                                                        "error", (("Elegir carpeta", "folder_settings"),)))
        elif not self.config.client_secret_path or not Path(self.config.client_secret_path).is_file():
            self.set_guidance("configuration", Guidance("Falta conectar el canal", "Selecciona tu JSON OAuth y autoriza el canal con Google.",
                                                        "error", (("Conectar canal", "connect"), ("Ajustes", "youtube_settings"))))
        else:
            self.set_guidance("configuration", None)

    def refresh_folder(self) -> None:
        self.configure_library_columns()
        folder = Path(self.config.watch_folder) if self.config.watch_folder else None
        selected = self.video_table.selectionModel().selectedRows()
        selected_item = self.video_table.item(selected[0].row(), 5) if selected else None
        selected_path = selected_item.text() if selected_item else ""
        self.video_table.blockSignals(True)
        self.video_table.setSortingEnabled(False)
        self.video_table.setRowCount(0)
        self.video_rows = {}
        self.transfer_candidates = 0
        self.processing_files = []
        if not folder or not folder.exists():
            self.video_summary.setText("Configura una carpeta valida.")
            self.refresh_connection_card()
            self.video_table.setSortingEnabled(True)
            self.video_table.blockSignals(False)
            self.set_transfer_state("idle")
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
        retry_required = self.store.retry_required_signatures()
        reviews = self.store.pending_upload_reviews()
        counts = {"Pendiente": 0, "Subido": 0, "Subido (manual)": 0, "Incidencia": 0, "En curso": 0, "En espera": 0, "Por verificar": 0, "Revisar": 0}
        for _, path in sorted(paths, key=lambda item: item[0]):
            try:
                signature = engine.file_signature(path)
                title = engine.creation_title(path)
                size = engine.human_size(path.stat().st_size)
                size_bytes = path.stat().st_size
                created = engine.datetime.fromtimestamp(path.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            except OSError:
                continue
            registry_row = registry_by_signature.get(signature)
            status_row = statuses_by_signature.get(signature)
            if registry_row and registry_row[3] and registry_row[4] == "manual_confirmed":
                status = "Subido (manual)"
            elif registry_row and registry_row[3] and registry_row[4] in {"uploaded", "youtube_title_exists"}:
                status = "Subido"
            elif registry_row and registry_row[3] and registry_row[4] == "processing":
                status = "En curso"
            elif signature in reviews and not (status_row and status_row[3] in {"uploading", "processing"}):
                status = "Revisar"
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
            if status in {"Pendiente", "En espera"} and signature not in retry_required:
                self.transfer_candidates += 1
            if status == "En curso" and ((registry_row and registry_row[4] == "processing")
                                         or (status_row and status_row[3] == "processing")):
                self.processing_files.append(path.name)
            row = self.video_table.rowCount()
            self.video_table.insertRow(row)
            values = [path.name, title, size, created, status, str(path), "...", "...", "...", "..."]
            status_icon, status_color = STATUS_ICONS[status]
            for column, value in enumerate(values):
                if column == 2 or column in (6, 8, 9):
                    item = NumericTableItem(value, size_bytes if column == 2 else -1)
                else:
                    item = table_item(value, status_color if column == 4 else "")
                item.setToolTip(value)
                self.video_table.setItem(row, column, item)
            self.video_table.item(row, 4).setIcon(app_icon(status_icon, status_color))
            self.video_table.item(row, 5).setData(Qt.UserRole, signature)
            if status_row and status_row[4]:
                self.video_table.item(row, 4).setToolTip(status_row[4])
            if status == "Subido" and registry_row:
                self.video_table.item(row, 4).setToolTip(
                    f"Ultima confirmacion: {registry_row[5]}\nhttps://youtu.be/{registry_row[3]}\nSe conserva aunque el archivo siga en la carpeta.")
            if status == "Subido (manual)" and registry_row:
                self.video_table.item(row, 4).setToolTip(
                    f"Confirmado por ti: {registry_row[5]}\nhttps://youtu.be/{registry_row[3]}\nNo es una verificación automática ni autoriza limpieza automática.")
            video_id = registry_row[3] if registry_row else ""
            if not video_id and status in {"Por verificar", "Incidencia"}:
                identity = self.store.upload_identity(signature)
                video_id = identity[1] if isinstance(identity, tuple) else ""
            self.video_rows[row] = {
                "path": str(path),
                "signature": signature,
                "title": title,
                "status": status,
                "youtube_id": video_id,
                "error": status_row[4] if status_row else "",
            }
        self.video_table.setSortingEnabled(True)
        manual_summary = f" ({counts['Subido (manual)']} manual{'es' if counts['Subido (manual)'] != 1 else ''})" if counts['Subido (manual)'] else ""
        self.video_summary.setText(
            f"Total {len(paths)} / Pendientes {counts['Pendiente']} / Revisar {counts['Revisar']} / En curso {counts['En curso']} / En espera {counts['En espera']} / Por verificar {counts['Por verificar']} / Subidos {counts['Subido'] + counts['Subido (manual)']}{manual_summary} / Incidencias {counts['Incidencia']}"
        )
        self.refresh_transfer_state()
        live_paths = {item["path"] for item in self.video_rows.values()}
        for source in ("manual_confirmation", "verification"):
            notice = self.guidance_notices.get(source)
            if notice and notice.level == "info" and notice.target and notice.target not in live_paths and not self.manual_confirmation_running:
                self.set_guidance(source, None)
        issues = counts["Incidencia"] + counts["Por verificar"] + counts["Revisar"]
        if issues:
            self.set_guidance("library", Guidance(f"{issues} video(s) necesitan revision",
                f"{counts['Revisar']} pendientes de revisión / {counts['Por verificar']} por verificar / {counts['Incidencia']} con incidencia.",
                "warning", (("Revisar videos", "videos"), ("Consola", "console"))))
        else:
            self.set_guidance("library", None)
        review_item = next((item for item in self.video_rows.values() if item["status"] == "Revisar"), None)
        self.set_guidance("review", Guidance("Revisar antes de subir", f"{counts['Revisar']} vídeo(s) esperan tu autorización.",
                                             "warning", (("Revisar", "review_video"), ("Abrir local", "open_local")), review_item["path"]) if review_item else None)
        for row in range(self.video_table.rowCount()):
            if self.video_table.item(row, 5).text() == selected_path:
                self.video_table.selectRow(row)
                break
        self.video_table.blockSignals(False)
        self.video_selection_changed()
        self.local_media_timer.start(80)

    def user_video_selection_changed(self) -> None:
        self.guidance_browsing = False
        self.video_selection_changed()
        if "selection" in self.guidance_notices:
            self.guidance_selected = "selection"
            self.guidance_browsing = True
        self.render_guidance()

    def video_selection_changed(self) -> None:
        selected = self.video_table.selectionModel().selectedRows()
        if not selected:
            self.set_guidance("selection", None)
            return
        item = self.selected_video_row()
        if not item:
            self.set_guidance("selection", None)
            return
        if item["status"] == "Revisar":
            notice = Guidance("Revisar antes de subir", "Autoriza la subida o revisa el archivo local. No se subirá automáticamente.",
                              "warning", (("Revisar", "review_video"), ("Abrir local", "open_local"), ("Vincular YouTube", "manual_verify"), ("Borrar local", "delete_local")), item["path"])
        elif item["status"] == "Por verificar":
            actions = ((("Ver YouTube", "open_video"), ("Ver local", "open_local"), ("Confirmar coincidencia", "manual_verify"),
                        ("Comprobar este vídeo", "check_video"), ("Consola", "console")) if item["youtube_id"] else
                       (("Asignar enlace", "manual_verify"), ("Ver local", "open_local"), ("YouTube Studio", "studio"), ("Consola", "console")))
            notice = Guidance("Vídeo por verificar", "Compara el archivo y el vídeo de YouTube antes de confirmar que coinciden.", "warning", actions, item["path"])
        elif item["status"] == "Subido (manual)":
            notice = Guidance("Confirmado por ti", "La coincidencia es manual. No autoriza el borrado automático del archivo.", "info",
                              (("Ver YouTube", "open_video"), ("Ver local", "open_local"), ("Editar confirmación", "manual_verify"),
                               ("Comprobar con API", "check_video"), ("Borrar local", "delete_local")), item["path"])
        elif item["status"] == "Pendiente":
            notice = Guidance("Vídeo pendiente", "Todavía no hay una subida confirmada para este archivo.", "info",
                              (("Subir", "upload_file"), ("Ver local", "open_local"), ("Vincular YouTube", "manual_verify"), ("Borrar local", "delete_local")), item["path"])
        elif item["status"] == "Subido":
            notice = Guidance("Subida confirmada", "La marca se conserva mientras el archivo no cambie.", "info",
                              (("Ver YouTube", "open_video"), ("Ver local", "open_local"), ("Comprobar", "check_video"), ("Borrar local", "delete_local")), item["path"])
        elif item["status"] == "En espera":
            notice = Guidance("Archivo en espera", "La restricción de cuota no cambia el archivo ni confirma una subida.", "warning",
                              (("Cuota API", "quota"), ("Ver local", "open_local"), ("Límites del canal", "channel_limits"), ("Consola", "console")), item["path"])
        elif item["status"] == "En curso":
            uploading = self.worker and self.worker.active_path == Path(item["path"])
            actions = (("Cancelar subida", "cancel_upload"), ("Ver local", "open_local"), ("Consola", "console")) if uploading else (
                (("Ver YouTube", "open_video"), ("Ver local", "open_local"), ("Comprobar", "check_video"), ("Consola", "console")) if item["youtube_id"] else
                (("Ver local", "open_local"), ("Consola", "console")))
            notice = Guidance("Transferencia en curso" if uploading else "Procesamiento pendiente",
                              "La recepción y el procesamiento son pasos diferentes.", "info", actions, item["path"])
        else:
            notice = problem_guidance(item.get("error", ""), "Subida", item["path"])
            if notice.actions and notice.actions[0][1] == "videos":
                notice = replace(notice, actions=(("Reintentar video", "retry_video"), ("Consola", "console")))
        self.set_guidance("selection", replace(notice, diagnostic=item.get("error", ""), target=item["path"]))

    def selected_video_row(self) -> dict | None:
        selected = self.video_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, APP_NAME, "Selecciona primero un video de la tabla.")
            return None
        row = selected[0].row()
        path = self.video_table.item(row, 5).text() if self.video_table.item(row, 5) else ""
        signature = ""
        youtube_id = ""
        error = ""
        for data in self.video_rows.values():
            if data.get("path") == path:
                signature = data.get("signature", "")
                youtube_id = data.get("youtube_id", "")
                error = data.get("error", "")
                break
        return {
            "path": path,
            "signature": signature,
            "youtube_id": youtube_id,
            "error": error,
            "title": self.video_table.item(row, 1).text() if self.video_table.item(row, 1) else "",
            "status": self.video_table.item(row, 4).text() if self.video_table.item(row, 4) else "",
        }

    def upload_selected_video(self) -> None:
        item = self.selected_video_row()
        if not item:
            return
        self.queue_video(item)

    def queue_video(self, item: dict) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
        path = Path(item["path"])
        if not path.exists():
            QMessageBox.warning(self, APP_NAME, "El archivo seleccionado ya no existe.")
            self.refresh_folder()
            return
        if item["status"] in {"Subido", "Subido (manual)"}:
            QMessageBox.information(self, APP_NAME, "Este video ya aparece como subido en el registro.")
            return
        if item["status"] == "Revisar":
            self.review_selected_video(item)
            return
        if self.worker and self.worker.active_path == path:
            QMessageBox.information(self, APP_NAME, "Este video ya se esta subiendo. Cancela o espera a que termine antes de reintentar.")
            return
        if item.get("signature"):
            self.store.clear_upload_incident(item["signature"])
        self.start_worker(manual_path=path)
        if self.transfer_strip.phase not in {"uploading", "canceling"}:
            self.set_transfer_state("queued", path.name, 0)
        self.log(f"Subida manual solicitada para {path.name}.")

    def retry_selected_video(self) -> None:
        item = self.selected_video_row()
        if not item:
            return
        if item["status"] == "Subido":
            self.queue_video(item)
            return
        self.queue_video(item)
        self.refresh_folder()

    def open_selected_local_video(self) -> None:
        item = self.selected_video_row()
        if not item:
            return
        path = Path(item["path"])
        if not path.exists():
            QMessageBox.warning(self, APP_NAME, "El archivo seleccionado ya no existe.")
            return
        os.startfile(str(path))

    def delete_selected_local_video(self, item: dict | None = None) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
        item = item or self.selected_video_row()
        if not item:
            return
        path = Path(item["path"])
        try:
            if engine.file_signature(path) != item["signature"]:
                raise OSError("El archivo ha cambiado desde la última revisión. Actualiza la biblioteca y vuelve a seleccionarlo.")
        except OSError as exc:
            QMessageBox.warning(self, "Borrar archivo local", engine.describe_error(exc))
            self.refresh_folder()
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Borrar archivo local")
        dialog.setTextFormat(Qt.PlainText)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText(f"Borrar {path.name}?")
        verified = None
        if item["status"] == "Subido":
            warning = "Figura como subido. Puedes comprobar YouTube antes de borrar la copia local. Si borras sin comprobar, podrías perder la única copia si el vídeo ya no está disponible."
            verified = dialog.addButton("Comprobar y borrar", QMessageBox.AcceptRole)
            verified.setIcon(app_icon("circle-check"))
        else:
            warning = "Este archivo no tiene una confirmación automática de subida. Si lo borras, podrías perder su única copia."
        warning += "\n\nEl borrado es permanente y no elimina vídeos del canal. «Borrar de todos modos» deja Auto en OFF y espera a que termine la transferencia activa."
        dialog.setInformativeText(warning)
        force = dialog.addButton("Borrar de todos modos", QMessageBox.DestructiveRole)
        force.setObjectName("DangerButton")
        force.setIcon(app_icon("trash"))
        cancel = dialog.addButton("Cancelar", QMessageBox.RejectRole)
        cancel.setIcon(app_icon("x"))
        dialog.setDefaultButton(cancel)
        dialog.exec()
        if verified is not None and dialog.clickedButton() is verified:
            threading.Thread(target=self._delete_local_verified_thread, args=([item],), daemon=True).start()
        elif dialog.clickedButton() is force:
            self.begin_local_deletion([item])

    def confirm_video_manually(self) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
        item = self.selected_video_row()
        if not item:
            return
        if item["status"] in {"Subido", "En curso"}:
            QMessageBox.information(self, "Confirmación manual", "No se sustituye una subida confirmada automáticamente o una transferencia en curso.")
            return
        if self.worker and self.worker.active_path == Path(item["path"]):
            QMessageBox.information(self, "Confirmación manual", "Este archivo se está transfiriendo. Espera a que termine antes de vincularlo manualmente.")
            return
        try:
            if engine.file_signature(Path(item["path"])) != item["signature"]:
                raise OSError("El archivo ha cambiado. Actualiza la biblioteca antes de compararlo.")
        except OSError as exc:
            QMessageBox.warning(self, "Confirmación manual", engine.describe_error(exc))
            return
        self.auto_enabled = False
        self.update_auto_button()
        if self.worker:
            self.worker.pause_after_current()
        self.manual_confirmation_running = True
        self.auto_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        dialog = ManualConfirmationDialog(item, self)
        accepted = dialog.exec() == QDialog.Accepted
        decision = dialog.decision if accepted else ""
        upload_requested = bool(dialog.upload_requested) if accepted else False
        video_id = dialog.video_id() if accepted else ""
        dialog.deleteLater()
        if not accepted or decision not in {"match", "different"}:
            self.manual_confirmation_running = False
            self.auto_btn.setEnabled(not self.local_delete_running)
            self.upload_btn.setEnabled(not self.local_delete_running)
            self.render_guidance()
            return
        self.set_guidance("manual_confirmation", Guidance("Guardando confirmación manual" if decision == "match" else "Descartando asociación",
                                                         "Esperando la operación activa y guardando la decisión, sin consultar la API.", target=item["path"]))
        self.guidance_selected = "manual_confirmation"
        self.guidance_browsing = True
        self.render_guidance()
        threading.Thread(target=self._confirm_manual_thread, args=(dict(item), video_id, decision, upload_requested), daemon=True).start()

    def _confirm_manual_thread(self, item: dict, video_id: str, decision: str = "match", upload_requested: bool = False) -> None:
        lock = self.worker.operation_lock if self.worker else threading.RLock()
        while not lock.acquire(timeout=0.25):
            if self._closing:
                return
        result = {"item": item, "video_id": video_id, "decision": decision, "upload_requested": upload_requested}
        try:
            if self._closing:
                return
            if decision == "match":
                self.store.confirm_manual_match(Path(item["path"]), item["signature"], video_id,
                                                self.config.connected_channel_id, acknowledged=True, cancelled=lambda: self._closing)
            elif decision == "different":
                self.store.reject_manual_match(Path(item["path"]), item["signature"], video_id, upload_requested=upload_requested)
                if upload_requested and not self._closing:
                    self.store.approve_upload_review(Path(item["path"]), item["signature"])
            else:
                raise ValueError("La decisión de comparación no es válida.")
        except Exception as exc:
            result["error"] = engine.describe_error(exc)
        finally:
            lock.release()
        if not self._closing:
            self.events.put(("manual_confirmation_result", result))

    def check_selected_video(self) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
        item = self.selected_video_row()
        if not item:
            return
        if not item.get("youtube_id"):
            self.confirm_video_manually()
            return
        if item["signature"] in self.single_verifications:
            return
        self.single_verifications.add(item["signature"])
        self.set_guidance("verification", Guidance("Comprobando este vídeo", "Consultando su ID en YouTube, sin recargar todo el canal.", target=item["path"]))
        threading.Thread(target=self._check_single_video_thread, args=(dict(item),), daemon=True).start()

    def _check_single_video_thread(self, item: dict) -> None:
        result = {"item": item, "confirmed": False}
        try:
            path = Path(item["path"])
            if engine.file_signature(path) != item["signature"]:
                raise OSError("El archivo ha cambiado desde la selección.")
            registry, _ = self.store.registry_index()
            statuses, _ = self.store.upload_status_index()
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            client.uploaded_video_index(force=True, video_ids=[item["youtube_id"]])
            matched, resolved, reason, state = client.verify_local_file(path, item["title"], item["youtube_id"])
            result["detail"] = reason
            if matched and state == "processed" and engine.file_signature(path) == item["signature"]:
                result["confirmed"] = self.store.apply_reconciliation(item["signature"], path, item["title"], resolved,
                                                                     "uploaded", "uploaded", "", registry.get(item["signature"]), statuses.get(item["signature"]))
                if not result["confirmed"]:
                    result["detail"] = "El estado ha cambiado durante la consulta. Se conserva el estado más reciente."
            elif matched:
                result["detail"] = "YouTube todavía no confirma el procesamiento completo."
        except Exception as exc:
            result["error"] = engine.describe_error(exc)
        if not self._closing:
            self.events.put(("single_verification_result", result))

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

    def run_short_video_cleanup(self) -> None:
        if self.short_cleanup_scanning or self.local_delete_running or self.manual_confirmation_running:
            return
        self.refresh_folder()
        items = [dict(item) for item in self.video_rows.values()]
        if not items:
            QMessageBox.information(self, "Vídeos cortos", "No hay vídeos locales para revisar.")
            return
        self.short_cleanup_scanning = True
        self.short_cleanup_action.setEnabled(False)
        self.set_guidance("cleanup", Guidance("Buscando vídeos cortos", "Leyendo la duración de los archivos locales..."))
        self.guidance_selected = "cleanup"
        self.guidance_browsing = True
        self.render_guidance()
        threading.Thread(target=self._scan_short_video_cleanup, args=(items,), daemon=True).start()

    def _scan_short_video_cleanup(self, items: list[dict]) -> None:
        try:
            result = scan_short_videos(items, cancelled=lambda: self._closing,
                                       progress=lambda done, total: self.events.put(("short_cleanup_progress", (done, total))))
        except Exception as exc:
            result = {"items": [], "errors": [f"No se pudo completar la revisión: {engine.describe_error(exc)}"], "cancelled": False}
        if not self._closing:
            self.events.put(("short_cleanup_ready", result))

    def confirm_short_video_cleanup(self, result: dict) -> None:
        self.short_cleanup_scanning = False
        self.short_cleanup_action.setEnabled(True)
        self.set_guidance("cleanup", None)
        if result.get("cancelled"):
            return
        items, errors = result["items"], result["errors"]
        for error in errors:
            self.log(error, source="Limpieza", level="warning")
        if not items:
            message = "No se han encontrado vídeos de menos de 30 segundos."
            if errors:
                message += f"\n\n{len(errors)} archivo(s) sin duración verificable o modificados se han conservado. Consulta la Consola."
            QMessageBox.information(self, "Vídeos cortos", message)
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Limpiar vídeos de menos de 30 segundos")
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText(f"Borrar {len(items)} archivo(s) local(es), {engine.human_size(sum(item['size'] for item in items))}?")
        unconfirmed = sum(item.get("status") != "Subido" for item in items)
        detail = "Se borran solo los archivos locales seleccionados por duración. Los vídeos del canal no se borran."
        if unconfirmed:
            detail += f"\n\n{unconfirmed} archivo(s) no están confirmados como subidos: podrías perder su única copia."
        if errors:
            detail += f"\n\nSe conservan {len(errors)} archivo(s) que no se han podido revisar."
        dialog.setInformativeText(detail)
        dialog.setDetailedText("\n".join(f"{item['path']} / {item['seconds']} s / {item.get('status', 'Sin confirmar')} / {engine.human_size(item['size'])}" for item in items))
        confirm = dialog.addButton("Borrar archivos locales", QMessageBox.AcceptRole)
        confirm.setIcon(app_icon("trash", "#ff6b7a"))
        cancel = dialog.addButton("Cancelar", QMessageBox.RejectRole)
        for button in dialog.buttons():
            if button not in (confirm, cancel):
                def toggle_details(_checked=False, button=button):
                    expanded = not bool(button.property("filesExpanded"))
                    button.setProperty("filesExpanded", expanded)
                    button.setText("Ocultar archivos" if expanded else "Ver archivos")
                    button.setAccessibleName(button.text())
                button.clicked.connect(toggle_details)
                button.click()
        dialog.setDefaultButton(cancel)
        decorate_buttons(dialog)
        dialog.exec()
        if dialog.clickedButton() is confirm:
            self.begin_local_deletion(items, short_only=True)

    def begin_local_deletion(self, items: list[dict], short_only: bool = False) -> None:
        if self.local_delete_running or self.manual_confirmation_running:
            return
        self.auto_enabled = False
        self.update_auto_button()
        if self.worker:
            self.worker.pause_after_current()
        self.local_delete_running = True
        self.auto_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.short_cleanup_action.setEnabled(False)
        self.set_guidance("cleanup", Guidance("Limpieza de vídeos cortos" if short_only else "Borrado local",
                                             "Esperando a que termine la transferencia activa y comprobando los archivos locales."))
        threading.Thread(target=self._delete_local_files_thread, args=(items, short_only), daemon=True).start()

    def _delete_local_files_thread(self, items: list[dict], short_only: bool = False) -> None:
        lock = self.worker.operation_lock if self.worker else threading.RLock()
        while not lock.acquire(timeout=0.25):
            if self._closing:
                return
        try:
            delete = delete_short_videos if short_only else delete_local_files
            result = delete(items, cancelled=lambda: self._closing, stable_seconds=max(2, self.config.stable_wait_seconds))
            errors = result["errors"]
            for item in result["deleted"]:
                try:
                    self.store.mark_local_deleted(item["signature"])
                except Exception as exc:
                    errors.append(f"{Path(item['path']).name}: borrado local completado, no se pudo actualizar el registro ({engine.describe_error(exc)})")
            self.events.put(("manual_local_delete_result", {"deleted": len(result["deleted"]), "errors": errors}))
        except Exception as exc:
            self.events.put(("manual_local_delete_result", {"deleted": 0, "errors": [engine.describe_error(exc)]}))
        finally:
            lock.release()

    def review_selected_video(self, item: dict | None = None) -> None:
        item = item or self.selected_video_row()
        if not item:
            return
        review = self.store.pending_upload_reviews().get(item["signature"])
        if not review:
            self.refresh_folder()
            return
        seconds = review.get("seconds")
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Revisar antes de subir")
        dialog.setIcon(QMessageBox.Question)
        dialog.setText(Path(item["path"]).name)
        dialog.setInformativeText((f"Este vídeo dura {seconds} segundos, menos de 30." if seconds is not None else
                                   "Windows no ha podido leer su duración.") + "\n\nNo se subirá sin tu autorización.")
        approve = dialog.addButton("Autorizar y subir", QMessageBox.AcceptRole)
        approve.setIcon(app_icon("arrow-up"))
        open_local = dialog.addButton("Abrir local", QMessageBox.ActionRole)
        open_local.setIcon(app_icon("folder-open"))
        delete = dialog.addButton("Borrar local", QMessageBox.DestructiveRole)
        delete.setIcon(app_icon("trash"))
        later = dialog.addButton("Más tarde", QMessageBox.RejectRole)
        dialog.setDefaultButton(later)
        dialog.exec()
        try:
            if dialog.clickedButton() is approve:
                self.store.approve_upload_review(Path(item["path"]), item["signature"])
                self.refresh_folder()
                self.queue_video(dict(item, status="Pendiente"))
            elif dialog.clickedButton() is open_local:
                os.startfile(item["path"])
            elif dialog.clickedButton() is delete:
                self.delete_selected_local_video(item)
        except OSError as exc:
            self.report_problem(engine.describe_error(exc), "cleanup", item["path"])
            QMessageBox.warning(self, "Revisión", engine.describe_error(exc))

    def _delete_local_verified_thread(self, items: list[dict]) -> None:
        deleted = 0
        errors = []
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            client.uploaded_video_index(force=True, video_ids=list({item.get("youtube_id") for item in items if item.get("youtube_id")}))
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
                if engine.file_signature(path) != item["signature"]:
                    errors.append(f"{path.name}: el archivo ha cambiado durante la comprobacion")
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
        if self.youtube_check_running or self.setup_dialog is not None or self._closing:
            return
        if not self.config.client_secret_path or not Path(self.config.client_secret_path).exists():
            self.refresh_connection_card()
            return
        pause = self.store.api_pause(engine.api_scope(self.config.client_secret_path))
        if pause:
            self.api_pause_state = pause
            self.update_quota_status()
            return
        self.youtube_check_running = True
        self.set_guidance("activity", Guidance("Comprobando YouTube", "Consultando solo los estados que necesitan verificacion."))
        self.status.setText("Comprobando videos con YouTube...")
        threading.Thread(target=self._check_youtube_thread, args=(full,), daemon=True).start()

    def _check_youtube_thread(self, full: bool = True) -> None:
        try:
            client = engine.YouTubeClient(self.store, self.config, lambda text: self.events.put(("log", text)))
            changed = engine.reconcile_local_uploads(
                self.store, self.config, client, full=full,
                is_active=lambda path: bool(self.worker and self.worker.active_path == path),
            )
            if changed:
                self.events.put(("folder_refresh", False))
                self.events.put(("log", f"Comprobacion de YouTube: {changed} estado(s) actualizado(s)."))
            if full:
                self.events.put(("youtube", client.channel_info()))
            else:
                self.events.put(("youtube_check_done", None))
        except Exception as exc:
            if engine.is_youtube_quota_error(exc) and not engine.is_youtube_channel_upload_limit(exc):
                state = exc.state if isinstance(exc, engine.ApiQuotaUnavailable) else (
                    self.store.api_pause(client.scope) or self.store.defer_api(client.scope, exc))
                self.events.put(("api_quota", state))
                self.events.put(("youtube_check_done", None))
            else:
                self.events.put(("youtube_error", engine.describe_error(exc)))

    def update_quota_status(self) -> None:
        if self.channel_limit_state:
            retry_at = engine.datetime.fromisoformat(self.channel_limit_state["retry_at"]).astimezone()
            if retry_at <= engine.datetime.now().astimezone():
                self.channel_limit_state = None
                self.set_guidance("channel_limit", None)
        if not self.api_pause_state:
            return
        retry = engine.datetime.fromisoformat(self.api_pause_state["retry_at"]).astimezone()
        if retry <= engine.datetime.now().astimezone():
            self.api_pause_state = None
            self.set_guidance("quota", None)
            self.status.setText("Pausa finalizada / preparado para reintentar")
            self.refresh_transfer_state(cycle_finished=True)
            self.check_youtube(full=False)
            if self.worker:
                self.worker.refresh()
            return
        remaining = engine.remaining_text(retry)
        diagnostic_key = tuple(self.api_pause_state.get(key, "") for key in ("kind", "bucket", "retry_at", "reason"))
        if diagnostic_key != self.last_quota_diagnostic:
            self.last_quota_diagnostic = diagnostic_key
            state = self.api_pause_state
            self.log(f"Restriccion de YouTube: tipo={state.get('kind', '')}; ambito={state.get('bucket', 'general')}; "
                     f"motivo={state.get('reason', 'no indicado')}; proximo_intento={state['retry_at']}; "
                     f"criterio={state.get('source', 'no indicado')}", source="API", level="WARNING")
        label = "Limite temporal API" if self.api_pause_state.get("kind") == "api" else "Cuota diaria API"
        self.status.setText(f"{label} / Proximo intento {retry:%d/%m %H:%M} / {remaining}")
        title = label if self.api_pause_state.get("kind") == "api" else (
            "Cuota de subidas agotada" if self.api_pause_state.get("bucket") == "upload" else "Cuota de consultas agotada")
        self.set_guidance("quota", Guidance(title, f"Proximo intento {retry:%d/%m %H:%M} / {remaining}. Los estados se conservan.",
                                            "warning", (("Cuota API", "quota"), ("Comprobar", "refresh"),
                                                        ("Solicitar ampliación", "quota_request"), ("Consola", "console"))))

    def show_channel_limit(self) -> None:
        if self.channel_limit_state:
            retry = engine.datetime.fromisoformat(self.channel_limit_state["retry_at"]).astimezone()
            self.set_guidance("channel_limit", Guidance("Límite de subidas del canal", f"Última subida rechazada. Reintento recomendado {retry:%d/%m %H:%M} (estimación).",
                                                        "warning", (("YouTube Studio", "studio"), ("Límites del canal", "channel_limits"),
                                                                    ("Cuota API", "quota"), ("Consola", "console")), diagnostic=self.channel_limit_state.get("message", "")))
            self.update_quota_status()

    def show_channel_limits_info(self) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Límites del canal y cuota API")
        dialog.setIcon(QMessageBox.Information)
        dialog.setText("Son dos límites diferentes.")
        dialog.setInformativeText("El límite del canal afecta a sus subidas desde web, móvil y API. YouTube no ofrece un contador exacto de subidas restantes.\n\nLa cuota API pertenece al proyecto de Google Cloud. Su consola muestra los datos oficiales disponibles, que pueden tener retraso. El horario recomendado por la app no garantiza que el canal esté desbloqueado.")
        studio = dialog.addButton("YouTube Studio", QMessageBox.ActionRole)
        studio.setIcon(app_icon("external-link"))
        help_button = dialog.addButton("Ayuda oficial", QMessageBox.ActionRole)
        help_button.setIcon(app_icon("circle-question-mark"))
        quota = dialog.addButton("Cuota API", QMessageBox.ActionRole)
        quota.setIcon(app_icon("monitor"))
        close = dialog.addButton("Cerrar", QMessageBox.RejectRole)
        dialog.setDefaultButton(close)
        decorate_buttons(dialog)
        dialog.exec()
        if dialog.clickedButton() is studio:
            webbrowser.open("https://studio.youtube.com/")
        elif dialog.clickedButton() is help_button:
            webbrowser.open("https://support.google.com/youtube/answer/10383400?hl=es")
        elif dialog.clickedButton() is quota:
            webbrowser.open(quota_console_url(self.config.client_secret_path))

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
        self.set_guidance("channel", None)
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
        self.channel_preview_title.setRawText(video.get("title") or t("Sin titulo"))
        video_id = video.get("id", "")
        privacy_text = privacy_labels.get(video.get("privacy", ""), video.get("privacy", "-") or "-")
        published = video.get("published_at", "")[:10] or "Sin fecha"
        self.channel_preview_meta.setText(f"https://youtu.be/{video_id}")
        self.channel_preview_duration.setText(f"Duracion\n{video.get('duration', '-')}")
        self.channel_preview_privacy.setText(f"Privacidad\n{privacy_text}")
        self.channel_preview_date.setText(f"Publicado\n{published}")
        self.channel_preview_playlist.setRawText(t("Lista") + "\n" + playlists)
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
        self.report_problem(message, "channel")
        if engine.is_youtube_quota_error(message):
            scope = engine.api_scope(self.config.client_secret_path)
            self.api_pause_state = self.store.api_pause(scope) or self.store.api_pause(scope, "upload")
            self.update_quota_status()

    def open_settings(self) -> None:
        if self.settings_dialog is not None:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return
        dialog = SettingsDialog(self.store, self.config, self)
        self.settings_dialog = dialog
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.destroyed.connect(lambda: setattr(self, "settings_dialog", None))
        dialog.saved.connect(self.apply_saved_settings)
        dialog.saved.connect(lambda: self.set_guidance("settings", None))
        dialog.problem.connect(lambda message: self.report_problem(message, "settings"))
        dialog.setup_requested.connect(self.open_setup)
        dialog.console_requested.connect(self.open_console)
        dialog.show()

    def apply_saved_settings(self) -> None:
        updated = self.store.load_config()
        display_only = replace(updated, library_columns=self.config.library_columns, language=self.config.language) == self.config
        self.refresh_all(light=display_only)

    def open_console(self) -> None:
        if self.diagnostic_window is None:
            self.diagnostic_window = DiagnosticWindow(self.diagnostic_buffer, self)
        self.diagnostic_window.show()
        self.diagnostic_window.raise_()
        self.diagnostic_window.activateWindow()

    def process_events(self) -> None:
        for _ in range(100):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                self.sync_status_hint()
                return
            if kind == "log":
                self.log(value)
            elif kind == "problem":
                self.report_problem(value["message"], value.get("source", "upload"), value.get("path", ""),
                                    value.get("operation", ""), value.get("diagnostic", ""))
                if value.get("source", "upload") == "upload" and (
                        not value.get("path") or Path(value["path"]).name == Path(self.transfer_filename).name):
                    self.set_transfer_state("idle")
                    self.refresh_transfer_state(cycle_finished=True)
            elif kind == "progress":
                percent = int(value.get("percent", 0))
                filename = value.get("filename", "")
                if filename:
                    self.set_transfer_state("uploading", filename, percent)
                    self.set_guidance("activity", Guidance("Archivo recibido" if percent >= 100 else "Transferencia en curso",
                        "Procesamiento pendiente de confirmar." if percent >= 100 else "YouTube aun no ha confirmado la recepcion completa del archivo."))
                    previous = self.guidance_notices.get("upload")
                    if percent == 0 and previous and Path(previous.target).name == filename:
                        self.set_guidance("upload", None)
                else:
                    self.refresh_transfer_state(cycle_finished=True)
            elif kind == "busy":
                if not self.api_pause_state:
                    self.status.setText("Trabajando..." if value else "Preparado")
                if value:
                    self.set_guidance("activity", Guidance("Revisando archivos", "Comprobando candidatos antes de iniciar una transferencia."))
                    if self.transfer_strip.phase == "idle" and self.auto_enabled and self.transfer_candidates:
                        self.set_transfer_state("queued", "", 0)
                else:
                    self.set_guidance("activity", None)
                    self.refresh_transfer_state(cycle_finished=True)
            elif kind == "upload_completed":
                self.set_transfer_state("processing", value.get("path", ""), 100)
                self.set_guidance("upload", None)
                self.channel_limit_state = None
                self.set_guidance("channel_limit", None)
                self.set_guidance("activity", Guidance("YouTube esta procesando el archivo", "La transferencia termino; falta confirmar el procesamiento antes de marcarlo Subido."))
                self.folder_refresh_timer.start(0)
                self.check_youtube(full=False)
            elif kind == "folder_refresh":
                self.folder_refresh_timer.start(150)
            elif kind == "upload_limited":
                self.auto_enabled = False
                self.update_auto_button()
                self.pause_transfer_state()
                self.channel_limit_state = value
                self.show_channel_limit()
            elif kind == "api_quota":
                self.api_pause_state = value
                self.pause_transfer_state()
                self.update_quota_status()
            elif kind == "youtube_check_done":
                self.youtube_check_running = False
                self.set_guidance("activity", None)
                if not self.api_pause_state and (not self.worker or not self.worker.active_path):
                    self.status.setText("Preparado / confirmaciones guardadas")
            elif kind == "youtube":
                self.youtube_check_running = False
                scope = engine.api_scope(self.config.client_secret_path)
                self.api_pause_state = self.store.api_pause(scope) or self.store.api_pause(scope, "upload")
                self.connection_value = "Conectado"
                self.connection_channel = value.get("title", "Canal conectado")
                self.refresh_connection_card()
                self.set_guidance("connection", None)
                self.set_guidance("activity", None)
                if self.api_pause_state:
                    self.update_quota_status()
                else:
                    self.set_guidance("quota", None)
                    self.status.setText("Canal conectado / confirmaciones guardadas")
                    self.refresh_transfer_state()
                if self._resume_after_setup_check:
                    self._resume_after_setup_check = False
                    if self.auto_enabled:
                        self.start_worker()
            elif kind == "youtube_error":
                self.youtube_check_running = False
                self.connection_value = "Sin conexion"
                self.refresh_connection_card()
                self.set_guidance("activity", None)
                self.report_problem(value, "connection")
            elif kind == "channel_shared":
                self.set_guidance("channel", None)
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
                    self.report_problem(errors[0], "channel")
                    QMessageBox.warning(self, APP_NAME, "\n".join(errors[:6]))
                else:
                    self.set_guidance("channel", None)
            elif kind == "channel_deleted":
                deleted_ids = {video.get("id") for video in value.get("deleted", [])}
                self.channel_videos = [video for video in self.channel_videos if video.get("id") not in deleted_ids]
                self.filter_channel_table()
                errors = value.get("errors", [])
                self.channel_summary.setText(f"{len(deleted_ids)} video(s) borrado(s) del canal")
                if errors:
                    self.report_problem(errors[0], "channel")
                    QMessageBox.warning(self, APP_NAME, "\n".join(errors[:6]))
                else:
                    self.set_guidance("channel", None)
            elif kind == "channel_error":
                self.channel_summary.setText(value)
                self.report_problem(value, "channel")
                QMessageBox.warning(self, APP_NAME, value)
            elif kind == "channel_playlist_changed":
                self.set_guidance("channel", None)
                self.channel_summary.setText(value)
                self.refresh_channel()
            elif kind in {"local_delete_result", "manual_local_delete_result"}:
                if kind == "manual_local_delete_result":
                    self.local_delete_running = False
                    self.short_cleanup_action.setEnabled(True)
                    self.auto_btn.setEnabled(True)
                    self.upload_btn.setEnabled(True)
                self.refresh_folder()
                deleted = int(value.get("deleted", 0))
                errors = value.get("errors", [])
                message = f"{deleted} archivo(s) local(es) borrado(s)."
                if errors:
                    self.report_problem(errors[0], "cleanup")
                    message += "\n\nNo borrados:\n" + "\n".join(errors[:8])
                    QMessageBox.warning(self, "Limpieza", message)
                else:
                    self.set_guidance("cleanup", None)
                    QMessageBox.information(self, "Limpieza", message)
            elif kind == "short_cleanup_progress":
                done, total = value
                self.set_guidance("cleanup", Guidance("Buscando vídeos cortos", f"Duración revisada: {done} de {total} archivos."))
            elif kind == "short_cleanup_ready":
                self.confirm_short_video_cleanup(value)
            elif kind == "upload_review":
                self.refresh_folder()
            elif kind == "manual_confirmation_result":
                self.manual_confirmation_running = False
                self.auto_btn.setEnabled(not self.local_delete_running)
                self.upload_btn.setEnabled(not self.local_delete_running)
                self.set_guidance("manual_confirmation", None)
                item = value["item"]
                self.refresh_folder()
                if value.get("error"):
                    self.report_problem(value["error"], "manual_confirmation", item["path"])
                elif value.get("decision", "match") == "different":
                    self.log(f"Candidato descartado manualmente: {Path(item['path']).name} -> {value['video_id']}.", source="Verificación")
                    self.set_guidance("manual_confirmation", Guidance("Asociación descartada", "Ese candidato no volverá a vincularse a este archivo. El vídeo de YouTube no se ha borrado.",
                                                                       actions=(("Ver local", "open_local"),), target=item["path"]))
                    if value.get("upload_requested"):
                        self.queue_video(dict(item, status="Pendiente", youtube_id=""))
                else:
                    self.log(f"Confirmación manual guardada: {Path(item['path']).name} -> https://youtu.be/{value['video_id']}. No es una verificación automática.", source="Verificación")
                    self.set_guidance("manual_confirmation", Guidance("Confirmación manual guardada", "No se repetirá la subida de este archivo. La limpieza automática no se basa en esta marca. Auto OFF.",
                                                                       actions=(("Ver YouTube", "open_video"), ("Ver local", "open_local")), target=item["path"]))
            elif kind == "single_verification_result":
                item = value["item"]
                self.single_verifications.discard(item["signature"])
                self.set_guidance("verification", None)
                self.refresh_folder()
                if value.get("error"):
                    self.report_problem(value["error"], "verification", item["path"])
                else:
                    self.set_guidance("verification", Guidance("Verificación automática confirmada" if value["confirmed"] else "Sin confirmación automática",
                                                               value.get("detail", ""), "info" if value["confirmed"] else "warning",
                                                               (("Ver YouTube", "open_video"), ("Ver local", "open_local")), item["path"]))
            elif kind == "cleanup_warning":
                self.log(value)
                self.set_guidance("cleanup", Guidance("Limpieza detenida por seguridad", "Hay archivos que YouTube no confirma. No se ha borrado ninguno; revisalos antes de repetir la limpieza.",
                                                       "warning", (("Revisar videos", "videos"), ("Consola", "console"))))

    def log(self, text: str, source: str = "Servicio", level: str | None = None) -> None:
        self.diagnostic_buffer.append(text, source=source, level=level)


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
        QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #687285; border-radius: 4px; background: #111317; }
        QCheckBox::indicator:checked { background: #ff0033; border-color: #ff3157; image: url("@CHECK@"); }
        QListWidget { background: #121214; border: 1px solid #303540; border-radius: 6px; padding: 4px; }
        QListWidget::item { padding: 2px 8px; border-bottom: 1px solid #252930; }
        QListWidget::item:selected { background: #34303a; color: white; }
        QListWidget::item:hover { background: #252930; }
        QListWidget::indicator { width: 16px; height: 16px; border: 1px solid #687285; border-radius: 4px; background: #111317; }
        QListWidget::indicator:checked { background: #ff0033; border-color: #ff3157; image: url("@CHECK@"); }
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
        #Card, #GuidanceCard {
            background: #191b20;
            border: 1px solid #2c3039;
            border-radius: 12px;
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
            font-size: 14pt;
            font-weight: 700;
        }
        #ProfileValue { color: #e3e7ed; font-weight: 600; }
        #ProfileField { background: transparent; border: none; }
        #TransferStrip { background: #191b20; border: 1px solid #303845; border-radius: 8px; }
        #TransferStrip[phase="paused"] { border-color: #8f712e; }
        #TransferStatus { font-weight: 600; }
        #GuidanceCard[level="warning"] { border-color: #916a20; background: #211e17; }
        #GuidanceCard[level="error"] { border-color: #b54048; background: #25191b; }
        #GuidanceValue { font-size: 12pt; font-weight: 700; background: transparent; }
        #GuidanceTool { padding: 6px; min-width: 26px; max-width: 38px; }
        #GuidanceAction { padding: 6px 10px; }
        #GuidanceTool:pressed, #GuidanceAction:pressed { padding-top: 7px; padding-bottom: 5px; }
        #SettingsSection {
            background: #191b20;
            border: 1px solid #2c3039;
            border-radius: 12px;
        }
        #PreviewPanel {
            background: #18181b;
            border: 1px solid #2a2b31;
            border-radius: 12px;
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
            background: #252930;
            border: 1px solid #363c46;
            border-radius: 10px;
            padding: 8px 12px;
            font-weight: 600;
            min-height: 22px;
        }
        QPushButton:hover, QToolButton:hover {
            background: #323844;
            border-color: #707a8c;
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
            padding-top: 9px;
            padding-bottom: 7px;
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
        #PrimaryButton:disabled {
            color: #757b87;
            background: #1c1d21;
            border-color: #282a30;
        }
        #DangerButton {
            background: #991b1b;
            border-color: #ef4444;
        }
        #DangerButton:hover {
            background: #b91c1c;
        }
        QTabWidget::pane {
            border: none;
            border-top: 1px solid #303540;
            border-radius: 0px;
            top: -1px;
        }
        QTabBar::tab {
            background: transparent;
            color: #a9b1bf;
            padding: 10px 18px;
            border-bottom: 2px solid transparent;
            margin-right: 8px;
        }
        QTabBar::tab:selected {
            background: #1d2027;
            border-bottom: 2px solid #ff3157;
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
            background: #22262e;
            color: #f6f7f9;
            border: none;
            border-bottom: 1px solid #353c48;
            padding: 8px;
            font-weight: 600;
        }
        QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {
            background: #121214;
            border: 1px solid #30313a;
            border-radius: 8px;
            padding: 8px;
        }
        #DiagnosticText { font-family: Consolas; font-size: 10pt; selection-background-color: #3f3b52; }
        QLineEdit > QToolButton { background: transparent; border: none; border-radius: 0px; padding: 0px; min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px; }
        QComboBox { padding-right: 28px; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox::down-arrow { image: url("@CHEVRON@"); width: 14px; height: 14px; }
        QSpinBox { padding-right: 28px; }
        QSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 24px; border: none; }
        QSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; border: none; }
        QSpinBox::up-arrow { image: url("@CHEVRON_UP@"); width: 12px; height: 12px; }
        QSpinBox::down-arrow { image: url("@CHEVRON@"); width: 12px; height: 12px; }
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
        QScrollBar:horizontal { background: #11141a; height: 10px; margin: 2px; border-radius: 5px; }
        QScrollBar::handle:horizontal { background: #3a4252; min-width: 34px; border-radius: 5px; }
        QScrollBar::handle:horizontal:hover { background: #576277; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
        QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
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
        QSlider::groove:horizontal { height: 4px; background: #363c46; border-radius: 2px; }
        QSlider::sub-page:horizontal { background: #ff3157; border-radius: 2px; }
        QSlider::handle:horizontal { width: 12px; margin: -4px 0; background: #f6f7f9; border-radius: 5px; }
        """.replace("@CHEVRON@", asset_path("icons/chevron-down.svg").as_posix())
        .replace("@CHEVRON_UP@", asset_path("icons/chevron-up.svg").as_posix())
        .replace("@CHECK@", asset_path("icons/check.svg").as_posix())
    )
    install_button_help(app)


def main() -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    apply_style(app)
    if len(sys.argv) == 2 and sys.argv[1] == "--probe-youtube-engine":
        if os.name == "nt":
            ctypes.windll.kernel32.SetErrorMode(ctypes.windll.kernel32.GetErrorMode() | 2)
        try:
            from PySide6.QtWebEngineCore import QWebEngineProfile
            from PySide6.QtWebEngineWidgets import QWebEngineView
            profile = QWebEngineProfile()
            if not profile.isOffTheRecord():
                sys.exit(1)
        except Exception:
            sys.exit(1)
        return
    if len(sys.argv) == 4 and sys.argv[1] == "--self-test-youtube":
        import json
        from youtube_sync_youtube_player import EmbeddedYouTubePlayer
        player = EmbeddedYouTubePlayer()
        player.native_base = Path(sys.argv[2]).parent / "native-player-check"
        player.muted = True
        player.resize(720, 405)
        messages = []
        finished = False
        def finish_youtube_test(playing):
            nonlocal finished
            if finished:
                return
            finished = True
            report = Path(sys.argv[2])
            report.write_text(json.dumps({"playing": playing, "messages": messages}), encoding="utf-8")
            player.grab().save(str(report.with_suffix(".png")))
            player.release()
            player.close()
            app.quit()
        player.status.connect(messages.append)
        player.reviewed.connect(lambda _: QTimer.singleShot(1000, lambda: finish_youtube_test(True)))
        player.failed.connect(lambda _: QTimer.singleShot(0, lambda: finish_youtube_test(False)))
        player.show()
        player.load_video(sys.argv[3])
        QTimer.singleShot(45000, lambda: finish_youtube_test(False))
        app.exec()
        return
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--self-test":
        set_language(os.environ.get("YOUTUBESYNC_SELF_TEST_LANGUAGE", "es"))
        import json
        import ssl
        import tempfile
        from youtube_sync_local_media import windows_media
        ssl.create_default_context()
        icon_check = not app_icon("folder-open").pixmap(24, 24).isNull() and not QPixmap(str(asset_path("icons/chevron-down.svg"))).isNull()
        diagnostics = DiagnosticWindow(DiagnosticBuffer())
        diagnostic_check = diagnostics.viewer.isReadOnly()
        diagnostics.close()
        manual_dialog = ManualConfirmationDialog({"path": str(asset_path("youtube-sync-logo.png")), "youtube_id": "aB3_dE6-fG9"})
        media_check_available = manual_dialog.preview.player.isAvailable()
        manual_dialog.opened_id = manual_dialog.video_id()
        manual_dialog.set_step(2)
        manual_check = manual_dialog.yes.isEnabled() and manual_dialog.video_id() == "aB3_dE6-fG9"
        manual_dialog.close()
        playback_check = None
        if len(sys.argv) == 4:
            from PySide6.QtCore import QEventLoop
            playback = ManualConfirmationDialog({"path": sys.argv[3]}, autoplay=False)
            playback.preview.audio.setMuted(True)
            loop = QEventLoop()
            frames = []
            def received_frame(frame):
                if frame.isValid() and not frame.toImage().isNull():
                    frames.append(frame.startTime())
                if len(set(frames)) >= 3:
                    loop.quit()
            playback.preview.video.videoSink().videoFrameChanged.connect(received_frame)
            playback.show()
            playback.preview.play_file()
            deadline = QTimer()
            deadline.setSingleShot(True)
            deadline.timeout.connect(loop.quit)
            deadline.start(8000)
            loop.exec()
            deadline.stop()
            playback_check = len(set(frames)) >= 3 and playback.preview.player.duration() > 0
            playback.close()
        media_check = {}
        native_check = False
        with tempfile.TemporaryDirectory(dir=Path(sys.argv[2]).parent) as temporary:
            def check_media():
                try:
                    media_check.update(windows_media(asset_path("youtube-sync-logo.png"), Path(temporary) / "thumbnail.png"))
                except Exception:
                    pass
            thread = threading.Thread(target=check_media, daemon=True)
            thread.start()
            thread.join(10)
            from types import SimpleNamespace
            from youtube_sync_browser_player import NativeBrowserPlayer
            settings = SettingsDialog(SimpleNamespace(base=Path(temporary)), engine.Config())
            native_check = settings.playback_login.accessibleName() == t("Gestionar sesión de reproducción") and NativeBrowserPlayer is not None
            language_check = settings.windowTitle() == t("Ajustes") and settings.language_combo.count() == 2
            settings.close()
            settings.deleteLater()
        preview = QWidget()
        preview.show()
        app.processEvents()
        preview.close()
        Path(sys.argv[2]).write_text(json.dumps({"ok": True, "ui": "qt", "ssl": True, "version": APP_VERSION,
                                               "icons": icon_check, "diagnostics": diagnostic_check,
                                               "library": len(LIBRARY_COLUMNS) == 10 and bool(media_check.get("thumbnail")),
                                               "manual": manual_check, "media": media_check_available,
                                               "playback": playback_check, "native": native_check,
                                               "language": os.environ.get("YOUTUBESYNC_SELF_TEST_LANGUAGE", "es"), "translations": language_check,
                                               "embedded": all(asset_path("../PySide6/" + name).is_file() for name in
                                                               ("QtWebEngineProcess.exe", "resources/icudtl.dat")) if getattr(sys, "frozen", False) else True}), encoding="utf-8")
        return
    window = MainWindow()
    if window.config.start_minimized and QSystemTrayIcon.isSystemTrayAvailable():
        window.hide()
    else:
        window.show()
    QTimer.singleShot(0, window.initialize_session)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
