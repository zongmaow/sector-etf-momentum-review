import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
from sector_momentum.data import TICKERS
from sector_momentum.engine import Strategy, backtest
from sector_momentum.exploration import UNIVERSE11, window_grid, compare_window, outcome, load_expanded, reset_generated_outputs


class ExplorationTests(unittest.TestCase):
    def test_full_grid_covers_every_year_and_every_monthly_36m_start(self):
        frame = pd.DataFrame(window_grid())
        years = frame[frame.kind == 'calendar_year']
        self.assertEqual(list(years.start.str[:4].astype(int)), list(range(2000, 2026)))
        rolling = frame[frame.kind == 'rolling_36m']
        expected = pd.period_range('2000-01', '2023-01', freq='M')
        self.assertEqual(list(pd.to_datetime(rolling.start).dt.to_period('M')), list(expected))
        self.assertEqual(len(rolling), 277)
        for row in rolling.itertuples():
            self.assertEqual(pd.Period(row.end, 'M').ordinal - pd.Period(row.start, 'M').ordinal + 1, 36)
        blocks = frame[frame.kind.isin(['five_year_block', 'remaining_years'])]
        covered = [year for row in blocks.itertuples() for year in range(int(row.start[:4]), int(row.end[:4]) + 1)]
        self.assertEqual(covered, list(range(2000, 2026)))

    def test_profitable_does_not_imply_outperforming_and_less_loss_is_not_profit(self):
        self.assertEqual(outcome(.05, .16), 'profit_underperform')
        self.assertEqual(outcome(-.12, -.18), 'loss_outperform')
        self.assertEqual(outcome(.09, -.05), 'profit_outperform')
        self.assertEqual(outcome(-.02, .03), 'loss_underperform')

    def test_period_comparison_keeps_existing_holdings_and_does_not_charge_new_formation(self):
        dates = pd.bdate_range('1998-12-31', '2001-12-31').difference(pd.DatetimeIndex(['2001-01-01']))
        levels = pd.DataFrame(100., index=dates, columns=TICKERS)
        # A carried position earns the first session's gain in 2001. Re-forming at
        # that close would miss it and pay a new formation fee.
        levels.loc['2001-01-02':, :] = 110.
        results = {'MOM12_1': backtest(levels, Strategy('mom'), end='2001-12-31'),
                   'EW': backtest(levels, Strategy('ew', equal_weight=True), end='2001-12-31'),
                   'SPY': backtest(levels, Strategy('spy', buy_hold_market=True), end='2001-12-31')}
        row = compare_window(results, {'kind': 'calendar_year', 'start': '2001-01-01', 'end': '2001-12-31'})
        for column in ['mom_total_return', 'ew_total_return', 'spy_total_return']:
            self.assertAlmostEqual(row[column], .1, places=12)
        fresh = backtest(levels, Strategy('mom'), start='2001-01-01', end='2001-12-31')
        self.assertLess(fresh.nav.iloc[-1] / fresh.nav.iloc[0] - 1, 0)

    def test_diagnostic_labels_cannot_exceed_history_or_silently_expand_midmonth(self):
        nav = pd.Series([100., 110.], index=pd.to_datetime(['2024-12-31', '2025-12-31']))
        results = {'MOM12_1': SimpleNamespace(nav=nav)}
        for first, last in [('2025-01-01', '2027-12-31'), ('2025-02-15', '2025-12-31'),
                            ('2025-01-01', '2025-12-15'), ('2024-01-01', '2025-12-31')]:
            with self.subTest(first=first, last=last), self.assertRaises(ValueError):
                compare_window(results, {'start': first, 'end': last})

    def test_rerun_removes_stale_optional_results_and_retains_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name in ['universe_comparisons.csv', 'eleven_MOM12_1_trades.csv',
                         'period_comparison.png', 'my_research_notes.md']:
                (path/name).write_text('prior output')
            reset_generated_outputs(path)
            self.assertEqual(sorted(p.name for p in path.iterdir()), ['my_research_notes.md'])

    def test_expanded_loader_requires_real_complete_columns_and_does_not_fill(self):
        frame = pd.DataFrame(100., index=pd.bdate_range('2020-01-02', periods=3), columns=UNIVERSE11+('SPY',))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'prices.csv'
            frame.to_csv(path, index_label='date')
            pd.testing.assert_frame_equal(load_expanded(path), frame.rename_axis('date'), check_freq=False)
            missing = frame.copy(); missing.iloc[0, -2] = np.nan
            missing.to_csv(path, index_label='date')
            with self.assertRaises(ValueError):
                load_expanded(path)
            frame.drop(columns='XLC').to_csv(path, index_label='date')
            with self.assertRaises(ValueError):
                load_expanded(path)


if __name__ == '__main__':
    unittest.main()
