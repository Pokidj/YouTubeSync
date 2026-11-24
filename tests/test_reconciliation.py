import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_layout import ui

engine = ui.engine


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.path = self.base / "video.mp4"
        self.path.write_bytes(b"clip original")
        with patch.object(engine, "app_dir", return_value=self.base):
            self.store = engine.Store()
        self.signature = engine.file_signature(self.path)
        self.config = engine.Config(watch_folder=str(self.base))
        self.client = engine.YouTubeClient(self.store, self.config, Mock())

    def index(self, states, metadata, candidates=None):
        self.client._known_titles = set()
        self.client._known_video_ids = set()
        self.client._known_video_states = states
        self.client._known_video_metadata = metadata
        self.client._known_title_candidates = candidates or {"Video": list(states)}

    def remember_processing(self):
        self.store.remember_upload(self.signature, self.path, "Video", "remote-id", "processing")
        self.store.upsert(self.signature, self.path, "Video", "processing", youtube_id="remote-id")

    def test_succeeded_is_finished_but_uploaded_alone_is_not(self):
        self.assertEqual(engine.remote_video_state({"status": {"uploadStatus": "uploaded"},
                                                   "processingDetails": {"processingStatus": "succeeded"}}), "processed")
        self.assertEqual(engine.remote_video_state({"status": {"uploadStatus": "uploaded"}}), "processing")
        self.assertEqual(engine.remote_video_state({"status": {"uploadStatus": "processed"},
                                                   "processingDetails": {"processingStatus": "failed"}}), "failed")

    def test_id_batches_do_not_load_the_entire_channel(self):
        service = Mock()
        service.videos.return_value.list.return_value.execute.return_value = {"items": [
            {"id": "remote-id", "snippet": {"title": "Video", "channelId": "owner"}, "status": {"uploadStatus": "uploaded"},
             "processingDetails": {"processingStatus": "succeeded"}},
        ]}
        with patch.object(self.client, "service", return_value=service), \
                patch.object(self.client, "channel_info", return_value={"id": "owner"}):
            titles, ids = self.client.uploaded_video_index(video_ids=[str(i) for i in range(101)])
        service.channels.assert_not_called()
        service.playlistItems.assert_not_called()
        self.assertEqual(service.videos.return_value.list.call_count, 3)
        self.assertIn("remote-id", ids)
        self.assertIn("Video", titles)

    def test_same_title_duration_size_and_name_are_not_proof(self):
        self.index({"remote-id": "processed"}, {"remote-id": {
            "filename": self.path.name, "size": self.path.stat().st_size, "duration": "PT30S"}})
        confirmed, _, _, state = self.client.verify_local_file(self.path, "Video")
        self.assertFalse(confirmed)
        self.assertEqual(state, "unverified")

    def test_different_content_with_identical_metadata_is_not_a_match(self):
        other = self.base / "other.mp4"
        other.write_bytes(b"clip distinto")
        self.assertEqual(other.stat().st_size, self.path.stat().st_size)
        self.index({"remote-id": "processed"}, {"remote-id": {
            "fingerprint": engine.full_content_fingerprint(other), "size": other.stat().st_size,
            "filename": self.path.name, "duration": "PT30S"}})
        self.assertFalse(self.client.verify_local_file(self.path, "Video")[0])

    def test_processed_identical_copy_wins_over_processing_copy(self):
        metadata = {"fingerprint": engine.full_content_fingerprint(self.path)}
        self.index({"old": "processing", "ready": "processed"}, {"old": metadata, "ready": metadata})
        self.assertEqual(self.client.verify_local_file(self.path, "Video", "old")[1::2], ("ready", "processed"))

    def test_saved_id_survives_a_remote_title_change(self):
        self.index({"remote-id": "processed"}, {"remote-id": {
            "fingerprint": engine.full_content_fingerprint(self.path)}}, {"Renombrado": ["remote-id"]})
        self.assertTrue(self.client.verify_local_file(self.path, "Video", "remote-id")[0])

    def test_processing_becomes_uploaded_without_any_upload_worker(self):
        self.remember_processing()
        self.index({"remote-id": "processed"}, {"remote-id": {
            "fingerprint": engine.full_content_fingerprint(self.path)}})
        with patch.object(self.client, "uploaded_video_index"):
            self.assertEqual(engine.reconcile_local_uploads(self.store, self.config, self.client), 1)
        self.assertTrue(self.store.has_success(self.signature))
        self.assertEqual(self.store.upload_status(self.signature), "uploaded")

    def test_missing_remote_video_returns_to_pending(self):
        self.remember_processing()
        self.index({}, {})
        with patch.object(self.client, "uploaded_video_index"):
            engine.reconcile_local_uploads(self.store, self.config, self.client)
        self.assertFalse(self.store.has_success(self.signature))
        self.assertEqual(self.store.upload_status(self.signature), "pending")

    def test_unconfirmed_content_is_not_a_success_or_a_new_upload(self):
        self.remember_processing()
        self.index({"remote-id": "processed"}, {"remote-id": {}})
        with patch.object(self.client, "uploaded_video_index"):
            engine.reconcile_local_uploads(self.store, self.config, self.client)
        self.assertFalse(self.store.has_success(self.signature))
        self.assertEqual(self.store.upload_status(self.signature), "verification_pending")
        with patch.object(self.client, "upload") as upload, patch.object(self.client, "delete_video") as delete:
            engine.SyncWorker(self.store, lambda: self.config, queue.Queue()).handle_file(self.path, self.client)
        upload.assert_not_called()
        delete.assert_not_called()

    def test_current_upload_is_never_reconciled(self):
        self.remember_processing()
        with patch.object(self.client, "uploaded_video_index"), patch.object(self.client, "verify_local_file") as verify:
            self.assertEqual(engine.reconcile_local_uploads(self.store, self.config, self.client,
                                                          is_active=lambda path: path == self.path), 0)
        verify.assert_not_called()

    def test_confirmations_remain_permanent_even_on_full_refresh(self):
        self.store.remember_upload(self.signature, self.path, "Video", "remote-id", "uploaded")
        self.store.upsert(self.signature, self.path, "Video", "uploaded", youtube_id="remote-id")
        for full in (False, True):
            with patch.object(self.client, "uploaded_video_index") as index, \
                    patch.object(self.client, "verify_local_file") as verify:
                self.assertEqual(engine.reconcile_local_uploads(self.store, self.config, self.client, full=full), 0)
            index.assert_not_called()
            verify.assert_not_called()
        self.assertTrue(self.store.has_success(self.signature))

    def test_absent_local_files_do_not_trigger_a_remote_query(self):
        self.remember_processing()
        self.path.unlink()
        with patch.object(self.client, "uploaded_video_index") as index:
            self.assertEqual(engine.reconcile_local_uploads(self.store, self.config, self.client, full=True), 0)
        index.assert_not_called()

    def test_full_refresh_with_known_ids_only_requests_those_ids(self):
        self.remember_processing()
        self.index({}, {})
        with patch.object(self.client, "uploaded_video_index") as index:
            engine.reconcile_local_uploads(self.store, self.config, self.client, full=True)
        index.assert_called_once_with(video_ids=["remote-id"])

    def test_idle_auto_worker_keeps_confirmed_files_without_network(self):
        self.store.remember_upload(self.signature, self.path, "Video", "remote-id", "uploaded")
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        worker.set_enabled(True)
        client = Mock()
        client.scope = "scope"
        with patch.object(worker, "available_client", return_value=client):
            worker.scan_once()
        client.uploaded_titles.assert_not_called()
        client.uploaded_video_index.assert_not_called()

    def test_auto_cleanup_checks_exact_ids_live_before_deleting(self):
        self.store.remember_upload(self.signature, self.path, "Video", "remote-id", "uploaded")
        self.config.auto_delete_uploaded = True
        row = (self.signature, "2000-01-01", "uploaded", "Video", str(self.path), "remote-id", "", 13)
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        client = Mock()
        client.verify_local_file.return_value = (True, "remote-id", "Confirmado", "processed")
        with patch.object(self.store, "uploaded_before", return_value=[row]), \
                patch.object(engine, "YouTubeClient", return_value=client):
            worker.auto_cleanup_once()
        client.uploaded_video_index.assert_called_once_with(force=True, video_ids=["remote-id"])
        self.assertFalse(self.path.exists())

    def test_auto_cleanup_preserves_a_file_changed_during_remote_verification(self):
        self.store.remember_upload(self.signature, self.path, "Video", "remote-id", "uploaded")
        self.config.auto_delete_uploaded = True
        row = (self.signature, "2000-01-01", "uploaded", "Video", str(self.path), "remote-id", "", 13)
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        client = Mock()

        def changed(*args):
            self.path.write_bytes(b"changed during verification")
            return True, "remote-id", "Confirmado", "processed"

        client.verify_local_file.side_effect = changed
        with patch.object(self.store, "uploaded_before", return_value=[row]), \
                patch.object(engine, "YouTubeClient", return_value=client):
            worker.auto_cleanup_once()
        self.assertTrue(self.path.exists())

    def test_retry_clears_error_without_losing_remote_identity(self):
        self.store.upsert(self.signature, self.path, "Video", "error", youtube_id="remote-id", error="Red")
        self.store.clear_upload_incident(self.signature)
        self.assertEqual(self.store.upload_identity(self.signature), ("Video", "remote-id"))
        self.assertEqual(self.store.upload_status(self.signature), "pending")

    def test_legacy_fingerprint_remains_compatible(self):
        self.index({"remote-id": "processed"}, {"remote-id": {
            "fingerprint": engine.file_content_fingerprint(self.path),
            "filename": self.path.name, "size": self.path.stat().st_size}})
        self.assertTrue(self.client.verify_local_file(self.path, "Video")[0])

    def test_legacy_sample_without_original_metadata_is_not_enough(self):
        self.index({"remote-id": "processed"}, {"remote-id": {
            "fingerprint": engine.file_content_fingerprint(self.path)}})
        self.assertEqual(self.client.verify_local_file(self.path, "Video")[3], "unverified")

    def test_full_hash_detects_changes_outside_the_old_samples(self):
        original = bytearray(8 * 1024 * 1024)
        self.path.write_bytes(original)
        other = self.base / "other.mp4"
        original[2 * 1024 * 1024] = 1
        other.write_bytes(original)
        self.assertEqual(engine.file_content_fingerprint(self.path), engine.file_content_fingerprint(other))
        self.assertNotEqual(engine.full_content_fingerprint(self.path), engine.full_content_fingerprint(other))

    def test_changed_local_file_is_not_reconciled_using_an_old_identity(self):
        self.remember_processing()
        self.path.write_bytes(b"a different video")
        with patch.object(self.client, "uploaded_video_index"), patch.object(self.client, "verify_local_file") as verify:
            self.assertEqual(engine.reconcile_local_uploads(self.store, self.config, self.client), 0)
        verify.assert_not_called()

    def test_network_error_does_not_mark_video_missing(self):
        self.remember_processing()
        with patch.object(self.client, "uploaded_video_index", side_effect=TimeoutError("offline")):
            with self.assertRaises(TimeoutError):
                engine.reconcile_local_uploads(self.store, self.config, self.client)
        self.assertEqual(self.store.upload_status(self.signature), "processing")
        self.assertEqual(self.store.upload_identity(self.signature)[1], "remote-id")

    def test_late_api_snapshot_cannot_overwrite_a_new_upload(self):
        self.remember_processing()
        registry, _ = self.store.registry_index()
        statuses, _ = self.store.upload_status_index()
        self.store.remember_upload(self.signature, self.path, "Video", "new-id", "processing")
        applied = self.store.apply_reconciliation(self.signature, self.path, "Video", "remote-id",
                                                  "uploaded", "uploaded", "",
                                                  registry[self.signature], statuses[self.signature])
        self.assertFalse(applied)
        self.assertEqual(self.store.upload_identity(self.signature)[1], "new-id")
        self.assertFalse(self.store.has_success(self.signature))


if __name__ == "__main__":
    unittest.main()
