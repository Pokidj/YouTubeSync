import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QTabWidget, QMessageBox
from youtube_sync_library import DEFAULT_LIBRARY_COLUMNS, LIBRARY_COLUMNS, normalize_library_columns, media_cells
from youtube_sync_local_media import LocalMediaLoader, windows_media

ui, ROOT = fixture.ui, fixture.ROOT


class LibraryConfigTests(unittest.TestCase):
    def test_defaults_are_independent_and_invalid_values_are_safe(self):
        config = ui.engine.Config()
        self.assertEqual(config.library_columns, list(DEFAULT_LIBRARY_COLUMNS))
        config.library_columns.append("thumbnail")
        self.assertNotIn("thumbnail", ui.engine.Config().library_columns)
        for value in (None, [], "file", [False, {}, "unknown"]):
            self.assertEqual(normalize_library_columns(value), list(DEFAULT_LIBRARY_COLUMNS))
        self.assertEqual(normalize_library_columns(["status", "status", None, "resolution", [], "file"]),
                         ["status", "resolution", "file"])

    def test_order_visibility_and_old_config_survive_reopening(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            with patch.object(ui.engine, "app_dir", return_value=Path(temporary)):
                store = ui.engine.Store()
                config = ui.engine.Config(library_columns=["thumbnail", "status", "file", "resolution"])
                store.save_config(config)
                self.assertEqual(store.load_config().library_columns, config.library_columns)
                data = json.loads(store.config_path.read_text())
                data.pop("library_columns")
                store.config_path.write_text(json.dumps(data))
                self.assertEqual(store.load_config().library_columns, list(DEFAULT_LIBRARY_COLUMNS))
                data["library_columns"] = ["status", {}, "status", "size"]
                store.config_path.write_text(json.dumps(data))
                self.assertEqual(store.load_config().library_columns, ["status", "size"])

    def test_media_values_are_real_dimensions_and_numeric_sort_values(self):
        cells = media_cells({"width": 3840, "height": 2160, "seconds": 3661, "fps": 59.94})
        self.assertEqual(cells[0], ("3840 x 2160", 8294400))
        self.assertEqual(cells[2], ("1:01:01", 3661))
        self.assertEqual(cells[3], ("59.94", 59.94))
        self.assertEqual(media_cells({})[0][0], "No disponible")


class LibraryLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)
        self.window.tabs.setCurrentIndex(0)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.base = Path(self.temporary.name)
        self.window.store.registry_index.return_value = ({}, {})
        self.window.store.upload_status_index.return_value = ({}, {})
        self.window.config.watch_folder = str(self.base)

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        self.temporary.cleanup()

    def clip(self, name="clip.mp4", size=100):
        path = self.base / name
        path.write_bytes(b"x" * size)
        return path

    def visual_keys(self):
        header = self.window.video_table.horizontalHeader()
        return [LIBRARY_COLUMNS[header.logicalIndex(i)][0] for i in range(header.count())
                if not self.window.video_table.isColumnHidden(header.logicalIndex(i))]

    def test_default_columns_headers_and_status_icons(self):
        self.clip()
        self.window.refresh_folder()
        self.assertEqual(self.visual_keys(), list(DEFAULT_LIBRARY_COLUMNS))
        self.assertEqual(self.window.video_table.verticalHeader().defaultSectionSize(), 34)
        for index in range(len(LIBRARY_COLUMNS)):
            self.assertFalse(self.window.video_table.horizontalHeaderItem(index).icon().isNull())
        self.assertFalse(self.window.video_table.item(0, 4).icon().isNull())
        self.assertEqual(self.window.video_table.item(0, 4).text(), "Pendiente")
        with patch.object(self.window.local_media, "request") as request:
            self.window.load_visible_local_media()
            request.assert_not_called()

    def test_hidden_identity_survives_reordering_and_numeric_size_sort(self):
        self.clip("big.mp4", 10000)
        small = self.clip("small.mp4", 2)
        self.clip("medium.mp4", 2000)
        self.window.config.library_columns = ["status", "size", "file"]
        self.window.refresh_folder()
        table = self.window.video_table
        self.assertEqual(self.visual_keys(), ["status", "size", "file"])
        table.sortItems(2, Qt.AscendingOrder)
        table.selectRow(0)
        self.assertEqual(self.window.selected_video_row()["path"], str(small))
        self.assertEqual([table.item(row, 2).data(Qt.UserRole) for row in range(3)], [2, 2000, 10000])
        self.assertTrue(table.isColumnHidden(1))
        self.assertTrue(table.isColumnHidden(5))
        self.assertTrue(self.window.selected_video_row()["title"])

    def test_optional_media_result_matches_signature_not_sorted_row_number(self):
        first, second = self.clip("first.mp4", 20), self.clip("second.mp4", 200)
        self.window.config.library_columns = ["thumbnail", "file", "resolution", "duration", "fps", "status"]
        self.window.refresh_folder()
        table = self.window.video_table
        table.sortItems(2, Qt.DescendingOrder)
        image = QImage(160, 90, QImage.Format_RGB32)
        image.fill(Qt.red)
        thumbnail = self.base / "thumbnail.png"
        image.save(str(thumbnail))
        self.window.apply_local_media(str(first), ui.engine.file_signature(first),
                                     {"width": 1920, "height": 1080, "seconds": 75, "fps": 60,
                                      "thumbnail": str(thumbnail), "thumbnail_checked": True})
        row = next(row for row in range(2) if table.item(row, 5).text() == str(first))
        self.assertEqual(table.item(row, 6).text(), "1920 x 1080")
        self.assertFalse(table.item(row, 7).icon().isNull())
        self.assertEqual(table.item(row, 8).text(), "1:15")
        self.assertEqual(table.item(row, 9).text(), "60")
        self.assertEqual(table.item(row, 4).text(), "Pendiente")
        self.assertEqual(table.verticalHeader().defaultSectionSize(), 64)
        self.assertEqual(table.item(1 - row, 6).text(), "...")

    def test_stale_result_cannot_describe_changed_file_or_change_uploaded_status(self):
        path = self.clip()
        signature = ui.engine.file_signature(path)
        self.window.config.library_columns = ["resolution", "status"]
        self.window.store.registry_index.return_value = ({signature: (signature, "title", str(path), "video-id", "uploaded", "today")}, {})
        self.window.refresh_folder()
        path.write_bytes(b"changed")
        self.window.apply_local_media(str(path), signature, {"width": 10, "height": 20})
        self.assertEqual(self.window.video_table.item(0, 6).text(), "...")
        self.assertEqual(self.window.video_table.item(0, 4).text(), "Subido")

    def test_settings_can_reorder_toggle_reset_save_and_reject_empty_selection(self):
        dialog = ui.SettingsDialog(self.window.store, self.window.config)
        try:
            self.assertEqual(dialog.selected_library_columns(), list(DEFAULT_LIBRARY_COLUMNS))
            dialog.library_columns.setCurrentRow(3)
            dialog.move_library_column(-1)
            self.assertEqual(dialog.selected_library_columns(), ["file", "size", "status", "created"])
            dialog.save()
            self.assertEqual(self.window.store.save_config.call_args.args[0].library_columns,
                             ["file", "size", "status", "created"])
            self.assertEqual(self.window.config.library_columns, list(DEFAULT_LIBRARY_COLUMNS))
            dialog.fill_library_columns(["thumbnail", "resolution", "file"])
            self.assertEqual(dialog.selected_library_columns(), ["thumbnail", "resolution", "file"])
            dialog.fill_library_columns(list(DEFAULT_LIBRARY_COLUMNS))
            for row in range(dialog.library_columns.count()):
                dialog.library_columns.item(row).setCheckState(Qt.Unchecked)
            self.window.store.save_config.reset_mock()
            with patch.object(QMessageBox, "warning") as warning:
                dialog.save()
            warning.assert_called_once()
            self.window.store.save_config.assert_not_called()
            dialog.settings_search.setText("miniatura")
            self.assertEqual(dialog.findChild(QTabWidget).tabText(dialog.findChild(QTabWidget).currentIndex()), "Biblioteca")
        finally:
            dialog.close()

    def test_display_settings_save_does_not_query_youtube(self):
        updated = ui.replace(self.window.config, library_columns=["status", "file"])
        self.window.store.load_config.return_value = updated
        with patch.object(self.window, "refresh_all") as refresh:
            self.window.apply_saved_settings()
        refresh.assert_called_once_with(light=True)

    def test_metadata_sort_requests_remaining_rows_not_just_the_viewport(self):
        for index in range(40):
            self.clip(f"clip-{index}.mp4")
        self.window.config.library_columns = ["file", "resolution"]
        self.window.refresh_folder()
        self.window.video_table.sortItems(6, Qt.AscendingOrder)
        with patch.object(self.window.local_media, "request", return_value=None) as request:
            self.window.load_visible_local_media()
        self.assertEqual(request.call_count, 40)

    def test_all_column_options_fit_in_minimum_settings_window(self):
        dialog = ui.SettingsDialog(self.window.store, self.window.config)
        try:
            dialog.resize(900, 650)
            dialog.show()
            dialog.settings_search.setText("columnas")
            for _ in range(3):
                self.app.processEvents()
            last = dialog.library_columns.visualItemRect(dialog.library_columns.item(9))
            self.assertLess(last.bottom(), dialog.library_columns.viewport().height())
        finally:
            dialog.close()


class LocalMediaTests(unittest.TestCase):
    def test_cache_including_unavailable_formats_is_reused_and_invalidated_by_file_change(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            base = Path(temporary)
            path = base / "clip.mp4"
            path.write_bytes(b"not-a-valid-video")
            signature = ui.engine.file_signature(path)
            loader = LocalMediaLoader(base / "cache")
            with patch("youtube_sync_local_media.windows_media", return_value={}) as read:
                self.assertEqual(loader.load(path, signature, True), {})
                self.assertEqual(LocalMediaLoader(base / "cache").load(path, signature, True), {})
                self.assertEqual(read.call_count, 1)
                path.write_bytes(b"changed-file")
                self.assertEqual(loader.load(path, signature, True), {})
                self.assertEqual(read.call_count, 1)
                loader.load(path, ui.engine.file_signature(path), True)
                self.assertEqual(read.call_count, 2)

    def test_worker_queue_is_bounded_lazy_and_stops_without_new_jobs(self):
        loader = LocalMediaLoader(ROOT / "work/library-test-cache")
        self.assertFalse(loader.started)
        with patch("youtube_sync_local_media.threading.Thread") as thread:
            for index in range(100):
                loader.request("unused.mp4", str(index), False)
            self.assertEqual(thread.call_count, 2)
            self.assertEqual(loader.jobs.qsize(), 32)
            self.assertEqual(len(loader.pending), 32)
            loader.request("unused.mp4", "0", True)
            self.assertEqual(loader.jobs.qsize(), 32)
            loader.shutdown()
            loader.request("unused.mp4", "extra", True)
            self.assertEqual(loader.jobs.qsize(), 32)

    @unittest.skipUnless(os.name == "nt", "Windows Explorer provider")
    def test_native_windows_thumbnail_with_real_image(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            base = Path(temporary)
            source, output = base / "source.png", base / "thumbnail.png"
            image = QImage(320, 180, QImage.Format_RGB32)
            image.fill(Qt.red)
            image.save(str(source))
            data = windows_media(source, output)
            self.assertTrue(data.get("thumbnail"))
            thumbnail = QImage(str(output))
            self.assertFalse(thumbnail.isNull())
            self.assertGreater(thumbnail.pixelColor(thumbnail.width() // 2, thumbnail.height() // 2).red(), 200)


if __name__ == "__main__":
    unittest.main()
