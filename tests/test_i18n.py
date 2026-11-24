import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication, QStyleOptionViewItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
import youtube_sync_engine as engine
import youtube_sync_app as ui
from youtube_sync_diagnostics import DiagnosticBuffer, DiagnosticWindow
from youtube_sync_help import HELP, describe_control
from youtube_sync_i18n import language, set_language, t
from youtube_sync_i18n_widgets import QComboBox, QLabel, QLineEdit, RawLabel
from youtube_sync_manual_ui import ManualConfirmationDialog
from youtube_sync_setup import SetupWizard
from youtube_sync_translations import TEMPLATES


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
        ui.apply_style(cls.app)

    def tearDown(self):
        set_language("es")
        self.app.processEvents()

    def test_default_and_invalid_language_are_spanish(self):
        self.assertEqual(engine.Config().language, "es")
        self.assertEqual(set_language("invalid"), "es")
        self.assertEqual(t("Ajustes"), "Ajustes")

    def test_config_round_trip_and_existing_config_migration(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(engine, "app_dir", return_value=Path(folder)):
            store = engine.Store()
            config = store.load_config()
            self.assertEqual(config.language, "es")
            config.language = "en"
            store.save_config(config)
            self.assertEqual(store.load_config().language, "en")
            config.language = "unknown"
            store.save_config(config)
            self.assertEqual(store.load_config().language, "es")

    def test_widgets_translate_but_inputs_and_user_names_do_not(self):
        set_language("en")
        self.assertEqual(QLabel("Ajustes").text(), "Settings")
        label = QLabel()
        label.setRawText("Subido")
        self.assertEqual(label.text(), "Subido")
        self.assertEqual(RawLabel("Sin lista").text(), "Sin lista")
        field = QLineEdit("Ajustes")
        field.setPlaceholderText("Titulo")
        self.assertEqual(field.text(), "Ajustes")
        self.assertEqual(field.placeholderText(), "Title")

    def test_enum_models_preserve_canonical_values(self):
        set_language("en")
        combo = QComboBox()
        combo.addItems(["Privado", "Oculto", "Publico"])
        combo.setCurrentText("Oculto")
        option = QStyleOptionViewItem()
        combo.itemDelegate().initStyleOption(option, combo.model().index(1, 0))
        self.assertEqual(option.text, "Unlisted")
        self.assertEqual(combo.currentText(), "Oculto")
        combo.setProperty("translatedItemCount", 0)
        combo.itemDelegate().initStyleOption(option, combo.model().index(1, 0))
        self.assertEqual(option.text, "Oculto")

    def test_templates_preserve_paths_and_ids(self):
        set_language("en")
        text = "Subida manual solicitada para vídeo {prueba} 01.mp4."
        self.assertEqual(t(text), "Manual upload requested for vídeo {prueba} 01.mp4.")
        self.assertEqual(t("AHORA / 2 DE 4"), "NOW / 2 OF 4")
        self.assertEqual(t("No se pudo comprobar YouTube: Sin conexion"), "Could not check YouTube: Disconnected")
        self.assertEqual(t("C:\\clips\\Subido.mp4"), "C:\\clips\\Subido.mp4")
        for source, destination in TEMPLATES:
            from string import Formatter
            names = {name for _, name, _, _ in Formatter().parse(source) if name is not None}
            expected = {name for _, name, _, _ in Formatter().parse(destination) if name is not None}
            self.assertEqual(names, expected, source)
            value = source.format_map(dict.fromkeys(names, "123"))
            self.assertNotEqual(t(value), value, source)

    def test_all_registered_button_help_has_english_translation(self):
        set_language("en")
        for description in set(HELP.values()):
            self.assertNotEqual(t(description), description, description)
        button = ui.QPushButton("Guardar")
        self.assertEqual(button.text(), "Save")
        self.assertEqual(t(describe_control(button)), "Save this window's changes and apply them to the app.")
        ui.decorate_buttons(button.parent() or button)

    def test_settings_saves_language_without_translating_data(self):
        set_language("en")
        with tempfile.TemporaryDirectory() as folder:
            store = Mock(base=Path(folder))
            dialog = ui.SettingsDialog(store, engine.Config(playlist_name="Privado", playlist_id="PL_123"))
            self.assertEqual(dialog.windowTitle(), "Settings")
            self.assertEqual(dialog.language_combo.currentData(), "es")
            self.assertEqual(dialog.privacy.currentText(), "Privado")
            dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("en"))
            with patch.object(engine, "set_run_at_startup"):
                dialog.save()
            config = store.save_config.call_args.args[0]
            self.assertEqual(config.language, "en")
            self.assertEqual(config.privacy_status, "private")
            self.assertEqual(config.playlist_name, "Privado")
            self.assertEqual(config.playlist_id, "PL_123")
            dialog.close()

    def test_main_window_table_translation_never_changes_upload_identity(self):
        store = Mock()
        store.base = ROOT / "work" / "i18n-tests"
        store.load_config.return_value = engine.Config(language="en")
        store.api_pause.return_value = None
        with patch.object(engine, "Store", return_value=store), patch.object(ui.MainWindow, "build_tray"), patch.object(ui.MainWindow, "refresh_all"):
            window = ui.MainWindow()
        try:
            window.timer.stop()
            self.assertEqual(language(), "en")
            self.assertEqual(window.tabs.tabText(1), "Channel")
            table = window.video_table
            table.setRowCount(1)
            for column, value in ((0, "Subido.mp4"), (1, "Pendiente"), (4, "Subido")):
                table.setItem(0, column, ui.table_item(value))
            delegate = table.itemDelegate()
            for column, expected in ((0, "Subido.mp4"), (1, "Pendiente"), (4, "Uploaded")):
                option = QStyleOptionViewItem()
                delegate.initStyleOption(option, table.model().index(0, column))
                self.assertEqual(option.text, expected)
            self.assertEqual(table.item(0, 4).text(), "Subido")
            window.channel_preview_title.setRawText("Pendiente")
            self.assertEqual(window.channel_preview_title.text(), "Pendiente")
        finally:
            window._allow_exit = True
            window.close()
            window.deleteLater()

    def test_manual_wizard_and_diagnostics_use_selected_language(self):
        set_language("en")
        dialog = ManualConfirmationDialog({"path": str(ROOT / "tests/fixtures/local-preview.mp4"), "youtube_id": "aB3_dE6-fG9"}, autoplay=False)
        self.assertEqual(dialog.title.text(), "Review the local file")
        self.assertEqual(dialog.next.text(), "Next: YouTube")
        dialog.reject()
        buffer = DiagnosticBuffer()
        buffer.append("Servicio en segundo plano iniciado.")
        self.assertIn("Background service started.", buffer.report())
        self.assertIn("[Service]", buffer.report())
        self.assertEqual(buffer.entries[0].message, "Servicio en segundo plano iniciado.")
        console = DiagnosticWindow(buffer)
        self.assertEqual(console.windowTitle(), "Console / YouTubeSync")
        console.close()

    def test_both_languages_fit_settings_and_channel_viewports(self):
        screenshots = ROOT / "work" / "language-qa"
        screenshots.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as folder:
            for code in ("es", "en"):
                config = engine.Config(language=code, watch_folder=folder, connected_channel_name="Mi canal")
                store = Mock(base=Path(folder))
                store.load_config.return_value = config
                store.api_pause.return_value = None
                with patch.object(engine, "Store", return_value=store), patch.object(ui.MainWindow, "build_tray"), patch.object(ui.MainWindow, "refresh_all"):
                    window = ui.MainWindow()
                window.timer.stop()
                try:
                    window.refresh_connection_card()
                    window.tabs.blockSignals(True)
                    window.tabs.setCurrentIndex(1)
                    window.tabs.blockSignals(False)
                    window.show()
                    for width, height in ((940, 620), (1600, 1000)):
                        window.resize(width, height)
                        for _ in range(4):
                            self.app.processEvents()
                            window.adjust_channel_layout()
                        self.assertLessEqual(window.channel_preview_scroll.widget().width(), window.channel_preview_scroll.viewport().width())
                        self.assertTrue(window.grab().save(str(screenshots / f"channel-{code}-{width}.png")))
                    settings = ui.SettingsDialog(store, config)
                    settings.resize(900, 650)
                    settings.show()
                    for _ in range(4):
                        self.app.processEvents()
                    self.assertGreaterEqual(settings.language_combo.width(), 100)
                    self.assertTrue(settings.rect().contains(settings.language_combo.mapTo(settings, settings.language_combo.rect().center())))
                    self.assertGreaterEqual(settings.extensions.y(), settings.folder.y() + settings.folder.height())
                    self.assertTrue(settings.grab().save(str(screenshots / f"settings-{code}.png")))
                    settings.close()
                finally:
                    window._allow_exit = True
                    window.close()
                    window.deleteLater()


if __name__ == "__main__":
    unittest.main()
