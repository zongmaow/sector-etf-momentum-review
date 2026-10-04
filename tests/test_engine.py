import unittest

import numpy as np
import pandas as pd

from sector_momentum.data import SECTORS, TICKERS
from sector_momentum.engine import Strategy, backtest, self_financing_trade
from sector_momentum.signals import momentum_scores, select_names


def constant_levels():
    # A synthetic weekday calendar isolates accounting from exchange-calendar data.
    dates = pd.bdate_range("1998-12-31", "2000-03-31")
    return pd.DataFrame(100.0, index=dates, columns=TICKERS)


def execution_example():
    levels = constant_levels()
    old_names = list(SECTORS[:3])
    new_names = list(SECTORS[3:6])
    levels.loc["1999-11-30":, old_names] = [130.0, 120.0, 110.0]
    levels.loc["1999-12-31":, new_names] = [160.0, 150.0, 140.0]
    levels.loc["2000-01-03":, old_names] *= 2
    levels.loc["2000-01-04":, old_names] *= 1.1
    levels.loc["2000-02-01":, old_names] *= 0.9
    levels.loc["2000-02-01":, new_names] *= 2
    levels.loc["2000-02-02":, new_names] *= 1.2
    return levels


class SignalTests(unittest.TestCase):
    def test_windows_have_known_returns_and_only_skip_rule_excludes_last_month(self):
        dates = pd.date_range("2024-03-31", periods=13, freq=pd.offsets.MonthEnd())
        monthly = pd.DataFrame({"A": [100.0] + [110.0] * 10 + [130.0, 140.0]}, index=dates)
        self.assertAlmostEqual(momentum_scores(monthly, "12_1").iloc[-1, 0], 0.3)
        self.assertAlmostEqual(momentum_scores(monthly, "12_0").iloc[-1, 0], 0.4)
        self.assertAlmostEqual(momentum_scores(monthly, "1_0").iloc[-1, 0], 140 / 130 - 1)
        changed = monthly.copy()
        changed.iloc[-1, 0] = 200.0
        self.assertAlmostEqual(momentum_scores(changed, "12_1").iloc[-1, 0], 0.3)
        self.assertAlmostEqual(momentum_scores(changed, "12_0").iloc[-1, 0], 1.0)

    def test_buffer_retains_rank_four_but_replaces_rank_five(self):
        scores = pd.Series({"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "E": 0.0})
        incumbents = ("A", "B", "D")
        self.assertEqual(select_names(scores, incumbents), ("A", "B", "C"))
        self.assertEqual(select_names(scores, incumbents, buffer_rank=4), incumbents)
        scores[["D", "E"]] = [0.0, 1.0]
        self.assertEqual(select_names(scores, incumbents, buffer_rank=4), ("A", "B", "C"))

    def test_equal_scores_use_alphabetical_tie_break(self):
        scores = pd.Series({"Z": 1.0, "C": 1.0, "B": 1.0, "A": 1.0})
        self.assertEqual(select_names(scores), ("A", "B", "C"))


class TradeAccountingTests(unittest.TestCase):
    def assert_cash_accounting(self, before, cash, after, fee, buys, sells, rate):
        self.assertAlmostEqual(after.sum() + fee, before.sum() + cash)
        self.assertAlmostEqual(cash + sells - buys - fee, 0)
        self.assertAlmostEqual(fee, rate * (buys + sells))

    def test_initial_purchase_fee_reduces_available_investment(self):
        before = np.zeros(2)
        after, fee, buys, sells = self_financing_trade(before, 100, np.array([0.5, 0.5]), 0.01)
        # Only purchases are charged: investment + 1% * investment = cash.
        expected_investment = 100 / 1.01
        np.testing.assert_allclose(after, [expected_investment / 2] * 2)
        self.assertAlmostEqual(fee, 100 - expected_investment)
        self.assertAlmostEqual(sells, 0)
        self.assert_cash_accounting(before, 100, after, fee, buys, sells, 0.01)

    def test_full_rotation_pays_both_sales_and_postfee_purchases(self):
        before = np.array([60.0, 40.0])
        after, fee, buys, sells = self_financing_trade(before, 0, np.array([0.0, 1.0]), 0.01)
        # Sell 60, buy 60-fee; fee = 1% * (120-fee).
        expected_fee = 1.2 / 1.01
        np.testing.assert_allclose(after, [0, 100 - expected_fee])
        self.assertAlmostEqual(sells, 60)
        self.assert_cash_accounting(before, 0, after, fee, buys, sells, 0.01)

    def test_cash_top_up_obeys_same_self_financing_identity(self):
        before = np.array([40.0, 30.0])
        after, fee, buys, sells = self_financing_trade(before, 30, np.array([0.5, 0.5]), 0.1)
        # Both positions increase: purchases = 30-fee, so fee=3/1.1.
        expected_fee = 3 / 1.1
        np.testing.assert_allclose(after, [(100 - expected_fee) / 2] * 2)
        self.assertAlmostEqual(sells, 0)
        self.assert_cash_accounting(before, 30, after, fee, buys, sells, 0.1)

    def test_drift_rebalancing_charges_only_changed_positions(self):
        before = np.array([60.0, 40.0])
        after, fee, buys, sells = self_financing_trade(before, 0, np.array([0.5, 0.5]), 0.01)
        # Equal-weight restoration buys 9.9 and sells 10.1; gross traded is 20.
        np.testing.assert_allclose(after, [49.9, 49.9])
        self.assertAlmostEqual(fee, 0.2)
        self.assertAlmostEqual(buys, 9.9)
        self.assertAlmostEqual(sells, 10.1)
        self.assert_cash_accounting(before, 0, after, fee, buys, sells, 0.01)
        repeated, second_fee, _, _ = self_financing_trade(after, 0, np.array([0.5, 0.5]), 0.01)
        np.testing.assert_allclose(repeated, after)
        self.assertAlmostEqual(second_fee, 0)


class ExecutionTests(unittest.TestCase):
    def test_formation_and_rotation_take_effect_after_execution_close(self):
        result = backtest(execution_example(), Strategy("timing"), cost_bps=0, initial_nav=1000)
        initial_trade = result.trades.iloc[0]
        self.assertEqual(initial_trade.signal_date, pd.Timestamp("1999-12-31"))
        self.assertEqual(initial_trade.execution_date, pd.Timestamp("2000-01-03"))
        # Jan 3's doubling occurs before purchase; Jan 4's 10% is earned.
        self.assertAlmostEqual(result.nav.loc["2000-01-03"], 1000)
        self.assertAlmostEqual(result.nav.loc["2000-01-04"], 1100)
        february_trade = result.trades.iloc[1]
        self.assertEqual(february_trade.selected, ",".join(SECTORS[3:6]))
        # Old holdings lose 10% on Feb 1; new holdings' same-day doubling is absent.
        self.assertAlmostEqual(result.nav.loc["2000-02-01"], 990)
        self.assertAlmostEqual(result.nav.loc["2000-02-02"], 1188)

    def test_future_prices_cannot_change_previous_path_or_decisions(self):
        levels = execution_example()
        original = backtest(levels, Strategy("original", buffer_rank=4), cost_bps=5)
        cutoff = pd.Timestamp("2000-02-15")
        changed = levels.copy()
        future = changed.index > cutoff
        changed.loc[future, list(SECTORS)] *= np.linspace(1, 3, future.sum())[:, None]
        altered = backtest(changed, Strategy("original", buffer_rank=4), cost_bps=5)
        pd.testing.assert_series_equal(original.nav.loc[:cutoff], altered.nav.loc[:cutoff])
        pd.testing.assert_frame_equal(original.weights.loc[:cutoff], altered.weights.loc[:cutoff])
        before_decisions = original.decisions.loc[original.decisions.execution_date <= cutoff].reset_index(drop=True)
        after_decisions = altered.decisions.loc[altered.decisions.execution_date <= cutoff].reset_index(drop=True)
        pd.testing.assert_frame_equal(before_decisions, after_decisions)
        self.assertNotAlmostEqual(original.nav.iloc[-1], altered.nav.iloc[-1])

    def test_static_equal_weights_are_not_charged_again_each_month(self):
        result = backtest(constant_levels(), Strategy("equal", equal_weight=True), cost_bps=100, initial_nav=1000)
        self.assertAlmostEqual(result.nav.iloc[-1], 1000 / 1.01)
        self.assertTrue(bool(result.trades.iloc[0].initial_formation))
        self.assertFalse(bool(result.trades.iloc[1].initial_formation))
        np.testing.assert_allclose(result.trades.iloc[1:].fee, 0, atol=1e-10)

    def test_midmonth_start_is_rejected_instead_of_trading_before_it(self):
        with self.assertRaises(ValueError):
            backtest(constant_levels(), Strategy("date"), start="2000-01-15")


if __name__ == "__main__":
    unittest.main()
