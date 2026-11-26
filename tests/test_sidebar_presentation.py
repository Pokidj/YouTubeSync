import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QFrame
from PySide6.QtGui import QPalette

import test_layout as fixture
import test_local_preview as local_fixture
from test_layout import ui
from youtube_sync_icons import BUTTON_TONES
from youtube_sync_preview_ui import PreviewInfoPill
from youtube_sync_transport_ui import TransportControls
from fake_youtube_player import FakeYouTubePlayer


class SidebarPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    setUp = fixture.ResponsiveLayoutTests.setUp
    tearDown = fixture.ResponsiveLayoutTests.tearDown
    settle = fixture.ResponsiveLayoutTests.settle
    select_file = local_fixture.LocalPreviewTests.select_fixture
    select_preview_video = fixture.ResponsiveLayoutTests.select_preview_video

    def test_both_footers_are_inside_one_framed_panel_and_outside_scrolling(self):
        self.select_file()
        self.select_preview_video()
        for host, scroll, commands in (
                (self.window.local_preview_host, self.window.local_preview_scroll, self.window.local_preview.actions_widget),
                (self.window.channel_preview_host, self.window.channel_preview_scroll, self.window.channel_playback.controls_widget)):
            self.assertIsInstance(host, QFrame)
            self.assertEqual(host.objectName(), "PreviewPanel")
            self.assertEqual(scroll.widget().objectName(), "PreviewContent")
            self.assertTrue(host.isAncestorOf(commands))
            self.assertFalse(scroll.isAncestorOf(commands))
            self.assertEqual(commands.parentWidget().objectName(), "PreviewFooter")

    def test_local_path_is_selectable_above_the_player_and_data_uses_pills(self):
        item = self.select_file()
        preview = self.window.local_preview
        self.assertEqual(preview.path.text(), item["path"])
        self.assertTrue(preview.path.textInteractionFlags() & ui.Qt.TextSelectableByMouse)
        self.assertLess(preview.layout().indexOf(preview.path), preview.layout().indexOf(preview.player))
        self.assertEqual(set(preview.fields), {"status", "size", "created", "duration"})
        for pill in preview.pills:
            self.assertEqual(pill.objectName(), "InfoPill")
            self.assertFalse(pill.isHidden())
        self.assertEqual(preview.fields["status"][1].text(), "Pendiente")
        self.assertEqual(preview.fields["size"][1].text(), "10 KB")
        self.assertEqual(preview.fields["created"][1].text(), "2026-11-25")

    def test_duration_uses_existing_media_results_without_api_or_autoplay(self):
        item = self.select_file()
        preview = self.window.local_preview
        with patch.object(ui.engine, "YouTubeClient") as client, patch.object(preview.player, "play_file") as play:
            self.window.apply_local_media(item["path"], item["signature"], {"seconds": 61.5, "thumbnail_checked": True})
            self.assertEqual(preview.fields["duration"][1].text(), "1:01")
            self.window.apply_local_media(item["path"], "stale-signature", {"seconds": 300})
            self.assertEqual(preview.fields["duration"][1].text(), "1:01")
            self.window.video_selection_changed()
            self.assertEqual(preview.fields["duration"][1].text(), "1:01")
            preview.select(dict(item, signature="changed"))
            self.assertEqual(preview.fields["duration"][1].text(), "-")
            for invalid in (None, "10", -2, float("nan"), float("inf")):
                preview.set_media({"seconds": invalid})
                self.assertEqual(preview.fields["duration"][1].text(), "-")
            client.assert_not_called()
            play.assert_not_called()

    def test_local_media_duration_updates_after_explicit_playback_and_hides_on_clear(self):
        self.select_file()
        preview = self.window.local_preview
        preview.player.player.durationChanged.emit(83000)
        self.assertEqual(preview.fields["duration"][1].text(), "1:23")
        preview.select(None)
        self.assertTrue(all(pill.isHidden() for pill in preview.pills))
        self.assertTrue(preview.path.isHidden())
        self.assertTrue(preview.actions_widget.isHidden())

    def test_pills_reflow_and_footers_remain_contained_at_minimum_and_wide_sizes(self):
        self.select_file()
        self.select_preview_video()
        for tab, host, scroll, commands in (
                (0, self.window.local_preview_host, self.window.local_preview_scroll, self.window.local_preview.actions_widget),
                (1, self.window.channel_preview_host, self.window.channel_preview_scroll, self.window.channel_playback.controls_widget)):
            self.window.tabs.blockSignals(True)
            self.window.tabs.setCurrentIndex(tab)
            self.window.tabs.blockSignals(False)
            for size in ((940, 620), (1280, 780), (1920, 1080), (940, 620)):
                self.window.resize(*size)
                self.settle()
                self.assertEqual((self.window.width(), self.window.height()), size)
                self.assertTrue(host.rect().contains(commands.mapTo(host, commands.rect().bottomRight())))
                self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
            for widths, two_columns in (([1400, 350], False), ([700, 1050], True)):
                self.window.resize(1920, 1080)
                splitter = self.window.local_splitter if tab == 0 else self.window.channel_splitter
                splitter.setSizes(widths)
                self.settle()
                if tab == 0:
                    self.assertEqual(self.window.local_preview._two_columns, two_columns)
                    for pill in self.window.local_preview.pills:
                        self.assertGreaterEqual(pill.height(), pill.minimumSizeHint().height())

    def test_local_and_youtube_actions_share_functional_tones(self):
        preview = self.window.local_preview
        expected = {"upload_file": "success", "manual_verify": "success", "retry_video": "warning",
                    "review_video": "warning", "locate_file": "info", "check_video": "info",
                    "open_video": "info", "delete_local": "danger"}
        for name, tone in expected.items():
            self.assertEqual(preview.buttons[name].property("actionTone"), tone)
        for button, tone in ((self.window.upload_btn, "success"), (self.window.cancel_btn, "danger"),
                             (self.window.refresh_btn, "info"), (self.window.channel_playback.transport.toggle, "success"),
                             (self.window.channel_playback.stop_button, "danger"),
                             (self.window.channel_playlist_button, "info")):
            self.assertEqual(button.property("actionTone"), tone)

    def test_youtube_transport_lives_below_video_and_above_metadata_not_in_footer(self):
        self.select_preview_video()
        playback = self.window.channel_playback
        self.assertIs(playback.transport.parentWidget(), playback)
        self.assertFalse(playback.controls_widget.isAncestorOf(playback.transport))
        self.assertLess(playback.layout().indexOf(playback.media), playback.layout().indexOf(playback.transport))
        playback.transport.show()
        playback.transport.set_active(True)
        playback.player.telemetry.emit({"position": 5, "duration": 100, "volume": 50, "playing": True, "muted": False})
        for size in ((940, 620), (1280, 780), (1920, 1080)):
            self.window.resize(*size)
            self.settle()
            self.assertGreaterEqual(playback.transport.y(), playback.media.y() + playback.media.height())
            self.assertGreaterEqual(self.window.channel_info_pills[0].y(), playback.y() + playback.height())

    def test_both_metadata_groups_use_the_same_icon_heading_value_component(self):
        self.select_file()
        self.select_preview_video()
        for pill in self.window.local_preview.pills + self.window.channel_info_pills:
            self.assertIsInstance(pill, PreviewInfoPill)
            self.assertFalse(pill.glyph.pixmap().isNull())
            self.assertEqual(pill.value.textFormat(), ui.Qt.PlainText)
            self.assertEqual(pill.layout().contentsMargins().left(), 0)
        self.assertEqual([pill.heading.text() for pill in self.window.channel_info_pills],
                         ["Duracion", "Privacidad", "Publicado", "Lista"])
        self.assertEqual(self.window.channel_preview_duration.text(), "-")
        self.assertEqual(self.window.channel_preview_privacy.text(), "Privado")

    def test_shared_transport_sizing_order_and_volume_match_the_local_reference(self):
        player = FakeYouTubePlayer()
        transport = TransportControls(player)
        self.addCleanup(transport.close)
        local = self.window.local_preview.player
        for button in (transport.toggle, transport.back, transport.forward, transport.mute, transport.captions):
            self.assertEqual(button.size(), local.play_button.size())
            self.assertEqual(button.iconSize(), local.play_button.iconSize())
            self.assertTrue(button.toolTip())
        row = transport.layout().itemAtPosition(1, 0).layout()
        self.assertEqual([row.itemAt(i).widget() for i in range(4)],
                         [transport.toggle, transport.back, transport.forward, transport.mute])
        self.assertEqual(transport.volume.minimumWidth(), local.volume.minimumWidth())
        self.assertEqual(transport.volume.maximumWidth(), local.volume.maximumWidth())

    def test_semantic_colors_render_and_disabled_buttons_remain_muted(self):
        for tone in BUTTON_TONES:
            button = self.window.action_button("Test", tone=tone, primary=True)
            button.setParent(self.window)
            button.show()
            button.ensurePolished()
            self.assertEqual(button.palette().color(QPalette.Button).name(), BUTTON_TONES[tone][0])
            button.setEnabled(False)
            button.ensurePolished()
            self.assertEqual(button.palette().color(QPalette.Disabled, QPalette.Button).name(), "#1c1d21")
            button.deleteLater()


if __name__ == "__main__":
    unittest.main()
