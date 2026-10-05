"""Frozen top-three, long-only momentum transfer check on French ten industries.

This uses value-weighted *research industry portfolios*, not synthetic ETF history.
Only monthly data are available, so formation is at prior month end rather than
the ETF engine's following-session close. Cost is hypothetical and applies only
to switches between industry baskets, not constituent-level implementation.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import sys

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "reports/local/effectiveness/external"
RAW_DIR = REPO / "data/raw/french"
sys.path.insert(0, str(REPO / "src"))
from sector_momentum.engine import self_financing_trade
from sector_momentum.evaluation import active_stats, paired_block_bootstrap


def parse_monthly_value_weighted(path: Path) -> pd.DataFrame:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    marker = "Average Value Weighted Returns -- Monthly"
    starts = [i for i, line in enumerate(lines) if line.strip() == marker]
    if len(starts) != 1:
        raise ValueError("Exactly one monthly value-weighted section is required")
    header = next(csv.reader([lines[starts[0] + 1]]))
    names = [x.strip() for x in header[1:]]
    if len(names) != 10 or len(set(names)) != 10:
        raise ValueError("Unexpected ten-industry schema")
    rows = []
    for line in lines[starts[0] + 2 :]:
        cells = next(csv.reader([line]))
        if not cells or not (cells[0].strip().isdigit() and len(cells[0].strip()) == 6):
            break
        if len(cells) != 11:
            raise ValueError("Unexpected row width")
        date = pd.Period(cells[0].strip(), freq="M")
        values = np.asarray([float(x.strip()) for x in cells[1:]])
        if np.isin(values, [-99.99, -999]).any():
            raise ValueError(f"Missing-value sentinel found in {date}")
        if not np.isfinite(values).all() or (values <= -100).any():
            raise ValueError(f"Invalid monthly industry return in {date}")
        rows.append((date, *values / 100))
    result = pd.DataFrame(rows, columns=["month", *names]).set_index("month")
    result = result.loc[:"2025-12"]
    if not result.index.is_unique or not result.index.is_monotonic_increasing:
        raise ValueError("Monthly series must be unique and increasing")
    if not result.index.equals(pd.period_range(result.index[0], result.index[-1], freq="M")):
        raise ValueError("Non-contiguous monthly series")
    return result


def signals_for_holding_month(returns: pd.DataFrame) -> pd.DataFrame:
    levels = (1 + returns).cumprod()
    # Holding month t: level[t-2] / level[t-13] uses eleven returns t-12..t-2.
    return levels.shift(2) / levels.shift(13) - 1


def run_path(returns: pd.DataFrame, scores: pd.DataFrame, kind: str,
             cost_bps: float = 5., start: str = "1960-01") -> pd.DataFrame:
    invest = returns.loc[start:]
    names = list(returns.columns)
    values = np.zeros(len(names))
    cash = 1.
    rows = []
    for month, r in invest.iterrows():
        score = scores.loc[month]
        if score.isna().any():
            raise ValueError("Insufficient warm-up")
        order = sorted(names, key=lambda name: (-score[name], name))
        selected = order[:3] if kind == "MOM12_1" else names
        target = np.array([1 / len(selected) if name in selected else 0 for name in names])
        pre_nav = float(values.sum() + cash)
        pre_weights = values / pre_nav
        after, fee, buys, sells = self_financing_trade(values, cash, target, cost_bps / 10000)
        pnl = after * r.to_numpy()
        values = after + pnl
        cash = 0.
        nav = float(values.sum())
        if not np.isclose(nav - pre_nav, pnl.sum() - fee, atol=1e-11 * pre_nav):
            raise ArithmeticError("Monthly self-financing reconciliation failed")
        if not np.isclose(fee, cost_bps / 10000 * (buys + sells), atol=1e-11 * pre_nav):
            raise ArithmeticError("Per-side cost reconciliation failed")
        rows.append({"month": month, "nav": nav, "return": nav / pre_nav - 1,
                     "fee_fraction": fee / pre_nav, "half_gross_turnover": (buys + sells) / (2 * pre_nav),
                     "selected": ",".join(selected),
                     "signal_start": str(month - 13), "signal_end": str(month - 2),
                     **{f"pre_weight_{name}": float(pre_weights[j]) for j, name in enumerate(names)},
                     **{f"target_weight_{name}": float(target[j]) for j, name in enumerate(names)},
                     **{f"contribution_{name}": float(pnl[j] / pre_nav) for j, name in enumerate(names)}})
    return pd.DataFrame(rows).set_index("month")


def confidence(active: pd.Series) -> dict:
    stats = active_stats(active, pd.Series(0., index=active.index))
    stats["bootstrap"] = {str(block): paired_block_bootstrap(active, block_size=block, draws=20000, seed=20261004)
                          for block in (3, 6, 12)}
    values = active.to_numpy()
    n = len(values)
    errors = values - values.mean()
    meat = float(errors @ errors)
    for lag in range(1, min(12, n - 1) + 1):
        meat += 2 * (1 - lag / 13) * float(errors[lag:] @ errors[:-lag])
    se = math.sqrt(max(meat * n / (n - 1) / n ** 2, 0))
    stats["mean_hac12_se_ann"] = se * 12
    stats["mean_hac12_asymptotic_normal_p"] = math.erfc(abs(values.mean() / se) / math.sqrt(2)) if se > 0 else None
    return stats


def summarise(momentum: pd.DataFrame, ew: pd.DataFrame, start: str, end: str) -> dict:
    m = momentum.loc[start:end]
    b = ew.loc[start:end]
    active = m["return"] - b["return"]
    n = len(m)
    cum_m = float((1 + m["return"]).prod())
    cum_b = float((1 + b["return"]).prod())
    nav_m = np.r_[1., (1 + m["return"]).cumprod().to_numpy()]
    nav_b = np.r_[1., (1 + b["return"]).cumprod().to_numpy()]
    return {"period": f"{start} to {end}", "n_months": n,
            "mom_cagr": cum_m ** (12 / n) - 1, "ew10_cagr": cum_b ** (12 / n) - 1,
            "mom_total_return": cum_m - 1, "ew10_total_return": cum_b - 1,
            "mom_max_drawdown_monthly": float((nav_m / np.maximum.accumulate(nav_m) - 1).min()),
            "ew10_max_drawdown_monthly": float((nav_b / np.maximum.accumulate(nav_b) - 1).min()),
            "mom_volatility_ann": float(m["return"].std(ddof=1) * np.sqrt(12)),
            "ew10_volatility_ann": float(b["return"].std(ddof=1) * np.sqrt(12)),
            "mom_mean_fee_ann": float(12 * m.fee_fraction.mean()),
            "ew10_mean_fee_ann": float(12 * b.fee_fraction.mean()),
            "monthly_active_win_fraction": float((active > 0).mean()),
            **confidence(active)}


def checks() -> dict:
    # First formation buys 1/(1+c), fee c/(1+c); no risk-free cash is silently added.
    x, fee, buys, sells = self_financing_trade(np.zeros(10), 1., np.repeat(.1, 10), .0005)
    assert np.isclose(fee, .0005 / 1.0005, atol=1e-14)
    assert np.isclose(x.sum() + fee, 1., atol=1e-14)
    assert np.isclose(buys, x.sum()) and sells == 0
    # Independent direct compounding verifies every signal's eleven-return window.
    r = parse_monthly_value_weighted(RAW_DIR / "10_Industry_Portfolios.csv")
    s = signals_for_holding_month(r)
    errors = []
    for month in pd.period_range("1960-01", "2025-12", freq="M"):
        direct = (1 + r.loc[month - 12 : month - 2]).prod() - 1
        assert len(r.loc[month - 12 : month - 2]) == 11
        errors.append(np.max(np.abs(direct.to_numpy() - s.loc[month].to_numpy())))
    assert max(errors) < 1e-12
    jan20 = pd.Period("2020-01", freq="M")
    altered = r.copy()
    altered.loc[jan20 - 1] = .5  # Excluded recent month.
    altered.loc[jan20] = -.5     # Outcome month not yet known.
    altered.loc[jan20 + 1:] = .25 # Future months not yet known.
    assert np.allclose(signals_for_holding_month(altered).loc[jan20], s.loc[jan20], atol=1e-12)
    # Pretrade weights must reflect prior returns, rather than reset every day.
    path = pd.read_csv(ROOT / "ew10_monthly_ledger.csv", index_col=0)
    prior_r = r.loc[pd.Period("1960-01", freq="M")].to_numpy()
    direct_weights = (1 + prior_r) / (1 + prior_r).sum()
    feb_weights = path.loc["1960-02", [f"pre_weight_{name}" for name in r.columns]].astype(float).to_numpy()
    assert np.allclose(feb_weights, direct_weights, atol=1e-12)
    return {"initial_formation_cost_reconciles": True, "all_monthly_accounting_reconciles": True,
            "signal_direct_compounding_max_abs_error": float(max(errors)),
            "excluded_recent_and_future_returns_do_not_change_signal": True,
            "prior_return_drift_matches_independent_direct_weights": True,
            "holding_signal_latest_return_lag_months": 2, "holding_signal_return_count": 11}


def main() -> None:
    global ROOT, RAW_DIR, REPO
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=REPO)
    parser.add_argument('--raw-dir',type=Path,required=True,help='directory containing saved original 10_Industry_Portfolios.csv; no downloads')
    parser.add_argument('--out',type=Path,help='generated external results; default REPO/reports/local/effectiveness/external')
    args=parser.parse_args()
    REPO=args.repo.resolve(); RAW_DIR=args.raw_dir.resolve()
    ROOT=(args.out or REPO/'reports/local/effectiveness/external').resolve()
    if not (RAW_DIR/'10_Industry_Portfolios.csv').is_file():
        parser.error(f'Missing saved input: {RAW_DIR / "10_Industry_Portfolios.csv"}; no data will be downloaded')
    ROOT.mkdir(parents=True,exist_ok=True)
    r = parse_monthly_value_weighted(RAW_DIR / "10_Industry_Portfolios.csv")
    scores = signals_for_holding_month(r)
    r.to_csv(ROOT / "ff10_monthly_returns_through_2025.csv", index_label="month")
    scores.loc["1960-01":].to_csv(ROOT / "ff10_holding_month_scores.csv", index_label="month")
    paths = {name: run_path(r, scores, name) for name in ("MOM12_1", "EW10")}
    for name, path in paths.items():
        path.to_csv(ROOT / f"{name.lower()}_monthly_ledger.csv", index_label="month")
    returns = pd.concat({name: path["return"] for name, path in paths.items()}, axis=1)
    returns["active"] = returns.MOM12_1 - returns.EW10
    returns.to_csv(ROOT / "comparison_returns.csv", index_label="month")
    summaries = [summarise(paths["MOM12_1"], paths["EW10"], start, end) for start, end in (
        ("1960-01", "1999-12"), ("2000-01", "2025-12"), ("1960-01", "2025-12"))]
    # A supplemental family of three highly related period means; Holm remains
    # valid with dependent tests and prevents privileging the pooled sample.
    pvalues = np.asarray([s["mean_hac12_asymptotic_normal_p"] for s in summaries])
    order = np.argsort(pvalues)
    sorted_adjusted = np.minimum(1., np.maximum.accumulate(pvalues[order] * np.arange(3, 0, -1)))
    adjusted = np.empty(3)
    adjusted[order] = sorted_adjusted
    for s, p in zip(summaries, adjusted):
        s["mean_hac12_holm3_p"] = float(p)
    decadal = []
    for start in range(1960, 2026, 10):
        decadal.append(summarise(paths["MOM12_1"], paths["EW10"], f"{start}-01", f"{min(start + 9, 2025)}-12"))
    (ROOT / "basic_summary.json").write_text(json.dumps({"primary_periods": summaries, "decades": decadal}, indent=2) + "\n")
    pd.DataFrame([{k: v for k, v in s.items() if k != "bootstrap"} for s in summaries + decadal]).to_csv(ROOT / "basic_summary.csv", index=False)
    manifest = {"reference_snapshot_download_date": "2026-10-04", "data_vintage_header": (RAW_DIR / "10_Industry_Portfolios.csv").read_text().splitlines()[0],
                "sources": ["https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/10_Industry_Portfolios_CSV.zip",
                            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_ind_port.html",
                            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
                            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes10.zip",
                            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"],
                "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.iterdir() if p.suffix in (".csv", ".json")},
                "raw_input_sha256": {str(RAW_DIR / "10_Industry_Portfolios.csv"): hashlib.sha256((RAW_DIR / "10_Industry_Portfolios.csv").read_bytes()).hexdigest()},
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "imported_project_source_sha256": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for p in (REPO / "src/sector_momentum/engine.py", REPO / "src/sector_momentum/evaluation.py")},
                "input_first_month": str(r.index[0]), "input_last_month": str(r.index[-1]),
                "test_start": "1960-01", "test_end": "2025-12", "industry_names": list(r.columns),
                "cost_bps_per_side": 5., "classification": "French 10 SIC industry portfolios; stocks within each portfolio value weighted; portfolio weights across industries equal/top-three equal",
                "execution": "prior-month-end theoretical formation; no next-trading-close execution can be represented in monthly data",
                "signal": "holding month t uses compounded eleven monthly returns t-12 through t-2; excludes t-1",
                "limitations": ["These research portfolios are not ETFs, nor reconstructed SPDR histories.",
                                "Cost is a hypothetical external basket switching cost; constituent turnover, fund fees, bid-ask spreads and impact are not measured.",
                                "Full history is revised by French/CRSP; this snapshot is not a vintage point-in-time feed.",
                                "Current French returns use CRSP CIZ with daily compounding and ex-date dividend reinvestment; this changes history relative to earlier FIZ snapshots.",
                                "1960–1999 is a transfer check outside the ETF product sample, not genuinely unseen prospective out-of-sample evidence.",
                                "Initial formation fee is included in January 1960; subperiods use the continuous ledger and do not reset cash or charge another formation fee.",
                                "Final holdings are valued without liquidation costs."],
                "validation": checks()}
    (ROOT / "provenance.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    for s in summaries + decadal:
        print(s["period"], "MOM", round(100*s["mom_cagr"], 3), "EW", round(100*s["ew10_cagr"], 3),
              "active", round(100*s["annualized_arithmetic_active"], 3),
              "CI6", [round(100*x, 3) for x in s["bootstrap"]["6"]["ci95_annualized_arithmetic"]])


if __name__ == "__main__":
    main()
