# Sector rotation effectiveness: frozen research protocol

Prepared on 2026-10-04. The protocol was written before this round's conditional-return and trading-filter calculations. It defines this analysis; it cannot turn previously examined 2000–2025 market history into an unseen sample.

## Question and scope

The strategy is a long-only sector ETF portfolio using MOM12−1, equal weights in the top three sectors, and monthly rebalancing. Effectiveness means positive active return over a monthly equal-weight portfolio drawn from the same universe after execution costs, with evidence that is stable across time, costs, industry definitions and influential years. Absolute profits, smaller losses and outperformance of SPY are reported separately and do not replace this definition.

Three conclusions are evaluated separately: what the actual ledger explains; whether information available before trading is associated with different conditional returns; and whether actual trading filters using that information improve results. Realized future industry persistence is used only for the first task.

## Fixed rules and timing

- Original ETF sample: nine sectors, 2000–2025; the original price snapshot is unchanged.
- Threshold calibration: the 120 holding months corresponding to 2000–2009 decisions determine one median of cross-sectional signal standard deviation. The threshold is not selected using returns.
- Primary conditional inference: 2010–2025. Direction stability is examined separately in 2010–2017 and 2018–2025; these are retrospective time checks.
- The month-end signal uses information available by the previous month-end: eleven months of cumulative total return over the preceding twelve months, excluding the most recent month. Execution follows the original engine: the next trading day's close, with existing holdings receiving execution-day returns.
- Primary cost: 5 bp per side; robustness checks use 0 and 10 bp, recalculating actual holdings and fees.
- Monthly net active return equals MOM12−1 net monthly return minus the corresponding equal-weight net monthly return. Calendar months are the primary return convention.

## Four fixed conditional hypotheses

Every condition uses data known at the decision. Expected directions are research hypotheses; tests remain two-sided and directions are not changed after observing results.

1. **H1: recovery after a market decline.** At the previous month-end, SPY's cumulative return over the past 24 months is below zero and its most recent 3-month cumulative return is above zero. Hypothesis: previous winners have lower active returns. This is a simplified transfer of a literature mechanism to a long-only sector setting, not a claim of equivalence to a long-short stock momentum crash model.
2. **H2: agreement between recent and intermediate industry rankings.** The Spearman rank correlation between the nine sectors' most recent 3-month returns and MOM12−1 scores is at least zero. Hypothesis: active returns are higher when the condition holds.
3. **H3: a larger industry opportunity set.** The sample standard deviation of the nine MOM12−1 scores exceeds its median in the 2000–2009 calibration period. Hypothesis: active returns are higher when the condition holds. Greater dispersion does not itself imply continued trends.
4. **H4: large opportunities with stable leaders.** H3 holds, and the intersection of the current and preceding two month-end top-three sets contains at least two sectors. Hypothesis: active returns are higher when the condition holds.

No return-driven thresholds, lookback searches or selection of the best years are added. Other ranking measures already examined remain descriptive and are not new evidence of a successful filter.

## Inference and the standard for high confidence

- Report months in each state, counts of distinct consecutive state runs, both groups' mean net active returns, and their difference. State runs are not necessarily statistically independent; their counts help reveal concentration in one or two events.
- Test the four fixed mean differences using HAC standard errors with a Bartlett kernel, 12 monthly lags and a finite-sample degrees-of-freedom correction. Also test the mean net active return in each hypothesis's expected favorable group. The four contrasts and four favorable-group means form one eight-test Holm family. H1's favorable group is the condition being false; H2–H4 favor the condition being true. A difference between groups does not establish positive active return in the favorable group.
- Jointly resample state labels and outcomes using contiguous six-month circular blocks, 20,000 draws and fixed seed 20261004. Twelve-month blocks provide sensitivity checks. Percentile 95% intervals describe retrospective sample uncertainty, not future success probabilities; small state groups and nonstationarity limit reliability.
- Use the fixed auxiliary exposure regression: active return ~ constant + state label + contemporaneous SPY return + state label × contemporaneous SPY return. The interaction allows market beta to vary by state; the state coefficient is the linear conditional-return difference when market return is zero. This diagnostic does not create another significance opportunity for selecting a filter, establish causality or remove every other factor exposure.
- Remove each year in turn, and separately remove 2022, to check dependence on an influential year.
- Calling a condition's effectiveness evidence high confidence requires, at minimum: Holm-adjusted p < 0.05 for both the primary contrast and favorable-group active mean, with the hypothesized direction; six- and twelve-month-block 95% intervals excluding zero; the same direction in both time halves; at least 24 condition months and five state runs; an unchanged direction after removing 2022; and directionally consistent external industry evidence. These are cautious reporting standards for this analysis, not mathematically sufficient conditions or guarantees of future returns.
- If the standard is not met, report the hypothesis as unconfirmed. Weak linear association does not imply that every possible model is unable to predict returns.

## Three fixed trading filters

The filters are retrospective trading tests. Each switches to equal weight in the same universe when momentum is disabled. They do not introduce cash timing, and the best filter is not selected as a final strategy.

- **F1:** equal weight when H1 holds; otherwise the original momentum strategy.
- **F2:** momentum when H2 holds; otherwise equal weight.
- **F3:** momentum when H4 holds; otherwise equal weight.

All filters start from cash on the same date in 2010; new original-momentum and EW9 accounts start simultaneously as controls. Daily valuation, monthly weight drift, actual cross-mode trading costs and initial formation costs follow the original self-financing equation. Published monthly returns are not spliced together in place of trading. Check that always-momentum and always-equal-weight filters reduce exactly to the original engine.

Each of three filters is tested against EW9 and original momentum using monthly mean-return differences. These six HAC tests have their own Holm correction, with block intervals reported alongside them. This trading-test family is disclosed separately from the four-condition family; the smallest p-value across the two families is not used to claim discovery.

## External industry-portfolio validation

Use official Kenneth French ten-industry value-weighted monthly returns and the factor market return, restricted to complete months through 2025. These are research portfolios with different industry classifications, stock weights and investability from the ETFs; they must not be presented as pre-inception ETF histories. Official histories are revised and are not a fully archived point-in-time vintage feed.

- Keep MOM12−1 and equal-weight top-three holdings, compared with ten-industry equal weight. Monthly data allow theoretical formation at month-end for the following month, not the ETF engine's next-trading-close delay.
- Earlier external period: 1960–1999, with thresholds calibrated on 1950–1959. Contemporary external period: 2000–2025, calibrated on 1960–1999. Signal-dispersion thresholds are each calibration period's median and are not selected again using conditional returns.
- H1's market proxy uses French monthly market total return, Mkt−RF + RF. Other conditions use the ten industries; the top-three stability threshold is unchanged.
- Five bp per side is a common research-friction assumption, not an estimate of historical costs for trading underlying industry stock baskets. Actual costs could have been substantially higher.
- External results assess transferability of the mechanism; retrospective historical replication is not prospective validation.

## Deliverables

A complete research report, originally produced in Chinese; the frozen protocol; monthly features and state labels; every result for the four hypotheses and three filters; external historical replication; source and data hashes; reproducible scripts; and necessary financial-ledger checks. Retain the original project's primary conclusion. Do not present an ex-post explanation as a profitable environment already identified in advance.
