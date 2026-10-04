import unittest
import numpy as np
import pandas as pd
from sector_momentum.data import TICKERS
from sector_momentum.engine import Strategy, backtest
from sector_momentum.reporting import period_result


class PnlTests(unittest.TestCase):
    def test_wealth_changes_and_period_returns_reconcile_with_fees(self):
        dates = pd.bdate_range('1998-12-31', '2000-04-28')
        rng = np.random.default_rng(44)
        levels = pd.DataFrame(100*np.exp(np.cumsum(rng.normal(0,.01,(len(dates),len(TICKERS))),axis=0)),index=dates,columns=TICKERS)
        result = backtest(levels, Strategy('account', sleeve_fraction=.2), cost_bps=10, end='2000-04-30')
        np.testing.assert_allclose(result.daily_pnl.sum(axis=1).iloc[1:], result.nav.diff().iloc[1:], rtol=1e-9, atol=1e-8)
        self.assertLess(result.daily_pnl.COST.sum(), 0)
        metric = period_result(result, '2000-02-29', '2000-04-30')
        self.assertAlmostEqual(sum(metric['pnl_return_decomposition'].values()), metric['total_return'], places=12)
        # Changing an account sleeve must affect its risk path, rather than mixing scalar CAGRs.
        pure = backtest(levels, Strategy('pure'), cost_bps=10, end='2000-04-30')
        self.assertFalse(np.allclose(result.nav, pure.nav))


if __name__ == '__main__':
    unittest.main()
