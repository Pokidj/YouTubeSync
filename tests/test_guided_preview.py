import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_layout as fixture
from PySide6.QtCore import QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QMenu, QPushButton, QToolButton
from PySide6.QtMultimedia import QMediaPlayer
from youtube_sync_help import describe_control, install_button_help
from youtube_sync_manual_ui import ManualConfirmationDialog
from youtube_sync_local_player import media_time
from youtube_sync_setup import SetupWizard
from youtube_sync_diagnostics import DiagnosticWindow, DiagnosticBuffer
from fake_youtube_player import FakeYouTubePlayer

ROOT, ui = fixture.ROOT, fixture.ui


class HoverHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)

    def test_app_settings_setup_and_diagnostic_buttons_have_descriptive_help(self):
        helper = install_button_help(self.app)
        settings = ui.SettingsDialog(self.window.store, self.window.config)
        diagnostic = DiagnosticWindow(DiagnosticBuffer())
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            self.window.store.base = Path(temporary)
            setup = SetupWizard(self.window.store, self.window.config)
            manual = ManualConfirmationDialog({"path": str(ROOT / "tests/fixtures/local-preview.mp4")}, autoplay=False)
            try:
                incomplete = []
                for window in (self.window, settings, diagnostic, setup, manual):
                    helper.refresh(window)
                    for button in window.findChildren(QAbstractButton):
                        label = button.accessibleName() or button.text()
                        if not label and not button.toolTip():
                            continue  # Native tab scrolling controls have no app action.
                        self.assertTrue(button.toolTip(), label)
                        if len(button.toolTip()) <= len(label) or "Ejecuta la acción" in button.toolTip():
                            incomplete.append((type(window).__name__, label, button.toolTip()))
                        self.assertEqual(button.toolTip(), button.accessibleDescription(), label)
                self.assertEqual(incomplete, [])
            finally:
                manual.close()
                setup.close()
                diagnostic.render_timer.stop()
                diagnostic.close()
                settings.close()

    def test_dynamic_states_and_icon_only_buttons_receive_hover_help(self):
        button = QPushButton("ON")
        helper = install_button_help(self.app)
        helper.apply(button)
        self.assertIn("Desactiva", button.toolTip())
        button.setText("OFF")
        self.app.sendEvent(button, QEvent(QEvent.ToolTip))
        self.assertIn("Activa", button.toolTip())
        icon = QToolButton()
        icon.setToolTip("Cancelar subida actual")
        helper.apply(icon)
        self.assertIn("bloque", icon.toolTip())
        self.assertEqual(describe_control(icon), icon.toolTip())

    def test_tray_and_context_menu_actions_have_hover_descriptions(self):
        menu = QMenu()
        show = menu.addAction("Mostrar")
        upload = menu.addAction("Subir pendientes")
        self.app.sendEvent(menu, QEvent(QEvent.Show))
        self.assertTrue(menu.toolTipsVisible())
        self.assertIn("bandeja", show.toolTip())
        self.assertIn("pendientes", upload.toolTip())
        menu.close()


class LocalPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        embedded = patch("youtube_sync_manual_ui.EmbeddedYouTubePlayer", FakeYouTubePlayer)
        embedded.start()
        self.addCleanup(embedded.stop)

    def test_time_formatter(self):
        self.assertEqual(media_time(61000), "1:01")
        self.assertEqual(media_time(3601000), "1:00:01")
        self.assertEqual(media_time(-50), "0:00")

    def test_real_video_decodes_and_stops_on_advance_and_close(self):
        dialog = ManualConfirmationDialog({"path": str(ROOT / "tests/fixtures/local-preview.mp4"),
                                           "youtube_id": "aB3_dE6-fG9"})
        frames = []
        dialog.preview.video.videoSink().videoFrameChanged.connect(
            lambda frame: frames.append(frame.toImage()) if frame.isValid() else None)
        dialog.preview.audio.setMuted(True)
        dialog.show()
        try:
            for _ in range(80):
                QTest.qWait(50)
                if len(frames) >= 3:
                    break
            self.assertGreaterEqual(len(frames), 3)
            image = frames[0]
            self.assertFalse(image.isNull())
            self.assertGreater(image.pixelColor(10, 10).green(), 40)
            self.assertGreater(dialog.preview.player.duration(), 1000)
            self.assertEqual(dialog.preview.player.playbackState(), QMediaPlayer.PlayingState)
            dialog.preview.pause()
            self.assertEqual(dialog.preview.player.playbackState(), QMediaPlayer.PausedState)
            dialog.preview.player.setPosition(500)
            self.assertEqual(dialog.preview.seek.value(), 500)
            with patch("youtube_sync_manual_ui.webbrowser.open", return_value=True) as browser:
                dialog.advance()
            browser.assert_not_called()
            self.assertEqual(dialog.remote_preview.video_id, "aB3_dE6-fG9")
            self.assertNotEqual(dialog.preview.player.playbackState(), QMediaPlayer.PlayingState)
            dialog.reject()
            self.assertEqual(dialog.preview.player.playbackState(), QMediaPlayer.StoppedState)
            self.assertTrue(dialog.preview.player.source().isEmpty())
        finally:
            dialog.close()
            dialog.deleteLater()
            self.app.processEvents()

    def test_each_wizard_page_fits_without_overlapping_navigation(self):
        dialog = ManualConfirmationDialog({"path": str(ROOT / "tests/fixtures/local-preview.mp4"),
                                           "youtube_id": "aB3_dE6-fG9"}, autoplay=False)
        try:
            dialog.show()
            dialog.opened_id = dialog.video_id()
            for size in ((640, 510), (760, 580), (1000, 750)):
                dialog.resize(*size)
                for page in range(4):
                    dialog.set_step(page)
                    self.app.processEvents()
                    self.assertLessEqual(dialog.pages.y() + dialog.pages.height(), dialog.cancel.y())
                    for button in dialog.findChildren(QAbstractButton):
                        if button.isVisible():
                            point = button.mapTo(dialog, button.rect().bottomRight())
                            self.assertTrue(dialog.rect().contains(point), (size, page, button.text()))
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
