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
        duration = patch.object(engine, "local_video_duration", return_value=60.0)
        duration.start()
        self.addCleanup(duration.stop)
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
                if reason == "processing":
                    with self.assertRaises(engine.HttpError):
                        engine.reconcile_local_uploads(self.store, self.config, client, full=True)
                else:
                    engine.reconcile_local_uploads(self.store, self.config, client, full=True)
                    client.uploaded_video_index.assert_not_called()
                self.assertEqual(self.store.upload_status(signature), reason)
                self.assertEqual(self.store.upload_identity(signature)[1], "remote-id")

    def test_worker_reuses_its_client_until_settings_change(self):
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        first = worker.available_client(self.config)
        self.assertIs(worker.available_client(self.config), first)
        self.config.privacy_status = "unlisted"
        self.assertIsNot(worker.available_client(self.config), first)

    def test_server_quota_reason_is_available_in_diagnostics(self):
        events = queue.Queue()
        worker = engine.SyncWorker(self.store, lambda: self.config, events)
        worker.pause_for_youtube_limit(self.error())
        messages = [value for kind, value in list(events.queue) if kind == "log"]
        self.assertTrue(any("quotaExceeded" in message and "HttpError" in message for message in messages))

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

    def test_daily_upload_limit_reported_as_rate_limit_uses_daily_reset(self):
        error = self.error("rateLimitExceeded", "Quota exceeded for quota metric Video Uploads and limit Video Uploads per day")
        kind, retry, _ = engine.youtube_retry_prediction(error)
        self.assertEqual(kind, "proyecto")
        self.assertEqual(retry, engine.next_pacific_midnight())
        self.assertIn("diaria", engine.youtube_error_message(error))

    def test_quota_exceeded_with_a_per_minute_limit_is_not_treated_as_daily(self):
        error = self.error("quotaExceeded", "Quota exceeded for Queries per minute")
        self.assertEqual(engine.youtube_retry_prediction(error)[0], "api")

    def test_repeated_temporary_limits_back_off_instead_of_polling_every_minute(self):
        error = self.error("rateLimitExceeded")
        first = self.store.defer_api(self.scope, error)
        self.store.clear_api_pause(self.scope)
        second = self.store.defer_api(self.scope, error)
        self.assertEqual(second["attempts"], 2)
        self.assertGreater(datetime.fromisoformat(second["retry_at"]), datetime.fromisoformat(first["retry_at"]))
        same = self.store.defer_api(self.scope, engine.ApiQuotaUnavailable(second))
        self.assertEqual(same, second)
        self.assertEqual(second["reason"], "rateLimitExceeded")
        self.assertIn("temporal", engine.youtube_error_message(engine.ApiQuotaUnavailable(second)))

    def test_shared_cache_coalesces_simultaneous_background_checks(self):
        import threading
        import time
        service = Mock()
        service.videos.return_value.list.return_value.execute.side_effect = lambda: (time.sleep(0.02) or {"items": []})
        failures = []

        def run():
            try:
                engine.YouTubeClient(self.store, self.config, Mock()).uploaded_video_index(video_ids=["known-id"])
            except Exception as exc:
                failures.append(exc)

        with patch.object(engine.YouTubeClient, "service", return_value=service), \
                patch.object(engine.YouTubeClient, "channel_info", return_value={"id": "owner"}):
            threads = [threading.Thread(target=run) for _ in range(6)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
        self.assertEqual(failures, [])
        self.assertFalse(any(thread.is_alive() for thread in threads))
        service.videos.return_value.list.assert_called_once()

    def test_expired_and_invalid_pauses_are_discarded(self):
        for retry in ("2000-01-01T00:00:00+00:00", "not-a-date", "2026-01-01"):
            self.store.save_service_cache(self.scope, "quota_general", {"retry_at": retry})
            self.assertIsNone(self.store.api_pause(self.scope))
            self.assertIsNone(self.store.service_cache(self.scope, "quota_general"))

    def test_throttling_without_a_named_quota_is_temporary(self):
        error = self.error("", "Too many requests", 429)
        self.assertTrue(engine.is_youtube_quota_error(error))
        self.assertEqual(engine.youtube_retry_prediction(error)[0], "api")

    def test_check_cache_is_shared_between_clients_but_forced_checks_are_live(self):
        first = engine.YouTubeClient(self.store, self.config, Mock())
        second = engine.YouTubeClient(self.store, self.config, Mock())
        service = Mock()
        service.videos.return_value.list.return_value.execute.return_value = {"items": []}
        for client in (first, second):
            with patch.object(client, "service", return_value=service), \
                    patch.object(client, "channel_info", return_value={"id": "owner"}):
                client.uploaded_video_index(video_ids=["known-id"])
        self.assertEqual(service.videos.return_value.list.call_count, 1)
        with patch.object(second, "service", return_value=service), \
                patch.object(second, "channel_info", return_value={"id": "owner"}):
            second.uploaded_video_index(force=True, video_ids=["known-id"])
        self.assertEqual(service.videos.return_value.list.call_count, 2)

    def test_automatic_scan_does_not_repeat_checks_without_new_identity_evidence(self):
        signature = engine.file_signature(self.path)
        self.store.upsert(signature, self.path, "Video", "verification_pending", youtube_id="known-id")
        worker = engine.SyncWorker(self.store, lambda: self.config, queue.Queue())
        with patch.object(worker, "is_stable", return_value=True):
            self.assertEqual(list(worker.iter_videos(self.base, self.config)), [])

    def test_shared_cache_is_not_reused_after_account_authorization_changes(self):
        service = Mock()
        service.videos.return_value.list.return_value.execute.return_value = {"items": []}
        with patch.object(engine.YouTubeClient, "service", return_value=service), \
                patch.object(engine.YouTubeClient, "channel_info", return_value={"id": "owner"}):
            first = engine.YouTubeClient(self.store, self.config, Mock())
            first.uploaded_video_index(video_ids=["known-id"])
            first.token_path.write_text("new-authorization")
            second = engine.YouTubeClient(self.store, self.config, Mock())
            second.uploaded_video_index(video_ids=["known-id"])
        self.assertEqual(service.videos.return_value.list.call_count, 2)

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
