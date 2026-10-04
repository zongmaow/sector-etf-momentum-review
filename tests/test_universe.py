"""Universe changes preserve accounting and never imply pre-inception data."""
import json
import unittest

import numpy as np
import pandas as pd

from sector_momentum.data import BENCHMARK, SECTORS
from sector_momentum.engine import Strategy, backtest


EXPANDED = SECTORS + ("XLRE", "XLC")


def synthetic_levels():
    # These dates and levels are synthetic; they make no historical ETF claim.
    dates = pd.bdate_range("1998-12-31", "2000-03-31")
    levels = pd.DataFrame(100.0, index=dates, columns=EXPANDED + (BENCHMARK,))
    levels.loc["1999-11-30":, ["XLC", "XLRE", "XLK"]] = [150., 140., 130.]
    levels.loc["2000-01-04":, "XLC"] *= 1.1
    return levels


class UniverseTests(unittest.TestCase):
    def test_default_and_explicit_original_universe_match_every_ledger(self):
        levels = synthetic_levels()
        for strategy in (Strategy("momentum"), Strategy("equal", equal_weight=True),
                         Strategy("market", buy_hold_market=True),
                         Strategy("sleeve", sleeve_fraction=0.2, buffer_rank=4)):
            default = backtest(levels, strategy)
            explicit = backtest(levels, strategy, universe=SECTORS)
            pd.testing.assert_series_equal(default.nav, explicit.nav, check_exact=True)
            for field in ("weights", "trades", "decisions", "daily_pnl"):
                pd.testing.assert_frame_equal(getattr(default, field),
                                              getattr(explicit, field), check_exact=True)

    def test_new_sectors_can_be_selected_and_trade_with_same_execution_rule(self):
        result = backtest(synthetic_levels(), Strategy("expanded"), universe=EXPANDED,
                          cost_bps=0, initial_nav=1000.)
        self.assertEqual(result.trades.iloc[0].selected, "XLC,XLRE,XLK")
        first = result.decisions[result.decisions.signal_date == pd.Timestamp("1999-12-31")]
        self.assertEqual(set(first.loc[first.selected, "ticker"]), {"XLC", "XLRE", "XLK"})
        np.testing.assert_allclose(first.loc[first.selected, "target_weight"], 1 / 3)
        self.assertEqual(result.trades.iloc[0].execution_date, pd.Timestamp("2000-01-03"))
        self.assertAlmostEqual(result.nav.loc["2000-01-03"], 1000.)
        self.assertAlmostEqual(result.nav.loc["2000-01-04"], 1000. * (1 + 0.1 / 3))

    def test_equal_weight_expanded_universe_has_eleven_equal_targets(self):
        result = backtest(synthetic_levels(), Strategy("equal", equal_weight=True),
                          universe=EXPANDED, cost_bps=5, initial_nav=1000.)
        initial_trade = result.trades.iloc[0]
        target = json.loads(initial_trade.target_weights_json)
        np.testing.assert_allclose([target[name] for name in EXPANDED], 1 / 11)
        self.assertEqual(target[BENCHMARK], 0.)
        self.assertEqual(set(result.weights.columns), {*EXPANDED, BENCHMARK, "CASH"})
        self.assertAlmostEqual(initial_trade.posttrade_nav + initial_trade.fee, 1000.)
        self.assertAlmostEqual(initial_trade.fee, 0.0005 * initial_trade.buys)

    def test_missing_new_sector_is_rejected_even_if_it_would_not_be_selected(self):
        levels = synthetic_levels().drop(columns="XLC")
        with self.assertRaisesRegex(ValueError, "XLC"):
            backtest(levels, Strategy("expanded"), universe=EXPANDED)

    def test_missing_or_nonfinite_new_sector_is_not_filled(self):
        for value in (np.nan, np.inf, 0.):
            levels = synthetic_levels()
            levels.loc["1999-07-01", "XLC"] = value
            with self.assertRaisesRegex(ValueError, "finite and positive"):
                backtest(levels, Strategy("expanded"), universe=EXPANDED)

    def test_invalid_universe_is_rejected(self):
        levels = synthetic_levels()
        for universe in ((), ("XLK", "XLK"), ("XLK", BENCHMARK), ("", "XLK")):
            with self.subTest(universe=universe), self.assertRaises(ValueError):
                backtest(levels, Strategy("invalid"), universe=universe)

    def test_arbitrary_small_universe_uses_its_own_equal_weight_reference(self):
        universe = ("XLRE", "XLC")
        result = backtest(synthetic_levels(), Strategy("two", equal_weight=True),
                          universe=universe, cost_bps=0)
        initial = json.loads(result.trades.iloc[0].target_weights_json)
        self.assertEqual(initial, {"XLRE": 0.5, "XLC": 0.5, BENCHMARK: 0.})


if __name__ == "__main__":
    unittest.main()
