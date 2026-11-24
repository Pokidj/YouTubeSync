import json
import unittest
from unittest.mock import Mock, patch

import test_layout as fixture
from PySide6.QtCore import QProcess, QUrl, Qt
from PySide6.QtTest import QTest
from youtube_sync_youtube_player import (APP_ID, EVENT_PREFIX, PLAYER_ORIGIN, EmbeddedYouTubePlayer,
                                        playback_error, player_html)
from youtube_sync_youtube_webview import PlayerIdentity, PlayerPage
from youtube_sync_manual_ui import ManualConfirmationDialog
from fake_youtube_player import FakeYouTubePlayer


class PlayerProtocolTests(unittest.TestCase):
    def test_official_embed_uses_the_same_app_identity_and_no_credentials(self):
        html = player_html("aB3_dE6-fG9")
        self.assertIn("https://www.youtube.com/iframe_api", html)
        self.assertIn('"controls": 1', html)
        self.assertIn(PLAYER_ORIGIN, html)
        self.assertEqual(PLAYER_ORIGIN, "https://" + APP_ID.lower())
        self.assertIn("strict-origin-when-cross-origin", html)
        self.assertNotIn("access_token", html)
        self.assertNotIn("password", html)
        for invalid in ("<script>alert(1)</script>", "not-an-id", "https://evil.test/watch?v=aB3_dE6-fG9"):
            with self.assertRaises(ValueError):
                player_html(invalid)

    def test_referer_identifies_our_app_only_on_youtube_player_requests(self):
        for url, expected in (("https://www.youtube.com/embed/aB3_dE6-fG9", True),
                              ("https://www.youtube.com/iframe_api", True),
                              ("https://www.youtube.com.evil.test/embed/aB3_dE6-fG9", False),
                              ("https://www.googlevideo.com/videoplayback", False)):
            request = Mock()
            request.requestUrl.return_value = QUrl(url)
            PlayerIdentity.interceptRequest(Mock(), request)
            self.assertEqual(request.setHttpHeader.call_count, int(expected))
            if expected:
                request.setHttpHeader.assert_called_with(b"Referer", (PLAYER_ORIGIN + "/").encode("ascii"))

    def test_console_messages_are_validated_and_never_execute_native_commands(self):
        page = Mock()
        for message in ("Other message", EVENT_PREFIX + "invalid", EVENT_PREFIX + json.dumps({"id": "bad", "type": "state", "value": 1}),
                        EVENT_PREFIX + json.dumps({"id": "aB3_dE6-fG9", "type": "native_command", "value": 1})):
            PlayerPage.javaScriptConsoleMessage(page, None, message, 1, "")
        page.event.emit.assert_not_called()
        PlayerPage.javaScriptConsoleMessage(page, None, EVENT_PREFIX + json.dumps({"id": "aB3_dE6-fG9", "type": "state", "value": 1}), 1, "")
        page.event.emit.assert_called_once_with("aB3_dE6-fG9", "state", 1)

    def test_top_level_navigation_cannot_turn_player_into_a_google_login(self):
        for url, allowed in ((PLAYER_ORIGIN + "/", True), ("about:blank", True),
                             ("https://accounts.google.com", False), ("file:///C:/private", False)):
            self.assertEqual(PlayerPage.acceptNavigationRequest(Mock(), QUrl(url), None, True), allowed)

    def test_restrictions_are_described_without_pretending_oauth_unblocks_playback(self):
        self.assertIn("privado", playback_error(100))
        self.assertIn("propietario", playback_error(101))
        self.assertIn("153", playback_error(153))


class EmbeddedLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        self.player = EmbeddedYouTubePlayer()
        self.player.prefer_native = False
        self.addCleanup(self.player.release)
        self.addCleanup(self.player.close)

    def test_preflight_failure_is_confined_to_child_process_and_never_creates_webview(self):
        with patch("youtube_sync_youtube_player.QProcess") as process, patch.object(self.player, "start_view") as start:
            self.player.load_video("aB3_dE6-fG9")
            probe = self.player.probe
            self.player.probe_failed(probe)
        self.assertIsNone(self.player.view)
        self.assertIsNone(self.player.probe)
        self.assertFalse(self.player.timer.isActive())
        start.assert_not_called()
        self.assertIn("--probe-youtube-engine", process.return_value.start.call_args.args[1])

    def test_successful_preflight_starts_webview_and_ignores_stale_process_results(self):
        with patch("youtube_sync_youtube_player.QProcess") as process, patch.object(self.player, "start_view") as start:
            process.NormalExit = QProcess.NormalExit
            self.player.load_video("aB3_dE6-fG9")
            probe = self.player.probe
            self.player.probe_finished(Mock(), 0, QProcess.NormalExit)
            start.assert_not_called()
            self.player.probe_finished(probe, 0, QProcess.NormalExit)
        start.assert_called_once()

    def test_ready_is_not_proof_that_playback_started_and_wrong_id_events_are_ignored(self):
        self.player.view = Mock()
        self.player.video_id = "aB3_dE6-fG9"
        played = Mock()
        self.player.reviewed.connect(played)
        self.player.player_event("zY8_xW5-vU2", "state", 1)
        self.player.player_event("aB3_dE6-fG9", "ready", 0)
        played.assert_not_called()
        self.player.player_event("aB3_dE6-fG9", "state", 1)
        played.assert_called_once_with("aB3_dE6-fG9")
        self.player.view = None

    def test_close_cancels_only_our_probe_and_mutes_and_removes_the_web_page(self):
        probe, view, profile = Mock(), Mock(), Mock()
        self.player.probe, self.player.view = probe, view
        self.player.profile = profile
        with patch.object(self.player.layout, "removeWidget"):
            self.player.release()
        probe.kill.assert_called_once()
        view.page.return_value.setAudioMuted.assert_called_once_with(True)
        view.setUrl.assert_called_once_with(QUrl("about:blank"))
        view.deleteLater.assert_called_once()
        view.page.return_value.deleteLater.assert_called_once()
        profile.deleteLater.assert_called_once()
        self.assertIsNone(self.player.probe)
        self.assertIsNone(self.player.view)

    def test_a_stale_renderer_failure_cannot_interrupt_a_new_candidate(self):
        self.player.view = Mock()
        with patch.object(self.player, "timed_out") as failed:
            self.player.renderer_failed(Mock())
            failed.assert_not_called()
            self.player.renderer_failed(self.player.view)
            failed.assert_called_once()
        self.player.view = None


class GuidedYouTubeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        player = patch("youtube_sync_manual_ui.EmbeddedYouTubePlayer", FakeYouTubePlayer)
        player.start()
        self.addCleanup(player.stop)
        self.dialog = ManualConfirmationDialog({"path": str(fixture.ROOT / "tests/fixtures/local-preview.mp4"), "youtube_id": "aB3_dE6-fG9"}, autoplay=False)
        self.dialog.remote_preview.auto_review = False
        self.addCleanup(self.dialog.close)

    def test_next_embeds_video_without_opening_external_browser_or_unlocking_early(self):
        with patch("youtube_sync_manual_ui.webbrowser.open") as browser:
            self.dialog.advance()
        browser.assert_not_called()
        self.assertEqual(self.dialog.remote_preview.video_id, "aB3_dE6-fG9")
        self.assertFalse(self.dialog.next.isEnabled())
        self.dialog.remote_preview.reviewed.emit("aB3_dE6-fG9")
        self.assertTrue(self.dialog.next.isEnabled())
        self.dialog.advance()
        self.assertEqual(self.dialog.remote_preview.video_id, "")
        self.assertEqual(self.dialog.pages.currentIndex(), 2)

    def test_editing_link_invalidates_review_and_stops_the_previous_candidate(self):
        self.dialog.advance()
        self.dialog.remote_preview.reviewed.emit("aB3_dE6-fG9")
        self.dialog.link.setText("zY8_xW5-vU2")
        self.assertFalse(self.dialog.next.isEnabled())
        self.assertEqual(self.dialog.remote_preview.video_id, "")
        self.dialog.remote_preview.reviewed.emit("aB3_dE6-fG9")
        self.assertFalse(self.dialog.next.isEnabled())

    def test_error_keeps_manual_decision_locked_but_browser_fallback_can_be_reviewed(self):
        self.dialog.advance()
        self.dialog.remote_preview.failed.emit("Vídeo privado")
        self.assertFalse(self.dialog.next.isEnabled())
        with patch("youtube_sync_manual_ui.webbrowser.open", return_value=True) as browser:
            self.dialog.open_remote()
        browser.assert_called_once_with("https://www.youtube.com/watch?v=aB3_dE6-fG9")
        self.assertTrue(self.dialog.next.isEnabled())
        self.assertEqual(self.dialog.remote_preview.video_id, "")

    def test_enter_in_candidate_field_does_not_close_the_comparison(self):
        self.dialog.show()
        self.dialog.advance()
        self.dialog.link.setFocus()
        QTest.keyClick(self.dialog.link, Qt.Key_Return)
        self.assertFalse(self.dialog._closed)
        self.assertEqual(self.dialog.remote_preview.video_id, "aB3_dE6-fG9")
