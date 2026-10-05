# Sector rotation effectiveness: independent method review

Date: 2026-10-04. The review covers the existing long-only nine-sector ETF portfolio: MOM12−1, equal weights in the top three sectors, month-end signals, next-trading-close execution and 5 bp per side. The existing research definitions, 312 months of historical results, earlier commonality diagnostics and statistical code were reviewed. This document does not change the primary strategy.

## 1. Confidence can improve without guaranteeing a profitable switch

Answer three distinct questions:

1. **P&L mechanism:** which actual holdings and relative returns made historical months succeed or fail? The ledger can provide relatively high-confidence answers.
2. **Conditional historical relationship:** is a feature known before trading stably associated with subsequent net active return? This requires robust inference, multiple periods and suitable controls.
3. **Ex-ante decision:** does using that feature to choose when to increase industry concentration add net return in subsequent data? This requires new data following genuinely frozen rules, or clearly bounded external validation. All existing 2000–2025 history has been examined repeatedly and cannot be relabeled genuinely unseen.

“The strategy performs better when previous industry leaders continue to lead during the holding period” has strong accounting and mathematical support. It nevertheless includes future holding-period returns and cannot directly become a condition identifiable when trading. The 312 months are not 312 independent market environments; 277 overlapping three-year windows are not 277 independent experiments.

## 2. What the literature supports, and its boundaries

| Original research | What it supports | What it does not directly support |
|---|---|---|
| Moskowitz & Grinblatt (1999), *Do Industries Explain Momentum?* | An academic basis for persistence in industry relative returns; historical long-short industry momentum is not attributable solely to stock selection | A guarantee that nine broad sector ETFs, equal-weight top three, MOM12−1 and 2000–2025 data will outperform EW9 after actual execution costs. Research industry portfolios and modern sector ETFs are different universes |
| Daniel & Moskowitz (2016), *Momentum Crashes* | A mechanism for momentum losses when market declines, high volatility and rebounds coincide, motivating a predefined stress hypothesis | In winner-minus-loser stock portfolios, the short leg can lose sharply when previous losers rebound. This project has no short leg; benchmark underperformance or declines in previous winners are more plausible manifestations. The paper's crash frequency and prediction model cannot simply be reused |
| Cooper, Gutierrez & Hameed (2004), *Market States and Momentum* | A literature basis for market-state conditioning, provided state definitions and holding rules are explicit | Treating any arbitrary 12-month return threshold as already validated, or using realized holding-period bull/bear states as trading inputs |
| Pan, Liano & Huang (2004), *Industry momentum strategies and autocorrelations in stock returns* | A decomposition distinguishing own-industry autocorrelation, cross-industry lag relationships and differences in average returns | Equivalence between its weekly, shorter-horizon portfolios and this project. Other research reaches different industry-momentum attribution results; positive own-industry autocorrelation is not the sole established causal explanation |
| White (2000), *A Reality Check for Data Snooping*; Harvey, Liu & Zhu (2016), *… and the Cross-Section of Expected Returns* | Repeated model and condition selection on one dataset inflates ordinary significance; attempted hypotheses and test families must be disclosed | Treating a universal t > 3 threshold as a high-confidence certificate, or using corrections on a few final tests to erase earlier unrecorded exploration |

References link to papers, authors or publishers:

- [Moskowitz & Grinblatt, original publication](https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146)
- [Daniel & Moskowitz, NBER working paper](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf)
- [Cooper et al., original publication](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2004.00665.x)
- [Pan et al., original publication](https://www.sciencedirect.com/science/article/pii/S0927539803000495)
- [Research on changes over time in industry-momentum attribution, original publication](https://www.sciencedirect.com/science/article/pii/S0148619506000531)
- [White, original publication](https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152)
- [Harvey et al., NBER working-paper page](https://www.nber.org/papers/w20592)

## 3. A limited set of hypotheses to freeze

Stop searching for profitable years or sector subsets. Specify each hypothesis's expected direction, one feature definition, one threshold rule and one primary outcome first. At most five price-reproducible hypotheses are suggested here; they are not five established conditions:

1. **Stress state:** at the previous month-end, SPY's past 12-month return is negative and realized volatility over the preceding 63 trading days exceeds a long-run median formed solely from previous months. Hypothesis: subsequent active returns are worse. If warm-up is insufficient, expand it or move the valid start date; never fill the gap with the full-sample median.
2. **Trend agreement:** the rank correlation between recent three-month industry returns and the original intermediate rankings is at least zero. Hypothesis: subsequent active returns are better. A direction reversal was already observed across periods in the previous analysis; that failure evidence must remain visible.
3. **Industry dispersion:** intermediate-signal cross-sectional standard deviation exceeds a median estimated solely from prior months. Hypothesis: dispersion offers opportunities but need not improve returns on its own. Any interaction with trend agreement must be declared as an additional test in advance, not added after a failed main effect.
4. **Stable leadership:** stability of the preceding three monthly top-three lists. Use only lists available at the decision, never whether leaders remain ahead next month. Recent ranking stability does not itself prove persistence in relative returns.
5. **Recent realized strategy effectiveness:** whether the preceding 12-month mean net active return over EW9 is positive. This tests persistence of effectiveness rather than assuming it. The feature has 12-month overlap and requires longer-block robustness checks.

Median thresholds must use only information available at each decision, for example an expanding median after the first 60 months, with a fixed minimum history. Original data begin in late 1998, so a 120-month historical median cannot be estimated in early 2000. Future observations cannot supply the warm-up.

## 4. Alignment of timing and returns

- The primary outcome may remain the next calendar month's actual-NAV net active return, with the first execution day's return accruing to old holdings. If testing the current top-three selection, an auxiliary outcome should run from its execution close to the following execution close, with explicit fee allocation.
- Month-end observables must end at `signal_date`. Lagged windows, historical thresholds and historical beta estimates must never extend beyond that date.
- A “rebound environment” defined by subsequent gains is an ex-post mechanism. A tradable version can use only a rebound already observed before the decision or a prediction specified in advance.
- Rankings use adjusted prices with corporate actions represented in the current supplier snapshot. Hashes make this reproducible, but do not turn it into the daily vintage actually received at the time. Current-snapshot research must be distinguished from point-in-time data.

## 5. Minimum requirements for statistical inference

### Primary measure

The main quantity is the difference in subsequent monthly mean net active return between the condition group and remaining months:

`E[MOM_net − EW_net | Z=1] − E[MOM_net − EW_net | Z=0]`.

A group's positive absolute return does not establish effective sector selection; a slightly positive active mean does not establish that the feature discriminates between groups. Report both means, their difference and intervals, month counts, years represented, worst active return and trading frequency.

### Dependence and multiple testing

- Jointly resample whole rows containing features, state labels and outcomes in consecutive monthly blocks. Never resample labels, strategy returns and benchmark returns separately.
- Six-month blocks can be primary, with fixed three- and twelve-month checks. Twelve-month-overlap features require at least a twelve-month-block result; longer-horizon features need an explanation of longer dependence.
- Use HAC uncertainty for conditional regression contrasts. Small conditional samples should not receive apparently precise probabilities from normal approximations.
- Publish every frozen test. Holm is appropriate for a finite, explicit family, but does not repair earlier exploration of unknown size. A multi-strategy bootstrap maximum statistic must compare all candidates on each jointly resampled history, with explicit null hypotheses, centering and test directions.
- A percentile bootstrap interval for a mean is not a zero-mean test p-value. A bootstrap p-value requires explicit centering under the null, not simply counting negative uncentered draws.
- Count draws with empty or nearly empty state groups and handle them under a predefined rule. Do not silently discard them and report only favorable results.

### Control for market exposure

Active return over EW9 may still reflect different betas. At minimum, examine this descriptive model:

`MOM_net − EW_net = α + β · SPY_excess + δ · Z + γ · Z · SPY_excess + ε`.

`δ` is the model's conditional-intercept difference; `γ` allows market exposure to change by state. Use HAC throughout. Separate conditional CAPM regressions can also be reported, with attention to sample size and extreme-event leverage. If the raw return difference survives but the conditional-intercept difference disappears, describe exposure selection rather than market-independent sector-selection alpha. CAPM cannot remove every risk or establish causality.

## 6. Historical validation and robustness

Retain the existing 2000–2010, 2011–2017 and 2018–2025 periods, report all three, and do not change boundaries in response to results. Every split is a check on known history. Expanding/rolling prediction can also estimate thresholds or models each year using earlier months and concatenate subsequent outcomes. This tests whether the procedure could have run at the time; rules designed after viewing history are still not preregistered tests on unseen data.

Suggested order for limited sensitivity checks:

1. Costs of 0/5/10 bp, comparing the original strategy with EW. Do not alter the signal when changing fees.
2. The three fixed periods and leave-one-year-out checks, looking for dependence on 2022 or a single crisis. Leaving out a year is not new out-of-sample evidence.
3. Nine- versus eleven-sector universes on the same 2020–2025 dates. Six years of universe expansion cannot independently establish high confidence.
4. Concentration controls: all 84 fixed three-sector combinations, or a predefined distribution of random top-three strategies. Independently redrawing sectors every month changes costs and holding stability; disclose this difference rather than presenting the random strategy as a perfect control.
5. If feasible, replicate the same long-horizon momentum logic in French 12/49 industry portfolios. This broadens time and cross-sectional coverage, but underlying industry portfolios and monthly returns are not an investable daily ETF-execution backtest. Successful replication supports external generality without becoming the same experiment as the ETF study.

[French's twelve-industry construction notes](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_12_ind_port.html) use SIC industries. Historical security groupings do not map exactly to GICS sectors in the ETFs. Preserve this boundary when citing external results.

## 7. Suggested language about confidence

| Result | Appropriate statement |
|---|---|
| Holdings P&L reconciles to NAV; active returns improve when selected leaders subsequently outperform omitted industries | High-confidence explanation of historical P&L, still containing ex-post returns |
| A conditional-return interval crosses zero or direction reverses across periods | No stable ex-ante discriminating information identified; not proof that every condition is ineffective |
| A multiplicity-adjusted result is significant but depends on one year/industry or disappears after controlling for market beta | A local historical relationship or exposure difference, not a robust sector-selection advantage |
| Consistent direction across periods, positive corrected intervals, cost robustness, persistence after exposure controls and external replication | Stronger historical conditional evidence, still requiring new data after freezing rules to confirm prospective value |
| Repeated new observations after genuinely frozen rules, with acceptable risk and costs | Gradually greater confidence in ex-ante deployment; intervals are not probabilities of inevitable future profits |

A complete and useful conclusion may be that sector rotation's gains and failures can be explained clearly, while available data still cannot reliably identify when to enable it. Do not narrow conditions repeatedly simply to satisfy a demand for high confidence.

## 8. Item-by-item review of this round's frozen protocol

Reviewed `outputs/sector-etf-effectiveness-study/research_protocol.md`. The five suggestions above preceded freezing; the coordinating agent's frozen H1–H4 and F1–F3 take precedence. No hypotheses or tuning are added. The four hypotheses, fixed calibration periods, 2010–2025 inference sample, actual cost engine and French ten-industry replication are operationally feasible.

| Item | Review finding |
|---|---|
| H1: negative past 24-month market return with a recent three-month rebound | The rebound has already occurred before trading, so timing is valid. The condition omits Daniel–Moskowitz's high-volatility state and is not a full replication of that model. H1 may contain few events; scarcity is a result limitation, not a reason to adjust thresholds to manufacture more events |
| H2: recent three-month agreement with intermediate rankings | All inputs are observable then. Similar earlier period checks already showed direction reversals, so its explored status must remain explicit; it is not a newly discovered preregistered hypothesis |
| H3: signal standard deviation above the 2000–2009 calibration median | No future information when used from 2010 onward. Explicitly associate the 120 calibration values with January 2000–December 2009 holding months and their previous-month decisions. Applying the resulting threshold to the calibration period must not be called tradable |
| H4: H3 with at least two sectors shared by three successive top-three sets | No look-ahead. A three-way intersection differs from mean pairwise overlap; implementation must use the stated intersection. Keep the denominator at three and do not change the threshold when expanding to ten industries |
| HAC + Holm for four hypotheses | Appropriate for a finite frozen condition family. Significant two-sided results in the opposite direction reject the original hypothesis rather than confirm it. Holm does not undo repeated full-history inspection |
| Joint circular-block bootstrap | Resampling labels and outcomes in the same blocks is correct. Six-/twelve-month checks are useful but cannot remove nonstationarity or few-event limitations. Explicitly handle and count empty-state draws |
| Three actual trading filters | Simultaneous 2010 formation from cash with original-momentum/equal-weight controls avoids mixing starting paths. Charge every actual buy and sell across modes rather than replacing monthly net returns |
| French ten-industry replication | Differences in monthly formation, implementation costs, classification and market proxy are disclosed, making this a valid transfer check. It is historical validation in other periods/industry portfolios, not a hidden sample for the nine ETFs |

Four interpretation points need to be tightened without searching for new parameters:

1. **A significant contrast does not establish positive value in the favorable group.** If group active means are −3% and −4%, even a significant difference does not establish effectiveness in that condition. Separately report the favorable-group net active mean and interval, the contrast and interval, and filter increments over the benchmark and original strategy. If only the contrast is significant, describe discrimination or relatively less underperformance.
2. **Interval-direction consistency needs an explicit definition.** For a strong conclusion, both block-length contrast intervals should exclude zero in the hypothesized direction. Two same-sign point estimates are insufficient. The 24-month/five-run minimum is a reporting threshold, not a guarantee of adequate power.
3. **Market exposure can change by state.** A fixed-beta `active ~ 1 + Z + market` is a basic check, but also report the fixed interaction specification `active ~ 1 + Z + market + Z*market`. Otherwise state-dependent beta may contaminate the conditional intercept. Market excess return is the CAPM convention; if total return is used, describe a market-control regression rather than a complete CAPM.
4. **Filters are multiple candidates too.** Holm correction for four conditions does not automatically cover significance of the best of three filters. If intervals are descriptive retrospective comparisons, disclose the lack of filter-selection adjustment and do not select a winner. A high-confidence filter-improvement claim needs its own defined and corrected filter family.

Official French ten-industry construction notes: [Detail for 10 Industry Portfolios](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_ind_port.html). At each June-end, portfolios are grouped by four-digit SIC using available Compustat/CRSP classifications; industry returns run from July to the following June. This differs from GICS sector ETFs and bounds the external replication.
