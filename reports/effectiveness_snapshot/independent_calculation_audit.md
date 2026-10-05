# ETF effectiveness study: independent calculation audit

Review date: 2026-10-04. Reviewed `work/sector-effectiveness/study.py` and `outputs/sector-etf-effectiveness-study`. No research script or data was changed. The independent reproduction program was `independent_audit.py`; the complete error record was `independent_audit.json`, both in the original study directory.

## Conclusion

No financial-calculation, timing-alignment or statistical-implementation error was found that would change this round's ETF conclusion. Actual switching trades, the calibrated threshold, HAC on the complete calendar grid, the Holm eight- and six-test families, and return units passed independent reproduction. H1 has very few state observations and a high proportion of block draws missing a state; its intervals are fragile descriptions rather than reliable general inference about recovery periods.

## 1. Features and timing

- For all 312 months, independently calculated intermediate signals `P[signal−1]/P[signal−12]−1`, recent three-month returns, market three-month/two-year returns, ranking agreement and standard deviation directly from each month's last actual trading-day prices. Maximum errors were no greater than `1.2e−16`.
- Independently checked all 312 top-three selections. Ties were resolved by sector code; every selection matched.
- Checked the three-way intersection of the current and preceding two top-three sets for 310 months with sufficient history. Every result matched. The earliest two stability values were missing, not known zeros.
- All 192 months in the primary 2010–2025 inference period had valid two-year market history for H1 and three-decision history for H4. Early missing conditions were marked invalid and excluded from primary inference.
- Independently reproduced the decision-score standard-deviation median corresponding to the 2000–2009 holding months as `0.11786584746618972`, exactly matching the manifest. It is used only as a threshold from 2010 onward, avoiding a future-informed threshold.

## 2. Actual filter-trading ledgers

The independent implementation valued adjusted-price units daily without calling the study's trading filters. It solved the fee equation `C=c·Σ|w(V−C)−x|` using a separate fixed-point iteration, then updated units. It checked 192 trades for each of F1/F2/F3, always momentum and always equal weight.

- Every signal date was the month-end preceding the holding month; execution was the following first trading day's close.
- Existing units received the execution-day price change; new units took effect after the close.
- Every momentum/equal-weight choice matched the contemporaneous H1/H2/H4 label. No precomputed benchmark monthly returns were spliced together.
- Initial formation from cash was charged, all later cross-mode buys and sells were charged, and no final liquidation was invented.
- Maximum relative daily NAV error across the five accounts was no greater than `4.2e−15`; maximum dollar fee error was no greater than `1.6e−11`; turnover error was below `3.4e−16`.
- Daily sector P&L plus fees reconciled to independent NAV changes, with maximum absolute error below `2.8e−9` dollars, attributable to floating-point differences.

The original engine recalculated six always-momentum/always-equal-weight cases at 0/5/10 bp. Monthly returns matched the study outputs within approximately `1.0e−16`. The constant-filter degeneration checks passed.

The original full-period cached monthly returns used by the condition study were also independently rebuilt from cash in 2000 using the original engine. All six MOM12−1 and EW9 paths at 0/5/10 bp matched, with errors approximately `1.0e−16`. Thus this audit found no mismatch between cached results and the current prices/code.

## 3. HAC, conditional means and multiple testing

Independently reproduced the OLS sandwich using a complete 192×192 Bartlett kernel matrix, a 12-month bandwidth and the `n/(n−k)` finite-sample correction.

- OLS conditional-contrast coefficients matched the difference between the two independently calculated group means.
- Favorable-group means used a no-intercept indicator regression. Inputs and error scores were zero outside the group, while their calendar positions remained in the grid. This preserves actual lag distances rather than compressing separated conditional months into an adjacent sequence.
- Maximum differences in independently calculated standard errors and two-sided asymptotic-normal p-values were below `2.4e−15`.
- Each cost scenario had four conditional contrasts plus four favorable-group mean tests, forming an eight-test Holm family. Each scenario also had three filters tested against both EW9 and MOM, forming a six-test family. Sorting, cumulative maxima and clipping were correct, with maximum errors below `5.6e−16`.
- Two-sided significance and a hypothesized direction are separate concepts. H1's point estimate had the opposite direction to “previous winners perform worse during recovery”; H4's estimate also opposed its original hypothesis. Neither can be described as confirming the hypothesis.
- The primary hypothesis family had no statistical confirmation: all Holm-eight adjusted values were 1. The filters also had no positive incremental-return evidence surviving multiplicity correction.

## 4. Explicit limits of block resampling

The code jointly resampled state labels and outcomes in the same contiguous monthly blocks. Percentile intervals are not null-hypothesis p-values; p-values came from HAC, so the two quantities were not confused. Here “joint” means resampling labels and outcomes together, not simultaneous interval coverage across all four conditions.

H1 had only five months in one consecutive state run. Among 20,000 draws:

| Block length | Draws missing a state group, discarded | Share of all draws | Valid draws used for intervals |
|---|---:|---:|---:|
| 6 months | 3,629 | 18.15% | 16,371 |
| 12 months | 4,858 | 24.29% | 15,142 |

These counts can be reconciled to CSV `valid_draws` and the manifest's 20,000 total draws. After discarding empty-group draws, the resulting distribution is conditional on that state being sampled. It is not an ordinary, adequately sampled 95% interval. H2/H3/H4 retained all 20,000 draws for both block lengths.

H1's main limitation is the number of events, rather than the size of its HAC p-value. This sample cannot reliably determine whether sector momentum is harmed in all crisis recoveries.

## 5. Units and provenance

- Conditional means, contrasts and intervals are monthly simple-return decimals; multiply by 100 for monthly percentages.
- `annualized_arithmetic_difference` and its intervals multiply the monthly quantities by 12. They are arithmetic annualized means, not CAGR.
- Filter CAGR comes from actual NAV and elapsed calendar years. Multiplying a conditional monthly mean by 12 does not imply an attainable conditional annual compounded return.
- The original condition study used holdings continuously inherited from 2000; the filter study used fair, same-date formation from cash in 2010. Their different first-month paths are an explicit design choice, not a data error.
- SHA-256 identities for prices, the frozen protocol and the study script matched the manifest.

Additional provenance recommendation: `study.py` read `reports/snapshot/monthly_returns.csv`, whose identity was not yet separately recorded in the manifest. This audit independently reproduced and matched it; its SHA-256 was `e2d2b2177515c1f281bc4092f3cec3abd5d2abfc088ed79dca7a6a735407d100`. Adding it to the final provenance record would document every read dependency without changing these numerical results.

## Supported final statement

The four fixed price-environment hypotheses and three actual trading filters did not identify a robust, cost-adjusted ex-ante switch in the 2010–2025 nine-sector ETF sample. Confidence in the calculation of this negative result is relatively high, but it covers only this round's fixed rules. It does not prove that every sector-rotation or environment-identification method is ineffective. Historical P&L mechanisms must remain distinct from predictably profitable environments.
