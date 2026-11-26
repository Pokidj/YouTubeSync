import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QItemSelectionModel
import test_layout as fixture
from test_layout import ui


class ChannelPlaylistBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass()
        cls.app = fixture.ResponsiveLayoutTests.app

    setUp = fixture.ResponsiveLayoutTests.setUp
    tearDown = fixture.ResponsiveLayoutTests.tearDown

    def videos(self):
        return [dict(id=f"video-{index}", title=f"Clip {index}", memberships=[dict(playlist_id="old", item_id=f"item-{index}")])
                for index in range(3)]

    def select_videos(self, count=2):
        videos = self.videos()
        self.window.channel_videos = videos
        self.window.channel_table.setRowCount(3)
        for index, video in enumerate(videos):
            self.window.channel_table.setItem(index, 6, ui.table_item(f"https://youtu.be/{video['id']}"))
        self.window.channel_playlists_by_label = {"Ninguna": "", "Destino": "destination"}
        with patch.object(self.window, "fetch_thumbnail"):
            selection = self.window.channel_table.selectionModel()
            for index in range(count):
                selection.select(self.window.channel_table.model().index(index, 6), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        return videos

    def result(self):
        return next(value for kind, value in list(self.window.events.queue) if kind == "channel_playlist_changed")

    def test_group_confirmation_snapshots_only_selected_videos_and_prevents_duplicate_starts(self):
        videos = self.select_videos()
        with patch.object(ui.QInputDialog, "getItem", return_value=("Destino", True)) as choose, \
                patch.object(ui.QMessageBox, "question", return_value=ui.QMessageBox.Yes) as confirm, \
                patch.object(ui.threading, "Thread") as thread:
            self.window.channel_batch_playlist_button.click()
            self.window.change_selected_channel_playlist()
        self.assertIn("2", confirm.call_args.args[2])
        self.assertIn("Destino", confirm.call_args.args[2])
        self.assertEqual(confirm.call_args.args[-1], ui.QMessageBox.No)
        selected, destination = thread.call_args.kwargs["args"]
        self.assertEqual([video["id"] for video in selected], ["video-0", "video-1"])
        self.assertEqual(destination, "destination")
        videos[0]["memberships"][0]["item_id"] = "changed"
        self.assertEqual(selected[0]["memberships"][0]["item_id"], "item-0")
        self.assertTrue(self.window.channel_playlist_running)
        self.assertFalse(self.window.channel_batch_playlist_button.isEnabled())
        thread.assert_called_once()
        choose.assert_called_once()

    def test_cancelled_confirmation_does_not_start_any_work(self):
        self.select_videos()
        with patch.object(ui.QInputDialog, "getItem", return_value=("Destino", True)), \
                patch.object(ui.QMessageBox, "question", return_value=ui.QMessageBox.No), \
                patch.object(ui.threading, "Thread") as thread:
            self.window.change_selected_channel_playlist()
        thread.assert_not_called()
        self.assertFalse(self.window.channel_playlist_running)

    def test_batch_uses_one_client_and_continues_after_a_video_specific_error(self):
        client = Mock()
        client.replace_video_playlist.side_effect = [None, RuntimeError("video not found"), None]
        with patch.object(ui.engine, "YouTubeClient", return_value=client) as create:
            self.window._change_channel_playlist_thread(self.videos(), "destination")
        create.assert_called_once()
        self.assertEqual(client.replace_video_playlist.call_count, 3)
        result = self.result()
        self.assertEqual(result["updated"], ["video-0", "video-2"])
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["skipped"], 0)

    def test_quota_failure_stops_without_retrying_the_remaining_videos(self):
        client = Mock()
        client.replace_video_playlist.side_effect = [None, RuntimeError("quotaExceeded")]
        with patch.object(ui.engine, "YouTubeClient", return_value=client):
            self.window._change_channel_playlist_thread(self.videos(), "destination")
        self.assertEqual(client.replace_video_playlist.call_count, 2)
        self.assertEqual(self.result()["updated"], ["video-0"])
        self.assertEqual(self.result()["skipped"], 1)

    def test_connection_failure_reports_all_videos_as_unattempted(self):
        with patch.object(ui.engine, "YouTubeClient", side_effect=RuntimeError("invalid_grant")):
            self.window._change_channel_playlist_thread(self.videos(), "destination")
        self.assertEqual(self.result()["updated"], [])
        self.assertEqual(self.result()["skipped"], 3)
        self.assertIn("invalid_grant", self.result()["errors"][0])

    def test_partial_result_reenables_controls_and_refreshes_once(self):
        self.select_videos(1)
        self.window.channel_playlist_running = True
        self.window.events.put(("channel_playlist_changed", dict(updated=["video-0"], errors=["quotaExceeded"], skipped=2)))
        with patch.object(self.window, "refresh_channel") as refresh, patch.object(self.window, "report_problem") as report, \
                patch.object(ui.QMessageBox, "warning") as warning:
            self.window.process_events()
        self.assertFalse(self.window.channel_playlist_running)
        self.assertTrue(self.window.channel_playlist_button.isEnabled())
        self.assertTrue(self.window.channel_batch_playlist_button.isEnabled())
        refresh.assert_called_once()
        report.assert_called_once()
        self.assertIn("2 sin intentar", warning.call_args.args[2])

    def test_single_and_group_playlist_buttons_are_compact(self):
        self.select_videos(1)
        for button in (self.window.channel_playlist_button, self.window.channel_batch_playlist_button):
            self.assertEqual(button.text(), "")
            self.assertLessEqual(button.width(), 54)
            self.assertTrue(button.toolTip())
        self.assertTrue(self.window.channel_playback.controls_widget.isAncestorOf(self.window.channel_playlist_button))
        bars = []
        for layout in self.window.tabs.widget(1).findChildren(ui.QHBoxLayout):
            widgets = [layout.itemAt(index).widget() for index in range(layout.count())]
            if self.window.channel_batch_playlist_button in widgets:
                bars.append(widgets)
        self.assertEqual(len(bars), 1)
        index = bars[0].index(self.window.channel_batch_playlist_button)
        self.assertEqual(bars[0][index - 1].accessibleName(), "Privacidad")
        self.select_videos(2)
        self.assertFalse(self.window.channel_playlist_button.isEnabled())
        self.assertTrue(self.window.channel_batch_playlist_button.isEnabled())

    def test_refresh_in_progress_prevents_a_second_playlist_operation(self):
        self.select_videos()
        self.window.channel_loader = Mock()
        try:
            with patch.object(ui.QInputDialog, "getItem") as choose, patch.object(ui.threading, "Thread") as thread:
                self.window.change_selected_channel_playlist()
            choose.assert_not_called()
            thread.assert_not_called()
        finally:
            self.window.channel_loader = None


class PlaylistMutationSafetyTests(unittest.TestCase):
    def client(self):
        client = object.__new__(ui.engine.YouTubeClient)
        client.service = Mock()
        return client, client.service.return_value.playlistItems.return_value

    def test_destination_is_added_before_previous_memberships_are_removed(self):
        client, items = self.client()
        sequence = []
        items.insert.return_value.execute.side_effect = lambda: sequence.append("insert")
        items.delete.return_value.execute.side_effect = lambda: sequence.append("delete")
        client.replace_video_playlist("video", [dict(playlist_id="old", item_id="old-item")], "new")
        self.assertEqual(sequence, ["insert", "delete"])

    def test_failed_destination_insert_preserves_existing_memberships(self):
        client, items = self.client()
        items.insert.return_value.execute.side_effect = RuntimeError("quotaExceeded")
        with self.assertRaises(RuntimeError):
            client.replace_video_playlist("video", [dict(playlist_id="old", item_id="old-item")], "new")
        items.delete.assert_not_called()

    def test_existing_destination_is_not_inserted_or_deleted_again(self):
        client, items = self.client()
        client.replace_video_playlist("video", [dict(playlist_id="new", item_id="keep"), dict(playlist_id="old", item_id="remove")], "new")
        items.insert.assert_not_called()
        items.delete.assert_called_once_with(id="remove")

    def test_none_destination_only_removes_playlist_memberships(self):
        client, items = self.client()
        client.replace_video_playlist("video", [dict(playlist_id="old", item_id="remove")], "")
        items.insert.assert_not_called()
        items.delete.assert_called_once_with(id="remove")
        client.service.return_value.videos.assert_not_called()


if __name__ == "__main__":
    unittest.main()
