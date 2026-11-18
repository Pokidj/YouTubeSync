import json
import queue
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from test_layout import ui

engine = ui.engine


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.secret = self.base / "oauth.json"
        self.secret.write_text("{}")
        self.path = self.base / "video.mp4"
        self.path.write_bytes(b"video")
        self.config = engine.Config(watch_folder=str(self.base), client_secret_path=str(self.secret))
        self.scope = engine.api_scope(str(self.secret))
        with patch.object(engine, "app_dir", return_value=self.base):
            self.store = engine.Store()

    def error(self, reason="quotaExceeded", message="Quota exceeded", status=403):
        return engine.HttpError(engine.httplib2.Response({"status": str(status)}),
                                json.dumps({"error": {"message": message, "errors": [{"reason": reason}]}}).encode())

    def test_transport_stops_repeating_requests_after_quota_error(self):
        raw = Mock()
        error = self.error()
        raw.request.return_value = (error.resp, error.content)
        transport = engine.QuotaAwareHttp(raw, self.store, self.scope)
        response, _ = transport.request("https://youtube.googleapis.com/youtube/v3/videos")
        self.assertEqual(response.status, 403)
        with self.assertRaises(engine.ApiQuotaUnavailable):
            transport.request("https://youtube.googleapis.com/youtube/v3/channels")
        raw.request.assert_called_once()

    def test_upload_bucket_does_not_disable_read_requests(self):
        raw = Mock()
        error = self.error(message="Quota exceeded for Video Uploads per day")
        raw.request.side_effect = [(error.resp, error.content), (engine.httplib2.Response({"status": "200"}), b"{}")]
        transport = engine.QuotaAwareHttp(raw, self.store, self.scope)
        url = "https://www.googleapis.com/upload/youtube/v3/videos"
        transport.request(url, method="POST")
        with self.assertRaises(engine.ApiQuotaUnavailable):
            transport.request(url, method="POST")
        self.assertEqual(transport.request("https://youtube.googleapis.com/youtube/v3/videos")[0].status, 200)
        self.assertEqual(raw.request.call_count, 2)
        self.assertIsNone(self.store.api_pause(self.scope))

    def test_channel_upload_limit_does_not_disable_read_requests(self):
        raw = Mock()
        error = self.error("uploadLimitExceeded", "The user has exceeded the number of videos", 403)
        raw.request.return_value = (error.resp, error.content)
        engine.QuotaAwareHttp(raw, self.store, self.scope).request("https://www.googleapis.com/upload/youtube/v3/videos", method="POST")
        self.assertIsNone(self.store.api_pause(self.scope))

    def test_pause_survives_restart_and_is_scoped_to_credentials(self):
        state = self.store.defer_api(self.scope, self.error())
        with patch.object(engine, "app_dir", return_value=self.base):
            reopened = engine.Store()
        self.assertEqual(reopened.api_pause(self.scope), state)
        self.assertIsNone(reopened.api_pause("another-project"))

    def test_expired_pause_allows_a_single_new_network_attempt(self):
        self.store.save_service_cache(self.scope, "quota_general", {
            "retry_at": (datetime.now().astimezone() - timedelta(seconds=1)).isoformat(), "kind": "proyecto"})
        raw = Mock()
        raw.request.return_value = (engine.httplib2.Response({"status": "200"}), b"{}")
        engine.QuotaAwareHttp(raw, self.store, self.scope).request("https://youtube.googleapis.com/youtube/v3/videos")
        raw.request.assert_called_once()

    def test_quota_error_during_upload_waits_instead_of_creating_an_incident(self):
        client = Mock()
        client.verify_local_file.return_value = (False, "", "missing", "missing")
        client.upload.side_effect = self.error()
        events = queue.Queue()
        worker = engine.SyncWorker(self.store, lambda: self.config, events)
        worker.set_enabled(True)
        worker.handle_file(self.path, client)
        self.assertEqual(self.store.upload_status(engine.file_signature(self.path)), "waiting_quota")
        self.assertTrue(worker.enabled_event.is_set())
        self.assertTrue(any(kind == "api_quota" for kind, _ in list(events.queue)))
        client.delete_video.assert_not_called()

    def test_processing_and_confirmed_records_survive_quota_failures(self):
        signature = engine.file_signature(self.path)
        for reason in ("processing", "uploaded"):
            with self.subTest(state=reason):
                self.store.remember_upload(signature, self.path, "Video", "remote-id", reason)
                self.store.upsert(signature, self.path, "Video", reason, youtube_id="remote-id")
                client = Mock()
                client.uploaded_video_index.side_effect = self.error()
                with self.assertRaises(engine.HttpError):
                    engine.reconcile_local_uploads(self.store, self.config, client, full=True)
                self.assertEqual(self.store.upload_status(signature), reason)
                self.assertEqual(self.store.upload_identity(signature)[1], "remote-id")

    def test_worker_reuses_its_client_until_settings_change(self):
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        first = worker.available_client(self.config)
        self.assertIs(worker.available_client(self.config), first)
        self.config.privacy_status = "unlisted"
        self.assertIsNot(worker.available_client(self.config), first)

    def test_index_cache_avoids_repeated_full_channel_scans(self):
        client = engine.YouTubeClient(self.store, self.config, Mock())
        service = Mock()
        service.playlistItems.return_value.list.return_value.execute.return_value = {"items": []}
        with patch.object(client, "service", return_value=service), \
                patch.object(client, "channel_info", return_value={"uploads": "uploads-id"}):
            client.uploaded_titles()
            client.uploaded_titles()
        service.playlistItems.return_value.list.assert_called_once()

    def test_full_catalog_cache_lasts_five_minutes_but_not_forever(self):
        client = engine.YouTubeClient(self.store, self.config, Mock())
        service = Mock()
        service.playlistItems.return_value.list.return_value.execute.return_value = {"items": []}
        with patch.object(client, "service", return_value=service), \
                patch.object(client, "channel_info", return_value={"uploads": "uploads-id"}), \
                patch.object(engine.time, "monotonic", return_value=100) as clock:
            client.uploaded_titles()
            clock.return_value = 200
            client.uploaded_titles()
            self.assertEqual(service.playlistItems.return_value.list.call_count, 1)
            clock.return_value = 401
            client.uploaded_titles()
            self.assertEqual(service.playlistItems.return_value.list.call_count, 2)

    def test_worker_checks_processing_ids_instead_of_loading_the_channel(self):
        signature = engine.file_signature(self.path)
        self.store.remember_upload(signature, self.path, "Video", "remote-id", "processing")
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        worker.set_enabled(True)
        client = Mock(scope=self.scope)
        id_client = Mock()
        worker._id_client = id_client
        with patch.object(worker, "available_client", return_value=client), \
                patch.object(worker, "is_stable", return_value=True), \
                patch.object(worker, "handle_file") as handle:
            worker.scan_once()
        client.uploaded_titles.assert_not_called()
        id_client.uploaded_video_index.assert_called_once_with(force=False, video_ids=["remote-id"])
        handle.assert_called_once_with(self.path, id_client)

    def test_id_batch_verification_does_not_fall_back_to_a_full_channel_scan(self):
        client = engine.YouTubeClient(self.store, self.config, Mock())
        service = Mock()
        service.videos.return_value.list.return_value.execute.return_value = {"items": []}
        with patch.object(client, "service", return_value=service), \
                patch.object(client, "channel_info", return_value={"id": "owner"}):
            client.uploaded_video_index(video_ids=["known-id"])
            self.assertEqual(client.verify_local_file(self.path, "Video", "known-id")[3], "missing")
        service.playlistItems.assert_not_called()

    def test_new_upload_id_is_not_hidden_by_a_recent_full_catalog_cache(self):
        client = engine.YouTubeClient(self.store, self.config, Mock())
        service = Mock()
        service.playlistItems.return_value.list.return_value.execute.return_value = {"items": []}
        service.videos.return_value.list.return_value.execute.return_value = {"items": []}
        with patch.object(client, "service", return_value=service), \
                patch.object(client, "channel_info", return_value={"uploads": "uploads-id"}):
            client.uploaded_titles()
            client.uploaded_video_index(video_ids=["just-uploaded"])
        service.videos.return_value.list.assert_called_once()
        self.assertEqual(service.videos.return_value.list.call_args.kwargs["id"], "just-uploaded")

    def test_reset_calculation_handles_pacific_dst_changes(self):
        for current, expected in (("2026-11-17T13:00:00+00:00", "2026-11-18T08:00:00+00:00"),
                                  ("2026-03-08T10:00:00+00:00", "2026-03-09T07:00:00+00:00"),
                                  ("2026-11-01T07:30:00+00:00", "2026-11-02T08:00:00+00:00")):
            with self.subTest(now=current):
                self.assertEqual(engine.next_pacific_midnight(datetime.fromisoformat(current)).astimezone(timezone.utc),
                                 datetime.fromisoformat(expected))

    def test_temporary_rate_limit_has_a_short_retry_not_a_daily_pause(self):
        kind, retry, _ = engine.youtube_retry_prediction(self.error("rateLimitExceeded"))
        self.assertEqual(kind, "api")
        self.assertLess((retry - datetime.now().astimezone()).total_seconds(), 65)

    def test_channel_can_use_a_persisted_snapshot_without_verifying_it_again(self):
        snapshot = {"videos": [{"id": "remote-id", "title": "Video"}], "playlists": []}
        self.store.save_service_cache(self.scope, "gallery", snapshot)
        self.store.defer_api(self.scope, self.error())
        loader = ui.ChannelLoader(self.store, self.config)
        ready, cached = Mock(), Mock()
        loader.finished.connect(ready)
        loader.cached.connect(cached)
        loader.run()
        ready.assert_called_once_with(snapshot["videos"], [])
        cached.assert_called_once()


if __name__ == "__main__":
    unittest.main()
