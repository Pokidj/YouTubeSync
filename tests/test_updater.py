import hashlib
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from test_layout import ui, ROOT
import youtube_sync_updater as updater
import youtube_sync_update_ui as update_ui

sys.path.insert(0, str(ROOT / "scripts"))
import create_release


def package_bytes(version="1.1", extra=None, manifest=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("YouTubeSync/YouTubeSync.exe", b"example-exe")
        archive.writestr("YouTubeSync/_internal/python312.dll", b"example-runtime")
        archive.writestr(updater.MANIFEST, json.dumps(manifest or {
            "app": "YouTubeSync", "version": version, "platform": "windows", "architecture": "x64"}))
        if extra:
            archive.writestr(extra, "unexpected")
    return stream.getvalue()


def metadata(body=None):
    body = package_bytes() if body is None else body
    name = updater.package_name("1.1")
    return {"tag_name": "v1.1", "html_url": updater.RELEASES_URL + "/tag/v1.1", "draft": False,
            "prerelease": False, "body": "Cambios de prueba", "assets": [{
                "name": name, "state": "uploaded", "size": len(body),
                "digest": "sha256:" + hashlib.sha256(body).hexdigest(),
                "browser_download_url": updater.RELEASES_URL + "/download/v1.1/" + name,
            }]}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.opener = Mock()
        self.client = updater.ReleaseClient(self.opener)

    def download(self, body, document=None, cancel=None, progress=None):
        self.opener.open.return_value = io.BytesIO(body)
        return self.client.download(updater.parse_release(document or metadata(body)), self.base,
                                    cancel or threading.Event(), progress or Mock())

    def test_versions_are_compared_numerically_without_downgrades(self):
        self.assertTrue(updater.Release("1.10", "v1.10", "", "", None).is_newer("1.9"))
        self.assertFalse(updater.Release("1.0.0", "v1.0.0", "", "", None).is_newer("1.0"))
        self.assertFalse(updater.Release("0.9", "v0.9", "", "", None).is_newer("1.0"))

    def test_drafts_and_prereleases_are_not_offered(self):
        for flag in ("draft", "prerelease"):
            data = metadata()
            data[flag] = True
            self.assertIsNone(updater.parse_release(data))
        with self.assertRaises(updater.UpdateError):
            updater.release_version("1.1rc1")

    def test_release_without_an_app_asset_does_not_use_the_source_archive(self):
        data = metadata()
        data["assets"][0]["name"] = "source-code.zip"
        result = updater.parse_release(data)
        self.assertTrue(result.is_newer("1.0"))
        self.assertIsNone(result.asset)

    def test_asset_must_have_a_digest_and_belong_to_the_expected_repository(self):
        for change in ({"digest": None}, {"browser_download_url": "https://example.invalid/file.zip"}, {"size": -1}):
            data = metadata()
            data["assets"][0].update(change)
            with self.assertRaises(updater.UpdateError):
                updater.parse_release(data)

    def test_latest_404_means_no_published_release_not_an_update(self):
        self.opener.open.side_effect = urllib.error.HTTPError(updater.LATEST_URL, 404, "Not Found", {}, None)
        self.assertIsNone(self.client.latest())

    def test_rate_limit_is_a_github_error_not_a_youtube_state_change(self):
        self.opener.open.side_effect = urllib.error.HTTPError(updater.LATEST_URL, 403, "Forbidden", {}, None)
        with self.assertRaisesRegex(updater.UpdateError, "GitHub"):
            self.client.latest()

    def test_invalid_metadata_is_reported(self):
        self.opener.open.return_value = io.BytesIO(b"not-json")
        with self.assertRaises(updater.UpdateError):
            self.client.latest()

    def test_latest_request_uses_the_public_repository_without_a_user_token(self):
        self.opener.open.return_value = io.BytesIO(json.dumps(metadata()).encode())
        self.assertEqual(self.client.latest().version, "1.1")
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, updater.LATEST_URL)
        self.assertIsNone(request.get_header("Authorization"))

    def test_verified_download_has_the_expected_bytes_and_no_partial_files(self):
        body = package_bytes()
        progress = Mock()
        result = self.download(body, progress=progress)
        self.assertEqual(result.read_bytes(), body)
        progress.assert_called_with(len(body), len(body))
        self.assertEqual(list(self.base.glob("*.part")), [])

    def test_bad_hash_does_not_replace_an_existing_download(self):
        body = package_bytes()
        data = metadata(body)
        data["assets"][0]["digest"] = "sha256:" + "0" * 64
        existing = self.base / updater.package_name("1.1")
        existing.write_bytes(b"keep-existing")
        with self.assertRaises(updater.UpdateError):
            self.download(body, data)
        self.assertEqual(existing.read_bytes(), b"keep-existing")
        self.assertEqual(list(self.base.glob("*.part")), [])

    def test_truncated_or_oversized_download_is_not_published(self):
        body = package_bytes()
        for size in (len(body) - 1, len(body) + 1):
            with self.subTest(size=size):
                data = metadata(body)
                data["assets"][0]["size"] = size
                with self.assertRaises(updater.UpdateError):
                    self.download(body, data)
        self.assertFalse((self.base / updater.package_name("1.1")).exists())
        self.assertEqual(list(self.base.glob("*.part")), [])

    def test_cancel_cleans_the_partial_file(self):
        cancel = threading.Event()
        with self.assertRaises(updater.DownloadCancelled):
            self.download(package_bytes(), cancel=cancel, progress=lambda _received, _total: cancel.set())
        self.assertEqual(list(self.base.iterdir()), [])

    def test_zip_traversal_is_rejected_without_extracting_any_files(self):
        body = package_bytes(extra="YouTubeSync/../../outside.exe")
        with self.assertRaises(updater.UpdateError):
            self.download(body)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_manifest_version_and_architecture_must_match(self):
        for manifest in ({"app": "YouTubeSync", "version": "1.0", "platform": "windows", "architecture": "x64"},
                         {"app": "YouTubeSync", "version": "1.1", "platform": "windows", "architecture": "arm64"}):
            with self.assertRaises(updater.UpdateError):
                self.download(package_bytes(manifest=manifest))

    def test_redirects_must_remain_on_allowed_https_github_hosts(self):
        for url in ("http://github.com/file", "https://github.com.example.invalid/file", "https://example.invalid/file"):
            with self.assertRaises(updater.UpdateError):
                updater.GitHubRedirects.validate(url)
        updater.GitHubRedirects.validate("https://release-assets.githubusercontent.com/asset?signature=test")

    def test_packager_builds_a_complete_archive_and_checksum(self):
        source, output = self.base / "app", self.base / "release"
        (source / "_internal").mkdir(parents=True)
        (source / "YouTubeSync.exe").write_bytes(b"example-exe")
        (source / "_internal/python312.dll").write_bytes(b"example-runtime")
        package, checksum = create_release.create_package(source, output, "1.1")
        updater.validate_package(package, "1.1")
        self.assertIn(hashlib.sha256(package.read_bytes()).hexdigest(), checksum.read_text())
        with self.assertRaises(ValueError):
            create_release.create_package(source, source / "release", "1.1")

    def test_packager_rejects_personal_configuration(self):
        source = self.base / "app"
        (source / "_internal").mkdir(parents=True)
        (source / "YouTubeSync.exe").write_bytes(b"example-exe")
        (source / "_internal/python312.dll").write_bytes(b"example-runtime")
        (source / "config.json").write_text("{}")
        with self.assertRaises(ValueError):
            create_release.create_package(source, self.base / "release", "1.1")

    def test_packager_does_not_rename_an_old_binary_as_a_new_version(self):
        def old_version(command, **_kwargs):
            Path(command[-1]).write_text(json.dumps({"ok": True, "ssl": True, "version": "1.0"}))
        with patch.object(create_release.subprocess, "run", side_effect=old_version):
            with self.assertRaises(RuntimeError):
                create_release.validate_binary(self.base, "1.1")


class UpdatePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = ui.QApplication.instance() or ui.QApplication([])

    def setUp(self):
        self.panel = update_ui.UpdatePanel(ROOT / "work" / "update-ui-tests")

    def tearDown(self):
        self.panel.shutdown()
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_no_release_is_not_claimed_as_up_to_date(self):
        self.panel.checked(None)
        self.assertIn("No hay", self.panel.status.text())
        self.assertTrue(self.panel.download_button.isHidden())

    def test_new_version_with_a_package_can_be_downloaded(self):
        self.panel.checked(updater.parse_release(metadata()))
        self.assertTrue(self.panel.download_button.isEnabled())
        self.assertEqual(self.panel.download_button.text(), "Descargar 1.1")

    def test_missing_package_disables_download(self):
        data = metadata()
        data["assets"] = []
        self.panel.checked(updater.parse_release(data))
        self.assertFalse(self.panel.download_button.isEnabled())
        self.assertIn("falta el paquete", self.panel.status.text())

    def test_closing_settings_cancels_background_downloads(self):
        self.panel.shutdown()
        self.assertTrue(self.panel.cancel.is_set())
        self.assertTrue(self.panel.closed)

    def test_check_is_asynchronous_and_does_not_allow_parallel_checks(self):
        with patch.object(update_ui.threading, "Thread") as worker:
            self.panel.check()
            self.panel.check()
        worker.assert_called_once()
        self.assertFalse(self.panel.check_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
