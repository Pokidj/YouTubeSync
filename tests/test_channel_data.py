import unittest
from unittest.mock import Mock, patch

from test_layout import ui
from youtube_sync_channel_data import split_gallery_rows


class ChannelDataTests(unittest.TestCase):
    def test_legacy_missing_placeholders_are_not_counted_as_channel_videos(self):
        rows = [{"id": "real", "title": "Mi vídeo", "privacy": "private"},
                {"id": "reference", "title": "Sin titulo", "privacy": "desconocido", "duration": "—"}]
        available, missing = split_gallery_rows(rows)
        self.assertEqual(available, rows[:1])
        self.assertEqual(missing, ["reference"])
        self.assertEqual(len(rows), 2)

    def test_explicit_metadata_preserves_real_videos_named_sin_titulo(self):
        row = {"id": "real", "title": "Sin titulo", "privacy": "desconocido", "metadata_available": True}
        self.assertEqual(split_gallery_rows([row]), ([row], []))

    def test_unavailable_references_are_unique_and_available_data_wins(self):
        missing = {"id": "same", "metadata_available": False}
        real = {"id": "same", "metadata_available": True, "privacy": "unlisted"}
        self.assertEqual(split_gallery_rows([missing, real, missing]), ([real], []))
        self.assertEqual(split_gallery_rows([missing, missing]), ([], ["same"]))

    def test_legacy_minimal_but_named_metadata_is_preserved(self):
        row = {"id": "real", "title": "Video"}
        self.assertEqual(split_gallery_rows([row]), ([row], []))

    def test_gallery_regression_767_references_produce_486_available_videos(self):
        engine = ui.engine
        store, service = Mock(), Mock()
        client = engine.YouTubeClient(store, engine.Config(), Mock())
        ids = [f"id-{index}" for index in range(767)]
        client._known_title_candidates = {"Clip": ids}
        client._known_video_metadata = {video_id: {"title": "Clip", "privacy": "private" if index < 481 else "unlisted"}
                                        for index, video_id in enumerate(ids[:486])}
        client._channel_info = {"id": "channel", "title": "Canal"}
        with patch.object(client, "uploaded_video_index"), patch.object(client, "playlists", return_value=[]), \
                patch.object(client, "service", return_value=service):
            rows, playlists = client.channel_gallery()
        self.assertEqual(len(rows), 486)
        self.assertEqual(sum(row["privacy"] == "private" for row in rows), 481)
        self.assertEqual(sum(row["privacy"] == "unlisted" for row in rows), 5)
        self.assertEqual(len(client.gallery_unavailable_ids), 281)
        self.assertEqual(client._known_title_candidates["Clip"], ids)
        payload = store.save_service_cache.call_args.args[2]
        self.assertEqual(len(payload["videos"]), 486)
        self.assertEqual(len(payload["unavailable_ids"]), 281)
        self.assertEqual(payload["channel"]["unavailable_count"], 281)
        service.videos.assert_not_called()
        self.assertEqual(playlists, [])
