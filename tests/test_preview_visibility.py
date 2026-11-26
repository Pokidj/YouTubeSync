import unittest
from unittest.mock import patch

from PySide6.QtCore import QUrl
import test_layout as fixture
import youtube_sync_channel_ui as channel
from fake_youtube_player import FakeYouTubePlayer
import test_local_preview as local_fixture
from youtube_sync_i18n import set_language

ui, ROOT = fixture.ui, fixture.ROOT


class PreviewVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    def setUp(self):
        with patch.object(channel, "EmbeddedYouTubePlayer", FakeYouTubePlayer):
            fixture.ResponsiveLayoutTests.setUp(self)

    tearDown = fixture.ResponsiveLayoutTests.tearDown
    settle = fixture.ResponsiveLayoutTests.settle
    select_local = local_fixture.LocalPreviewTests.select_fixture
    select_channel = fixture.ResponsiveLayoutTests.select_preview_video

    def test_both_panels_start_hidden_and_controls_require_a_selection(self):
        for panel, button in ((self.window.local_preview_host, self.window.local_preview_button),
                              (self.window.channel_preview_host, self.window.channel_preview_button)):
            self.assertTrue(panel.isHidden())
            self.assertFalse(button.isEnabled())
            self.assertFalse(button.isChecked())

    def test_selection_reveals_the_corresponding_panel_and_clearing_hides_it(self):
        for select, panel, table, button in (
                (self.select_local, self.window.local_preview_host, self.window.video_table, self.window.local_preview_button),
                (self.select_channel, self.window.channel_preview_host, self.window.channel_table, self.window.channel_preview_button)):
            with self.subTest(table=table):
                select()
                self.assertFalse(panel.isHidden())
                self.assertTrue(button.isEnabled())
                self.assertTrue(button.isChecked())
                table.clearSelection()
                self.assertTrue(panel.isHidden())
                self.assertFalse(button.isEnabled())

    def test_manual_hide_survives_refresh_and_selection_changes_and_preserves_the_row(self):
        self.select_local()
        self.select_channel()
        for panel, table, button, refresh in (
                (self.window.local_preview_host, self.window.video_table, self.window.local_preview_button, self.window.video_selection_changed),
                (self.window.channel_preview_host, self.window.channel_table, self.window.channel_preview_button, self.window.update_channel_preview)):
            with self.subTest(table=table), patch.object(self.window, "fetch_thumbnail"):
                button.click()
                self.assertTrue(panel.isHidden())
                self.assertTrue(table.selectionModel().selectedRows())
                refresh()
                table.clearSelection()
                table.selectRow(0)
                self.assertTrue(panel.isHidden())
                self.assertTrue(button.isEnabled())
                button.click()
                self.assertFalse(panel.isHidden())
                self.assertTrue(button.isChecked())
        self.assertTrue(self.window.local_preview.player.player.source().isEmpty())
        self.assertFalse(self.window.channel_playback.active_id)

    def test_manual_hide_is_independent_between_tabs(self):
        self.select_local()
        self.select_channel()
        self.window.local_preview_button.click()
        self.assertTrue(self.window.local_preview_host.isHidden())
        self.assertFalse(self.window.channel_preview_host.isHidden())
        self.window.channel_loaded = True
        self.window.tabs.setCurrentIndex(1)
        self.window.tabs.setCurrentIndex(0)
        self.assertTrue(self.window.local_preview_host.isHidden())

    def test_toggle_names_and_help_are_translated(self):
        try:
            set_language("en")
            self.select_local()
            button = self.window.local_preview_button
            self.assertEqual(button.accessibleName(), "Hide preview")
            self.assertEqual(button.text(), "")
            width = button.width()
            button.click()
            self.assertEqual(button.accessibleName(), "Show preview")
            self.assertEqual(button.text(), "")
            self.assertEqual(button.width(), width)
        finally:
            set_language("es")

    def test_hiding_local_preview_releases_media_without_clearing_selection(self):
        item = self.select_local()
        player = self.window.local_preview.player.player
        player.setSource(QUrl.fromLocalFile(item["path"]))
        self.window.local_preview_button.click()
        self.assertTrue(player.source().isEmpty())
        self.assertEqual(self.window.selected_video_row()["path"], item["path"])

    def test_hiding_channel_preview_stops_playback_and_closes_fullscreen(self):
        self.select_channel()
        panel = self.window.channel_playback
        panel.open_popup()
        self.assertIsNotNone(panel.popup)
        self.window.channel_preview_button.click()
        self.assertIsNone(panel.popup)
        self.assertFalse(panel.active_id)
        self.assertFalse(panel.player.video_id)
        self.assertEqual(self.window.current_channel_video()["id"], "layout-video")

    def test_hidden_panel_returns_space_to_table_and_restores_splitter_width(self):
        self.select_local()
        self.select_channel()
        self.window.channel_loaded = True
        for index, splitter, table, button in ((0, self.window.local_splitter, self.window.video_table, self.window.local_preview_button),
                                               (1, self.window.channel_splitter, self.window.channel_table, self.window.channel_preview_button)):
            with self.subTest(tab=index):
                self.window.tabs.setCurrentIndex(index)
                self.window.resize(1280, 780)
                self.settle()
                splitter.setSizes([700, 450])
                self.settle()
                sizes = splitter.sizes()
                width = table.width()
                button.click()
                self.settle()
                self.assertGreater(table.width(), width + 200)
                button.click()
                self.settle()
                self.assertAlmostEqual(splitter.sizes()[1], sizes[1], delta=3)


if __name__ == "__main__":
    unittest.main()
