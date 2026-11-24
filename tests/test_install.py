from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_layout as fixture
import youtube_sync_install as install
import youtube_sync_updater as updater
from test_updater import package_bytes, metadata


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.body = package_bytes()
        self.path = self.folder / updater.package_name("1.1")
        self.path.write_bytes(self.body)
        self.release = updater.parse_release(metadata(self.body))
        for context in (patch.object(updater, "APP_VERSION", "1.0"),
                        patch.object(install, "installer_identity", return_value=("YouTubeSync", "1.1", "YouTubeSync Installer"))):
            context.start()
            self.addCleanup(context.stop)

    def test_rechecks_digest_before_execution(self):
        self.path.write_bytes(self.body + b"changed")
        with self.assertRaises(ValueError):
            install.prepare_install(self.path, self.release)

    def test_rejects_installed_or_older_version(self):
        with patch.object(updater, "APP_VERSION", "1.1"):
            with self.assertRaises(ValueError):
                install.prepare_install(self.path, self.release)

    def test_launch_is_detached_waits_for_app_and_never_forces_close_or_reboot(self):
        plan = install.prepare_install(self.path, self.release)
        with patch.object(install.subprocess, "Popen") as process:
            install.launch_installer(plan, "en", pid=1234)
        command = process.call_args.args[0]
        self.assertTrue(Path(command[0]).samefile(self.path))
        for argument in ("/UPDATEPID=1234", "/NORESTART", "/NOCLOSEAPPLICATIONS", "/LANG=english", "/RELAUNCH=1"):
            self.assertIn(argument, command)
        self.assertNotIn("/FORCECLOSEAPPLICATIONS", command)
        self.assertTrue(process.call_args.kwargs["close_fds"])

    def test_changed_file_is_not_executed(self):
        plan = install.prepare_install(self.path, self.release)
        self.path.write_bytes(self.body + b"changed")
        with patch.object(install.subprocess, "Popen") as process:
            with self.assertRaises(ValueError):
                install.launch_installer(plan, "es")
        process.assert_not_called()

    def test_cancel_installation_confirmation_does_not_close_or_run(self):
        from youtube_sync_update_ui import UpdatePanel
        from youtube_sync_i18n_widgets import QMessageBox
        panel = UpdatePanel(self.folder)
        panel.release, panel.downloaded_path = self.release, self.path
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No), patch("youtube_sync_update_ui.threading.Thread") as worker:
            panel.request_install()
        worker.assert_not_called()
        self.assertFalse(panel.preparing)
        panel.shutdown()
        panel.close()

    def test_installer_keeps_userdata_and_has_stable_app_identity(self):
        script = (fixture.ROOT / "packaging/YouTubeSync.iss").read_text(encoding="utf-8")
        self.assertNotIn("[UninstallDelete]", script)
        self.assertNotIn("{userappdata}", script)
        self.assertIn("PrivilegesRequired=lowest", script)
        self.assertIn("UsePreviousAppDir=yes", script)
        self.assertIn("WaitForSingleObject(Process, 90000)", script)
        self.assertIn("YouTubeSync Installer", script)


class UpdateShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.ResponsiveLayoutTests.setUp(self)

    def tearDown(self):
        fixture.ResponsiveLayoutTests.tearDown(self)

    def test_active_transfer_prevents_installation(self):
        self.window.worker = Mock(active_path="video.mp4")
        with patch.object(fixture.ui, "launch_installer") as launch, patch.object(fixture.ui.QMessageBox, "warning"):
            self.window.install_update(Mock())
        launch.assert_not_called()

    def test_installer_failure_keeps_app_open(self):
        with patch.object(fixture.ui, "launch_installer", side_effect=OSError("test")), patch.object(fixture.ui.QMessageBox, "warning"):
            self.window.install_update(Mock())
        self.assertFalse(self.window._allow_exit)

    def test_startup_entry_is_refreshed_after_install_location_changes(self):
        self.window.config.run_at_startup = True
        self.window.config.watch_folder = str(fixture.ROOT)
        self.window.config.client_secret_path = str(Path(__file__))
        with patch.object(fixture.ui.engine, "set_run_at_startup") as startup, patch.object(self.window, "check_youtube"), patch.object(self.window, "start_worker"):
            self.window.initialize_session()
        startup.assert_called_once_with(True)

    def test_approved_update_uses_real_shutdown_not_tray_hide(self):
        with patch.object(fixture.ui, "launch_installer") as launch, patch.object(self.window, "stop_background_work") as stop, patch.object(fixture.ui.QApplication, "quit") as quit_app:
            self.window.install_update(Mock())
        launch.assert_called_once()
        stop.assert_called_once()
        quit_app.assert_called_once()
        self.assertTrue(self.window._allow_exit)
