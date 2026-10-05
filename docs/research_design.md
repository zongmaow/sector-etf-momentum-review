# Sector ETF momentum: research design

Initial design record: 2026-10-04. Phase-one closure: 2026-10-05.

This document records the question, rules, accounting and validation. Numerical findings are consolidated in the [final review](final_review.md), the action in the [manager memo](final_manager_memo.md), and the short introduction in the [framework](framework.md). Historical prices are used for simulated accounts, and the researcher already knows the historical events.

## 1. Question and research object

A manager with an existing SPY policy allocation considers a 20% sector rotation sleeve. Does momentum selection within the same universe add net value after fees, and is that value worth concentration, active risk and implementation burden?

The fixed product universe is XLK, XLF, XLE, XLY, XLP, XLV, XLI, XLB and XLU. SPY is the market reference and account core. These tickers represent actual product histories, not unchanging underlying sector definitions or an unbiased history of today's full eleven-sector universe. XLRE and XLC are not backfilled before inception; expansion is reported separately.

Absolute profits, benchmark outperformance, statistical evidence and mandate suitability are separate questions. Simple sector equal-weighting does not stand for all passive investing.

## 2. Signals, positions and comparisons

Let `P[i,m]` be ETF i's adjusted price level at the common month-end trading session.

| Rule | Signal at month-end m | Question |
|---|---|---|
| MOM12-1, primary | `P[i,m-1] / P[i,m-12] - 1` | Does medium-term relative strength persist? |
| MOM12-0 | `P[i,m] / P[i,m-12] - 1` | What changes when the latest month is included? |
| MOM1 | `P[i,m] / P[i,m-1] - 1` | How does short-term ranking differ? |
| Buffer12-1 | Primary signal; retain incumbents ranked <=4 | Do membership replacements justify their costs? |

The primary signal contains eleven monthly return intervals and skips the latest month. Monthly trading and the eleven-month observation horizon are separate dimensions. The skip-month convention draws on [French's stock momentum definition](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_mom_factor.html); stock long-short evidence is not evidence for this long-only ETF strategy.

All momentum rules hold three ETFs with target weights of 1/3. Ties are resolved alphabetically by ticker. Portfolios are long-only, unlevered and continuously invested: even when all nine decline, the rule selects the relative top three. Crisis protection is not assumed. The buffer initially selects the top three, then retains incumbents ranked within the top four and fills vacancies by rank.

| Comparison | Purpose |
|---|---|
| Monthly nine-sector equal-weighting, EW9 | Simple allocation in the same universe |
| Buy-and-hold SPY | Market reference |
| Random three-sector concentrated controls | Identity-selection diagnostics with similar transitions |
| 80% SPY + 20% strategy account | Net value and account active risk |
| 90% SPY + 10% momentum account | Fixed allocation sensitivity |

Momentum versus EW9 changes both selection and concentration; the difference is not pure momentum alpha. Blended accounts are simulated from actual holdings, not weighted averages of standalone CAGRs.

## 3. Data and execution timing

- Daily warm-up begins on 1998-12-31; the principal trading sample is 2000-2025. The first decision is at December 1999 month-end, with cash formation at the close of the first trading session in 2000.
- Vendor adjusted prices and corporate-action fields are preserved. Inputs, manifests and script identities have hashes. Adjusted prices proxy total returns; dividends are not added again.
- XNYS coverage checks reject missing data without interpolation or forward-filling. Additional data or vendor revisions can change identities and results.
- Decisions follow month-end; execution is at the next session's close. Old positions earn execution-day returns; new positions earn returns after trading. Signal endpoints, execution dates and old/new membership are logged.
- Formation costs are included. The short initial cash period earns no interest. Final holdings are marked to market without assumed liquidation. Fractional shares are allowed; the $1 million calculation unit can be scaled proportionally without establishing $100 million capacity.

The following close is a daily execution proxy. Real quotes, auction fill probability and market impact have not been validated. ETF operating expenses are embedded in historical fund prices; the additional basis points model trading costs.

## 4. Drift, self-financing and P&L

Positions drift with returns before comparison with targets. For pretrade values `x_i`, total wealth `V`, target weights `w_i` and per-side fee `c`, solve:

```text
C = c * sum_i |w_i * (V - C) - x_i|
posttrade_holding_i = w_i * (V - C)
sum_i posttrade_holding_i + C = V
```

The primary assumption is 5 bps per side, with fixed 0/10 bps sensitivities. Unchanged membership can still generate trades after drift. Turnover is measured as half-gross traded value; formation and subsequent trading are recorded separately, with actual cumulative fees.

Daily dollar P&L plus negative fees must reconcile to the NAV change. Event contributions divide window P&L by starting NAV and reconcile to the window's total return. This explains holdings gains and losses; it is neither factor attribution nor a sum of standalone ETF CAGRs.

## 5. Evaluation and historical partitions

Positions remain continuous across development (2000-2010), confirmation (2011-2017) and final historical (2018-2025) summaries. Event and rolling windows are slices without cost resets. These are known historical periods, not contemporaneous live out-of-sample evidence.

Report CAGR, volatility, maximum drawdown, worst rolling twelve-month outcomes, costs, turnover, sector contributions and active returns versus EW9/SPY. With monthly active return `a_t = r_strategy,t - r_benchmark,t`:

```text
annualized arithmetic active return = 12 * mean(a_t)
tracking error TE                  = sqrt(12) * std(a_t)
information ratio IR               = sqrt(12) * mean(a_t) / std(a_t)
```

Mean active return differs from the CAGR gap, and its interval is not a CAGR interval. Worst twelve-month active performance compounds each portfolio separately over the same window before taking the difference; monthly active returns are not compounded directly.

SPY-proxy CAPM uses zero-trading-cost SPY market returns and subtracts French monthly RF once from each side. The original implementation uses HAC3 and asymptotic normal p-values. Missing RF is explicitly labeled a zero-RF assumption. A CAPM intercept is not causal alpha; an RF input does not establish complete multifactor attribution.

The original primary comparison uses a six-month circular-block bootstrap with 2,000 draws and seed 2026. The follow-up uses 20,000 draws, seed 20261004, six/twelve-month block sensitivity and HAC12. Settings and outputs remain separate. More draws reduce simulation error without adding independent historical evidence. Numerical differences are explained in the [final review](final_review.md).

The 2% account tracking-error budget is an illustrative threshold without an actual mandate. Passing a risk budget, a statistical result or one IR cannot substitute for net value and implementation judgment.

## 6. Follow-up diagnostics and boundaries

| Extension | Method | Output |
|---|---|---|
| Period and product universe | All calendar years, non-overlapping five-year blocks and overlapping three-year windows; common cash formation in 2020 for nine/eleven sectors | [Complete exploration grid](../reports/exploratory_snapshot) |
| Return accounting | 311 complete execution intervals; selected/omitted returns and actual fee bridge | [Mechanism study](../reports/effectiveness_snapshot/mechanism) |
| Environment conditions | 2000-2009 calibration, 2010-2025 inference; four limited conditions, HAC and Holm checks | [Protocol](../reports/effectiveness_snapshot/research_protocol.md) |
| Executable filters | Hold EW9 when momentum is disabled; recompute cross-mode trading and costs | [Effectiveness study](../reports/effectiveness_snapshot/industry_rotation_effectiveness.md) |
| French replication | Ten value-weighted industries, monthly returns, SIC classification, 1960-2025 | [External replication](../reports/effectiveness_snapshot/external) |
| Concentrated random controls | Fixed identity remapping and monthly overlap matching; 4,096 paths each, 0/5/10 bps | [Protocol](../research/random_control_protocol.md) and [results](../reports/random_control_snapshot) |

The authors record defining the extensions before computation, but methods and results were published in the same Git commit, **without independent public preregistration**. These are retrospective diagnostics. Historical percentiles are not alpha p-values or future win probabilities. Rules or universes changed after viewing history cannot be relabeled independent validation.

Fixed identity remapping preserves membership transitions throughout the history. The monthly sensitivity retains and adds sectors according to the original strategy's adjacent overlap. Each path recomputes drift, trading and fees: equal membership overlap does not imply equal dollar turnover. Industry risk exposures differ, and strict exchangeability has not been established.

French portfolios differ in classification, underlying value weights and theoretical monthly execution. They do not reproduce the ETF next-close delay or earlier underlying-stock trading costs. Filter accounts newly formed from cash in 2010 are kept separate from slices of the original continuous account.

## 7. Validation and completion

| Check | Relationship to validate |
|---|---|
| Future-data perturbation | Past signals and positions do not change |
| Manual signal examples | Correct 12-1, 12-0 and 1m endpoints |
| Execution-day price jump | Old positions earn execution-day returns |
| Drift and fees | Actual trades, self-financing and cash reconcile |
| Zero and higher costs | Zero-fee gross/net paths agree; higher costs cannot create wealth for a fixed strategy |
| Buffer and ties | Retention, filling and tied rankings are reproducible |
| Data and actions | Missing data are rejected; splits do not create mechanical total returns |
| Independent calculation | Small examples, ledgers and extended outputs can be checked |

Implementation and commands are in the [README](../README.md). Historical test counts, source identities and edits to the original memo are documented in [snapshot provenance](snapshot_provenance.md); portable-script verification is in the [reproduction check](../reports/reproduction_check/README.md).

Completion requires traceable real data, consistent rules and comparisons, verified timing and costs, full disclosure of adverse findings and historical exploration, and a decision supported by evidence. Phase-one closure does not require a winning strategy. Economic explanation would need point-in-time information and a new protocol; only new decision records collected after freezing constitute prospective observations.
