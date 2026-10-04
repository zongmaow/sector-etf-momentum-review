# Sector ETF momentum: investment review

Historical research using supplier-adjusted ETF levels; simulated holdings and execution.

Decision: does a fixed sector momentum rule justify an active allocation after costs?

| Portfolio | CAGR | Volatility | Max drawdown | Annual half-gross turnover* |
|---|---:|---:|---:|---:|
| MOM12_1 | 8.32% | 19.05% | -46.20% | 2.70 |
| MOM12_0 | 7.66% | 18.49% | -46.03% | 2.74 |
| MOM1 | 5.22% | 18.56% | -58.68% | 8.16 |
| BUFFER12_1 | 7.79% | 19.35% | -50.39% | 1.57 |
| EW9 | 8.68% | 18.27% | -53.29% | 0.15 |
| SPY | 8.02% | 19.39% | -55.19% | 0.00 |
| ACCOUNT_MOM20 | 8.14% | 18.96% | -52.99% | 0.56 |
| ACCOUNT_EW20 | 8.17% | 19.05% | -54.81% | 0.04 |
| ACCOUNT_BUFFER20 | 8.03% | 19.03% | -53.78% | 0.33 |
| ACCOUNT_MOM10 | 8.09% | 19.16% | -54.10% | 0.28 |

*Initial formation is excluded from turnover but included in net returns. Costs are 5 bps per side. SPY is buy-and-hold; account sleeves rebalance monthly.*

Primary mean active return vs EW9 (arithmetic annualization): -0.28%; TE 7.21%; IR -0.04.
Circular-block 95% interval for annualized mean active return: [-2.76%, 2.05%]. This is not an interval for CAGR.
Final historical period interval: [-2.64%, 4.75%].
80% SPY / 20% momentum account TE vs SPY: 1.60%; illustrative budget 2.00%.

## Manager interpretation

The primary rule does not improve average net return over EW9 in this snapshot. Do not select a different window just because it wins this table; secondary variants require a new prospective test.

The CAPM market regression uses each reported strategy at 5 bps per side against buy-and-hold SPY at 0 bp. Charging trading costs on the strategy and not on the market slightly lowers the intercept.

The full account must be compared with both SPY and an 80% SPY / 20% EW9 account. Their difference helps isolate the implemented selection rule from the decision to add a sector sleeve.

The buffer changes both trading and holdings. Compare its gross and net outcomes before attributing an improvement to cost savings. See summary.csv, episodes.csv, and analysis.json for fixed window/cost/time comparisons.

The four historical episodes are explanations of failure or resilience, not four separate experiments used to choose the rule. Daily dollar P&L records reconcile sector gains, SPY gains and fees to total wealth changes.

Known limits: revised Yahoo adjustments; synthetic next-close fills; no taxes, spreads by date, market impact, or institutional capacity test; changing sector definitions; nine historical products omit today’s separate real-estate and communication ETFs; retrospective holdout; no multi-factor or matched-concentration random controls.

Generated from the saved input and config hashes recorded in analysis.json.
