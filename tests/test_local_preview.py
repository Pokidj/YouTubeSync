import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtTest import QTest
import test_layout as fixture
from test_layout import ROOT, ui


class LocalPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    setUp = fixture.ResponsiveLayoutTests.setUp
    tearDown = fixture.ResponsiveLayoutTests.tearDown
    settle = fixture.ResponsiveLayoutTests.settle

    def select_fixture(self):
        path = ROOT / "tests/fixtures/local-preview.mp4"
        item = dict(path=str(path), signature=ui.engine.file_signature(path), title="Preview", status="Pendiente", youtube_id="", error="")
        self.window.tabs.setCurrentIndex(0)
        table = self.window.video_table
        table.blockSignals(True)
        table.setRowCount(1)
        for column, value in ((0, path.name), (1, "Preview"), (2, "10 KB"), (3, "2026-11-25"), (4, "Pendiente"), (5, str(path))):
            table.setItem(0, column, ui.table_item(value))
        self.window.video_rows = {0: item}
        with patch.object(self.window.local_media, "request", return_value=None):
            table.selectRow(0)
            table.blockSignals(False)
            self.window.user_video_selection_changed()
        return item

    def test_tab_bar_is_above_profile_and_notices_inside_local_page(self):
        self.window.tabs.setCurrentIndex(0)
        self.settle()
        bar = self.window.tabs.tabBar()
        for card in (self.window.state_card, self.window.guidance_card):
            self.assertTrue(self.window.tabs.widget(0).isAncestorOf(card))
            self.assertGreater(card.mapTo(self.window, card.rect().topLeft()).y(),
                               bar.mapTo(self.window, bar.rect().bottomLeft()).y())

    def test_selecting_does_not_autoplay_and_refreshing_same_identity_keeps_playback(self):
        item = self.select_fixture()
        preview = self.window.local_preview
        self.assertEqual(preview.identity, (item["path"], item["signature"]))
        self.assertTrue(preview.player.player.source().isEmpty())
        self.assertFalse(preview.youtube.isVisible())
        with patch.object(preview.player, "set_file") as change:
            self.window.video_selection_changed()
            change.assert_not_called()
            preview.select(dict(item, signature="changed"))
            change.assert_called_once_with(item["path"])

    def test_real_local_video_delivers_frames_and_transport_works(self):
        self.select_fixture()
        preview = self.window.local_preview.player
        preview.audio.setMuted(True)
        frames = []
        preview.video.videoSink().videoFrameChanged.connect(lambda frame: frames.append(frame.isValid()))
        preview.play_file()
        deadline = time.monotonic() + 6
        while not any(frames) and time.monotonic() < deadline:
            self.app.processEvents()
            QTest.qWait(20)
        self.assertTrue(any(frames), "The local fixture must render video frames")
        self.assertGreater(preview.player.duration(), 0)
        preview.pause()
        preview.player.setPosition(500)
        self.assertEqual(preview.player.position(), 500)
        preview.volume.setValue(35)
        self.assertAlmostEqual(preview.audio.volume(), .35, places=2)
        preview.release()
        self.assertTrue(preview.player.source().isEmpty())

    def test_switching_tabs_and_clearing_selection_release_the_file(self):
        self.select_fixture()
        with patch.object(self.window.local_preview, "release") as stop, patch.object(self.window, "refresh_channel"):
            self.window.tab_changed(1)
            stop.assert_called_once()
        self.window.video_table.clearSelection()
        self.assertIsNone(self.window.local_preview.identity)
        self.assertTrue(self.window.local_preview.player.player.source().isEmpty())

    def test_thumbnail_click_starts_selected_local_player(self):
        self.select_fixture()
        player = self.window.local_preview.player
        self.settle()
        with patch.object(player, "play_file") as play:
            QTest.mouseClick(player.thumbnail, ui.Qt.LeftButton)
            play.assert_called_once()

    def test_preview_thumbnail_is_updated_even_with_default_columns(self):
        item = self.select_fixture()
        with patch.object(self.window.local_preview.player, "set_thumbnail") as thumbnail:
            self.window.apply_local_media(item["path"], item["signature"], {"thumbnail": "fixture.png", "thumbnail_checked": True})
            thumbnail.assert_called_once_with("fixture.png")
            self.window.apply_local_media(item["path"], "stale", {"thumbnail": "wrong.png"})
            thumbnail.assert_called_once()

    def test_explorer_selects_file_without_starting_playback_or_a_shell(self):
        item = self.select_fixture()
        with patch.object(ui.subprocess, "Popen") as explorer, patch.object(ui.os, "startfile") as external:
            self.window.reveal_file_button.click()
        explorer.assert_called_once_with(["explorer.exe", "/select,", str(Path(item["path"]).resolve())])
        external.assert_not_called()
        self.assertTrue(self.window.local_preview.player.player.source().isEmpty())

    def test_explorer_without_selection_opens_configured_folder_and_handles_missing_paths(self):
        self.window.config = ui.engine.Config(watch_folder=str(ROOT))
        with patch.object(ui.os, "startfile") as explorer:
            self.window.open_folder_button.click()
            explorer.assert_called_once_with(str(ROOT.resolve()))
        self.window.config.watch_folder = ""
        with patch.object(ui.QMessageBox, "warning") as warning, patch.object(ui.os, "startfile") as explorer:
            self.window.open_watch_folder()
            warning.assert_called_once()
            explorer.assert_not_called()

    def test_folder_button_always_opens_settings_root_despite_selected_file(self):
        item = self.select_fixture()
        self.window.config.watch_folder = str(ROOT)
        self.assertNotEqual(ROOT, Path(item["path"]).parent)
        with patch.object(ui.os, "startfile") as folder, patch.object(ui.subprocess, "Popen") as reveal:
            self.window.open_folder_button.click()
            folder.assert_called_once_with(str(ROOT.resolve()))
            reveal.assert_not_called()

    def test_locate_requires_selection_and_does_not_open_a_different_folder(self):
        self.assertFalse(self.window.reveal_file_button.isEnabled())
        with patch.object(ui.QMessageBox, "information") as information, patch.object(ui.subprocess, "Popen") as reveal:
            self.window.reveal_selected_local_file()
            information.assert_called_once()
            reveal.assert_not_called()
        self.select_fixture()
        self.assertTrue(self.window.reveal_file_button.isEnabled())
        self.window.video_table.clearSelection()
        self.assertFalse(self.window.reveal_file_button.isEnabled())

    def test_missing_file_and_nonfolder_config_report_errors_without_launching_explorer(self):
        self.window.config.watch_folder = str(ROOT / "README.md")
        with patch.object(ui.QMessageBox, "warning") as warning, patch.object(ui.os, "startfile") as folder:
            self.window.open_watch_folder()
            warning.assert_called_once()
            folder.assert_not_called()
        with patch.object(self.window, "selected_video_row", return_value={"path": str(ROOT / "missing.mp4")}), \
                patch.object(ui.QMessageBox, "warning") as warning, patch.object(ui.subprocess, "Popen") as reveal:
            self.window.reveal_selected_local_file()
            warning.assert_called_once()
            reveal.assert_not_called()

    def test_locate_is_disabled_when_the_configured_folder_disappears(self):
        self.select_fixture()
        self.assertTrue(self.window.reveal_file_button.isEnabled())
        self.window.config.watch_folder = ""
        self.window.refresh_folder()
        self.assertFalse(self.window.reveal_file_button.isEnabled())

    def test_preview_resizes_without_expanding_window_or_hiding_controls(self):
        self.select_fixture()
        for width, height in ((940, 620), (1280, 780), (1920, 1080), (940, 620)):
            self.window.resize(width, height)
            self.settle()
            self.assertEqual(self.window.width(), width)
            scroll = self.window.local_preview_scroll
            self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
            player = self.window.local_preview.player
            self.assertAlmostEqual(player.surface.height(), player.width() * 9 / 16, delta=2)
            for control in (player.play_button, player.mute_button, player.volume):
                self.assertTrue(player.rect().contains(control.mapTo(player, control.rect().bottomRight())))
        self.window.resize(1920, 1080)
        self.settle()
        self.window.local_splitter.setSizes([800, 1000])
        self.settle()
        self.assertGreater(self.window.local_preview_scroll.width(), 800)

    def test_deletion_releases_preview_before_starting_background_work(self):
        self.select_fixture()
        with patch.object(self.window.local_preview, "release") as release, patch.object(ui.threading, "Thread") as thread:
            self.window.begin_local_deletion([])
            release.assert_called_once()
            thread.return_value.start.assert_called_once()
            self.assertFalse(self.window.local_preview.player.isEnabled())


if __name__ == "__main__":
    unittest.main()
