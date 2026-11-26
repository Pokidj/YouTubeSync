import unittest
import time
from unittest.mock import Mock, patch

from PySide6.QtTest import QTest
from shiboken6 import isValid

import test_layout as fixture
import test_local_preview as local_fixture
import test_channel_ui as channel_fixture
from test_layout import ui
import youtube_sync_local_player as local_player


class LocalPlayerWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    setUp = fixture.ResponsiveLayoutTests.setUp
    tearDown = fixture.ResponsiveLayoutTests.tearDown
    settle = fixture.ResponsiveLayoutTests.settle
    select_file = local_fixture.LocalPreviewTests.select_fixture
    select_channel = fixture.ResponsiveLayoutTests.select_preview_video

    def test_pending_file_has_no_guided_check_even_if_supplied_by_an_old_notice(self):
        item = self.select_file()
        preview = self.window.local_preview
        self.assertTrue(preview.verify.isHidden())
        self.assertNotIn("manual_verify", [action for _label, action in self.window.active_guidance.actions])
        preview.set_actions(item, (("Comparar", "manual_verify"),))
        requested = Mock()
        preview.action_requested.connect(requested)
        preview.verify.click()
        self.assertTrue(preview.verify.isHidden())
        requested.assert_not_called()
        self.window.video_rows[0].update(status="Por verificar", youtube_id="candidate-video")
        self.window.video_table.item(0, 4).setText("Por verificar")
        self.window.video_selection_changed()
        self.assertFalse(preview.verify.isHidden())

    def test_local_fullscreen_moves_same_player_and_escape_preserves_position(self):
        self.select_file()
        player = self.window.local_preview.player
        player.audio.setMuted(True)
        self.settle()
        player.play_file()
        QTest.qWait(250)
        player.pause()
        player.player.setPosition(500)
        source = player.player.source()
        media = player.player
        with patch.object(local_player, "mark_fullscreen") as mark:
            player.fullscreen_button.click()
            self.app.processEvents()
            popup = player.popup
            escape_timer = popup.escape_poll
            hwnd = int(popup.winId())
            self.assertTrue(popup.isFullScreen())
            self.assertIs(player.player, media)
            self.assertIs(player.parentWidget(), self.window.local_preview)
            self.assertIs(popup.view.player, media)
            self.assertIs(player.player.videoOutput(), popup.view.video)
            popup.view.volume.setValue(35)
            self.assertAlmostEqual(player.audio.volume(), .35, places=2)
            self.assertEqual(player.volume.value(), 35)
            self.assertEqual(player.player.source(), source)
            mark.assert_called_with(hwnd, True)
            for control in (popup.view.play_button, popup.view.seek, popup.view.volume, popup.view.fullscreen_button):
                self.assertTrue(popup.rect().contains(control.mapTo(popup, control.rect().bottomRight())))
            self.assertTrue(popup.windowFlags() & ui.Qt.FramelessWindowHint)
            QTest.keyClick(popup, ui.Qt.Key_Escape)
            self.app.processEvents()
            self.assertIsNone(player.popup)
            self.assertTrue(not isValid(popup) or not popup.isVisible())
            self.assertTrue(not isValid(escape_timer) or not escape_timer.isActive())
            self.assertIs(player.parentWidget(), self.window.local_preview)
            self.assertEqual(player.player.source(), source)
            self.assertEqual(player.player.position(), 500)
            self.assertIs(player.player.videoOutput(), player.video)
            mark.assert_called_with(hwnd, False)
        self.settle()

    def test_closing_fullscreen_or_clearing_selection_releases_the_local_file(self):
        self.select_file()
        player = self.window.local_preview.player
        player.audio.setMuted(True)
        for clear_selection in (False, True):
            player.fullscreen_button.click()
            self.app.processEvents()
            popup = player.popup
            self.assertIsNotNone(popup)
            if clear_selection:
                self.window.video_table.clearSelection()
            else:
                popup.close()
            self.app.processEvents()
            self.assertIsNone(player.popup)
            self.assertTrue(player.player.source().isEmpty())
            self.assertTrue(not isValid(popup) or not popup.isVisible())

    def test_fullscreen_receives_decoded_frames_and_returns_to_the_inline_output(self):
        self.select_file()
        player = self.window.local_preview.player
        player.audio.setMuted(True)
        player.fullscreen_button.click()
        popup = player.popup
        frames = []

        def received(frame):
            if frame.isValid():
                image = frame.toImage()
                if not image.isNull():
                    frames.append(any(image.pixelColor(image.width() * x // 4, image.height() * y // 4).value() > 10
                                      for x in (1, 2, 3) for y in (1, 2, 3)))

        popup.view.video.videoSink().videoFrameChanged.connect(received)
        deadline = time.monotonic() + 4
        while not any(frames) and time.monotonic() < deadline:
            self.app.processEvents()
            QTest.qWait(20)
        self.assertTrue(any(frames), "Fullscreen must receive nonblank decoded video frames")
        source = player.player.source()
        popup.view.fullscreen_button.click()
        self.assertIsNone(player.popup)
        self.assertIs(player.player.videoOutput(), player.video)
        self.assertEqual(player.player.source(), source)

    def test_minimum_window_keeps_youtube_play_in_view_before_loading(self):
        self.select_channel()
        self.window.resize(940, 620)
        self.settle()
        self.window.reveal_channel_controls()
        self.app.processEvents()
        controls = self.window.channel_playback.transport
        viewport = self.window.channel_preview_scroll.viewport()
        self.assertFalse(controls.isHidden())
        self.assertTrue(controls.toggle.isEnabled())
        self.assertTrue(viewport.rect().contains(controls.toggle.mapTo(viewport, controls.toggle.rect().bottomRight())))
        self.assertTrue(viewport.rect().contains(controls.fullscreen.mapTo(viewport, controls.fullscreen.rect().bottomRight())))
        self.assertFalse(hasattr(self.window.channel_playback, "play"))


class YouTubePlayWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    setUp = channel_fixture.ChannelPlayerTests.setUp
    tearDown = channel_fixture.ChannelPlayerTests.tearDown

    def test_selected_video_keeps_transport_visible_and_starts_only_from_play(self):
        controls = self.panel.transport
        self.assertFalse(controls.isHidden())
        self.assertTrue(controls.toggle.isEnabled())
        self.assertFalse(controls.seek.isEnabled())
        self.assertFalse(self.panel.player.video_id)
        self.assertIs(self.panel.popout, controls.fullscreen)
        controls.toggle.click()
        self.assertEqual(self.panel.player.video_id, channel_fixture.VIDEO)
        self.assertFalse(controls.isHidden())
        self.assertFalse(controls.toggle.isEnabled())
        self.panel.player.telemetry.emit({"position": 5, "duration": 100, "volume": 50, "playing": True, "muted": False})
        self.assertTrue(controls.toggle.isEnabled())
        controls.toggle.click()
        self.assertEqual(self.panel.player.commands[-1], ("pause", None))
        self.panel.stop()
        self.assertFalse(controls.isHidden())
        self.assertTrue(controls.toggle.isEnabled())
        self.assertFalse(controls.seek.isEnabled())

    def test_unavailable_transport_cannot_seek_or_share_a_stale_time(self):
        self.panel.transport.toggle.click()
        controls = self.panel.transport
        self.panel.player.telemetry.emit({"position": 5, "duration": 100, "volume": 50, "playing": True, "muted": False})
        self.panel.player.available.emit(False)
        self.assertFalse(controls.ready)
        self.assertFalse(controls.toggle.isEnabled())
        self.assertFalse(self.panel.can_share_position())
        self.assertFalse(controls.isHidden())


if __name__ == "__main__":
    unittest.main()
