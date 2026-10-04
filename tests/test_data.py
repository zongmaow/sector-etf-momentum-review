"""Data contract tests; no network access is used."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import types

import numpy as np
import pandas as pd

from sector_momentum.data import (
    TICKERS, download_yahoo, load_total_returns, normalize_yfinance,
    sha256_file, validate_calendar, validate_research_coverage,
)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.bdate_range("2024-01-02", periods=3, name="date")
        self.levels = pd.DataFrame(
            np.arange(30, dtype=float).reshape(3, 10) + 100,
            index=self.dates, columns=TICKERS,
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "total_return.csv"

    def save(self, frame=None):
        (self.levels if frame is None else frame).to_csv(self.path, index_label="date")
        return self.path

    def supplier(self):
        fields = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]
        raw = pd.DataFrame(index=self.dates)
        for field in fields:
            for ticker in TICKERS:
                raw[(field, ticker)] = self.levels[ticker] if field == "Adj Close" else 0.0
        raw.columns = pd.MultiIndex.from_tuples(raw.columns, names=["Price", "Ticker"])
        return raw

    def test_loader_preserves_levels_and_column_order(self):
        loaded = load_total_returns(self.save(self.levels.loc[:, list(reversed(TICKERS))]))
        pd.testing.assert_frame_equal(loaded, self.levels, check_freq=False)

    def test_loader_rejects_missing_extra_and_duplicate_headers(self):
        for frame in [self.levels.drop(columns="SPY"), self.levels.assign(extra=100)]:
            with self.subTest(columns=list(frame.columns)), self.assertRaises(ValueError):
                load_total_returns(self.save(frame))
        self.path.write_text("date,XLK,XLK\n2024-01-02,100,100\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_total_returns(self.path)

    def test_loader_rejects_missing_nonfinite_nonpositive_and_nonnumeric(self):
        for bad in [np.nan, np.inf, 0, -1, "not-a-price"]:
            frame = self.levels.astype(object)
            frame.iloc[1, 0] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                load_total_returns(self.save(frame))

    def test_dates_are_not_silently_sorted_or_deduplicated(self):
        frames = [self.levels.iloc[::-1], pd.concat([self.levels, self.levels.iloc[[0]]])]
        for frame in frames:
            with self.subTest(dates=list(frame.index)), self.assertRaises(ValueError):
                load_total_returns(self.save(frame))

    def test_calendar_rejects_intraday_timezone_weekend_and_missing_dates(self):
        indexes = [
            pd.DatetimeIndex(["2024-01-02 09:30"]),
            pd.DatetimeIndex(["2024-01-02"], tz="UTC"),
            pd.DatetimeIndex(["2024-01-06"]),
            pd.DatetimeIndex([pd.NaT]),
            pd.DatetimeIndex([]),
        ]
        for index in indexes:
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_calendar(index)

    def test_both_supplier_column_orientations_extract_adj_close(self):
        raw = self.supplier()
        for frame in [raw, raw.swaplevel(0, 1, axis=1)]:
            actual = normalize_yfinance(frame, TICKERS)
            pd.testing.assert_frame_equal(actual, self.levels)
        self.assertFalse(np.allclose(normalize_yfinance(raw, TICKERS), raw["Close"]))

    def test_missing_adjusted_field_or_ticker_is_rejected(self):
        raw = self.supplier()
        for frame in [raw.drop(columns="Adj Close", level=0), raw.drop(columns=[("Adj Close", "SPY")])]:
            with self.subTest(columns=list(frame.columns)), self.assertRaises(ValueError):
                normalize_yfinance(frame, TICKERS)

    def test_flat_single_ticker_requires_explicit_adjusted_field(self):
        raw = pd.DataFrame({"Close": [50, 60, 70], "Adj Close": [100, 110, 120]}, index=self.dates)
        actual = normalize_yfinance(raw, ["SPY"])
        self.assertEqual(actual["SPY"].tolist(), [100, 110, 120])
        with self.assertRaises(ValueError):
            normalize_yfinance(raw.drop(columns="Adj Close"), ["SPY"])

    def test_file_hash_identifies_exact_bytes(self):
        self.path.write_bytes(b"snapshot\n")
        self.assertEqual(sha256_file(self.path), hashlib.sha256(b"snapshot\n").hexdigest())
        original = sha256_file(self.path)
        self.path.write_bytes(b"snapshot\r\n")
        self.assertNotEqual(sha256_file(self.path), original)

    def test_download_saves_snapshot_and_truthful_manifest_without_double_counting(self):
        raw = self.supplier()
        raw[("Dividends", "SPY")] = [0, 5, 0]
        fake = types.SimpleNamespace(__version__="test", download=Mock(return_value=raw))
        with patch.dict("sys.modules", {"yfinance": fake}):
            result = download_yahoo(self.tmp.name, "2024-01-01", "2024-01-10")
        pd.testing.assert_frame_equal(result, self.levels)
        manifest = json.loads((Path(self.tmp.name) / "manifest.json").read_text())
        for filename in ["raw_yahoo.csv", "total_return.csv"]:
            self.assertEqual(manifest["files"][filename]["sha256"], sha256_file(Path(self.tmp.name) / filename))
        self.assertFalse(manifest["download_options"]["auto_adjust"])
        self.assertTrue(manifest["download_options"]["actions"])
        self.assertFalse(fake.download.call_args.kwargs["auto_adjust"])
        self.assertFalse(fake.download.call_args.kwargs["back_adjust"])
        self.assertTrue(fake.download.call_args.kwargs["actions"])
        self.assertTrue(fake.download.call_args.kwargs["keepna"])
        self.assertIn("do not add", manifest["return_treatment"])
        self.assertTrue(any("No independent" in warning for warning in manifest["limitations"]))

    def test_saved_decimal_levels_round_trip_exactly(self):
        self.levels.iloc[0, 0] = 123.12345678901234
        fake = types.SimpleNamespace(__version__="test", download=Mock(return_value=self.supplier()))
        with patch.dict("sys.modules", {"yfinance": fake}):
            download_yahoo(self.tmp.name, "2024-01-01", "2024-01-10")
        loaded = load_total_returns(Path(self.tmp.name) / "total_return.csv")
        np.testing.assert_array_equal(loaded.to_numpy(), self.levels.to_numpy())

    def test_download_rejects_incomplete_action_snapshot(self):
        raw = self.supplier().drop(columns=[("Stock Splits", "SPY")])
        fake = types.SimpleNamespace(__version__="test", download=Mock(return_value=raw))
        with patch.dict("sys.modules", {"yfinance": fake}), self.assertRaisesRegex(ValueError, "action fields"):
            download_yahoo(self.tmp.name, "2024-01-01", "2024-01-10")
        self.assertFalse((Path(self.tmp.name) / "manifest.json").exists())


class ResearchCoverageTests(unittest.TestCase):
    def setUp(self):
        # January 1 and January 15 were NYSE holidays in this fixed example.
        self.dates = pd.bdate_range("2024-01-01", "2024-01-31").difference(
            pd.DatetimeIndex(["2024-01-01", "2024-01-15"])
        )
        self.levels = pd.DataFrame(100.0, index=self.dates, columns=TICKERS)

    def test_normal_holidays_are_not_missing_sessions(self):
        report = validate_research_coverage(self.levels, "2024-01-01", "2024-01-31")
        self.assertEqual(report["expected_sessions"], 21)
        self.assertEqual(report["observed_sessions"], 21)
        self.assertEqual(report["missing_sessions"], 0)

    def test_missing_last_month_end_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "2024-01-31"):
            validate_research_coverage(self.levels.iloc[:-1], "2024-01-01", "2024-01-31")

    def test_missing_middle_session_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "2024-01-17"):
            validate_research_coverage(self.levels.drop(pd.Timestamp("2024-01-17")), "2024-01-01", "2024-01-31")

    def test_holiday_observation_is_rejected(self):
        frame = self.levels.reindex(self.levels.index.union(pd.DatetimeIndex(["2024-01-15"]))).fillna(100.0)
        with self.assertRaisesRegex(ValueError, "non-session observations=1"):
            validate_research_coverage(frame, "2024-01-01", "2024-01-31")

    def test_historical_and_weekend_bounds_use_explicit_calendar_range(self):
        dates = pd.DatetimeIndex(["1998-12-16", "1998-12-17", "1998-12-18"])
        levels = pd.DataFrame(100.0, index=dates, columns=TICKERS)
        report = validate_research_coverage(levels, "1998-12-16", "1998-12-20")
        self.assertEqual(report["expected_sessions"], 3)

    def test_invalid_bounds_are_rejected(self):
        bounds = [
            ("2024-02-01", "2024-01-31"),
            ("2024-01-01 09:00", "2024-01-31"),
            ("NaT", "2024-01-31"),
        ]
        for start, end in bounds:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                validate_research_coverage(self.levels, start, end)


if __name__ == "__main__":
    unittest.main()
