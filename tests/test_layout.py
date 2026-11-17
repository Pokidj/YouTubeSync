import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "outputs/youtube-sync-modern/src"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
import youtube_sync_modern as ui


class ResponsiveLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
        ui.apply_style(cls.app)

    def setUp(self):
        store = Mock()
        store.load_config.return_value = ui.legacy.Config()
        with patch.object(ui.legacy, "Store", return_value=store), \
                patch.object(ui.MainWindow, "build_tray"), \
                patch.object(ui.MainWindow, "refresh_all"):
            self.window = ui.MainWindow()
        self.window.timer.stop()
        self.window.tabs.blockSignals(True)
        self.window.tabs.setCurrentIndex(1)
        self.window.tabs.blockSignals(False)
        self.window.show()

    def tearDown(self):
        self.window._allow_exit = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def settle(self):
        for _ in range(4):
            self.app.processEvents()
            self.window.adjust_channel_layout()

    def test_preview_fits_narrow_and_wide_windows(self):
        for width, height in ((940, 620), (1280, 780), (1920, 1080)):
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.settle()
                scroll = self.window.channel_preview_scroll
                thumb = self.window.channel_preview_thumb
                self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
                self.assertAlmostEqual(thumb.height(), thumb.width() * 9 / 16, delta=2)
                pills = self.window.channel_info_pills
                self.assertGreaterEqual(pills[0].y(), thumb.y() + thumb.height())
                buttons = scroll.widget().findChildren(ui.QPushButton)
                play = next(button for button in buttons if button.text() == "Reproducir")
                self.assertGreaterEqual(play.y(), max(p.y() + p.height() for p in pills))
                scroll.ensureWidgetVisible(play)
                self.app.processEvents()
                self.assertTrue(scroll.viewport().rect().contains(
                    play.mapTo(scroll.viewport(), play.rect().center())))
                self.assertTrue(self.window.channel_table.isColumnHidden(6))
                self.assertGreaterEqual(self.window.channel_table.height(), 100)

    def test_dragging_splitter_reflows_pills(self):
        self.window.resize(1600, 1000)
        self.settle()
        self.window.channel_splitter.setSizes([1000, 330])
        self.settle()
        self.assertFalse(self.window._pills_two_columns)
        self.window.channel_splitter.setSizes([600, 700])
        self.settle()
        self.assertTrue(self.window._pills_two_columns)

    def test_thumbnail_load_does_not_change_size_hint(self):
        thumb = self.window.channel_preview_thumb
        hint = thumb.sizeHint()
        thumb.set_image((ROOT / "outputs/youtube-sync-modern/assets/youtube-sync-logo.png").read_bytes())
        self.assertFalse(thumb._source.isNull())
        self.assertEqual(thumb.sizeHint(), hint)

    def test_long_metadata_remains_inside_preview(self):
        self.window.resize(940, 620)
        self.window.channel_preview_title.setText("Un titulo de video largo " * 8)
        self.window.channel_preview_playlist.setText("Lista\n" + "Lista de reproduccion larga " * 10)
        self.settle()
        scroll = self.window.channel_preview_scroll
        self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        for pill in self.window.channel_info_pills:
            self.assertGreaterEqual(pill.height(), pill.minimumSizeHint().height())

    def test_tables_are_read_only(self):
        for table in (self.window.video_table, self.window.channel_table):
            self.assertEqual(table.editTriggers(), ui.QAbstractItemView.NoEditTriggers)

    def test_event_batch_yields_to_ui(self):
        for index in range(250):
            self.window.events.put(("log", f"Log {index}"))
        self.window.process_events()
        self.assertEqual(self.window.events.qsize(), 150)
        self.assertLessEqual(self.window.console.document().maximumBlockCount(), 2000)

    def test_settings_reuses_open_window(self):
        self.window.open_settings()
        first = self.window.settings_dialog
        self.window.open_settings()
        self.assertIs(self.window.settings_dialog, first)
        first.close()


if __name__ == "__main__":
    unittest.main()
