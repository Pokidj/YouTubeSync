import io
import json
import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from googleapiclient.http import HttpRequest, MediaIoBaseUpload
from test_layout import ui

engine = ui.engine


class UploadTransportTests(unittest.TestCase):
    def test_308_without_location_continues_to_next_chunk(self):
        store = Mock()
        store.api_pause.return_value = None
        store.token_path_for.return_value = Path("test-token-not-read")
        client = engine.YouTubeClient(store, engine.Config(), Mock())
        with patch.object(client, "_authorize", return_value=Mock()), patch.object(engine, "build") as build:
            client.service()
        transport = build.call_args.kwargs["http"]
        self.assertEqual(transport.http.timeout, 30)
        self.assertNotIn(308, transport.http.redirect_codes)
        self.assertIn(301, transport.http.redirect_codes)
        transport.http.proxy_info = None
        media = MediaIoBaseUpload(io.BytesIO(b"12345678"), "video/mp4", chunksize=4, resumable=True)
        responses = [
            (engine.httplib2.Response({"status": "200", "location": "http://127.0.0.1/fake-session"}), b""),
            (engine.httplib2.Response({"status": "308", "range": "bytes=0-3"}), b""),
            (engine.httplib2.Response({"status": "201"}), b'{"id":"test-video"}'),
        ]
        request = HttpRequest(transport, lambda response, body: json.loads(body),
                              "http://127.0.0.1/fake-start", method="POST", body="{}", resumable=media)
        # Replace socket I/O only: exercise the actual redirect and chunk-processing logic.
        with patch.object(transport.http, "_conn_request", side_effect=responses) as network:
            status, body = request.next_chunk()
            self.assertIsNone(body)
            self.assertEqual(status.progress(), 0.5)
            _, body = request.next_chunk()
            self.assertEqual(body["id"], "test-video")
            self.assertEqual(network.call_count, 3)

    def test_error_record_does_not_delete_a_processing_video(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            path = Path(temporary) / "video.mp4"
            path.write_bytes(b"test-video")
            store = Mock()
            store.has_success.return_value = False
            store.upload_identity.return_value = ("Video", "remote-id")
            store.upload_status.return_value = "error"
            client = Mock()
            client.verify_local_file.return_value = (True, "remote-id", "fingerprint", "processing")
            worker = engine.SyncWorker(store, engine.Config, queue.Queue())
            worker.handle_file(path, client)
            client.delete_video.assert_not_called()
            client.upload.assert_not_called()
            self.assertEqual(store.upsert.call_args.args[3], "processing")

    def test_cancel_does_not_delete_remote_videos(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            path = Path(temporary) / "video.mp4"
            path.write_bytes(b"test-video")
            store = Mock()
            store.has_success.return_value = False
            store.upload_identity.return_value = ("", "")
            client = Mock()
            client.verify_local_file.return_value = (False, "", "missing", "missing")
            client.upload.side_effect = engine.UploadCancelled("Cancelado")
            worker = engine.SyncWorker(store, engine.Config, queue.Queue())
            worker.handle_file(path, client)
            client.delete_video.assert_not_called()
            client.remove_incomplete_upload.assert_not_called()
            self.assertEqual(store.upsert.call_args.args[3], "cancelled")

    def test_processing_record_only_becomes_success_after_confirmation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            base = Path(temporary)
            path = base / "video.mp4"
            path.write_bytes(b"test-video")
            with patch.object(engine, "app_dir", return_value=base):
                store = engine.Store()
                signature = engine.file_signature(path)
                store.remember_upload(signature, path, "Video", "remote-id", reason="processing")
                self.assertFalse(store.has_success(signature))
                client = Mock()
                client.verify_local_file.return_value = (True, "remote-id", "fingerprint", "processed")
                engine.SyncWorker(store, engine.Config, queue.Queue()).handle_file(path, client)
                self.assertTrue(store.has_success(signature))
                self.assertEqual(store.upload_status(signature), "uploaded")
                client.upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
