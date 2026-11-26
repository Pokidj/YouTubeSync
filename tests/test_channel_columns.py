import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_layout as fixture
from PySide6.QtCore import Qt
from youtube_sync_channel_columns import CHANNEL_COLUMNS, DEFAULT_CHANNEL_COLUMNS, normalize_channel_columns, selection_color, duration_sort_value
from youtube_sync_youtube_player import player_html
from youtube_sync_first_party_player import media_expression
from fake_youtube_player import FakeYouTubePlayer
import youtube_sync_channel_ui as channel
from youtube_sync_i18n import set_language

ui = fixture.ui
VIDEO = "aB3_cD6-eF9"


class ChannelColumnDataTests(unittest.TestCase):
    def test_normalization_rejects_unknown_duplicates_and_empty_settings(self):
        self.assertEqual(normalize_channel_columns(["size", "size", [], "unknown", "title"]), ["size", "title"])
        self.assertEqual(normalize_channel_columns([]), list(DEFAULT_CHANNEL_COLUMNS))
        self.assertEqual(selection_color("invalid"), "green")
        self.assertEqual(duration_sort_value("1:02:03"), 3723)
        self.assertEqual(duration_sort_value("-"), -1)

    def test_preferences_survive_reopening_without_touching_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(ui.engine, "app_dir", return_value=Path(folder)):
            store = ui.engine.Store()
            store.save_config(ui.engine.Config(channel_columns=["size", "id", "title"], channel_selection_color="blue"))
            saved = ui.engine.Store().load_config()
        self.assertEqual(saved.channel_columns, ["size", "id", "title"])
        self.assertEqual(saved.channel_selection_color, "blue")

    def test_native_controls_hidden_only_when_app_controls_exist(self):
        html = player_html(VIDEO, custom_controls=True, captions_off=True)
        self.assertIn('"controls": 0', html)
        self.assertIn("window.captionsWanted=false", html)
        self.assertIn("onApiChange:applyCaptions", html)
        self.assertIn('"controls": 1', player_html(VIDEO))
        self.assertIn("window.captionsWanted=null", player_html(VIDEO))
        script = media_expression(VIDEO, captions=False)
        self.assertLess(script.index("ad-showing"), script.index("p.unloadModule"))
        self.assertIn("catch(e)", script)


class ChannelColumnUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        with patch.object(channel, "EmbeddedYouTubePlayer", FakeYouTubePlayer):
            fixture.ResponsiveLayoutTests.setUp(self)
        thumbnails = patch.object(self.window, "fetch_thumbnail")
        thumbnails.start()
        self.addCleanup(thumbnails.stop)

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        set_language("es")

    def load(self):
        rows = [{"id": VIDEO, "title": "Clip", "duration": "10:01", "privacy": "private", "size": 1000,
                 "resolution": "1920 x 1080", "fps": 60, "quality": "HD", "processing": "processed"}]
        self.window.apply_channel_rows(rows, [])
        while self.window.channel_render_pending:
            self.window.append_channel_render_batch()
        self.window.channel_table.selectRow(0)

    def test_hidden_and_reordered_columns_keep_video_identity_and_extra_data(self):
        self.window.config.channel_columns = ["size", "id", "resolution", "fps", "quality", "processing"]
        self.load()
        table = self.window.channel_table
        self.assertEqual(table.columnCount(), len(CHANNEL_COLUMNS))
        self.assertTrue(table.isColumnHidden(1))
        self.assertTrue(table.isColumnHidden(6))
        self.assertEqual(table.horizontalHeader().logicalIndex(0), 9)
        self.assertEqual(self.window.current_channel_video()["id"], VIDEO)
        self.assertEqual(table.item(0, 10).text(), "1920 x 1080")
        self.assertEqual(table.item(0, 9).data(Qt.UserRole), 1000)
        self.assertEqual(table.item(0, 2).data(Qt.UserRole), 601)
        self.assertIn("#15803d", table.styleSheet())

    def test_settings_reorder_color_and_empty_validation(self):
        dialog = ui.SettingsDialog(self.window.store, self.window.config)
        try:
            dialog.fill_channel_columns(["size", "title", "id"])
            dialog.channel_columns.setCurrentRow(2)
            dialog.move_channel_column(-1)
            dialog.channel_color.setCurrentIndex(dialog.channel_color.findData("blue"))
            dialog.save()
            config = self.window.store.save_config.call_args.args[0]
            self.assertEqual(config.channel_columns, ["size", "id", "title"])
            self.assertEqual(config.channel_selection_color, "blue")
            for row in range(dialog.channel_columns.count()):
                dialog.channel_columns.item(row).setCheckState(Qt.Unchecked)
            self.window.store.save_config.reset_mock()
            with patch.object(ui.QMessageBox, "warning") as warning:
                dialog.save()
            warning.assert_called_once()
            self.window.store.save_config.assert_not_called()
        finally:
            dialog.close()

    def test_playlist_action_uses_dialog_instead_of_permanent_selector(self):
        self.load()
        self.assertFalse(hasattr(self.window, "channel_playlist_combo"))
        self.window.set_channel_playlist_options([{"id": "list-id", "title": "Mi lista"}])
        while self.window.channel_render_pending:
            self.window.append_channel_render_batch()
        self.window.channel_table.selectRow(0)
        with patch.object(ui.QInputDialog, "getItem", return_value=("Mi lista", True)), \
                patch.object(ui.QMessageBox, "question", return_value=ui.QMessageBox.StandardButton.Yes), \
                patch.object(ui.threading, "Thread") as thread:
            self.window.change_selected_channel_playlist()
        self.assertEqual(thread.call_args.kwargs["args"][1], "list-id")

    def test_caption_toggle_is_synced_across_panel_and_fullscreen(self):
        self.load()
        playback = self.window.channel_playback
        playback.start()
        playback.player.telemetry.emit({"position": 20, "duration": 601, "volume": 65, "playing": True, "muted": False})
        self.assertTrue(playback.player.custom_controls)
        self.assertTrue(playback.player.captions_off)
        self.assertFalse(playback.transport.captions.isChecked())
        playback.transport.captions.click()
        playback.open_popup()
        self.assertTrue(playback.popup.transport.captions.isChecked())
        playback.popup.transport.captions.click()
        self.assertFalse(playback.transport.captions.isChecked())
        self.assertEqual(playback.player.commands[-2:], [("captions", True), ("captions", False)])

    def test_playlist_names_are_not_translated_or_confused_with_the_none_choice(self):
        set_language("en")
        self.load()
        self.window.set_channel_playlist_options([{"id": "list-id", "title": "None"}])
        while self.window.channel_render_pending:
            self.window.append_channel_render_batch()
        self.window.channel_table.selectRow(0)
        with patch.object(ui.QInputDialog, "getItem", return_value=("None / ist-id", True)) as choose, \
                patch.object(ui.QMessageBox, "question", return_value=ui.QMessageBox.StandardButton.Yes), \
                patch.object(ui.threading, "Thread") as thread:
            self.window.change_selected_channel_playlist()
        self.assertFalse(choose.call_args.kwargs["translate_items"])
        self.assertEqual(thread.call_args.kwargs["args"][1], "list-id")
