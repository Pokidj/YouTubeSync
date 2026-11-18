import os
import sys
import tempfile
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
        store.api_pause.return_value = None
        store.load_config.return_value = ui.engine.Config()
        with patch.object(ui.engine, "Store", return_value=store), \
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

    def test_retry_queues_the_original_selection_after_refresh(self):
        item = {"path": "C:/example/video.mp4", "signature": "signature", "status": "Incidencia"}
        with patch.object(self.window, "selected_video_row", side_effect=[item, None]) as selected, \
                patch.object(self.window, "refresh_folder"), \
                patch.object(self.window, "queue_video") as queue_video:
            self.window.retry_selected_video()
        selected.assert_called_once()
        queue_video.assert_called_once_with(item)
        self.window.store.clear_upload_incident.assert_called_once_with("signature")

    def test_selected_video_is_queued_before_a_new_worker_starts(self):
        worker = Mock()
        self.window.worker = None
        with patch.object(ui.engine, "SyncWorker", return_value=worker):
            self.window.start_worker(manual_path=Path("selected.mp4"))
        self.assertEqual(worker.method_calls[0], unittest.mock.call.upload_path(Path("selected.mp4")))
        self.assertEqual(worker.method_calls[-1], unittest.mock.call.start())
        self.window.worker = None

    def test_quota_waiting_is_not_an_incident_and_keeps_confirmed_uploads(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            registry, statuses = {}, {}
            for name, status, error in (("confirmed", "error", "quotaExceeded"),
                                        ("waiting", "error", "quotaExceeded"),
                                        ("broken", "error", "Archivo corrupto")):
                path = Path(temporary) / (name + ".mp4")
                path.write_bytes(name.encode())
                signature = ui.engine.file_signature(path)
                statuses[signature] = (signature, name, str(path), status, error, "2026-11-17")
                if name == "confirmed":
                    registry[signature] = (signature, name, str(path), "remote-id", "uploaded", "2026-11-17")
            self.window.config = ui.engine.Config(watch_folder=temporary)
            self.window.store.registry_index.return_value = (registry, {})
            self.window.store.upload_status_index.return_value = (statuses, {})
            self.window.refresh_folder()
            states = {Path(row["path"]).stem: row["status"] for row in self.window.video_rows.values()}
            self.assertEqual(states, {"confirmed": "Subido", "waiting": "En espera", "broken": "Incidencia"})

    def test_quota_countdown_retries_only_once_when_expired(self):
        self.window.api_pause_state = {"retry_at": "2000-01-01T00:00:00+00:00"}
        with patch.object(self.window, "check_youtube") as check:
            self.window.update_quota_status()
            self.window.update_quota_status()
        check.assert_called_once_with(full=True)

    def test_local_actions_receive_the_persisted_youtube_id(self):
        self.window.video_table.setRowCount(1)
        for column, text in ((0, "file.mp4"), (1, "Video"), (4, "Subido"), (5, "C:/file.mp4")):
            self.window.video_table.setItem(0, column, ui.table_item(text))
        self.window.video_rows[0] = {"path": "C:/file.mp4", "signature": "signature", "youtube_id": "remote-id"}
        self.window.video_table.selectRow(0)
        self.assertEqual(self.window.selected_video_row()["youtube_id"], "remote-id")

    def test_thumbnail_downloads_use_a_fixed_pool_not_one_thread_per_video(self):
        with patch.object(ui.threading, "Thread") as thread:
            for number in range(100):
                self.window.fetch_thumbnail({"id": str(number), "thumbnail": "https://example.invalid/image.jpg"})
        self.assertEqual(thread.call_count, 6)
        self.assertEqual(self.window.thumbnail_jobs.qsize(), 100)


if __name__ == "__main__":
    unittest.main()
