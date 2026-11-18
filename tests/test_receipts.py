import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_layout import ui

engine = ui.engine


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.path = self.base / "video.mp4"
        self.path.write_bytes(b"original clip")
        with patch.object(engine, "app_dir", return_value=self.base):
            self.store = engine.Store()
        self.signature = engine.file_signature(self.path)
        self.config = engine.Config(watch_folder=str(self.base))
        self.client = engine.YouTubeClient(self.store, self.config, Mock())
        self.service = Mock()
        self.service.videos.return_value.insert.return_value.next_chunk.return_value = (None, {"id": "received-id"})

    def upload(self):
        with patch.object(self.client, "service", return_value=self.service):
            return self.client.upload(self.path, "Video", threading.Event(), Mock())

    def set_remote(self, video_id="received-id", state="processed"):
        self.client._known_video_states = {video_id: state}
        self.client._known_video_metadata = {video_id: {"size": self.path.stat().st_size}}
        self.client._known_title_candidates = {"Video": [video_id]}

    def test_receipt_is_saved_at_completion_but_is_not_a_processed_confirmation(self):
        self.assertEqual(self.upload(), "received-id")
        self.assertEqual(self.store.receipt("received-id"),
                         (engine.full_content_fingerprint(self.path), self.path.stat().st_size))
        self.assertEqual(self.store.upload_identity(self.signature)[1], "received-id")
        self.assertEqual(self.store.upload_status(self.signature), "processing")
        self.assertFalse(self.store.has_success(self.signature))

    def test_local_receipt_links_the_file_even_if_the_remote_description_was_edited(self):
        self.upload()
        self.set_remote()
        confirmed, video_id, reason, state = self.client.verify_local_file(self.path, "Video", "received-id")
        self.assertTrue(confirmed)
        self.assertEqual((video_id, state), ("received-id", "processed"))
        self.assertIn("persistente", reason)

    def test_same_size_different_content_does_not_match_a_receipt(self):
        self.upload()
        self.path.write_bytes(b"differentclip")
        self.set_remote()
        self.assertFalse(self.client.verify_local_file(self.path, "Video", "received-id")[0])

    def test_receipt_for_another_id_is_not_accepted(self):
        self.upload()
        self.set_remote(video_id="other-id")
        self.assertFalse(self.client.verify_local_file(self.path, "Video", "other-id")[0])

    def test_confirmed_file_still_in_folder_is_skipped_after_restart_without_api(self):
        self.upload()
        self.set_remote()
        with patch.object(self.client, "uploaded_video_index"):
            engine.reconcile_local_uploads(self.store, self.config, self.client, full=True)
        with patch.object(engine, "app_dir", return_value=self.base):
            reopened = engine.Store()
        self.assertTrue(self.path.exists())
        self.assertTrue(reopened.has_success(self.signature))
        no_network = Mock()
        engine.SyncWorker(reopened, lambda: self.config, queue.Queue()).handle_file(self.path, no_network)
        no_network.verify_local_file.assert_not_called()
        no_network.upload.assert_not_called()

    def test_clearing_an_incident_does_not_erase_a_confirmed_identity(self):
        self.upload()
        self.store.remember_upload(self.signature, self.path, "Video", "received-id", "uploaded")
        self.store.clear_upload_incident(self.signature)
        self.assertTrue(self.store.has_success(self.signature))
        self.assertIsNotNone(self.store.receipt("received-id"))

    def test_cancelled_chunk_does_not_create_a_receipt_and_releases_the_file(self):
        media = engine.MediaFileUpload(str(self.path), chunksize=8 * 1024 * 1024, resumable=True)
        cancelled = threading.Event()
        cancelled.set()
        with patch.object(self.client, "service", return_value=self.service), \
                patch.object(engine, "MediaFileUpload", return_value=media):
            with self.assertRaises(engine.UploadCancelled):
                self.client.upload(self.path, "Video", cancelled, Mock())
        self.assertTrue(media.stream().closed)
        self.assertIsNone(self.store.receipt("received-id"))
        self.service.videos.return_value.insert.return_value.next_chunk.assert_not_called()

    def test_file_changed_during_transfer_is_not_confirmed(self):
        def changed():
            self.path.write_bytes(b"changed while uploading")
            return None, {"id": "received-id"}
        self.service.videos.return_value.insert.return_value.next_chunk.side_effect = changed
        with self.assertRaisesRegex(RuntimeError, "cambio durante"):
            self.upload()
        self.assertIsNone(self.store.receipt("received-id"))
        self.assertFalse(self.store.has_success(self.signature))
        self.assertEqual(self.store.upload_identity(self.signature)[1], "received-id")

    def test_old_unverified_records_do_not_gain_a_receipt_without_evidence(self):
        self.store.remember_upload(self.signature, self.path, "Video", "received-id", "unverified")
        self.set_remote()
        self.assertFalse(self.client.verify_local_file(self.path, "Video", "received-id")[0])
        self.assertIsNone(self.store.receipt("received-id"))

    def test_video_from_another_channel_does_not_count_as_uploaded_here(self):
        self.upload()
        self.service.videos.return_value.list.return_value.execute.return_value = {"items": [{
            "id": "received-id", "snippet": {"title": "Video", "channelId": "another-channel"},
            "status": {"uploadStatus": "processed"}}]}
        with patch.object(self.client, "service", return_value=self.service), \
                patch.object(self.client, "channel_info", return_value={"id": "owner"}):
            self.client.uploaded_video_index(video_ids=["received-id"])
        self.assertEqual(self.client.verify_local_file(self.path, "Video", "received-id")[3], "missing")


if __name__ == "__main__":
    unittest.main()
