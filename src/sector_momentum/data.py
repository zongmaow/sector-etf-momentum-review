"""Load daily adjusted-price levels and preserve the supplier snapshot.

Yahoo's ``Adj Close`` is used as a supplier-adjusted total-return proxy. Its
adjustments are not reconstructed or independently certified here. In particular,
dividends must not be credited again when returns are calculated from these levels.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

SECTORS = ("XLK", "XLF", "XLE", "XLY", "XLP", "XLV", "XLI", "XLB", "XLU")
BENCHMARK = "SPY"
TICKERS = SECTORS + (BENCHMARK,)


def validate_calendar(index: pd.Index) -> None:
    """Require distinct, increasing, timezone-naive daily observation dates.

    This validates observed dates. It does not identify every missing exchange
    session: an independently sourced exchange calendar is outside this loader.
    """
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("The date index must be a DatetimeIndex.")
    if len(index) == 0:
        raise ValueError("The input has no observations.")
    if index.hasnans:
        raise ValueError("Dates contain missing or invalid values.")
    if index.tz is not None:
        raise ValueError("Daily dates must be timezone-naive.")
    if not index.equals(index.normalize()):
        raise ValueError("Dates must represent daily observations, without times.")
    if not index.is_unique:
        raise ValueError("Duplicate observation dates are not allowed.")
    if not index.is_monotonic_increasing:
        raise ValueError("Observation dates must be in strictly increasing order.")
    if (index.dayofweek >= 5).any():
        raise ValueError("Weekend observations are not valid for these US ETFs.")


def _validate_levels(frame: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    validate_calendar(frame.index)
    if frame.columns.has_duplicates:
        raise ValueError("Duplicate ticker columns are not allowed.")
    missing = [ticker for ticker in tickers if ticker not in frame.columns]
    if missing:
        raise ValueError(f"Missing required adjusted-price columns: {missing}")
    try:
        selected = frame.loc[:, list(tickers)].apply(pd.to_numeric, errors="raise")
        selected = selected.astype(float)
    except (ValueError, TypeError) as exc:
        raise ValueError("Adjusted-price levels must be numeric.") from exc
    values = selected.to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("Adjusted-price levels must be finite; missing data is not filled.")
    if (values <= 0).any():
        raise ValueError("Adjusted-price levels must be strictly positive.")
    selected.index = selected.index.rename("date")
    selected.columns.name = None
    return selected


def load_total_returns(path: str | Path) -> pd.DataFrame:
    """Load ``date`` plus all ten ETF adjusted-price columns from a wide CSV.

    Despite the conventional filename ``total_return.csv``, values are levels,
    not daily returns. No sorting, interpolation, or forward filling is applied.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), None)
    if not header:
        raise ValueError("The CSV is empty.")
    if len(header) != len(set(header)):
        raise ValueError("Duplicate CSV columns are not allowed.")
    expected = {"date", *TICKERS}
    if set(header) != expected:
        missing = sorted(expected - set(header))
        extra = sorted(set(header) - expected)
        raise ValueError(f"CSV schema mismatch; missing={missing}, extra={extra}.")
    frame = pd.read_csv(path, encoding="utf-8-sig", float_precision="round_trip")
    try:
        dates = pd.to_datetime(frame.pop("date"), errors="raise")
        frame.index = pd.DatetimeIndex(dates, name="date")
    except (ValueError, TypeError) as exc:
        raise ValueError("The date column contains invalid dates.") from exc
    return _validate_levels(frame, TICKERS)


def validate_research_coverage(
    levels: pd.DataFrame,
    start: str = "1998-12-31",
    end: str = "2025-12-31",
) -> dict:
    """Require every NYSE session in the inclusive research window.

    The loader checks the observations that exist; this separate research gate
    also checks dates that are absent. A missing month-end cannot silently move
    a signal to an earlier date, nor can a missing session delay execution.

    ``exchange_calendars`` constructs a bounded schedule, with a moving default
    start approximately twenty years before today. Explicit bounds are essential
    for this 1998-starting study. A seven-day buffer allows holiday/weekend bounds
    and a one-date research window without requesting an out-of-bounds label.
    Dates outside the requested window are retained but not counted by this gate.

    This checks against the library's XNYS session schedule, not an independently
    certified official exchange calendar or the correctness of adjusted prices.
    """
    try:
        import exchange_calendars as xcals
    except ImportError as exc:
        raise RuntimeError("Install exchange_calendars to validate research session coverage.") from exc
    _validate_levels(levels, TICKERS)
    try:
        start_date, end_date = pd.Timestamp(start), pd.Timestamp(end)
    except (ValueError, TypeError) as exc:
        raise ValueError("Research bounds must be valid daily dates.") from exc
    for date in (start_date, end_date):
        if pd.isna(date) or date.tz is not None or date != date.normalize():
            raise ValueError("Research bounds must be timezone-naive daily dates.")
    if start_date > end_date:
        raise ValueError("Research start must not follow its inclusive end date.")
    calendar = xcals.get_calendar(
        "XNYS",
        start=start_date - pd.Timedelta(days=7),
        end=end_date + pd.Timedelta(days=7),
    )
    expected = pd.DatetimeIndex(calendar.sessions_in_range(start_date, end_date))
    if expected.tz is not None:
        expected = expected.tz_localize(None)
    if expected.empty:
        raise ValueError("The research window contains no NYSE sessions.")
    observed = levels.index[(levels.index >= start_date) & (levels.index <= end_date)]
    missing = expected.difference(observed)
    unexpected = observed.difference(expected)
    if len(missing) or len(unexpected):
        missing_dates = [date.date().isoformat() for date in missing[:10]]
        unexpected_dates = [date.date().isoformat() for date in unexpected[:10]]
        raise ValueError(
            "NYSE research session coverage mismatch; "
            f"missing={len(missing)} {missing_dates}, "
            f"non-session observations={len(unexpected)} {unexpected_dates}. "
            "Do not fill gaps or shift signal/execution dates."
        )
    return {
        "status": "passed",
        "calendar": "XNYS",
        "calendar_library": "exchange_calendars",
        "calendar_library_version": getattr(xcals, "__version__", "unknown"),
        "research_start_inclusive": start_date.date().isoformat(),
        "research_end_inclusive": end_date.date().isoformat(),
        "expected_sessions": len(expected),
        "observed_sessions": len(observed),
        "missing_sessions": 0,
        "non_session_observations": 0,
        "observations_outside_window": len(levels) - len(observed),
        "limitation": "Coverage checked against the library schedule; adjusted-return accuracy is not certified.",
    }


def normalize_yfinance(data: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    """Extract explicit ``Adj Close`` fields, accepting either column orientation.

    ``Close`` is deliberately not a fallback. With ``auto_adjust=False`` Yahoo
    exposes both fields, and silently selecting another field would change the
    treatment of corporate actions.
    """
    tickers = tuple(tickers)
    if not tickers or len(tickers) != len(set(tickers)):
        raise ValueError("Requested tickers must be nonempty and distinct.")
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("The supplier returned no data.")
    if data.columns.has_duplicates:
        raise ValueError("The supplier returned duplicate columns.")
    if isinstance(data.columns, pd.MultiIndex):
        if data.columns.nlevels != 2:
            raise ValueError("Expected a two-level Yahoo column index.")
        field_levels = [
            level for level in range(2)
            if "Adj Close" in data.columns.get_level_values(level)
        ]
        if len(field_levels) != 1:
            raise ValueError("An explicit, unambiguous Adj Close field is required.")
        levels = data.xs("Adj Close", axis=1, level=field_levels[0]).copy()
    else:
        if len(tickers) != 1 or "Adj Close" not in data.columns:
            raise ValueError("Flat Yahoo columns require one ticker and an Adj Close field.")
        levels = data.loc[:, ["Adj Close"]].copy()
        levels.columns = [tickers[0]]
    return _validate_levels(levels, tickers)


def sha256_file(path: str | Path) -> str:
    """Hash the exact saved bytes; a hash checks identity, not economic validity."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_yahoo(output_dir: str | Path, start: str, end: str) -> pd.DataFrame:
    """Download all ETFs, save supplier fields, adjusted levels, and a manifest.

    ``start`` is inclusive and ``end`` exclusive, following the supplier API.
    Network access and yfinance are needed only when this function is called.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Install yfinance to download the supplier data.") from exc
    if pd.Timestamp(start) >= pd.Timestamp(end):
        raise ValueError("start must precede the exclusive end date.")
    raw = yf.download(
        list(TICKERS),
        start=start,
        end=end,
        auto_adjust=False,
        back_adjust=False,
        actions=True,
        repair=False,
        keepna=True,
        ignore_tz=True,
        group_by="column",
        threads=False,
        progress=False,
    )
    levels = normalize_yfinance(raw, TICKERS)
    required_fields = {"Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"}
    if not isinstance(raw.columns, pd.MultiIndex) or raw.columns.nlevels != 2:
        raise ValueError("Expected multi-ticker supplier OHLC and action fields.")
    field_level = next(
        level for level in range(2) if "Adj Close" in raw.columns.get_level_values(level)
    )
    ticker_level = 1 - field_level
    for ticker in TICKERS:
        fields = set(raw.xs(ticker, axis=1, level=ticker_level).columns)
        if not required_fields.issubset(fields):
            raise ValueError(f"Supplier snapshot is missing OHLC/action fields for {ticker}: {sorted(required_fields - fields)}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_yahoo.csv"
    levels_path = output_dir / "total_return.csv"
    raw.to_csv(raw_path, index_label="date", float_format="%.17g")
    levels.to_csv(levels_path, index_label="date", float_format="%.17g")
    manifest = {
        "schema_version": 1,
        "source": "Yahoo Finance via yfinance",
        "source_url": "https://finance.yahoo.com/",
        "yfinance_version": getattr(yf, "__version__", "unknown"),
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_start_inclusive": start,
        "requested_end_exclusive": end,
        "tickers": list(TICKERS),
        "observed_start": levels.index[0].date().isoformat(),
        "observed_end": levels.index[-1].date().isoformat(),
        "observations": len(levels),
        "download_options": {
            "auto_adjust": False, "back_adjust": False, "actions": True,
            "repair": False, "keepna": True, "ignore_tz": True,
        },
        "files": {
            "raw_yahoo.csv": {"sha256": sha256_file(raw_path), "column_levels": raw.columns.nlevels},
            "total_return.csv": {"sha256": sha256_file(levels_path), "value_type": "supplier Adj Close levels"},
        },
        "return_treatment": "Compute returns from Adj Close ratios; do not add supplier dividends again.",
        "close_treatment": "Close is preserved as supplied and may reflect vendor split adjustments; it is not certified unadjusted data.",
        "checks_performed": [
            "all requested tickers present", "distinct increasing daily dates",
            "finite strictly positive adjusted levels", "OHLC and action fields retained",
        ],
        "limitations": [
            "No independent reconstruction or certification of total returns or corporate actions.",
            "No independent exchange-calendar check for missing trading sessions.",
            "Vendor adjustments and historical data may be revised; hashes identify this saved snapshot only.",
            "Recorded action fields are for audit; they are not an additional cash-flow input to adjusted-level returns.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return levels
