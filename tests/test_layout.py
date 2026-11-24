import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
import youtube_sync_app as ui


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
        store.base = ROOT / "work" / "layout-test-data"
        store.api_pause.return_value = None
        store.retry_required_signatures.return_value = set()
        store.pending_upload_reviews.return_value = {}
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
        thumb.set_image((ROOT / "assets/youtube-sync-logo.png").read_bytes())
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
        self.assertLessEqual(len(self.window.diagnostic_buffer.entries), 2000)

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

    def test_manual_queue_authorizes_a_single_explicit_retry(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "video.mp4"
            path.write_bytes(b"video")
            with patch.object(self.window, "start_worker") as start:
                self.window.queue_video({"path": str(path), "signature": "signature", "status": "Incidencia"})
        self.window.store.clear_upload_incident.assert_called_once_with("signature")
        start.assert_called_once_with(manual_path=path)

    def test_clicking_upload_on_the_active_file_does_not_authorize_another_attempt(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "video.mp4"
            path.write_bytes(b"video")
            self.window.worker = Mock(active_path=path)
            with patch.object(ui.QMessageBox, "information"), patch.object(self.window, "start_worker") as start:
                self.window.queue_video({"path": str(path), "signature": "signature", "status": "En curso"})
        self.window.store.clear_upload_incident.assert_not_called()
        start.assert_not_called()
        self.window.worker = None

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
        check.assert_called_once_with(full=False)

    def test_background_check_does_not_probe_channel_when_there_is_nothing_to_verify(self):
        client = Mock()
        with patch.object(ui.engine, "YouTubeClient", return_value=client), \
                patch.object(ui.engine, "reconcile_local_uploads", return_value=0):
            self.window._check_youtube_thread(full=False)
        client.channel_info.assert_not_called()

    def test_successful_connection_clears_stale_quota_notice(self):
        self.window.api_pause_state = {"kind": "proyecto", "retry_at": "2099-01-01T00:00:00+00:00"}
        self.window.events.put(("youtube", {"title": "Mi canal"}))
        self.window.process_events()
        self.assertIsNone(self.window.api_pause_state)
        self.assertNotIn("cuota", self.window.status.text().lower())

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

    def test_first_run_opens_setup_without_starting_uploads(self):
        with patch.object(self.window, "open_setup") as setup, patch.object(self.window, "start_worker") as worker:
            self.window.initialize_session()
        setup.assert_called_once()
        worker.assert_not_called()
        self.assertFalse(self.window.auto_enabled)

    def test_configured_users_keep_the_normal_startup_flow(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            secret = Path(temporary) / "client.json"
            secret.write_text("{}")
            self.window.config = ui.engine.Config(watch_folder=temporary, client_secret_path=str(secret))
            self.window.auto_enabled = True
            with patch.object(self.window, "open_setup") as setup, patch.object(self.window, "check_youtube") as check, \
                    patch.object(self.window, "start_worker") as worker:
                self.window.initialize_session()
            setup.assert_not_called()
            check.assert_called_once()
            worker.assert_called_once()

    def test_auto_after_setup_waits_for_the_remote_reconciliation(self):
        self.window.auto_enabled = True
        self.window._resume_after_setup_check = True
        self.window.events.put(("youtube", {"title": "Canal"}))
        with patch.object(self.window, "start_worker") as worker:
            self.window.process_events()
        worker.assert_called_once()
        self.assertFalse(self.window._resume_after_setup_check)

    def test_settings_search_finds_the_connection_tab(self):
        self.window.open_settings()
        dialog = self.window.settings_dialog
        dialog.settings_search.setText("conectar")
        tabs = dialog.findChild(ui.QTabWidget)
        self.assertEqual(tabs.tabText(tabs.currentIndex()), "YouTube")
        dialog.close()


if __name__ == "__main__":
    unittest.main()
