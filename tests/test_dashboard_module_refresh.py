"""A script upgrade must not retain an older imported view signature."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class DashboardModuleRefreshTests(unittest.TestCase):
    def test_cached_old_views_are_refreshed_and_all_tabs_render(self):
        with patch("socket.socket.connect", side_effect=AssertionError("No source requests")):
            with patch.object(sys, "path", [str(ROOT / "dashboard"), *sys.path]):
                import research_views

                def previous_signature(data):
                    raise AssertionError("The old one-argument view must not run")

                with patch.object(research_views, "persistent_activity", previous_signature), \
                        patch.object(research_views, "overview", lambda data: None):
                    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=60).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual([tab.label for tab in app.tabs], [
                    "Growth", "Growth drivers", "Account returns", "Concentration",
                    "Economics", "Decision priorities", "Account explorer",
                ])
                self.assertTrue(all(tab.children for tab in app.tabs))
                text = "\n".join(x.value for kind in (app.markdown, app.caption) for x in kind)
                self.assertIn("Full-window independent issuance", text)
                self.assertIn("one protocol-validated reward week", text)
                self.assertNotIn("Independent issuance and actual supply burn remain unavailable.", text)


if __name__ == "__main__":
    unittest.main()
