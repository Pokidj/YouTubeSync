import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from fake_youtube_player import FakeYouTubePlayer
import youtube_sync_channel_ui as channel
from youtube_sync_i18n import set_language, t

ui = fixture.ui
VIDEO = "aB3_cD6-eF9"
OTHER = "zY8_xW5-vU2"
DATA = {"position": 83.9, "duration": 180, "volume": 65, "playing": True, "muted": False}


class PlayerSharingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        with patch.object(channel, "EmbeddedYouTubePlayer", FakeYouTubePlayer):
            self.panel = channel.ChannelPlayback(ui.PreviewThumbnail(), Path(self.folder.name))
        self.panel.show()
        self.panel.select_video(VIDEO)

    def tearDown(self):
        self.panel.stop()
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()
        self.folder.cleanup()

    def test_share_requires_real_position_and_uses_seconds_not_minutes(self):
        requested = Mock()
        self.panel.share_requested.connect(requested)
        normal = Mock()
        self.panel.share_video_requested.connect(normal)
        self.panel.start()
        self.assertTrue(self.panel.share_here.isEnabled())
        self.panel.share_here.click()
        normal.assert_called_once_with()
        self.panel.share_from_position()
        requested.assert_not_called()
        self.panel.player.telemetry.emit(DATA)
        self.panel.share_here.click()
        requested.assert_called_once_with(VIDEO, 83)

    def test_fullscreen_shares_the_same_video_and_position(self):
        self.panel.start()
        self.panel.player.telemetry.emit(DATA)
        self.panel.open_popup()
        requested = Mock()
        self.panel.share_requested.connect(requested)
        self.assertTrue(self.panel.popup.share_here.isEnabled())
        self.panel.popup.share_here.click()
        requested.assert_called_once_with(VIDEO, 83)
        self.panel.set_share_busy(True)
        self.panel.player.telemetry.emit(DATA)
        self.assertFalse(self.panel.share_here.isEnabled())
        self.assertFalse(self.panel.popup.share_here.isEnabled())

    def test_stop_switch_and_unavailable_disable_time_sharing(self):
        self.panel.start()
        self.panel.player.telemetry.emit(DATA)
        self.panel.player.available.emit(False)
        self.assertFalse(self.panel.can_share_position())
        self.panel.select_video(OTHER)
        self.assertFalse(self.panel.can_share_position())
        self.panel.start()
        self.panel.player.telemetry.emit(dict(DATA, position=0))
        requested = Mock()
        self.panel.share_requested.connect(requested)
        self.panel.share_here.click()
        requested.assert_called_once_with(OTHER, 0)
        self.panel.stop()
        self.assertFalse(self.panel.can_share_position())
        self.assertTrue(self.panel.share_here.isEnabled())
        self.panel.select_video("")
        self.assertFalse(self.panel.share_here.isEnabled())


class ChannelSharingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        with patch.object(channel, "EmbeddedYouTubePlayer", FakeYouTubePlayer):
            fixture.ResponsiveLayoutTests.setUp(self)
        thumbnail_patch = patch.object(self.window, "fetch_thumbnail")
        thumbnail_patch.start()
        self.addCleanup(thumbnail_patch.stop)
        videos = [{"id": VIDEO, "title": "Mi clip", "privacy": "private", "duration": "3:00"},
                  {"id": OTHER, "title": "Otro clip", "privacy": "public", "duration": "3:00"}]
        with patch.object(self.window, "fetch_thumbnail"):
            self.window.apply_channel_rows(videos, [])
            while self.window.channel_render_pending:
                self.window.append_channel_render_batch()
        self.window.channel_table.selectRow(0)
        self.app.clipboard().setText("sin cambios")

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        set_language("es")

    def test_confirmation_captures_video_and_instant_before_background_work(self):
        dialog = Mock()
        dialog.exec.return_value = ui.QMessageBox.StandardButton.Yes
        dialog.checkBox.return_value.isChecked.return_value = True
        with patch.object(self.window, "share_confirmation", return_value=dialog) as confirm, \
                patch.object(ui.threading, "Thread") as thread:
            self.window.share_channel_video_at_position(VIDEO, 83)
            self.assertEqual(confirm.call_args.args[1], 83)
            args = thread.call_args.kwargs["args"]
            self.assertEqual((args[0]["id"], args[1]), (VIDEO, 83))
            self.assertTrue(self.window.channel_playback.share_busy)
            self.window.channel_table.selectRow(1)
            self.window.share_channel_video_at_position(OTHER, 12)
            thread.assert_called_once()
        self.assertEqual(self.app.clipboard().text(), "sin cambios")

    def test_declining_does_not_start_work_or_change_clipboard(self):
        dialog = Mock()
        dialog.exec.return_value = ui.QMessageBox.StandardButton.No
        with patch.object(self.window, "share_confirmation", return_value=dialog), \
                patch.object(ui.threading, "Thread") as thread:
            self.window.share_channel_video_at_position(VIDEO, 83)
        thread.assert_not_called()
        self.assertFalse(self.window.channel_playback.share_busy)
        self.assertEqual(self.app.clipboard().text(), "sin cambios")

    def test_existing_share_button_still_shares_from_the_beginning(self):
        dialog = Mock()
        dialog.exec.return_value = ui.QMessageBox.StandardButton.Yes
        with patch.object(self.window, "share_confirmation", return_value=dialog), \
                patch.object(ui.threading, "Thread") as thread:
            self.window.share_selected_channel_video()
        self.assertIsNone(thread.call_args.kwargs["args"][1])

    def test_success_sets_unlisted_before_copying_timestamp_link_without_stopping(self):
        player = self.window.channel_playback
        player.start()
        player.player.telemetry.emit(DATA)
        player.open_popup()
        popup = player.popup
        player.set_share_busy(True)
        with patch.object(ui.engine, "YouTubeClient") as client:
            self.window._share_channel_video_thread(dict(self.window.channel_videos[0]), 83)
            client.return_value.set_video_unlisted.assert_called_once_with(VIDEO)
            self.assertEqual(self.app.clipboard().text(), "sin cambios")
            self.window.process_events()
        self.assertEqual(self.app.clipboard().text(), f"https://youtu.be/{VIDEO}?t=83")
        self.assertEqual(self.window.channel_videos[0]["privacy"], "unlisted")
        self.assertIs(player.popup, popup)
        self.assertEqual(player.player.video_id, VIDEO)
        self.assertIn("1:23", popup.notice.text())
        self.assertFalse(player.share_busy)
        self.assertEqual(self.window.channel_overview.counts["unlisted"].text(), "1")

    def test_failure_keeps_clipboard_and_privacy_and_allows_retry(self):
        self.window.channel_playback.set_share_busy(True)
        with patch.object(ui.engine, "YouTubeClient") as client, patch.object(self.window, "report_problem"):
            client.return_value.set_video_unlisted.side_effect = RuntimeError("quotaExceeded")
            self.window._share_channel_video_thread(dict(self.window.channel_videos[0]), 83)
            self.window.process_events()
        self.assertEqual(self.app.clipboard().text(), "sin cambios")
        self.assertEqual(self.window.channel_videos[0]["privacy"], "private")
        self.assertFalse(self.window.channel_playback.share_busy)

    def test_standard_sharing_copies_a_plain_link_and_time_zero_is_explicit(self):
        for seconds, suffix in ((None, ""), (0, "?t=0")):
            with self.subTest(seconds=seconds), patch.object(ui.engine, "YouTubeClient"):
                self.window._share_channel_video_thread(dict(self.window.channel_videos[0]), seconds)
                self.window.process_events()
                self.assertEqual(self.app.clipboard().text(), f"https://youtu.be/{VIDEO}{suffix}")

    def test_invalid_time_or_unknown_video_never_asks_to_change_privacy(self):
        with patch.object(self.window, "share_confirmation") as confirm:
            for seconds in (-1, True, 3.2, 31 * 86400 + 1):
                self.window.share_channel_video_at_position(VIDEO, seconds)
            self.window.share_channel_video_at_position("unknown", 83)
        confirm.assert_not_called()

    def test_start_at_is_optional_and_unchecked_by_default(self):
        dialog = self.window.share_confirmation({"title": "Mi clip"}, 83)
        self.assertFalse(dialog.checkBox().isChecked())
        self.assertIn("1:23", dialog.checkBox().text())
        dialog.deleteLater()
        fake = Mock()
        fake.exec.return_value = ui.QMessageBox.StandardButton.Yes
        fake.checkBox.return_value.isChecked.return_value = False
        with patch.object(self.window, "share_confirmation", return_value=fake), patch.object(ui.threading, "Thread") as thread:
            self.window.share_channel_video_at_position(VIDEO, 83)
        self.assertIsNone(thread.call_args.kwargs["args"][1])

    def test_english_timestamp_feedback(self):
        set_language("en")
        self.assertEqual(t("Desde 1:23"), "From 1:23")
        self.assertEqual(t("Enlace copiado desde 1:23 / vídeo en Oculto"),
                         "Link copied from 1:23 / video set to Unlisted")
