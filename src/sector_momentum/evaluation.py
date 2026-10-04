"""Performance and uncertainty estimates for an ETF investment review."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _series(values: pd.Series, name: str) -> pd.Series:
    if not isinstance(values, pd.Series):
        raise TypeError(f"{name} must be a pandas Series")
    if not values.index.is_unique:
        raise ValueError(f"{name} has duplicate index values")
    if not values.index.is_monotonic_increasing:
        raise ValueError(f"{name} index must be increasing")
    numeric = values.astype(float)
    if np.isinf(numeric.to_numpy()).any():
        raise ValueError(f"{name} contains infinite values")
    return numeric


def _nav(nav: pd.Series) -> pd.Series:
    values = _series(nav, "nav")
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError("nav needs a DatetimeIndex")
    if values.index.hasnans or values.isna().any():
        raise ValueError("nav contains missing dates or values")
    if len(values) < 2 or (values <= 0).any():
        raise ValueError("nav needs at least two positive observations")
    return values


def summary_metrics(nav: pd.Series) -> dict:
    """Use actual elapsed time for CAGR and 252 observations/year for daily vol."""
    values = _nav(nav)
    years = (values.index[-1] - values.index[0]).total_seconds() / (
        365.25 * 24 * 60 * 60
    )
    if years <= 0:
        raise ValueError("nav must span a positive elapsed time")
    daily = values.pct_change(fill_method=None).dropna()
    return {
        "cagr": float((values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1),
        "annualized_volatility": (
            float(daily.std(ddof=1) * math.sqrt(252)) if len(daily) > 1 else None
        ),
        "max_drawdown": float((values / values.cummax() - 1).min()),
    }


def monthly_returns(nav: pd.Series) -> pd.Series:
    """Return changes between observed month-end NAVs, with calendar-end labels.

    Supply the preceding month-end's initial NAV to include the first investment
    month. Without that base, the first observed month is excluded. The caller
    must end the input at a completed research month; exchange holidays are not
    inferred here, and an unfinished final month is not a full monthly return.
    """
    values = _nav(nav)
    month_ends = values.resample(pd.offsets.MonthEnd()).last()
    result = month_ends.pct_change(fill_method=None).dropna()
    result.name = "monthly_return"
    return result


def _paired(strategy: pd.Series, benchmark: pd.Series) -> pd.DataFrame:
    joined = pd.concat(
        [_series(strategy, "strategy"), _series(benchmark, "benchmark")],
        axis=1,
        keys=["strategy", "benchmark"],
        join="inner",
    ).dropna()
    if len(joined) < 2:
        raise ValueError("need at least two aligned, finite returns")
    return joined


def active_stats(
    strategy_monthly: pd.Series, benchmark_monthly: pd.Series
) -> dict:
    """Report monthly active-return mean and annualized sample tracking error."""
    paired = _paired(strategy_monthly, benchmark_monthly)
    active = paired.strategy - paired.benchmark
    mean = float(active.mean())
    tracking_error = float(active.std(ddof=1) * math.sqrt(12))
    return {
        "mean_monthly": mean,
        "annualized_arithmetic_active": 12 * mean,
        "tracking_error_ann": tracking_error,
        "information_ratio": 12 * mean / tracking_error if tracking_error > 0 else None,
        "nobs": len(active),
    }


def _normal_stat(coefficient: float, standard_error: float) -> tuple:
    if standard_error == 0:
        return None, None
    tstat = coefficient / standard_error
    # erfc supplies a two-sided standard-normal tail, not a finite-sample t test.
    pvalue = math.erfc(abs(tstat) / math.sqrt(2))
    return float(tstat), float(pvalue)


def capm_hac(
    strategy_monthly: pd.Series,
    market_monthly: pd.Series,
    rf_monthly: pd.Series | None = None,
    lags: int = 3,
) -> dict:
    """OLS of excess strategy returns on excess market returns, with Bartlett HAC.

    Standard errors use the n/(n-2) degrees-of-freedom correction. The reported
    p-values use an asymptotic normal approximation. This describes historical
    market exposure; an intercept is not proof of a causal investment effect.
    """
    if not isinstance(lags, (int, np.integer)) or isinstance(lags, bool) or lags < 0:
        raise ValueError("lags must be a nonnegative integer")
    paired = _paired(strategy_monthly, market_monthly)
    if rf_monthly is not None:
        paired = paired.join(_series(rf_monthly, "rf").rename("rf"), how="inner").dropna()
    else:
        paired["rf"] = 0.0
    nobs = len(paired)
    if nobs < 6:
        raise ValueError("CAPM HAC needs at least six aligned monthly returns")
    x = np.column_stack([np.ones(nobs), (paired.benchmark - paired.rf).to_numpy()])
    y = (paired.strategy - paired.rf).to_numpy()
    if np.linalg.matrix_rank(x) < 2:
        raise ValueError("market excess returns cannot be constant")
    x_inverse = np.linalg.pinv(x)
    coefficients = x_inverse @ y
    residuals = y - x @ coefficients
    score = x * residuals[:, None]
    meat = score.T @ score
    used_lags = min(int(lags), nobs - 1)
    for lag in range(1, used_lags + 1):
        weight = 1 - lag / (used_lags + 1)
        lag_cross = score[lag:].T @ score[:-lag]
        meat += weight * (lag_cross + lag_cross.T)
    bread = x_inverse @ x_inverse.T
    covariance = bread @ meat @ bread * nobs / (nobs - 2)
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    alpha, beta = map(float, coefficients)
    alpha_se, beta_se = map(float, standard_errors)
    alpha_t, alpha_p = _normal_stat(alpha, alpha_se)
    beta_t, beta_p = _normal_stat(beta, beta_se)
    return {
        "alpha_monthly": alpha,
        "alpha_annualized_arithmetic": 12 * alpha,
        "beta": beta,
        "alpha_hac_se": alpha_se,
        "alpha_hac_tstat": alpha_t,
        "alpha_asymptotic_normal_p": alpha_p,
        "beta_hac_se": beta_se,
        "beta_hac_tstat": beta_t,
        "beta_asymptotic_normal_p": beta_p,
        "nobs": nobs,
        "lags": used_lags,
    }


def paired_block_bootstrap(
    active_monthly: pd.Series,
    block_size: int = 6,
    draws: int = 2000,
    seed: int = 2026,
) -> dict:
    """Circular-block percentile interval for the mean of paired active returns.

    Strategy and benchmark must be differenced on the same dates before calling.
    Contiguous blocks preserve local dependence. The interval is an exploratory
    historical estimate, conditional on the rule and sample supplied.
    """
    values = _series(active_monthly, "active_monthly").dropna().to_numpy()
    nobs = len(values)
    if not isinstance(block_size, (int, np.integer)) or isinstance(block_size, bool):
        raise ValueError("block_size must be an integer")
    if nobs < 2 or not 1 <= block_size < nobs:
        raise ValueError("block_size must be positive and smaller than the sample")
    if not isinstance(draws, (int, np.integer)) or isinstance(draws, bool) or draws < 2:
        raise ValueError("draws must be an integer of at least two")
    rng = np.random.default_rng(seed)
    blocks_per_draw = math.ceil(nobs / block_size)
    starts = rng.integers(0, nobs, size=(draws, blocks_per_draw))
    indices = (starts[:, :, None] + np.arange(block_size)) % nobs
    samples = values[indices.reshape(draws, -1)[:, :nobs]]
    means = samples.mean(axis=1)
    low, high = map(float, np.quantile(means, [0.025, 0.975]))
    mean = float(values.mean())
    return {
        "mean_monthly": mean,
        "ci95_monthly": [low, high],
        "annualized_arithmetic_mean": 12 * mean,
        "ci95_annualized_arithmetic": [12 * low, 12 * high],
        "nobs": nobs,
        "block_size": int(block_size),
        "draws": int(draws),
        "seed": int(seed),
    }
