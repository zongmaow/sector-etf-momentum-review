# External validation with ten historical industry portfolios

Study date: 2026-10-04. The data use Kenneth French's official 202608 CRSP vintage; research returns are strictly truncated at December 2025.

This validation did not identify a reliably confirmed ex-ante favorable environment across periods and industry universes. Mean long-run net active returns are positive for the ten-industry portfolios, but separate estimates for the earlier and contemporary periods remain substantially uncertain. The label 'industry momentum' does not imply the same returns across different industry classifications and investment instruments.

## Data and limits to comparability

The study uses the official monthly **value-weighted** returns for ten industries. At each June-end, the official construction groups stocks using SIC industry codes available at that time and calculates returns for the following year. These are research stock portfolios, rather than SPDR ETFs or simulated pre-inception histories of those ETFs. [Official construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_ind_port.html)

Stocks are value-weighted within each industry. This study separately constructs EW10 across the ten industries, assigning 10% to each industry every month; the momentum portfolio assigns 1/3 to each of the top three industries. **EW10 is not the source file's 'Average Equal Weighted Returns' table, which equal-weights stocks within industries.** The parser reads only the first monthly value-weighted return table and rejects the missing-value sentinels -99.99/-999.

French reconstructs and revises historical returns. Download vintages from 2025 onward use CRSP CIZ: monthly returns compound daily returns, with dividends reinvested on ex-dividend dates. This differs from the earlier FIZ format. The study retains the original ZIP, documentation, hashes and data vintage; it does not claim to preserve a complete point-in-time history. [Official data notes](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)

## Unchanged strategy rules

Targets for holding month t are formed at the end of month t-1. The signal compounds the 11 months from t-12 through t-2, skipping the most recent month, t-1. Industry names break ranking ties; each of the top three industries receives 1/3. The benchmark equal-weights the same ten industries monthly. The strategy is long-only, with no cash timing and no optimization of lookback, thresholds, number of selected industries or sample periods.

Monthly data permit only theoretical month-end execution; they cannot reproduce the original ETF ledger's next-session close execution. Weights drift with returns within each month and are then rebalanced monthly. Purchases and sales of the industry baskets each incur 5bp per side, with costs satisfying the self-financing equation C=c×sum(abs(w×(V−C)−x)). This uniform cost is a research assumption, rather than an estimate of actual 1960s stock-basket trading costs. Underlying stock-rebalancing costs, fund expenses and market impact are not measured.

The portfolio is formed from cash in January 1960, with formation costs included in the first month's return. The ledger runs continuously through 2025; the account is not reset and formation costs are not charged again at 2000 or other subperiod boundaries. No liquidation fee is charged at the end.

## Baseline return results

Active return below is the mean net monthly MOM−EW10 return multiplied by 12. Interval endpoints are annualized arithmetic-return percentage points. CAGR is reported separately and is not interchangeable with this measure. The HAC12 mean tests for the three baseline samples also receive a three-test Holm adjustment.

| Sample | MOM CAGR | EW10 CAGR | Annualized mean active return | 6-month block 95% interval | 12-month block 95% interval | Raw HAC12 p | Holm3 p |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1960-01 to 1999-12 | 14.36% | 12.61% | 1.78% | [-0.09, 3.70] | [0.02, 3.66] | 0.0517 | 0.1033 |
| 2000-01 to 2025-12 | 10.73% | 9.11% | 1.73% | [-1.16, 4.80] | [-1.08, 4.78] | 0.2402 | 0.2402 |
| 1960-01 to 2025-12 | 12.91% | 11.22% | 1.76% | [0.13, 3.43] | [0.22, 3.36] | 0.0255 | 0.0764 |

Both block intervals are positive for the full 1960–2025 sample, but this favorable pooled result should not be selected in isolation. Each of the two prespecified subperiods has an interval crossing zero, and the pooled mean's Holm3 p is not below 0.05. The sample supports the possibility of positive long-run industry-momentum returns; it does not establish a result that can be adopted directly for any industry ETF.

The 1960–1999 period is a transfer check outside the ETF product history, rather than a genuinely unseen prospective sample. The 2000–2025 period uses research portfolios from the same era but a different classification. Investment instruments, industry definitions, constituent stocks, execution timing and stock weights all change; differences cannot be attributed solely to the number of industries.

## Four frozen ex-ante conditions

H1: through the signal month, the market's cumulative past-24-month return is <0 and its recent three-month return is >0; market total return is French Mkt−RF with RF added back. H2: the Spearman correlation between industry recent-three-month returns and the MOM12−1 signal is ≥0. H3: the sample standard deviation of industry MOM signals exceeds the fixed calibration-period median. H4: H3 holds, and the intersection of the current and two preceding top-three sets contains at least two industries. All conditions use only information available before trading.

For 1960–1999, the H3/H4 threshold is 11.94%, calibrated on 120 decisions from 1950–1959. For 2000–2025, it is 10.35%, calibrated on 480 decisions from 1960–1999. These are cross-sectional standard deviations of the 11-month cumulative signal, rather than monthly return volatility. Thresholds were not selected using conditional returns.

The primary test is the difference between group means, using a Bartlett HAC kernel with a fixed 12-month lag, the n/(n−2) correction and two-sided asymptotic-normal p-values. The expected-favorable-group mean uses a no-intercept regression of y×I on I over the complete monthly calendar, with the n/(n−1) correction; this avoids incorrectly treating selected, compressed months as consecutive observations. Each sample family has a fixed eight-test Holm adjustment: four condition contrasts and four tests of expected-favorable-group means against zero. H1's favorable group is the condition-false group; for the other hypotheses it is the condition-true group.

The 6/12-month circular blocks jointly resample labels and outcomes, using 20,000 draws each and seed=20261004. Conditional means below are the selected months' average active returns multiplied by 12. They do not imply that a condition persists for a full year or that future returns will equal the table values.

### 1960-01 to 1999-12

| Hypothesis | True months/episodes | False months/episodes | True mean active return | False mean active return | True−false | Contrast Holm8 p | 6-month block contrast interval | 12-month block contrast interval | Favorable-group Holm8 p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 15/5 | 465/6 | -13.81% | 2.28% | -16.09% | 0.0043 | [-29.51, -2.42] | [-28.84, -2.99] | 0.0893 |
| H2 | 374/55 | 106/54 | 1.81% | 1.66% | 0.15% | 1.0000 | [-3.97, 4.26] | [-4.05, 4.44] | 0.6214 |
| H3 | 165/41 | 315/40 | 1.92% | 1.70% | 0.22% | 1.0000 | [-4.01, 4.61] | [-3.99, 4.40] | 1.0000 |
| H4 | 142/40 | 338/39 | 1.39% | 1.94% | -0.55% | 1.0000 | [-5.13, 4.18] | [-5.02, 3.97] | 1.0000 |

### 2000-01 to 2025-12

| Hypothesis | True months/episodes | False months/episodes | True mean active return | False mean active return | True−false | Contrast Holm8 p | 6-month block contrast interval | 12-month block contrast interval | Favorable-group Holm8 p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 31/10 | 281/11 | -0.67% | 2.00% | -2.66% | 1.0000 | [-17.44, 9.27] | [-20.58, 9.34] | 1.0000 |
| H2 | 243/42 | 69/41 | 0.32% | 6.71% | -6.39% | 0.5760 | [-13.64, 0.34] | [-13.31, 0.32] | 1.0000 |
| H3 | 183/30 | 129/29 | 2.53% | 0.60% | 1.93% | 1.0000 | [-3.60, 7.44] | [-3.01, 7.07] | 1.0000 |
| H4 | 149/37 | 163/36 | 2.17% | 1.33% | 0.83% | 1.0000 | [-5.55, 6.96] | [-4.81, 5.96] | 1.0000 |

### 2000-01 to 2012-12

| Hypothesis | True months/episodes | False months/episodes | True mean active return | False mean active return | True−false | Contrast Holm8 p | 6-month block contrast interval | 12-month block contrast interval | Favorable-group Holm8 p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 26/6 | 130/7 | 4.37% | -1.34% | 5.71% | 1.0000 | [-6.45, 17.61] | [-6.02, 17.15] | 1.0000 |
| H2 | 117/23 | 39/22 | -1.43% | 2.73% | -4.16% | 1.0000 | [-13.63, 5.08] | [-12.89, 4.17] | 1.0000 |
| H3 | 91/14 | 65/14 | 0.13% | -1.12% | 1.25% | 1.0000 | [-6.47, 8.49] | [-5.41, 7.29] | 1.0000 |
| H4 | 74/19 | 82/19 | -0.10% | -0.66% | 0.55% | 1.0000 | [-10.03, 9.67] | [-9.49, 8.71] | 1.0000 |

### 2013-01 to 2025-12

| Hypothesis | True months/episodes | False months/episodes | True mean active return | False mean active return | True−false | Contrast Holm8 p | 6-month block contrast interval | 12-month block contrast interval | Favorable-group Holm8 p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 5/4 | 151/5 | -26.83% | 4.87% | -31.70% | 0.1596 | [-91.30, 9.15] | [-91.63, 10.09] | 0.1596 |
| H2 | 126/20 | 30/19 | 1.94% | 11.88% | -9.93% | 0.3242 | [-20.45, -0.20] | [-20.05, -0.22] | 1.0000 |
| H3 | 92/16 | 64/16 | 4.90% | 2.35% | 2.56% | 1.0000 | [-5.08, 10.77] | [-4.50, 10.21] | 0.7460 |
| H4 | 75/18 | 81/18 | 4.40% | 3.35% | 1.06% | 1.0000 | [-6.02, 8.83] | [-4.39, 7.43] | 0.7460 |

### Evidence worth retaining

H1-true months underperformed markedly in 1960–1999, regardless of whether 6-month or 12-month blocks are used; the contrast's Holm8 p≈0.0043. However, there are only 15 such months, all in 1970–1976. The five contiguous state episodes cannot be treated as five independent crises, and the condition falls short of this study's reporting threshold of at least 24 months. The favorable complement's mean has Holm8 p≈0.0893, so positive returns were not simultaneously confirmed. In 2000–2025, the H1 contrast intervals cross zero, and the contrast changes direction between the two halves. This early observation therefore cannot be generalized into a stable ex-ante switch.

H2 agreement between recent and intermediate-term rankings did not deliver better returns; the contemporary ten-industry condition contrast is negative. This counterexample distinguishes apparent agreement in rankings from evidence that past winners will continue to win. Reversing H2 after seeing the results and recommending ranking disagreement would not be justified.

H3 greater opportunity has a positive contrast in both broad external samples, but intervals are wide and the Holm-adjusted tests are not significant. Adding past-leader stability in H4 did not establish an improvement. Neither past dispersion nor past stability automatically resolves the question of future persistence.

Leave-one-year-out results are stored in leave_one_year_out.csv. Frozen labels and thresholds are not recomputed; these results describe conditional-mean directions only, without calculating HAC across gaps left by deleted years. Excluding 2022 from 2000–2025 gives H1/H2/H3/H4 contrasts of −2.00, −7.25, +0.93 and +0.41 percentage points per year, respectively. This does not turn any unconfirmed hypothesis into a confirmed result.

The supplementary market regression is fixed as active=const+Z+M+Z×M and reports the two states' intercepts and beta difference. The contemporaneous market is used only to describe exposure, rather than as a tradable future input. The beta difference and conditional-mean difference are distinct quantities; an intercept change is not causal evidence. Complete results are stored in conditional_results.json.

## Reproduction and checks

analyze_external.py reads the source monthly value-weighted industry table and constructs the fixed signal and self-financing ledger. analyze_conditions.py applies inference to the frozen conditions. write_summary.py generates this memo from JSON.

Checks cover complete monthly coverage without gaps; rejection of missing-value sentinels; agreement between each holding month's 11-month signal and direct compounding; invariance of the current signal to changes in the skipped recent month or future returns; agreement between EW10 weight drift and independent calculation; agreement with the analytical solution for initial formation costs; reconciliation of monthly NAV changes to industry P&L less costs; and equality of monthly costs to gross purchases plus sales multiplied by the per-side rate. Source and generated-file hashes are in provenance.json.

comparison_returns.csv contains MOM12_1, EW10 and net active monthly returns from the continuous 1960–2025 ledger, allowing paired comparisons with ETF returns for the same months. Such comparisons describe transfer differences; they cannot isolate the effect of industry definitions or industry count.
