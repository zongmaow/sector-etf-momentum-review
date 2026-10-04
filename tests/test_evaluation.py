import math
import unittest

import numpy as np
import pandas as pd

from sector_momentum.evaluation import (
    active_stats,
    capm_hac,
    monthly_returns,
    paired_block_bootstrap,
    summary_metrics,
)


class EvaluationTests(unittest.TestCase):
    def test_summary_uses_elapsed_dates_and_sample_volatility(self):
        nav = pd.Series(
            [100.0, 110.0, 99.0],
            index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-12-31"]),
        )
        result = summary_metrics(nav)
        self.assertAlmostEqual(result["cagr"], 0.99 ** (365.25 / 365) - 1)
        self.assertAlmostEqual(result["annualized_volatility"], math.sqrt(0.02 * 252))
        self.assertAlmostEqual(result["max_drawdown"], -0.1)

    def test_monthly_returns_omit_initial_partial_month_and_align_labels(self):
        nav = pd.Series(
            [100.0, 105.0, 115.5, 103.95],
            index=pd.to_datetime(["2020-01-15", "2020-01-31", "2020-02-28", "2020-03-31"]),
        )
        result = monthly_returns(nav)
        self.assertEqual(list(result.index), list(pd.to_datetime(["2020-02-29", "2020-03-31"])))
        np.testing.assert_allclose(result.to_numpy(), [0.1, -0.1], atol=1e-14)

    def test_active_statistics_use_only_common_dates(self):
        strategy = pd.Series([0.01, 0.03, 0.02, -0.02], index=[1, 2, 3, 4])
        benchmark = pd.Series([0.01, 0.01, -0.01, 0.04], index=[2, 3, 4, 5])
        result = active_stats(strategy, benchmark)
        active = np.array([0.02, 0.01, -0.01])
        expected_te = np.std(active, ddof=1) * math.sqrt(12)
        self.assertEqual(result["nobs"], 3)
        self.assertAlmostEqual(result["annualized_arithmetic_active"], 12 * active.mean())
        self.assertAlmostEqual(result["tracking_error_ann"], expected_te)
        self.assertAlmostEqual(result["information_ratio"], 12 * active.mean() / expected_te)

    def test_previous_month_end_base_includes_first_investment_month(self):
        nav = pd.Series(
            [100.0, 100.0, 110.0, 121.0],
            index=pd.to_datetime(["1999-12-31", "2000-01-03", "2000-01-31", "2000-02-29"]),
        )
        result = monthly_returns(nav)
        self.assertEqual(result.index[0], pd.Timestamp("2000-01-31"))
        np.testing.assert_allclose(result.to_numpy(), [0.1, 0.1], atol=1e-14)

    def test_zero_tracking_error_has_no_information_ratio(self):
        returns = pd.Series([0.01, 0.02, -0.01])
        self.assertIsNone(active_stats(returns, returns)["information_ratio"])

    def test_capm_hac_matches_known_coefficients_and_direct_kernel(self):
        market = np.array([-0.035, -0.025, -0.015, -0.005, 0.005, 0.015, 0.025, 0.035])
        residual = np.array([0.003, -0.002, -0.001, 0, 0, -0.001, -0.002, 0.003])
        rf = np.full(8, 0.001)
        strategy = rf + 0.004 + 1.3 * market + residual
        result = capm_hac(pd.Series(strategy), pd.Series(market + rf), pd.Series(rf), lags=2)
        self.assertAlmostEqual(result["alpha_monthly"], 0.004)
        self.assertAlmostEqual(result["beta"], 1.3)
        self.assertAlmostEqual(result["alpha_annualized_arithmetic"], 0.048)
        x = np.column_stack([np.ones(8), market])
        distances = np.abs(np.arange(8)[:, None] - np.arange(8)[None, :])
        kernel = np.maximum(1 - distances / 3, 0)
        bread = np.linalg.inv(x.T @ x)
        direct_covariance = bread @ x.T @ np.diag(residual) @ kernel @ np.diag(residual) @ x @ bread * 8 / 6
        expected_alpha_se = math.sqrt(direct_covariance[0, 0])
        self.assertAlmostEqual(result["alpha_hac_se"], expected_alpha_se)
        self.assertAlmostEqual(result["alpha_hac_tstat"], 0.004 / expected_alpha_se)
        expected_p = math.erfc(abs(0.004 / expected_alpha_se) / math.sqrt(2))
        self.assertAlmostEqual(result["alpha_asymptotic_normal_p"], expected_p)

    def test_capm_recovers_coefficients_with_random_noise(self):
        rng = np.random.default_rng(8)
        market = rng.normal(0.005, 0.04, 120)
        x = np.column_stack([np.ones(120), market])
        noise = rng.normal(0, 0.01, 120)
        noise -= x @ (np.linalg.pinv(x) @ noise)
        result = capm_hac(pd.Series(0.002 + 0.8 * market + noise), pd.Series(market))
        self.assertAlmostEqual(result["alpha_monthly"], 0.002)
        self.assertAlmostEqual(result["beta"], 0.8)
        self.assertGreater(result["alpha_hac_se"], 0)

    def test_capm_rejects_singular_and_short_samples(self):
        with self.assertRaises(ValueError):
            capm_hac(pd.Series(np.arange(8) / 100), pd.Series(np.ones(8) / 100))
        with self.assertRaises(ValueError):
            capm_hac(pd.Series(np.arange(5) / 100), pd.Series(np.arange(5) / 100))

    def test_constant_active_return_bootstrap_is_degenerate(self):
        result = paired_block_bootstrap(pd.Series(np.full(24, 0.01)), draws=100, seed=5)
        np.testing.assert_allclose(result["ci95_monthly"], [0.01, 0.01], atol=1e-14)
        np.testing.assert_allclose(result["ci95_annualized_arithmetic"], [0.12, 0.12], atol=1e-14)

    def test_bootstrap_matches_manual_circular_sampling(self):
        active = np.array([-0.04, -0.02, 0.01, 0.02, 0.06])
        seed, draws, block_size = 31, 200, 2
        result = paired_block_bootstrap(pd.Series(active), block_size, draws, seed)
        rng = np.random.default_rng(seed)
        starts = rng.integers(0, len(active), size=(draws, 3))
        simulated_means = []
        for draw in starts:
            sample = []
            for start in draw:
                sample.extend([active[start], active[(start + 1) % len(active)]])
            simulated_means.append(np.mean(sample[: len(active)]))
        np.testing.assert_allclose(result["ci95_monthly"], np.quantile(simulated_means, [0.025, 0.975]))

    def test_invalid_nav_and_bootstrap_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            summary_metrics(pd.Series([100, 0], index=pd.date_range("2020-01-01", periods=2)))
        with self.assertRaises(ValueError):
            monthly_returns(pd.Series([100, 101], index=pd.to_datetime(["2020-01-02", "2020-01-01"])))
        with self.assertRaises(ValueError):
            paired_block_bootstrap(pd.Series([0.01, 0.02]), block_size=2)


if __name__ == "__main__":
    unittest.main()
