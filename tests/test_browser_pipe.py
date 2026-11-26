import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_layout as fixture
from PySide6.QtTest import QTest
from youtube_sync_browser_pipe import BrowserPipe


class BrowserPipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def test_cookie_and_browser_apis_are_not_available_to_the_player(self):
        pipe = Mock()
        for method, session in (("Network.getCookies", "session"), ("Storage.getCookies", None),
                                 ("Browser.close", None), ("Runtime.evaluate", None)):
            self.assertFalse(BrowserPipe.request(pipe, method, {}, Mock(), session))
        pipe.alive.assert_not_called()

    def test_real_windows_child_inherits_only_the_player_pipe_handles(self):
        script = r'''
import json, msvcrt, os, sys
arg=next(value for value in sys.argv if value.startswith('--remote-debugging-io-pipes='))
incoming,outgoing=map(int,arg.split('=',1)[1].split(','))
read=msvcrt.open_osfhandle(incoming,os.O_RDONLY|os.O_BINARY)
write=msvcrt.open_osfhandle(outgoing,os.O_WRONLY|os.O_BINARY)
data=b''
while b'\0' not in data:
    chunk=os.read(read,4096)
    if not chunk: sys.exit(2)
    data+=chunk
request=json.loads(data.split(b'\0',1)[0])
reply={'id':request['id'],'result':{'echo':request['params'],'transport':'private-pipe'}}
os.write(write,json.dumps(reply).encode()+b'\0')
os.close(read)
os.close(write)
'''
        with tempfile.TemporaryDirectory() as folder:
            pipe = BrowserPipe([sys.executable, "-c", script], Path(folder))
            results = []
            try:
                self.assertFalse(os.get_inheritable(pipe.read_fd))
                self.assertFalse(os.get_inheritable(pipe.write_fd))
                self.assertTrue(pipe.request("Target.getTargets", {"marker": 42}, results.append))
                for _ in range(250):
                    QTest.qWait(20)
                    if results:
                        break
                self.assertEqual(results[0]["result"], {"echo": {"marker": 42}, "transport": "private-pipe"})
                self.assertEqual(pipe.process.wait(timeout=3), 0)
            finally:
                pipe.mark_closed()
                if pipe.process.poll() is None:
                    pipe.process.terminate()  # Only the test's Python echo process.
                    pipe.process.wait(timeout=3)
                pipe.deleteLater()

    def test_launch_arguments_have_no_network_debugger_or_security_overrides(self):
        import youtube_sync_browser_pipe as module
        real_popen = module.subprocess.Popen
        # A short-lived Python process is used instead of opening a browser.
        captured = []
        def launch(args, **kwargs):
            captured.append((args, kwargs))
            return real_popen([sys.executable, "-c", "pass"], **kwargs)
        with tempfile.TemporaryDirectory() as folder, patch.object(module.subprocess, "Popen", side_effect=launch):
            pipe = BrowserPipe(["chrome.exe", "--user-data-dir=" + folder], Path(folder))
            try:
                pipe.process.wait(timeout=3)
                args, kwargs = captured[0]
                self.assertIn("--remote-debugging-pipe", args)
                self.assertEqual(len(kwargs["startupinfo"].lpAttributeList["handle_list"]), 2)
                self.assertTrue(kwargs["close_fds"])
                for forbidden in ("--remote-debugging-port", "--remote-allow-origins", "--disable-web-security", "--enable-automation"):
                    self.assertFalse(any(arg.startswith(forbidden) for arg in args))
            finally:
                pipe.mark_closed()
                pipe.deleteLater()
