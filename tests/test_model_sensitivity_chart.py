"""Check the chart's arithmetic, source anchors, null edge and rebuild identity."""

import hashlib
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("capture_chart", ROOT/"analysis/45_model_sensitivity_chart.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class ModelSensitivityChartTests(unittest.TestCase):
    def setUp(self):
        p = patch("socket.socket.connect", side_effect=AssertionError("No source collection"))
        p.start()
        self.addCleanup(p.stop)

    def test_threshold_matches_formula_and_inverse_capture(self):
        data = m.report()
        fixed = data["fixed_assumptions"]
        self.assertEqual(len(data["points"]), 76)
        self.assertNotIn("capture_fraction", fixed)
        self.assertIsNone(fixed["additional_issuance_near_per_week"])
        with localcontext() as ctx:
            ctx.prec = 80
            k = Decimal(fixed["reward_mint_near_per_week"])*Decimal(fixed["price_usd_per_near"])/(Decimal(fixed["fee_rate"])*Decimal(fixed["destruction_allocation"]))
            previous = None
            for row in data["points"]:
                capture = Decimal(row["capture_fraction"])
                actual = Decimal(row["required_activity_usd_per_week"])
                self.assertEqual(actual, k/capture)
                if previous is not None:
                    self.assertLess(actual, previous)
                previous = actual
            values = {r["capture_pct"]: Decimal(r["required_activity_usd_per_week"]) for r in data["points"]}
            self.assertEqual(values[25], values[50]*2)
            self.assertEqual(values[100], values[50]/2)

    def test_zero_capture_unreachable_and_fixed_units_are_visible(self):
        data = m.report()
        self.assertIsNone(data["zero_capture"]["value"])
        self.assertIn("UNREACHABLE", data["zero_capture"]["status"])
        self.assertFalse(any(r["capture_pct"] == 0 for r in data["points"]))
        svg = m.visual(data)
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib["width"], "800")
        text = " ".join(root.itertext())
        for label in ["Illustrative scenario", "USD billions/week", "21–27 September 2026", "618,436.07 NEAR/week",
                      "$5/NEAR", "0.1% fee", "25% purchase-and-destruction", "Not observed revenue", "investment break-even"]:
            self.assertIn(label, text)

    def test_generated_data_and_svg_match_saved_files_and_sources(self):
        for path, raw in m.outputs().items():
            self.assertEqual(path.read_bytes(), raw)
        for name, expected in m.report()["sources"].items():
            raw = (ROOT/name).read_bytes()
            self.assertEqual(len(raw), expected["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected["sha256"])


if __name__ == "__main__":
    unittest.main()
