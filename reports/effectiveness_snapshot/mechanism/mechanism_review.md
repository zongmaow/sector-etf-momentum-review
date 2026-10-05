# Return mechanics and strength of evidence for the fixed nine-sector MOM12−1 strategy

This page attributes realized returns using the saved nine-sector adjusted-price levels, trading ledger and NAV. The rule remains a past-twelve-month signal excluding the most recent month, the top three sectors at equal weights, execution at the next trading day's close, and 5bp per side. No parameters were adjusted, no new trading periods were selected, and the underlying analysis made no repository changes. All environment groupings explain realized outcomes; they are not independently validated trading filters.

## 1. What can be explained with high confidence: return identities

Immediately after each trade, the portfolio allocates exactly one-third of its net assets to each of three selected sectors; EW9 allocates one-ninth to each of nine sectors. Over a complete interval from just after execution to just before the next execution:

`Gross active return = (2/3) × (mean interval return of the three selected sectors − mean interval return of the six unselected sectors)`.

`Net active return = gross active return − MOM current-trade fee fraction × (1 + MOM gross return) + EW9 current-trade fee fraction × (1 + EW9 gross return)`.

The fee fraction is the actual cost of the current trade divided by pretrade NAV, including the self-financing cost calculation; it is not a mechanical subtraction of 5bp. Both identities were checked separately over 311 complete execution intervals. The maximum net-return discrepancy against the trading ledger is below 9×10⁻¹⁶. The intervals run from the 2000-01-03 close to immediately before execution on 2025-12-01. The final December 2025 holding interval had not reached another execution, so it is excluded from this diagnostic. Final performance still uses all 312 complete calendar months.

The same gross-return identity can also be written as:

`Gross active return = √2 × cross-sectional standard deviation of sector forward returns × corr(selection indicator, sector forward returns)`.

The standard deviation uses the nine-sector population convention, ddof=0. This decomposition shows that sector dispersion determines the potential magnitude of gains or losses; whether selected sectors subsequently rise more, or fall less, determines their direction. **High dispersion alone does not make momentum effective.** Both forward quantities become known only after the trade and can explain results, but cannot determine whether to trade next month.

## 2. Did leadership persist across the full sample?

The mean Spearman correlation between past momentum rankings and sector return rankings over the next complete holding interval is **0.00472**. A six-month circular-block bootstrap with 20,000 draws and fixed seed 20261004 gives a 95% interval of **[−0.0364, +0.0464]**. This does not support stable persistence, nor does it prove that industry momentum can never exist.

| Realized interval state | Intervals | Mean net active return of MOM relative to EW9 |
|---|---:|---:|
| Past and subsequent rankings positively correlated | 156 | +1.375% |
| Past and subsequent rankings uncorrelated or negatively correlated | 155 | −1.452% |

The table verifies the mechanical relationship: relative returns are earned when past winners remain ahead and lost when they reverse. Because the groups directly use subsequent returns, their strong relationship is not ex-ante predictive evidence; neither condition can be used as a real-time switch.

The selected top three and the subsequent best-performing top three overlap by an average of **1.013 sectors** per interval, with a bootstrap 95% interval of **[0.945, 1.080]**. Selecting three sectors randomly from nine has an expected overlap of 1 with any fixed set of three. This is an intuitive mathematical reference, rather than a completed random-portfolio return test; overlap near 1 cannot replace a net-return test.

The mean interval-return spread between selected and unselected sectors is **−0.0194%**, with a 95% interval of **[−0.3234%, +0.2868%]**. The sample therefore does not establish that past winners reliably outperform the remaining sectors.

## 3. Effects of costs and exceptional years

Across all 312 calendar months, net annualized arithmetic active return is **−0.278%**; its six-month bootstrap 95% interval is **[−2.616%, +2.074%]**. Intervals also cross zero with three-month or twelve-month blocks. Gross annualized arithmetic active return is **−0.0216%**, and additional trading costs relative to EW9 subtract approximately **0.256% per year**. Costs can turn a weak signal into negative returns, but removing them still does not establish a significantly positive advantage.

The strategy outperformed EW9 in 163 of the 312 months and had positive returns in 192 months. A win rate slightly above one-half does not ensure positive mean active returns.

After deleting one complete calendar year at a time, annualized arithmetic active returns remain negative in 25 of the 26 descriptive results. Only excluding 2006 produces +0.120%. Excluding 2022 produces **−0.872% per year**. These are sensitivity descriptions, rather than 26 independent validations; returns calculated after deleting a bad year are not investable returns.

Leave-one-year-out mean rank IC ranges from **−0.00530 to +0.01237**, remaining close to zero throughout; excluding 2022 gives −0.000167. The annualized arithmetic selected-minus-unselected return spread ranges from −0.994% to +0.474%, with an unstable sign. This supports a failure to establish a stable advantage, rather than a robust positive edge.

## 4. Did energy dominate the results?

Daily dollar P&L is normalized by each portfolio's own beginning-of-month NAV, then differenced sector by sector. Sector contributions plus costs reconcile exactly to net active returns.

| Sector | Mean contribution to full-sample annualized arithmetic active return |
|---|---:|
| Consumer discretionary XLY | +0.868 percentage points |
| Energy XLE | +0.517 percentage points |
| Industrials XLI | +0.449 percentage points |
| Health care XLV | +0.288 percentage points |
| Technology XLK | +0.270 percentage points |
| Financials XLF | −0.127 percentage points |
| Consumer staples XLP | −0.628 percentage points |
| Utilities XLU | −0.660 percentage points |
| Materials XLB | −1.001 percentage points |
| Additional costs | −0.255 percentage points |

Energy is not the largest positive contributor over the full period, but its positive contribution is highly concentrated. Excluding 2022 reduces its mean contribution from +0.517 to **+0.0186 percentage points per year**. This is contribution sensitivity for the actual original strategy, rather than a counterfactual strategy rerun with energy removed.

Energy contributed +8.58 percentage points to annual active return in 2005 and +12.68 in 2022; total annual active returns were +9.64 and +14.71 percentage points, respectively. The 2013 advantage came mainly from health care, consumer discretionary and financials; energy was never selected that year. The common explanation is persistence of relative sector leadership, rather than an inherent suitability of energy for rotation.

## 5. Was defensive loss reduction a stable pattern?

A CAPM regression of monthly excess returns on SPY total return less RF, with HAC lag=6, gives historical betas of **0.861** for MOM and **0.944** for EW9. Using the same market excess-return regressor for active returns gives a beta difference of **−0.0825**, with HAC p≈0.058; the annualized intercept is about +0.303%, with p≈0.800. The historical results suggest lower market exposure but do not establish stable alpha.

Grouping realized execution intervals by SPY's return, mean net active return is −0.234% when SPY rises and +0.288% when SPY does not rise. Block-bootstrap intervals for both group means and their difference all cross zero. **This does not support a high-confidence claim to activate the strategy in bear markets and deactivate it in bull markets.** The classification itself also depends on future market returns.

In 2002, avoiding weaker sectors such as technology, utilities and industrials did reduce losses, but the portfolio still lost 12.58%. This is realized relative defense, rather than cash or hedge protection, and does not establish general protection in bear markets.

## 6. Which annual-case explanations are supported by the ledger?

| Year | Net active return | Directly verifiable holding mechanics |
|---|---:|---|
| 2002 | +5.77pp | No technology, utilities or industrials holdings avoided some large declines; consumer-sector holdings still detracted |
| 2005 | +9.64pp | Energy and utilities were selected throughout the year, contributing +8.58pp and +3.73pp to active return, respectively |
| 2006 | −11.56pp | All nine sectors rose, but holding periods were misaligned; technology, industrials and sectors later removed and re-entered detracted, while costs were only about −0.41pp |
| 2009 | −7.21pp | Early-year holdings remained consumer staples, health care and utilities; technology entered later. Utilities contributed −4.85pp, industrials −2.94pp and financials −2.82pp to active return |
| 2011 | −5.32pp | Materials, energy and consumer discretionary were still held in the third quarter. Materials contributed −8.91pp and energy −2.26pp; the late-year defensive switch could not offset these losses |
| 2013 | +7.48pp | Health care, consumer discretionary and financials were selected for extended periods, contributing +9.15pp, +8.08pp and +4.54pp to active return, respectively; other sectors offset part of the advantage |
| 2022 | +14.71pp | Energy was selected all year and contributed +12.68pp to active return. Avoiding consumer discretionary declines also helped, but early technology and financials holdings detracted −3.83pp and −4.07pp, respectively |
| 2023 | −3.51pp | Technology actually contributed +3.17pp to active return. Energy at −4.83pp and materials at −4.55pp were the main detractors; the result cannot be attributed solely to missing technology's advance |

Annual sector contributions use each portfolio's own beginning-of-year NAV and differ from monthly-average contributions. Both describe returns from actual portfolio weights and holding times; neither constitutes causal evidence or equals the ETF's full-year buy-and-hold return.

## 7. Strong and weak conclusions

**Strong conclusions:** this rule's relative return depends on the subsequent advantage of selected sectors over the remaining sectors; dispersion increases the magnitude of outcomes but does not determine their direction; costs erode an already weak advantage; 2022 strongly affects energy's positive contribution; and 2013 demonstrates that the profitable mechanism is not confined to energy. These conclusions have direct ledger or identity support.

**Not currently supported with high confidence:** persistent relative strength among past winners reliably predicts next month's results; bull/bear states provide a dependable real-time switch; energy or any fixed sector is always more suitable for the rule; or relatively stable past rankings guarantee positive active returns. Full-sample statistical intervals, leave-one-year-out checks and counterexamples limit these claims.

Turning an explanation of effectiveness into a decision requires conditions observable before trading, fixed thresholds and rules, independent-sample or rolling validation, and adjustment for multiple attempts. Strong relationships defined here using future returns must not be presented as predictive models.

## Reproducible files

- `analyze_mechanism.py`: reads inputs, reconciles execution-interval returns and monthly/annual P&L, and calculates block bootstrap and CAPM/HAC results.
- `execution_intervals.csv`: 311 complete execution intervals, including returns, rank IC, subsequent top-three overlap and errors in each identity.
- `interval_sector_gross_active.csv`: sector-level gross active contributions over equal-weighted execution intervals.
- `calendar_month_active_attribution.csv`: sector-level and cost contributions to net active returns for 312 calendar months.
- `calendar_year_active_attribution.csv`: sector-level and cost contributions to net active returns for 26 calendar years.
- `mechanism_statistics.json`: complete numerical results and actual selection paths. A bootstrap after deleting a year would join the remaining segments; this report therefore uses deleted-year results only as descriptive means. Formal full-period intervals have no deleted-year joins.
