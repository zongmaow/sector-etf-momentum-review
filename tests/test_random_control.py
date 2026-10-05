"""Accounting and no-look-ahead checks for the new concentration diagnostics."""
import unittest
import gzip
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from sector_momentum.data import SECTORS, TICKERS
from sector_momentum.engine import Strategy, backtest, self_financing_trade
from sector_momentum.random_control import (
    _rebalance, remapped_targets, overlap_matched_targets,
    simulate_target_paths, independent_path_nav,
    _write_csv_archive, _empirical_midrank, _drawdown_episode,
)


def timing_levels():
    dates = pd.bdate_range('1998-12-31', '2000-03-31')
    prices = pd.DataFrame(100., index=dates, columns=TICKERS)
    prices.loc['1999-11-30':, list(SECTORS[:3])] = [130., 120., 110.]
    prices.loc['1999-12-31':, list(SECTORS[3:6])] = [160., 150., 140.]
    prices.loc['2000-01-03':, list(SECTORS[:3])] *= 2
    prices.loc['2000-01-04':, list(SECTORS[:3])] *= 1.1
    prices.loc['2000-02-01':, list(SECTORS[:3])] *= .9
    prices.loc['2000-02-01':, list(SECTORS[3:6])] *= 2
    prices.loc['2000-02-02':, list(SECTORS[3:6])] *= 1.2
    return prices


def schedule(prices):
    ref = backtest(prices, Strategy('reference'), 5, end='2000-03-31')
    template = np.array([[n in s.split(',') for n in SECTORS] for s in ref.trades.selected])
    return ref, pd.DatetimeIndex(ref.trades.execution_date), template


class RandomSelectionTests(unittest.TestCase):
    def test_fixed_bijections_preserve_entry_exit_and_are_reproducible(self):
        template = np.zeros((4, 9), bool)
        template[0, [0, 1, 2]] = True
        template[1, [1, 2, 3]] = True
        template[2, [4, 5, 6]] = True
        template[3, [4, 5, 6]] = True
        targets, mappings = remapped_targets(template, 32, 123)
        targets_again, mappings_again = remapped_targets(template, 32, 123)
        np.testing.assert_array_equal(targets, targets_again)
        np.testing.assert_array_equal(mappings, mappings_again)
        for p, mapping in enumerate(mappings):
            self.assertEqual(set(mapping), set(range(9)))
            for j, names in enumerate(template):
                self.assertEqual(set(np.flatnonzero(targets[p, j])), set(mapping[np.flatnonzero(names)]))
        np.testing.assert_array_equal(targets.sum(axis=2), 3)
        np.testing.assert_array_equal((targets[:, 1:] & targets[:, :-1]).sum(axis=2),
                                      np.broadcast_to([2, 0, 3], (32, 3)))

    def test_monthly_random_paths_preserve_zero_partial_and_full_overlap(self):
        template = np.zeros((4, 9), bool)
        template[0, [0, 1, 2]] = True
        template[1, [1, 2, 3]] = True
        template[2, [4, 5, 6]] = True
        template[3, [4, 5, 6]] = True
        targets = overlap_matched_targets(template, 32, 123)
        np.testing.assert_array_equal(targets, overlap_matched_targets(template, 32, 123))
        np.testing.assert_array_equal(targets.sum(axis=2), 3)
        np.testing.assert_array_equal((targets[:, 1:] & targets[:, :-1]).sum(axis=2),
                                      np.broadcast_to([2, 0, 3], (32, 3)))

    def test_bad_template_or_draw_count_is_rejected(self):
        for f in (remapped_targets, overlap_matched_targets):
            with self.assertRaises(ValueError):
                f(np.ones((2, 9)), 8)
            with self.assertRaises(ValueError):
                f(np.array([[1, 1, 1] + [0] * 6]), 0)


class BatchLedgerTests(unittest.TestCase):
    def test_batch_fee_solver_matches_scalar_solver_with_drift_and_cash(self):
        values = np.array([[60., 40., 0.], [0., 0., 0.], [18., 12., 50.]])
        cash = np.array([0., 100., 20.])
        target = np.array([[0., .5, .5], [1 / 3] * 3, [.5, 0., .5]])
        for rate in [0, .0005, .001, .01]:
            after, fee, gross, _, _ = _rebalance(values, cash, target, rate)
            for i in range(3):
                expected, expected_fee, buys, sells = self_financing_trade(values[i], cash[i], target[i], rate)
                np.testing.assert_allclose(after[i], expected, rtol=1e-13, atol=1e-12)
                self.assertAlmostEqual(fee[i], expected_fee, places=12)
                self.assertAlmostEqual(gross[i], buys + sells, places=12)

    def test_identity_daily_nav_fees_and_execution_jump_match_original_engine(self):
        prices = timing_levels()
        _, executions, template = schedule(prices)
        for cost in [0, 5, 10]:
            ref = backtest(prices, Strategy('reference'), cost, end='2000-03-31', initial_nav=1000.)
            actual = simulate_target_paths(prices, executions, template[None], ref.nav.index[0], cost)
            np.testing.assert_allclose(actual.sample_nav[0], ref.nav / 1000, rtol=1e-13)
            np.testing.assert_allclose(actual.sample_trades.fee, ref.trades.fee / 1000, atol=1e-13)
            self.assertEqual(actual.month_dates[0], pd.Timestamp('1999-12-31'))
        zero = simulate_target_paths(prices, executions, template[None], ref.nav.index[0], 0)
        self.assertAlmostEqual(zero.sample_nav.loc['2000-01-03', 0], 1.)
        self.assertAlmostEqual(zero.sample_nav.loc['2000-01-04', 0], 1.1)
        self.assertAlmostEqual(zero.sample_nav.loc['2000-02-01', 0], .99)
        self.assertAlmostEqual(zero.sample_nav.loc['2000-02-02', 0], 1.188)

    def test_random_paths_match_independent_scalar_accounting(self):
        prices = timing_levels()
        ref, executions, template = schedule(prices)
        targets, _ = remapped_targets(template, 3, 4)
        actual = simulate_target_paths(prices, executions, targets, ref.nav.index[0], 10)
        for i in range(3):
            scalar = independent_path_nav(prices, executions, targets[i], ref.nav.index[0], 10)
            np.testing.assert_allclose(actual.sample_nav[i], scalar, rtol=1e-13)

    def test_future_prices_do_not_change_prior_random_decisions_or_nav(self):
        prices = timing_levels()
        ref, executions, template = schedule(prices)
        cutoff = pd.Timestamp('2000-01-15')
        changed = prices.copy()
        changed.loc[changed.index > cutoff, list(SECTORS)] *= np.arange(1, 10)
        _, executions2, template2 = schedule(changed)
        for generator in (remapped_targets, overlap_matched_targets):
            a, b = generator(template, 8, 12), generator(template2, 8, 12)
            if isinstance(a, tuple):
                a, b = a[0], b[0]
            np.testing.assert_array_equal(a[:, executions <= cutoff], b[:, executions2 <= cutoff])
            before = simulate_target_paths(prices, executions, a, ref.nav.index[0], 5)
            after = simulate_target_paths(changed, executions2, b, ref.nav.index[0], 5)
            pd.testing.assert_frame_equal(before.sample_nav.loc[:cutoff], after.sample_nav.loc[:cutoff])

    def test_missing_execution_month_or_nonbinary_target_is_rejected(self):
        prices = timing_levels()
        ref, executions, template = schedule(prices)
        with self.assertRaises(ValueError):
            simulate_target_paths(prices, executions[:1], template[None, :1], ref.nav.index[0], 5)
        bad = template[None].astype(float)
        bad[0, 0, 0] = .5
        with self.assertRaises(ValueError):
            simulate_target_paths(prices, executions, bad, ref.nav.index[0], 5)


class DiagnosticOutputTests(unittest.TestCase):
    def test_compressed_csv_preserves_exact_ledger_bytes_and_pandas_loading(self):
        frame = pd.DataFrame({'sector': ['XLK,XLF,XLU', 'XLE'], 'fee': [.000123456789, 0.]})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ledger.csv.gz'
            other = Path(folder) / 'other.csv.gz'
            _write_csv_archive(frame, path, index=False, float_format='%.12g')
            _write_csv_archive(frame, other, index=False, float_format='%.12g')
            self.assertEqual(gzip.decompress(path.read_bytes()).decode(), frame.to_csv(index=False, float_format='%.12g'))
            self.assertEqual(path.read_bytes(), other.read_bytes())
            pd.testing.assert_frame_equal(pd.read_csv(path), frame)

    def test_shallower_drawdown_has_high_rank_with_half_weight_for_ties(self):
        depths = [-.65, -.60, -.55, -.46]
        self.assertEqual(_empirical_midrank(depths, -.45), 1.)
        self.assertEqual(_empirical_midrank(depths, -.70), 0.)
        self.assertEqual(_empirical_midrank(depths, -.55), .625)

    def test_drawdown_episode_uses_peak_before_trough_and_ignores_later_high(self):
        nav = pd.Series([1., 2., 1.5, 1., 3.], index=pd.date_range('2000-01-01', periods=5))
        self.assertEqual(_drawdown_episode(nav), {'max_drawdown': -.5, 'peak_date': '2000-01-02', 'trough_date': '2000-01-04'})


if __name__ == '__main__':
    unittest.main()
