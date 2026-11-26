import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_layout as fixture
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from fake_youtube_player import FakeYouTubePlayer
import youtube_sync_channel_ui as channel
from youtube_sync_i18n import set_language

ui = fixture.ui
VIDEO = "aB3_cD6-eF9"
OTHER = "zY8_xW5-vU2"


class ChannelOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)
        set_language("es")

    def load(self):
        videos = [{"id": VIDEO, "title": "Clip uno", "privacy": "public"},
                  {"id": OTHER, "title": "Clip dos", "privacy": "private"},
                  {"id": "third-video", "title": "Otro clip", "privacy": "unlisted"}]
        with patch.object(self.window, "fetch_thumbnail"):
            self.window.apply_channel_rows(videos, [])
            while self.window.channel_render_pending:
                self.window.append_channel_render_batch()
        return videos

    def test_video_context_is_only_visible_on_videos(self):
        self.assertTrue(self.window.video_context.isHidden())
        self.window.tabs.setCurrentIndex(0)
        self.assertFalse(self.window.video_context.isHidden())
        self.window.channel_loaded = True
        self.window.tabs.setCurrentIndex(1)
        self.assertTrue(self.window.video_context.isHidden())

    def test_totals_use_whole_channel_not_search_results(self):
        self.load()
        self.window.channel_search.setText("uno")
        counts = self.window.channel_overview.counts
        self.assertEqual([counts[key].text() for key in ("total", "public", "private", "unlisted")], ["3", "1", "1", "1"])
        self.assertEqual(len(self.window.channel_render_pending), 1)

    def test_old_cache_references_are_separate_from_the_visible_total(self):
        rows = self.load() + [{"id": "missing", "title": "Sin titulo", "privacy": "desconocido"}]
        with patch.object(self.window, "fetch_thumbnail"):
            self.window.apply_channel_rows(rows, [])
        self.assertEqual(len(self.window.channel_videos), 3)
        self.assertEqual(self.window.channel_overview.counts["total"].text(), "3")
        self.assertIn("1 referencias no disponibles", self.window.channel_overview.note.text())

    def test_access_action_opens_playback_settings_and_clears_old_search(self):
        self.window.open_settings()
        self.window.settings_dialog.settings_search.setText("limpieza")
        self.window.channel_playback.settings_requested.emit()
        dialog = self.window.settings_dialog
        self.assertEqual(dialog.settings_search.text(), "")
        self.assertIs(dialog.settings_tabs.currentWidget(), dialog.playback_settings_page)
        dialog.close()

    def test_unknown_visibility_is_not_claimed_to_be_private(self):
        self.window.channel_overview.set_videos([{"id": VIDEO, "privacy": "unknown"}, {"id": VIDEO, "privacy": "unknown"}])
        self.assertEqual(self.window.channel_overview.counts["total"].text(), "1")
        self.assertEqual(self.window.channel_overview.counts["private"].text(), "0")
        self.assertIn("sin clasificar", self.window.channel_overview.note.text())

    def test_not_loaded_and_loaded_empty_are_different(self):
        self.assertEqual(self.window.channel_overview.counts["total"].text(), "—")
        self.window.apply_channel_rows([], [])
        self.assertEqual(self.window.channel_overview.counts["total"].text(), "0")
        with patch.object(self.window, "refresh_channel") as refresh:
            self.window.tab_changed(1)
        refresh.assert_not_called()

    def test_avatar_download_reuses_background_thumbnail_pool_and_ignores_stale_channel(self):
        profile = {"id": "channel-one", "title": "Nombre real", "thumbnail": "https://example.test/avatar"}
        with patch.object(self.window, "fetch_thumbnail") as fetch:
            self.window.apply_channel_profile(profile)
        fetch.assert_called_once_with({"id": "channel:channel-one", "thumbnail": profile["thumbnail"]})
        image = (fixture.ROOT / "assets/youtube-sync-logo.png").read_bytes()
        self.window.apply_thumbnail("channel:other-channel", image)
        self.assertTrue(self.window.channel_overview.avatar.source.isNull())
        self.window.apply_thumbnail("channel:channel-one", image)
        self.assertFalse(self.window.channel_overview.avatar.source.isNull())
        self.assertEqual(self.window.channel_overview.name.text(), "Nombre real")

    def test_mutations_update_counts_and_cache_note_survives_row_batches(self):
        videos = self.load()
        self.window.channel_cache_loaded("2026-11-24T09:00:00+01:00")
        self.window.append_channel_render_batch()
        self.assertIn("Copia guardada", self.window.channel_overview.note.text())
        videos[0]["privacy"] = "private"
        self.window.filter_channel_table()
        self.assertEqual(self.window.channel_overview.counts["private"].text(), "2")

    def test_header_reflows_and_has_no_horizontal_overflow(self):
        for size in ((940, 620), (1280, 780), (1920, 1080)):
            self.window.resize(*size)
            self.settle()
            overview = self.window.channel_overview
            for widget in (overview.identity, overview.stats, overview.note):
                self.assertTrue(overview.rect().contains(widget.geometry()), (size, widget.geometry()))
            self.assertGreaterEqual(self.window.channel_table.height(), 150)

    settle = fixture.ResponsiveLayoutTests.settle

    def test_english_summary_keeps_user_channel_name_untouched(self):
        set_language("en")
        self.window.apply_channel_profile({"id": "channel", "title": "Privados"})
        self.window.channel_overview.set_videos([], "24/11 09:00", True)
        self.assertEqual(self.window.channel_overview.name.text(), "Privados")
        self.assertIn("Saved snapshot", self.window.channel_overview.note.text())

    def test_loader_reuses_profile_without_an_additional_channel_call(self):
        client = Mock(_channel_info={"id": "channel", "title": "Nombre"}, gallery_unavailable_ids=[])
        client.channel_gallery.return_value = ([], [])
        loader = ui.ChannelLoader(self.window.store, self.window.config)
        received = []
        loader.profile_ready.connect(received.append)
        with patch.object(ui.engine, "YouTubeClient", return_value=client):
            loader.run()
        self.assertEqual(received, [dict(client._channel_info, unavailable_count=0)])
        client.channel_info.assert_not_called()

    def test_quota_does_not_display_a_different_channels_snapshot(self):
        self.window.config.connected_channel_id = "new-channel"
        self.window.store.service_cache.return_value = {"checked_at": "2026-11-24T09:00:00+01:00",
                                                       "data": {"channel": {"id": "old-channel"}, "videos": [], "playlists": []}}
        client = Mock()
        client.channel_gallery.side_effect = RuntimeError("quotaExceeded")
        loader = ui.ChannelLoader(self.window.store, self.window.config)
        ready, failed = Mock(), Mock()
        loader.finished.connect(ready)
        loader.failed.connect(failed)
        with patch.object(ui.engine, "YouTubeClient", return_value=client), patch.object(ui.engine, "is_youtube_quota_error", return_value=True):
            loader.run()
        ready.assert_not_called()
        failed.assert_called_once()


class ChannelPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        with patch.object(channel, "EmbeddedYouTubePlayer", FakeYouTubePlayer):
            self.panel = channel.ChannelPlayback(ui.PreviewThumbnail(), Path(self.folder.name))
        self.panel.resize(350, 300)
        self.panel.show()
        self.panel.select_video(VIDEO)
        self.app.processEvents()

    def tearDown(self):
        self.panel.stop()
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_play_is_explicit_and_selection_changes_stop_the_previous_video(self):
        self.assertFalse(self.panel.player.video_id)
        self.panel.start()
        self.assertIsNone(self.panel.popup)
        self.assertEqual(self.panel.player.video_id, VIDEO)
        self.panel.select_video(OTHER)
        self.assertFalse(self.panel.player.video_id)
        self.assertEqual(self.panel.video_id, OTHER)
        self.assertIs(self.panel.media.currentWidget(), self.panel.thumbnail)

    def test_popup_moves_same_player_and_docking_does_not_reload(self):
        self.panel.start()
        player = self.panel.player
        with patch.object(player, "load_video", wraps=player.load_video) as load:
            self.panel.open_popup()
            self.assertIs(self.panel.player, player)
            self.assertIs(player.parentWidget(), self.panel.popup)
            self.panel.return_inline()
        load.assert_not_called()
        self.assertEqual(player.video_id, VIDEO)
        self.assertIs(self.panel.media.currentWidget(), player)
        self.assertIsNone(self.panel.popup)

    def test_closing_popup_stops_video_and_restores_thumbnail(self):
        self.panel.open_popup()
        self.panel.popup.close()
        self.assertIsNone(self.panel.popup)
        self.assertFalse(self.panel.player.video_id)
        self.assertIs(self.panel.media.currentWidget(), self.panel.thumbnail)

    def test_escape_returns_directly_to_panel_without_a_small_window(self):
        self.panel.open_popup()
        popup = self.panel.popup
        self.assertTrue(popup.isFullScreen())
        QTest.keyClick(popup, Qt.Key_Escape)
        self.assertIsNone(self.panel.popup)
        self.assertFalse(popup.isVisible())
        self.assertFalse(popup.escape_poll.isActive())
        self.assertEqual(self.panel.player.video_id, VIDEO)
        self.assertIs(self.panel.media.currentWidget(), self.panel.player)

    def test_hiding_panel_closes_popup_and_releases_audio(self):
        self.panel.open_popup()
        self.panel.hide()
        self.assertIsNone(self.panel.popup)
        self.assertFalse(self.panel.player.video_id)

    def test_open_external_uses_selected_video_without_changing_privacy(self):
        with patch.object(channel.webbrowser, "open") as open_browser:
            self.panel.open_external()
        open_browser.assert_called_once_with("https://www.youtube.com/watch?v=" + VIDEO)

    def test_no_selection_disables_all_actions_and_never_launches_browser(self):
        self.panel.select_video("")
        for button in (self.panel.transport.toggle, self.panel.popout, self.panel.browser, self.panel.stop_button):
            self.assertFalse(button.isEnabled())
        with patch.object(channel.webbrowser, "open") as open_browser:
            self.panel.start()
            self.panel.open_popup()
            self.panel.open_external()
        open_browser.assert_not_called()
        self.assertIsNone(self.panel.popup)

    def test_load_failure_keeps_thumbnail_and_retry_available(self):
        with patch.object(self.panel.player, "load_video", side_effect=OSError("Sin navegador")):
            self.panel.start()
        self.assertIn("Sin navegador", self.panel.status.text())
        self.assertFalse(self.panel.active_id)
        self.assertIs(self.panel.media.currentWidget(), self.panel.thumbnail)
        self.assertTrue(self.panel.transport.toggle.isEnabled())

    def test_async_failure_closes_popup_and_shows_a_visible_retry_message(self):
        self.panel.open_popup()
        self.panel.player.failed.emit("Revisa la sesión")
        self.assertIsNone(self.panel.popup)
        self.assertFalse(self.panel.active_id)
        self.assertIs(self.panel.media.currentWidget(), self.panel.thumbnail)
        self.assertEqual(self.panel.status.text(), "Revisa la sesión")
        self.assertTrue(self.panel.status.isVisible())

    def test_private_videos_use_the_same_session_in_first_party_context(self):
        self.panel.select_video(VIDEO, "private")
        self.assertTrue(self.panel.player.first_party)
        self.assertTrue(self.panel.access_settings.isHidden())
        self.assertFalse(hasattr(self.panel, "session"))
        self.panel.start()
        self.panel.select_video(VIDEO, "unlisted")
        self.assertFalse(self.panel.player.first_party)
        self.assertTrue(self.panel.access_settings.isHidden())
        self.assertFalse(self.panel.player.video_id)

    def test_explicit_monitor_button_opens_fullscreen_with_usable_controls(self):
        self.panel.start()
        self.panel.player.telemetry.emit({"position": 20, "duration": 100, "volume": 65, "playing": True, "muted": False})
        self.assertIsNone(self.panel.popup)
        self.panel.popout.click()
        self.app.processEvents()
        popup = self.panel.popup
        self.assertTrue(popup.isFullScreen())
        self.assertTrue(popup.transport.isVisible())
        self.assertTrue(popup.transport.isEnabled())
        self.assertTrue(popup.rect().contains(popup.transport.geometry()))
        popup.toggle_fullscreen()
        self.assertIsNone(self.panel.popup)
        self.assertFalse(popup.isVisible())
        self.panel.start()
        self.assertIsNone(self.panel.popup)
        self.panel.popout.click()
        self.assertTrue(self.panel.popup.isFullScreen())

    def test_fullscreen_notifies_windows_and_uses_whole_screen_not_work_area(self):
        with patch.object(channel, "mark_fullscreen") as mark:
            self.panel.open_popup()
            popup = self.panel.popup
            hwnd = int(popup.winId())
            self.assertTrue(popup.windowFlags() & Qt.FramelessWindowHint)
            self.assertEqual(popup.geometry(), self.panel.screen().geometry())
            mark.assert_called_with(hwnd, True)
            self.panel.return_inline()
            mark.assert_called_with(hwnd, False)

    def test_escape_in_hosted_browser_returns_to_panel_and_stops_polling(self):
        self.panel.open_popup()
        popup = self.panel.popup
        with patch.object(channel, "escape_pressed", return_value=True):
            popup.check_native_escape()
        self.assertIsNone(self.panel.popup)
        self.assertFalse(popup.isVisible())
        self.assertFalse(popup.escape_poll.isActive())
        self.assertEqual(self.panel.player.video_id, VIDEO)

    def test_private_failure_offers_settings_without_opening_a_login_browser(self):
        self.panel.select_video(VIDEO, "private")
        self.panel.start()
        requested = Mock()
        self.panel.settings_requested.connect(requested)
        self.panel.player.failed.emit("YouTube no da acceso a este vídeo")
        self.assertFalse(self.panel.access_settings.isHidden())
        self.panel.access_settings.click()
        requested.assert_called_once()

    def test_sidebar_and_popup_transport_control_one_live_player(self):
        data = {"position": 20, "duration": 100, "volume": 65, "playing": True, "muted": False}
        self.panel.start()
        self.panel.player.telemetry.emit(data)
        self.panel.open_popup()
        popup = self.panel.popup
        self.assertEqual(popup.transport.last_data, data)
        popup.transport.forward.click()
        self.assertEqual(self.panel.player.commands[-1], ("relative", 10))
        self.panel.return_inline()
        self.assertEqual(self.panel.transport.last_data, data)
        self.assertEqual(self.panel.player.video_id, VIDEO)
