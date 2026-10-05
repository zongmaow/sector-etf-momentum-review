"""Fixed four environment hypotheses, copied from the frozen parent protocol.

No returns choose thresholds. Outcomes are monthly MOM12_1 minus same-pool EW10,
net hypothetical five basis points per side. The data are monthly research
portfolios, so their timing and investability differ from the ETF implementation.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import math

import numpy as np
import pandas as pd

from analyze_external import REPO, ROOT, RAW_DIR, parse_monthly_value_weighted, signals_for_holding_month

PROTOCOL = REPO / "reports/effectiveness_snapshot/research_protocol.md"
SEED = 20261004
DRAWS = 20000


def parse_factors() -> pd.DataFrame:
    lines = (RAW_DIR / "F-F_Research_Data_Factors.csv").read_text(encoding="utf-8-sig").splitlines()
    header_rows = [i for i, line in enumerate(lines) if line.strip().startswith(",Mkt-RF,")
                   and len(next(csv.reader([lines[i + 1]]))[0].strip()) == 6]
    if len(header_rows) != 1:
        raise ValueError("Unexpected FF factor section count")
    start = header_rows[0]
    names = [x.strip() for x in next(csv.reader([lines[start]]))[1:]]
    if names != ["Mkt-RF", "SMB", "HML", "RF"]:
        raise ValueError("Unexpected FF factor schema")
    rows = []
    for line in lines[start + 1 :]:
        cells = next(csv.reader([line]))
        if not cells or not (cells[0].strip().isdigit() and len(cells[0].strip()) == 6):
            break
        values = np.asarray([float(x.strip()) for x in cells[1:]])
        if len(values) != 4 or not np.isfinite(values).all() or np.isin(values, [-99.99, -999]).any():
            raise ValueError("Missing or malformed factors")
        rows.append((pd.Period(cells[0].strip(), freq="M"), *values / 100))
    result = pd.DataFrame(rows, columns=["month", *names]).set_index("month").loc[:"2025-12"]
    if not result.index.equals(pd.period_range(result.index[0], result.index[-1], freq="M")):
        raise ValueError("Factor months are non-contiguous")
    result["market_total_return"] = result["Mkt-RF"] + result.RF
    if (result.market_total_return <= -1).any():
        raise ValueError("Invalid market total return")
    return result


def compute_features(returns: pd.DataFrame, market: pd.Series) -> pd.DataFrame:
    score = signals_for_holding_month(returns)
    levels = (1 + returns).cumprod()
    recent3 = levels.shift(1) / levels.shift(4) - 1
    ranks_a = score.rank(axis=1, method="average")
    ranks_b = recent3.rank(axis=1, method="average")
    a = ranks_a.sub(ranks_a.mean(axis=1), axis=0)
    b = ranks_b.sub(ranks_b.mean(axis=1), axis=0)
    agreement = (a * b).sum(axis=1, min_count=10) / np.sqrt((a*a).sum(axis=1, min_count=10) * (b*b).sum(axis=1, min_count=10))
    market_levels = (1 + market).cumprod()
    prior_market24 = market_levels.shift(1) / market_levels.shift(25) - 1
    prior_market3 = market_levels.shift(1) / market_levels.shift(4) - 1
    sets = []
    for month, row in score.iterrows():
        sets.append(None if row.isna().any() else set(sorted(score.columns, key=lambda name: (-row[name], name))[:3]))
    stable_count = []
    for i, group in enumerate(sets):
        if i < 2 or any(x is None for x in sets[i-2:i+1]):
            stable_count.append(np.nan)
        else:
            stable_count.append(len(sets[i] & sets[i-1] & sets[i-2]))
    result = pd.DataFrame({"market_total_return": market,
                           "prior_market24": prior_market24, "prior_market3": prior_market3,
                           "recent3_vs_momentum_spearman": agreement,
                           "momentum_std_ddof1": score.std(axis=1, ddof=1),
                           "top3_intersection_three_decisions": stable_count}, index=returns.index)
    result["top3_selected"] = ["" if s is None else ",".join(sorted(s)) for s in sets]
    result["signal_month"] = (result.index - 1).astype(str)
    result["H1"] = (result.prior_market24 < 0) & (result.prior_market3 > 0)
    result["H2"] = result.recent3_vs_momentum_spearman >= 0
    for family, start, end in [("early", "1950-01", "1959-12"), ("late", "1960-01", "1999-12")]:
        calibration = result.loc[start:end, "momentum_std_ddof1"]
        expected = 120 if family == "early" else 480
        if len(calibration) != expected or calibration.isna().any():
            raise ValueError("Incomplete threshold calibration")
        threshold = float(calibration.median())
        result[f"dispersion_threshold_{family}"] = threshold
        result[f"H3_{family}"] = result.momentum_std_ddof1 > threshold
        result[f"H4_{family}"] = result[f"H3_{family}"] & (result.top3_intersection_three_decisions >= 2)
    if result.loc["1950-01":].iloc[:, :6].isna().any().any():
        raise ValueError("Missing features after calibration start")
    # Verify latest information consists entirely of preceding months.
    for month in pd.period_range("1950-01", "2025-12", freq="M"):
        direct_m24 = (1 + market.loc[month - 24:month - 1]).prod() - 1
        direct_m3 = (1 + market.loc[month - 3:month - 1]).prod() - 1
        assert np.isclose(result.loc[month, "prior_market24"], direct_m24, atol=1e-12)
        assert np.isclose(result.loc[month, "prior_market3"], direct_m3, atol=1e-12)
    return result


def hac_ols(y: np.ndarray, x: np.ndarray, lags: int = 12) -> dict:
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    n, k = x.shape
    if n <= k or not np.isfinite(y).all() or not np.isfinite(x).all() or np.linalg.matrix_rank(x) != k:
        raise ValueError("Insufficient or singular inference design")
    inverse = np.linalg.pinv(x)
    coefficients = inverse @ y
    errors = y - x @ coefficients
    scores = x * errors[:, None]
    meat = scores.T @ scores
    for lag in range(1, min(lags, n - 1) + 1):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / (lags + 1)) * (cross + cross.T)
    bread = inverse @ inverse.T
    covariance = bread @ meat @ bread * n / (n - k)
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    t = np.divide(coefficients, se, out=np.full(k, np.nan), where=se > 0)
    p = [math.erfc(abs(z) / math.sqrt(2)) if np.isfinite(z) else None for z in t]
    return {"coefficients": coefficients.tolist(), "hac12_se": se.tolist(), "hac12_covariance": covariance.tolist(),
            "asymptotic_normal_p": p, "nobs": n, "k": k, "lags": min(lags, n-1)}


def holm(pvalues: list[float]) -> list[float]:
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    sorted_p = p[order]
    adjusted_sorted = np.minimum(1., np.maximum.accumulate(sorted_p * np.arange(len(p), 0, -1)))
    result = np.empty(len(p))
    result[order] = adjusted_sorted
    return result.tolist()


def contiguous_episodes(months: pd.PeriodIndex, mask: np.ndarray) -> int:
    active = np.asarray(mask, dtype=bool)
    previous_same = np.r_[False, active[:-1]]
    ordinals = months.asi8
    adjacent = np.r_[False, np.diff(ordinals) == 1]
    return int(np.sum(active & ~(previous_same & adjacent)))


def joint_block_bootstrap(y: np.ndarray, z: np.ndarray, block: int) -> dict:
    n = len(y)
    rng = np.random.default_rng(SEED)
    starts = rng.integers(0, n, size=(DRAWS, math.ceil(n / block)))
    indices = ((starts[:, :, None] + np.arange(block)) % n).reshape(DRAWS, -1)[:, :n]
    sample_y, sample_z = y[indices], z[indices].astype(bool)
    counts = sample_z.sum(axis=1)
    valid = (counts > 0) & (counts < n)
    sum_true = (sample_y * sample_z).sum(axis=1)
    sum_false = (sample_y * ~sample_z).sum(axis=1)
    mean_true = sum_true[valid] / counts[valid]
    mean_false = sum_false[valid] / (n - counts[valid])
    return {"block_months": block, "draws": DRAWS, "valid_draws": int(valid.sum()), "seed": SEED,
            "true_mean_ci95_ann": (np.quantile(mean_true, [.025, .975]) * 12).tolist(),
            "false_mean_ci95_ann": (np.quantile(mean_false, [.025, .975]) * 12).tolist(),
            "difference_true_minus_false_ci95_ann": (np.quantile(mean_true - mean_false, [.025, .975]) * 12).tolist()}


def analyse_family(frame: pd.DataFrame, family: str, interval: str, bootstrap: bool = True) -> list[dict]:
    y = frame.active.to_numpy()
    m = frame.market_total_return.to_numpy()
    masks = {"H1": frame.H1.to_numpy(), "H2": frame.H2.to_numpy(),
             "H3": frame[f"H3_{family}"].to_numpy(), "H4": frame[f"H4_{family}"].to_numpy()}
    output = []
    for name, z in masks.items():
        z = z.astype(bool)
        if z.all() or (~z).all():
            output.append({"sample": interval, "hypothesis": name, "inferential_failure": "Condition absent or always present", "true_months": int(z.sum()), "false_months": int((~z).sum())})
            continue
        fit = hac_ols(y, np.column_stack([np.ones(len(y)), z.astype(float)]))
        favorite = ~z if name == "H1" else z
        # Regress y*I on I, without an intercept, on the complete time axis.
        # The coefficient is the selected-group mean; zero-score excluded months
        # retain the true calendar spacing and the n/(n-1) finite-sample correction.
        favorite_mean = y[favorite].mean()
        favorite_fit = hac_ols(y * favorite.astype(float), favorite.astype(float)[:, None])
        favorite_se = favorite_fit["hac12_se"][0]
        favorite_p = favorite_fit["asymptotic_normal_p"][0]
        assert np.isclose(favorite_fit["coefficients"][0], favorite_mean, atol=1e-12)
        interaction = hac_ols(y, np.column_stack([np.ones(len(y)), z.astype(float), m, z.astype(float) * m]))
        row = {"sample": interval, "hypothesis": name, "n_months": len(y), "threshold_family": family,
               "true_months": int(z.sum()), "false_months": int((~z).sum()),
               "true_contiguous_episodes": contiguous_episodes(frame.index, z),
               "false_contiguous_episodes": contiguous_episodes(frame.index, ~z),
               "true_mean_active_ann": float(y[z].mean() * 12),
               "false_mean_active_ann": float(y[~z].mean() * 12),
               "difference_true_minus_false_ann": float(fit["coefficients"][1] * 12),
               "difference_hac12_se_ann": float(fit["hac12_se"][1] * 12),
               "difference_p": fit["asymptotic_normal_p"][1],
               "expected_favorable_state": False if name == "H1" else True,
               "expected_favorable_mean_active_ann": float(favorite_mean * 12),
               "expected_favorable_mean_hac12_se_ann": float(favorite_se * 12),
               "expected_favorable_mean_p": favorite_p,
               "aux_market_interaction": {"model": "active=const+Z+M+Z*M; contemporaneous market for exposure description, not a trading input",
                                          "intercept_false_ann": interaction["coefficients"][0] * 12,
                                          "intercept_increment_true_ann": interaction["coefficients"][1] * 12,
                                          "beta_false": interaction["coefficients"][2],
                                          "beta_increment_true": interaction["coefficients"][3],
                                          "full_hac": interaction},
               "bootstrap": {str(block): joint_block_bootstrap(y, z, block) for block in (6, 12)} if bootstrap else {}}
        output.append(row)
    if len(output) == 4 and all("inferential_failure" not in row for row in output):
        pvalues = [r["difference_p"] for r in output] + [r["expected_favorable_mean_p"] for r in output]
        adjusted = holm(pvalues)
        for i, row in enumerate(output):
            row["difference_holm8_p"] = adjusted[i]
            row["expected_favorable_mean_holm8_p"] = adjusted[i + 4]
    return output


def main() -> None:
    global ROOT, RAW_DIR, PROTOCOL
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,required=True,help='saved original French industry and factor CSV files; no downloads')
    parser.add_argument('--out',type=Path,default=ROOT,help='output from analyze_external.py')
    parser.add_argument('--protocol',type=Path,default=PROTOCOL,help='unchanged frozen protocol')
    args=parser.parse_args();RAW_DIR=args.raw_dir.resolve();ROOT=args.out.resolve();PROTOCOL=args.protocol.resolve()
    for path in [RAW_DIR/'10_Industry_Portfolios.csv',RAW_DIR/'F-F_Research_Data_Factors.csv',PROTOCOL,ROOT/'comparison_returns.csv']:
        if not path.is_file():
            parser.error(f'Missing saved input: {path}; no data will be downloaded')
    returns = parse_monthly_value_weighted(RAW_DIR / "10_Industry_Portfolios.csv")
    factors = parse_factors()
    factors.to_csv(ROOT / "ff_factors_monthly_through_2025.csv", index_label="month")
    features = compute_features(returns, factors.market_total_return)
    outcome = pd.read_csv(ROOT / "comparison_returns.csv", index_col=0)
    outcome.index = pd.PeriodIndex(outcome.index, freq="M")
    frame = features.join(outcome, how="inner")
    frame.to_csv(ROOT / "conditions_and_outcomes.csv", index_label="holding_month")
    calibration = {"early": {"holding_months": ["1950-01", "1959-12"], "n_months": 120,
                             "signal_std_median": float(features.dispersion_threshold_early.iloc[-1])},
                   "late": {"holding_months": ["1960-01", "1999-12"], "n_months": 480,
                            "signal_std_median": float(features.dispersion_threshold_late.iloc[-1])}}
    intervals = [("early", "1960-01", "1999-12"), ("late", "2000-01", "2025-12"),
                 ("late", "2000-01", "2012-12"), ("late", "2013-01", "2025-12")]
    conditional = []
    for family, start, end in intervals:
        conditional.extend(analyse_family(frame.loc[start:end], family, f"{start} to {end}"))
    drop_year = []
    for family, start, end in intervals[:2]:
        sample = frame.loc[start:end]
        for year in sorted(set(sample.index.year)):
            reduced = sample[sample.index.year != year]
            # This check is descriptive: deleting a year leaves a calendar gap.
            # Do not report HAC that would treat its two sides as adjacent months.
            for hypothesis in ("H1", "H2", "H3", "H4"):
                column = hypothesis if hypothesis in ("H1", "H2") else f"{hypothesis}_{family}"
                z = reduced[column].to_numpy(dtype=bool)
                y = reduced.active.to_numpy()
                true_mean = float(12 * y[z].mean())
                false_mean = float(12 * y[~z].mean())
                drop_year.append({"sample": f"{start} to {end}; drop {year}", "hypothesis": hypothesis,
                                  "n_months": len(y), "threshold_family": family,
                                  "true_months": int(z.sum()), "false_months": int((~z).sum()),
                                  "true_contiguous_episodes": contiguous_episodes(reduced.index, z),
                                  "false_contiguous_episodes": contiguous_episodes(reduced.index, ~z),
                                  "true_mean_active_ann": true_mean, "false_mean_active_ann": false_mean,
                                  "difference_true_minus_false_ann": true_mean - false_mean,
                                  "expected_favorable_state": hypothesis != "H1",
                                  "expected_favorable_mean_active_ann": false_mean if hypothesis == "H1" else true_mean})
    data = {"raw_input_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [RAW_DIR/"10_Industry_Portfolios.csv", RAW_DIR/"F-F_Research_Data_Factors.csv"]}, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), "calibration": calibration,
            "inference": {"HAC": "OLS score sandwich Bartlett lag12; n/(n-k) finite-sample correction; asymptotic normal two-sided p",
                          "favorable_group_mean_hac": "Regress active*I on I with no intercept on the uncompressed original monthly timeline, and n/(n-1) correction; avoids treating separated group months as adjacent",
                          "Holm": "8 hypotheses per sample: four condition contrasts, four expected favorable-state mean-versus-zero tests",
                          "bootstrap": "Joint label-outcome circular 6/12-month blocks, 20000 draws, seed20261004; retained draws require both groups",
                          "annualization": "Monthly arithmetic means/differences multiplied by12; not strategy CAGR",
                          "positive_group": "H1 complement, H2/H3/H4 true; fixed before conditional results"},
            "primary_and_halves": conditional,
            "leave_one_year_out": drop_year}
    (ROOT / "conditional_results.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    flat = [{k: v for k, v in row.items() if k not in ("aux_market_interaction", "bootstrap")} for row in conditional]
    pd.DataFrame(flat).to_csv(ROOT / "conditional_results.csv", index=False)
    pd.DataFrame(drop_year).to_csv(ROOT / "leave_one_year_out.csv", index=False)
    for row in conditional:
        print(row["sample"], row["hypothesis"], "n", row["true_months"], row["false_months"], "delta%", round(100*row["difference_true_minus_false_ann"],3),
              "pHolm8", round(row["difference_holm8_p"],4), "fave%", round(100*row["expected_favorable_mean_active_ann"],3), "faveHolm8", round(row["expected_favorable_mean_holm8_p"],4),
              "CI6", [round(100*x,3) for x in row["bootstrap"]["6"]["difference_true_minus_false_ci95_ann"]])


if __name__ == "__main__":
    main()
