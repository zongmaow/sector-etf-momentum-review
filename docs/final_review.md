# Sector ETF momentum: final phase-one review

Review date: 2026-10-05. Historical market data with simulated holdings, execution and costs.

**Phase one is closed: under the fixed nine-sector MOM12-1 rule and implementation assumptions, the evidence does not support adding a momentum sleeve to the existing SPY policy account.** This does not establish that all sector momentum fails or that passive investing necessarily beats active investing.

The original question concerns a proposed 20% allocation: is the net value from sector selection worth its active risk and implementation burden? The review compares simple same-universe allocation, the market and the full account, rather than asking only whether the strategy makes money.

## 1. What the historical results establish

The original continuous accounts are formed from cash on the same date in 2000 and run through the end of 2025. Month-end decisions trade at the following session's close; old positions earn execution-day returns. Actual purchases and sales pay 5 bps per side, including formation costs. Final holdings are not assumed liquidated.

| Portfolio | Net CAGR | Daily maximum drawdown | Annualized half-gross turnover, excluding formation |
|---|---:|---:|---:|
| Monthly nine-sector equal-weighting, EW9 | 8.68% | -53.29% | 0.15 |
| MOM12-1, equal weights in the top three | 8.32% | -46.20% | 2.70 |
| Buy-and-hold SPY | 8.02% | -55.19% | 0.00 |

Source: [original summary](../reports/snapshot/summary.csv). SPY also pays its initial purchase cost; it does not rebalance monthly afterward.

Momentum's full-period CAGR exceeded SPY but lagged EW9. The result cannot be described as momentum having lagged the market for all 25 years. Its maximum drawdown was shallower, so the return ranking is not a ranking of every risk objective. In the 2018-2025 continuous-path slice, SPY earned 14.20%, momentum 12.75% and EW9 11.69%; rankings vary by period.

EW9 includes a sector-weighting choice and monthly rebalancing, with active deviations from SPY's capitalization weights. These results compare the tested rules, not the entire active and passive fund populations, and do not approve replacing SPY with EW9.

## 2. Why the two active-return intervals differ

The primary statistic is twelve times the mean paired net monthly return difference, **not the difference between two CAGRs**: `12 * mean(r_MOM,m - r_EW9,m)`. Its full-period estimate is approximately -0.28 percentage points per year. CAGR compounds each complete wealth path; the measures are not interchangeable.

| Record | Sample and calculation | Six-month circular-block 95% interval, annualized percentage points |
|---|---|---:|
| [Original snapshot](../reports/snapshot/analysis.json) | 2000-2025; 2,000 draws; seed 2026 | [-2.76, +2.05] |
| [Follow-up accounting and conditions](../reports/effectiveness_snapshot/industry_rotation_effectiveness.md) | Same full-period active returns; 20,000 draws; seed 20261004 | [-2.62, +2.07] |

The follow-up changes draw count and seed and records separate settings. Original regressions use HAC3; later conditions and filters use HAC12 and disclose block-length sensitivity. Original values and generation-time hashes are retained. The earlier manager memo was edited, so the whole snapshot cannot be called unchanged. Historical source hashes should not be silently replaced with current ones; see [snapshot provenance](snapshot_provenance.md).

Both mean intervals cross zero: neither stable positive value nor inevitable future EW9 superiority is confirmed. More bootstrap draws reduce simulation error without adding independent historical events or estimating future profit probabilities. More draws also do not resolve repeated condition screening.

## 3. Return accounting is clear; an advance enablement rule is not

For complete execution intervals, let S be the mean holding-period return of the three selected sectors and O the mean return of the six omitted sectors. Post-execution gross active return satisfies:

```text
gross active return = 2/3 * (S - O)
net active return = gross active return
                    - relative effect of the two actual cost paths
```

The bridge error is below 9 * 10^-16 across 311 complete intervals. Dispersion magnifies gains and losses; selecting the subsequently stronger side determines the direction. However, S and O are future realized returns and cannot be used to screen trades in advance. This accounting identity does not identify economic causes such as earnings expectations, policy shocks or investor behavior.

Mean Spearman IC between past momentum ranks and subsequent industry returns is approximately 0.00472, with a six-month block 95% interval of [-0.0364, +0.0464]. Removing transaction costs does not establish a positive full-period mean gross advantage. Costs cannot be blamed for the entire result.

Four limited conditions observable at the decision examine recovery after a market decline, agreement between recent and medium-term rankings, high signal dispersion, and dispersion with stable membership. Thresholds are calibrated on 2000-2009; inference uses 2010-2025. None establishes reliable separation of subsequent net active returns. Recovery contains only five months in one state episode, insufficient for a general claim. Results, HAC settings and Holm families are in the [condition study](../reports/effectiveness_snapshot/industry_rotation_effectiveness.md).

Executable filters hold EW9 when momentum is disabled and incur every cross-mode trade. For accounts formed from cash together in 2010 and run through 2025, EW9 CAGR is 12.45%, original momentum 11.69%, and the three filters 11.60%, 11.21% and 11.06%. None improves original momentum CAGR.

These accounts are **newly formed in 2010**, not 2010-2025 slices of the account formed in 2000. Starting holdings, formation fees and state can differ; the comparisons must remain separate.

## 4. What concentrated controls add

Top-three momentum versus EW9 changes both sector selection and concentration. Two concentrated controls examine whether favorable three-sector holdings are being mistaken for ranking skill. The authors record writing the [protocol](../research/random_control_protocol.md) before computation. Methods and results were published in the same Git commit, without independent public preregistration; these are retrospective diagnostics.

- The primary control uses seed 20261005 for 4,096 random remappings of nine sector identities. Each path uses one mapping throughout history, preserving three holdings, adjacent membership overlap and transition structure.
- The sensitivity randomly retains and adds sectors each month according to original momentum's adjacent overlap, testing dependence on fixed identity remapping.

Both use the same historical input, execution timing and initial cash. Every path recomputes drift and actual trading costs at 0/5/10 bps. Identical membership overlap does not imply identical dollar trades, so actual turnover and cost distributions are disclosed.

The [control snapshot](../reports/random_control_snapshot/README.md) locates original momentum within historical return, risk and cost distributions. Sectors have different long-run risk exposures, and strict exchangeability has not been established. Percentiles are not alpha p-values, future win probabilities or tests on unseen history. Matching concentration and transitions does not match every style or economic exposure.

Results for 2000-2025 at 5 bps per side, with 4,096 paths per method:

| Concentrated control | Random CAGR 5th / 50th / 95th percentiles | Original momentum CAGR percentile | Fraction of random paths with CAGR above EW9 |
|---|---:|---:|---:|
| Fixed sector identity remapping | 5.95% / 8.15% / 10.46% | 54.81% | 35.50% |
| Monthly adjacent-overlap matching | 6.25% / 8.14% / 10.09% | 56.18% | 32.64% |

Original momentum CAGR of 8.32% is near the middle of both distributions, with no pronounced historical return advantage from selected identities. At 0 bps, its percentiles are 54.76% / 56.10%; at 10 bps, 54.83% / 56.18%. Costs do not turn it into a clear return-tail winner. This is not proof of equality or universal ineffectiveness.

Median actual annualized half-gross turnover is approximately 2.7090 / 2.7087, versus original momentum's 2.6976. Median annualized fee burden including formation is approximately 0.2728% / 0.2728%, versus 0.2717%. Similar transitions yield similar friction, not exactly equal dollar turnover. The 4,096 identity draws contain 4,076 distinct mappings; all draws are retained.

Momentum's maximum drawdown of -46.20% is shallower than random medians of -54.45% / -54.20%. Its drawdown is shallower than **94.87% / 95.70%** of random paths; conversely, only **5.13% / 4.30%** of random paths are shallower than momentum.

Original momentum's full-period maximum drawdown peaks on **2008-05-20** and reaches its trough on **2009-03-09**, during the financial crisis. These dates locate its largest decline. A complete event-by-event comparison has not been performed, so neither exclusive dependence on 2008 nor robustness across risk events is established. Middle-ranked returns need not mean middle-ranked risk. This observation is not guaranteed future protection or confirmed net incremental value. The 4,096 paths share one market history; they are not 4,096 independent historical samples. See the [result manifest](../reports/random_control_snapshot/summary.json).

## 5. External data broaden the evidence

[French ten-industry replication](../reports/effectiveness_snapshot/external/external_validation.md) uses value-weighted research portfolios. For 1960-2025, momentum CAGR is 12.91% versus 11.22% for equal-weighting. Annualized arithmetic active return is approximately +1.76 percentage points, with a six-month block interval of approximately [+0.13, +3.43]. After Holm correction across three basic mean tests, the full-period p-value is approximately 0.076; separate early and modern periods provide weaker evidence.

This supports the possibility of industry momentum in some definitions and histories, rather than establishing the current nine-ETF rule. French SIC industry classifications and underlying stock weights differ from SPDR GICS products. Theoretical monthly formation cannot reproduce next-session close execution. The 5 bps assumption applies to outer baskets, not historical implementation costs of underlying stocks.

Early recovery-state risk indications do not repeat reliably in modern ETFs. Universe sensitivity forms **new accounts from cash together in 2020 and runs through 2025**, rather than slicing the original account:

| Universe/reference | Momentum net CAGR | Equal-weight net CAGR |
|---|---:|---:|
| Nine sectors | 14.55% | 12.38% |
| Eleven sectors | 16.48% | 11.97% |
| Buy-and-hold SPY | 14.80% | -- |

Both momentum universes beat their corresponding equal-weight benchmarks in this period. XLRE/XLC change selection and equal-weight exposure together, so the difference is not solely the contribution of added ETFs. Six years and an expansion made after viewing history do not establish an enablement rule. Holdings changes and adverse years are retained in the [universe exploration](../reports/exploratory_snapshot/regime_comparison.md); the primary sample remains separate.

## 6. Unconfirmed momentum does not establish reversal

Buying the previous bottom three is not the negative return of buying the previous top three. The middle three can become future winners, leaving both momentum and reversed ranking behind EW9. Their costs and risks also differ. An IC interval crossing zero does not establish negative prediction merely because positive prediction is unconfirmed.

Reversing MOM12-1 ranks is a separate hypothesis, with a horizon different from short-term or long-term reversal. These labels cannot be interchanged, and current momentum results cannot substitute for independent validation. Phase one does not select a reversal rule after momentum's failure to establish value.

## 7. Decision and reconsideration conditions

The simulated manager retains the existing SPY policy allocation without a new momentum sleeve. The 20% momentum account's tracking error is approximately 1.60%, below the assumed 2% budget. Meeting that budget addresses permissible risk, not whether it is worth taking. This is a hypothetical mandate decision, not a live approval or a recommendation to add EW9.

Reconsideration would require new evidence:

1. Freeze the rules and retain monthly information, ranks, intended execution dates, cost estimates and observations. Distinguish genuinely new data after freezing from history already inspected.
2. Test the same limited questions in new markets or independent data, retaining failures and classification/trading differences. More markets do not necessarily supply independent macroeconomic events.
3. Before viewing new results, specify acceptable compensation, costs and account constraints and record multiple-screening scope. Economic standards follow the mandate and implementation burden, rather than a new cutoff chosen to pass this sample.
4. Economic persistence would require point-in-time earnings expectations, valuations, policy or supply/demand information and a new protocol. Price returns alone cannot certify those causes.

## 8. Deliverables and closed scope

| Deliverable | Auditable content |
|---|---|
| [Original backtest](../reports/snapshot) | Decision dates, execution, drift, self-financing fees, continuous performance and account risk |
| [Period/universe exploration](../reports/exploratory_snapshot) | All years and windows, added-sector sensitivity and adverse examples |
| [Accounting and conditions](../reports/effectiveness_snapshot) | P&L identity, limited conditions, actual filters, external replication and independent audit |
| [Concentrated controls](../reports/random_control_snapshot) | Recorded methods, actual costs and position in historical diagnostic distributions |
| [Provenance and reproduction](snapshot_provenance.md) | Historical versions, memo edits and hash scope; [portable-script check](../reports/reproduction_check/README.md) |
| [Manager memo](final_manager_memo.md) | Allocation decision, evidence boundaries and reconsideration conditions |

Extension protocols are authors' records of intended methods, without independent public preregistration. Portable ETF, accounting and French scripts were rerun: 25 common CSV files and three core JSON numerical summaries agree with published results. Scope, tolerance and code identities are in the [reproduction record](../reports/reproduction_check/README.md). Reproduction verifies calculation, not independent investment evidence.

Financial assumptions, input versions, validation and limits are retained. The contribution is an auditable investment review. Phase one is closed; economic causes or equal-weight performance sources would be separate research questions, not continuous changes to the same historical rule relabeled validation.
