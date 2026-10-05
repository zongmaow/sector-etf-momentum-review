"""Offline numerical and artifact-comparison checks; no historical vendor inputs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np


def load_script(name):
    path = Path(__file__).resolve().parents[1] / "research" / "effectiveness" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


comparison = load_script("verify_reproduction")
study = load_script("study")


class ArtifactComparisonTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.expected = Path(self.directory.name) / "expected"
        self.actual = Path(self.directory.name) / "actual"

    def test_csv_numeric_format_and_blank_values_are_accepted(self):
        self.expected.write_text("month,value,label\n2020-01,0.10,True\n2020-02,,False\n")
        self.actual.write_text("month,value,label\n2020-01,1e-1,True\n2020-02,,False\n")
        result = comparison.compare_csv(self.expected, self.actual)
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["numeric_cell_count"], 1)
        self.assertEqual(result["max_abs_numeric_difference"], 0)

    def test_csv_changed_numeric_schema_and_text_are_rejected(self):
        self.expected.write_text("month,value,label\n2020-01,0.10,A\n")
        for changed in [
            "month,value,label\n2020-01,0.11,A\n",
            "month,label,value\n2020-01,A,0.10\n",
            "month,value,label\n2020-01,0.10,B\n",
            "month,value,label\n2020-01,0.10,A\n2020-02,0.10,A\n",
        ]:
            with self.subTest(changed=changed):
                self.actual.write_text(changed)
                with self.assertRaises(comparison.ComparisonError):
                    comparison.compare_csv(self.expected, self.actual)

    def test_json_excludes_only_named_top_level_provenance(self):
        self.expected.write_text(json.dumps({"input_sha256": {"old/path": "old"}, "stats": {"n": 3, "value": .25}, "passed": True}))
        self.actual.write_text(json.dumps({"input_sha256": {"new/path": "new"}, "stats": {"n": 3.0, "value": .25}, "passed": True}))
        result = comparison.compare_json(self.expected, self.actual, ("input_sha256",))
        self.assertEqual(result["numeric_leaf_count"], 2)
        with self.assertRaises(comparison.ComparisonError):
            comparison.compare_json(self.expected, self.actual)

    def test_json_changed_value_missing_key_and_boolean_type_are_rejected(self):
        self.expected.write_text(json.dumps({"stats": {"n": 3, "value": .25}, "passed": True}))
        for changed in [
            {"stats": {"n": 3, "value": .26}, "passed": True},
            {"stats": {"n": 3}, "passed": True},
            {"stats": {"n": 3, "value": .25}, "passed": 1},
        ]:
            with self.subTest(changed=changed):
                self.actual.write_text(json.dumps(changed))
                with self.assertRaises(comparison.ComparisonError):
                    comparison.compare_json(self.expected, self.actual)


class EffectivenessNumericalTests(unittest.TestCase):
    def test_intercept_hac_has_known_bartlett_and_finite_sample_variance(self):
        # Four observations: mean 2.5, centered sum of squares 5, lag-one
        # centered cross sum 1.25. Bartlett lag-one weight is 1/2.
        y = np.array([1., 2., 3., 4.])
        x = np.ones((4, 1))
        no_lag = study.hac_ols(y, x, lags=0)
        one_lag = study.hac_ols(y, x, lags=1)
        self.assertAlmostEqual(no_lag["coef"][0], 2.5)
        self.assertAlmostEqual(no_lag["se"][0] ** 2, 5 / 12)
        self.assertAlmostEqual(one_lag["se"][0] ** 2, 25 / 48)
        self.assertEqual(one_lag["n"], 4)

    def test_holm_keeps_original_order_and_monotone_family_correction(self):
        np.testing.assert_allclose(study.holm([.04, .01, .03]), [.06, .03, .06])
        np.testing.assert_allclose(study.holm([.8, .7, .9]), [1., 1., 1.])

    def test_hac_rejects_unidentified_state_contrast(self):
        # If a state is true in every month, its coefficient cannot be
        # distinguished from the intercept; reporting a contrast would mislead.
        self.assertIsNone(study.hac_ols([1., 2., 3., 4.], np.ones((4, 2))))


if __name__ == "__main__":
    unittest.main()
