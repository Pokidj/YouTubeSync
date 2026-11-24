import json
import queue
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from test_layout import ui

engine = ui.engine


class UploadRetrySafetyTests(unittest.TestCase):
    def setUp(self):
        duration = patch.object(engine, "local_video_duration", return_value=60.0)
        duration.start()
        self.addCleanup(duration.stop)
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.path = self.base / "video.mp4"
        self.path.write_bytes(b"clip")
        self.signature = engine.file_signature(self.path)
        self.config = engine.Config(watch_folder=str(self.base))
        with patch.object(engine, "app_dir", return_value=self.base):
            self.store = engine.Store()
        self.worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        self.client = Mock()
        self.client.verify_local_file.return_value = (False, "", "No aparece", "missing")
        self.client.upload.side_effect = TimeoutError("Respuesta interrumpida")

    def claim(self):
        return self.store.record_upload_attempt(self.signature, self.path, "Video")

    def test_a_failed_transfer_cannot_be_started_again_automatically(self):
        self.worker.handle_file(self.path, self.client)
        self.worker.handle_file(self.path, self.client)
        self.assertEqual(self.client.upload.call_count, 1)
        self.assertEqual(self.store.daily_upload_attempt_count(), 1)
        self.assertEqual(self.store.upload_status(self.signature), "error")

    def test_resetting_display_status_to_pending_does_not_unlock_an_attempt(self):
        self.worker.handle_file(self.path, self.client)
        self.store.upsert(self.signature, self.path, "Video", "pending")
        self.worker.handle_file(self.path, self.client)
        self.assertEqual(self.client.upload.call_count, 1)

    def test_manual_retry_permits_exactly_one_additional_transfer(self):
        self.worker.handle_file(self.path, self.client)
        self.store.clear_upload_incident(self.signature)
        self.worker.handle_file(self.path, self.client)
        self.worker.handle_file(self.path, self.client)
        self.assertEqual(self.client.upload.call_count, 2)
        self.assertEqual(self.store.daily_upload_attempt_count(), 2)

    def test_automatic_scan_excludes_an_unconfirmed_previous_attempt(self):
        self.worker.handle_file(self.path, self.client)
        with patch.object(self.worker, "is_stable", return_value=True):
            self.assertEqual(list(self.worker.iter_videos(self.base, self.config)), [])

    def test_repeated_scans_do_not_repeat_uploads_or_catalog_queries_after_a_failure(self):
        self.worker.set_enabled(True)
        self.client.scope = "test-project"
        with patch.object(self.worker, "available_client", return_value=self.client), \
                patch.object(self.worker, "is_stable", return_value=True):
            for _ in range(10):
                self.worker.scan_once()
        self.client.upload.assert_called_once()
        self.client.uploaded_titles.assert_called_once()
        self.assertEqual(self.store.daily_upload_attempt_count(), 1)

    def test_full_reconciliation_cannot_unlock_a_missing_attempt(self):
        self.store.remember_upload(self.signature, self.path, "Video", "previous-id", "processing")
        self.store.upsert(self.signature, self.path, "Video", "processing", youtube_id="previous-id")
        self.claim()
        engine.reconcile_local_uploads(self.store, self.config, self.client, full=True)
        self.assertEqual(self.store.upload_status(self.signature), "error")
        self.assertIn(self.signature, self.store.retry_required_signatures())
        self.worker.handle_file(self.path, self.client)
        self.client.upload.assert_not_called()

    def test_restart_preserves_the_guard_and_migrates_old_pending_attempts(self):
        self.claim()
        self.store.upsert(self.signature, self.path, "Video", "pending", youtube_id="previous-id")
        with patch.object(engine, "app_dir", return_value=self.base):
            reopened = engine.Store()
        self.assertEqual(reopened.upload_status(self.signature), "error")
        self.assertEqual(reopened.upload_identity(self.signature)[1], "previous-id")
        self.assertIsNone(reopened.record_upload_attempt(self.signature, self.path, "Video"))

    def test_legacy_attempt_schema_is_upgraded_without_erasing_history(self):
        legacy = self.base / "legacy"
        legacy.mkdir()
        with closing(sqlite3.connect(legacy / "state.sqlite3")) as db, db:
            db.execute("""CREATE TABLE upload_attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,
                       signature TEXT NOT NULL,title TEXT NOT NULL,path TEXT NOT NULL,created_at TEXT NOT NULL)""")
            db.execute("INSERT INTO upload_attempts(signature,title,path,created_at) VALUES(?,?,?,?)",
                       (self.signature, "Video", str(self.path), "2026-11-20T12:00:00"))
        with patch.object(engine, "app_dir", return_value=legacy):
            reopened = engine.Store()
        with reopened._connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*),outcome,detail FROM upload_attempts").fetchone(), (1, "", ""))
        self.assertIsNone(reopened.record_upload_attempt(self.signature, self.path, "Video"))

    def test_cancelled_transfer_is_not_automatically_restarted(self):
        self.client.upload.side_effect = engine.UploadCancelled("Cancelado")
        self.worker.handle_file(self.path, self.client)
        self.worker.handle_file(self.path, self.client)
        self.assertEqual(self.client.upload.call_count, 1)

    def test_existing_processing_attempt_still_can_be_confirmed(self):
        self.claim()
        self.client.verify_local_file.return_value = (True, "received-id", "Huella confirmada", "processed")
        self.worker.handle_file(self.path, self.client)
        self.assertTrue(self.store.has_success(self.signature))
        self.client.upload.assert_not_called()

    def test_only_one_concurrent_worker_can_claim_the_same_file(self):
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.claim())) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_old_quota_rejection_cannot_authorize_a_later_attempt(self):
        first = self.claim()
        self.store.authorize_upload_retry(self.signature, first)
        self.assertIsNotNone(self.claim())
        self.store.authorize_upload_retry(self.signature, first)
        self.assertIsNone(self.claim())

    def test_quota_denial_before_a_session_allows_retry_after_the_global_pause(self):
        for session_started in (False, True):
            with self.subTest(session_started=session_started):
                self.store.clear_upload_incident(self.signature)
                error = engine.HttpError(engine.httplib2.Response({"status": "403"}),
                                         json.dumps({"error": {"message": "Quota exceeded", "errors": [
                                             {"reason": "quotaExceeded"}]}}).encode())
                error.upload_session_started = session_started
                self.client.upload.side_effect = error
                self.worker.handle_file(self.path, self.client)
                self.assertEqual(self.signature in self.store.retry_required_signatures(), session_started)

    def test_attempt_outcome_is_persisted_for_diagnosis(self):
        self.worker.handle_file(self.path, self.client)
        with self.store._connection() as db:
            outcome, detail = db.execute("SELECT outcome,detail FROM upload_attempts").fetchone()
        self.assertEqual(outcome, "error")
        self.assertIn("interrumpida", detail)

    def test_chunk_retries_reuse_a_session_instead_of_retrying_its_creation(self):
        client = engine.YouTubeClient(self.store, self.config, Mock())
        request = Mock(resumable_uri=None)
        service = Mock()
        service.videos.return_value.insert.return_value = request
        retries = []

        def next_chunk(num_retries):
            retries.append(num_retries)
            if len(retries) == 1:
                request.resumable_uri = "https://example.invalid/existing-session"
                return Mock(progress=lambda: 0.5), None
            return None, {"id": "received-id"}

        request.next_chunk.side_effect = next_chunk
        with patch.object(client, "service", return_value=service):
            self.assertEqual(client.upload(self.path, "Video", threading.Event(), Mock()), "received-id")
        self.assertEqual(retries, [0, 3])
        service.videos.return_value.insert.assert_called_once()

    def test_transport_error_records_whether_a_session_was_started(self):
        for session in (None, "https://example.invalid/existing-session"):
            with self.subTest(session=session):
                client = engine.YouTubeClient(self.store, self.config, Mock())
                service = Mock()
                service.videos.return_value.insert.return_value.resumable_uri = session
                service.videos.return_value.insert.return_value.next_chunk.side_effect = TimeoutError("Conexion")
                with patch.object(client, "service", return_value=service):
                    with self.assertRaises(TimeoutError) as caught:
                        client.upload(self.path, "Video", threading.Event(), Mock())
                self.assertEqual(caught.exception.upload_session_started, bool(session))


if __name__ == "__main__":
    unittest.main()
