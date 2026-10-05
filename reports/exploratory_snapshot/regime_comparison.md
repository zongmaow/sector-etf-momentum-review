# The same rule across periods and sector environments

This is a retrospective exploration. The primary rule, nine-sector full-sample conclusion and cost convention remain unchanged. The complete grid is in [all_windows.csv](all_windows.csv). All figures assume 5 bps per side; dividends are already included in the vendor adjusted-price total-return proxy.

## Profit and benchmark outperformance are different outcomes

| Year | Strategy net cumulative return | EW9 | SPY | Observation |
|---|---:|---:|---:|---|
| 2022 | 9.48% | -5.23% | -18.18% | Profitable and ahead of EW9 |
| 2011 | -2.16% | 3.16% | 1.89% | Loss and behind EW9 |
| 2006 | 4.63% | 16.19% | 15.85% | Profitable but behind EW9 |
| 2002 | -12.58% | -18.34% | -21.58% | Loss, but smaller than EW9's |

These examples were selected after reviewing all 26 complete calendar years. They are illustrations, not independent tests selected in advance. Losing less than the benchmark is not an absolute profit.

## Why sector contributions change

| Period and holding | Contribution to strategy cumulative return | Interpretation |
|---|---:|---|
| 2005 / XLE | +12.66 percentage points | Energy holdings contributed positively |
| 2013 / XLV | +13.55 percentage points | Health care holdings contributed positively |
| 2013 / XLY | +12.64 percentage points | Consumer discretionary holdings contributed positively |
| 2020 / XLK | +12.72 percentage points | Technology contributed positively; the market comparison still matters |
| 2022 / XLE | +18.58 percentage points | Holding-period contribution from the same energy product was positive |
| 2023 / XLE | -4.75 percentage points | The same product's contribution turned negative the next year |

Contributions equal simulated holding-period dollar P&L divided by the portfolio's beginning-of-year NAV. They reflect purchases, sales and the weight path; they are neither each ETF's full-year buy-and-hold return nor causal sector alpha. Trading fees are reported separately as COST. Sector contributions plus COST reconcile to the strategy's annual net return.

These differences describe how one rule fares as sector leadership persists or reverses. They do not establish a signal that identifies such environments before trading.

## Complete period comparisons

| Complete calendar interval | Strategy CAGR | EW9 CAGR | SPY CAGR |
|---|---:|---:|---:|
| 2000-2004 | 3.23% | 2.77% | -2.20% |
| 2005-2009 | 2.68% | 2.68% | 0.39% |
| 2010-2014 | 12.90% | 15.29% | 15.34% |
| 2015-2019 | 7.45% | 10.02% | 11.56% |
| 2020-2024 | 14.13% | 12.28% | 14.45% |
| 2025-2025 | 17.34% | 13.43% | 17.73% |

Of all 277 rolling three-year windows, the strategy made an absolute profit in 236, beat EW9 in 124 and beat SPY in 136. These highly overlapping windows describe this sample, not independent success rates or future probabilities.

The most favorable three-year window relative to EW9 was 2020-01 through 2022-12, with CAGRs of 16.42% versus 10.63%. The least favorable was 2009-03 through 2012-02, with 16.42% versus 26.48%. All windows are disclosed; highlighting extremes does not revise the primary full-sample conclusion.

## Adding real estate and communication services

[XLRE](https://www.ssga.com/us/en/individual/etfs/state-street-real-estate-select-sector-spdr-etf-xlre) launched in 2015 and [XLC](https://www.ssga.com/us/en/individual/etfs/state-street-communication-services-select-sector-spdr-etf-xlc) in 2018. Their fund histories cannot be backfilled to 2000. This comparison uses warm-up data from 2018-12-31. Both nine- and eleven-sector accounts are formed from cash at the close of the first trading session in 2020 and run through the end of 2025.

MOM12-1, equal weights in the top three, execution timing and costs are unchanged. Each universe has its own EW9 or EW11 benchmark because expansion changes equal-weight exposure as well as selection.

| Accounts formed in 2020; sample 2020-2025 | Strategy CAGR | Corresponding equal-weight CAGR | SPY CAGR |
|---|---:|---:|---:|
| Nine sectors | 14.55% | 12.38% | 14.80% |
| Eleven sectors | 16.48% | 11.97% | 14.80% |

The common period, annual results and complete three-year rolling grid are in [universe_comparisons.csv](universe_comparisons.csv). This tests sensitivity to the product universe; selecting historically favorable sectors does not establish the rule's effectiveness.

| Added sector and year | Contribution to the eleven-sector strategy's annual return |
|---|---:|
| 2020 / XLC | +12.31 percentage points |
| 2021 / XLC | -3.57 percentage points |
| 2021 / XLRE | +4.37 percentage points |
| 2022 / XLRE | -5.31 percentage points |

XLRE was selected at 6 of 72 monthly executions; XLC at 40 of 72.

Added-sector contributions can turn negative. Eleven-sector momentum still lagged EW11 in 2021 and 2023. Added ETF contributions are not the net benefit of universe expansion because those holdings also displace existing sectors. Full contributions and replacement paths are in [universe_annual_contributions.csv](universe_annual_contributions.csv) and [universe_holdings_comparison.csv](universe_holdings_comparison.csv).

## What this establishes

The results show transitions among profit, loss, outperformance and underperformance, with auditable holdings contributions. Turning these descriptions into a rule that trades only in favorable environments would require observable advance definitions, a new rule and genuinely subsequent validation. This exploration adds no timing conditions and does not relabel selected years as independent out-of-sample results.

The original nine-sector 2000-2025 conclusion is retained. Code and the complete exploration grid allow both favorable and unfavorable cases to be reproduced.
