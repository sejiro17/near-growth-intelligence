"""Exercise the console launcher without the repository on Python's import path."""

import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from websockets.sync.client import connect


ROOT = Path(__file__).resolve().parents[1]


class DashboardStartupTests(unittest.TestCase):
    def test_console_launcher_renders_opening_and_all_tabs(self):
        launcher = Path(sys.executable).parent / "streamlit"
        self.assertTrue(launcher.is_file(), "Run with the environment containing Streamlit")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile(mode="w+") as log:
            process = subprocess.Popen([
                str(launcher), "run", str(ROOT / "dashboard/app.py"),
                "--server.headless=true", "--server.address=127.0.0.1", f"--server.port={port}",
                "--browser.gatherUsageStats=false", "--server.fileWatcherType=none",
            ], cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 30
                opener = build_opener(ProxyHandler({}))
                while True:
                    try:
                        with opener.open(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        pass
                    if process.poll() is not None or time.monotonic() >= deadline:
                        log.seek(0)
                        self.fail("Streamlit did not start:\n" + log.read())
                    time.sleep(0.1)
                tabs, headings, markdown, exceptions = [], [], [], []
                with connect(f"ws://127.0.0.1:{port}/_stcore/stream",
                             origin=f"http://127.0.0.1:{port}", subprotocols=["streamlit"],
                             max_size=20 * 1024 * 1024, open_timeout=10) as session:
                    request = BackMsg()
                    request.rerun_script.query_string = ""
                    session.send(request.SerializeToString())
                    deadline = time.monotonic() + 90
                    while True:
                        message = ForwardMsg.FromString(session.recv(timeout=max(0.1, deadline - time.monotonic())))
                        if message.WhichOneof("type") == "script_finished":
                            self.assertEqual(message.script_finished, ForwardMsg.FINISHED_SUCCESSFULLY)
                            break
                        if message.WhichOneof("type") != "delta":
                            continue
                        delta = message.delta
                        if delta.WhichOneof("type") == "add_block" and delta.add_block.HasField("tab"):
                            tabs.append(delta.add_block.tab.label)
                        elif delta.WhichOneof("type") == "new_element":
                            element = delta.new_element
                            if element.HasField("exception"):
                                exceptions.append(element.exception.message)
                            elif element.HasField("heading"):
                                headings.append(element.heading.body)
                            elif element.HasField("markdown"):
                                markdown.append(element.markdown.body)
                self.assertEqual(exceptions, [])
                self.assertIn("NEAR Growth Intelligence", headings)
                self.assertEqual(tabs, ["Growth", "Growth drivers", "Account returns", "Concentration",
                                        "Economics", "Decision priorities", "Account explorer"])
                self.assertIn("Persistence and scoped execution", headings)
                self.assertIn("Supply reconciliation remains open", headings)
                for question in ("What grew?", "How much persisted?", "What executed successfully?",
                                 "What economic demand or value capture is demonstrated?"):
                    self.assertIn(question, "\n".join(markdown))
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
