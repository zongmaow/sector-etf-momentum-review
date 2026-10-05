# Concentrated random controls: methods and timing record

Method record dated 2026-10-05. The author records writing this protocol before the first random-control calculation. The protocol and first results were published together in commit `9114780`, so public Git history alone cannot independently establish their ordering. This is not public preregistration. The original ETF history and momentum results had already been observed; this is a retrospective diagnostic, not a new out-of-sample test.

Review update: the original seeds, path counts, costs, sample and trading rules were retained when compressed results were regenerated and maximum-drawdown percentiles and peak/trough dates were added. Those risk interpretations followed inspection of the first results; they are not prespecified hypotheses. The original `summary.json` is retained as `summary_9114780.json` in the results directory, preserving producer hashes and the result history.

## Purpose and primary method

Locate the industry identities chosen by MOM12−1 within a historical distribution of portfolios with the same concentration and membership-change schedule. Retain the original nine-sector universe, 2000–2025 sample, top-three equal target weights, month-end decisions and next-session-close execution.

The primary method is **fixed random industry-label remapping**: seed 20261005 and 4,096 independent mapping draws. Each path draws a uniform permutation of the nine sectors once and uses it throughout history. Each original top-three selection is mapped to the corresponding random three-sector selection. The mapping changes identities without using subsequent holding-period returns.

Each path preserves three holdings, monthly target weights, execution dates, adjacent membership overlap, entry/exit topology and a relabeled version of the original selection frequencies and co-holding structure. It does not retain the original economic sector exposures or make sectors with different risks exchangeable. Repeated mappings are allowed; report the number of unique mappings. Do not remove poor paths or choose the best random examples.

## One fixed sensitivity check

**Monthly overlap-matched random selection** uses seed 20261006 and 4,096 paths. Initially, select three of nine sectors uniformly. If the original momentum portfolio retains k names from its preceding selection, uniformly retain k names from the random path's previous three holdings and add 3−k from the six previously unheld sectors. The original overlap k is known at the current decision; no future returns enter it. This matches holding counts and additions/removals without preserving long-run sector preferences or co-holding structure.

Report both constructions separately. Do not switch the primary method based on results. Both are conditional on the original signal's historical trading schedule and do not represent all random trading rules.

## Execution, fees and comparisons

- Every path starts from cash on the same date, pays formation costs, allows daily weight drift and charges fees on actual traded dollars. No final liquidation is assumed.
- Use 0/5/10bp per side, with 5bp for the main interpretation. Disclose every cost level; do not select a rule by its preferred cost result.
- Retain the original fee equation: `C = c × Σ |w × (V−C) − x|`. Matching membership overlap does not exactly match dollar turnover or fees; recalculate and report them.
- Recompute MOM12−1, EW9 and SPY from the same input and check its price hash against the original snapshot. All paths use the same execution dates. Old holdings receive execution-day returns; new holdings begin earning returns after execution.
- Report CAGR, maximum drawdown, daily volatility, annualized arithmetic active return versus EW9, actual annualized turnover and fee burden.
- Report each metric's random-path P05/P50/P95, the original momentum historical percentile, and the proportions below momentum or above EW9/SPY. Percentiles are conditional historical diagnostics, not future profit probabilities or alpha p-values.
- Use the complete continuous 2000–2025 account as the primary result. Do not add period screening or derive an enablement rule from random-control results.

## Required correctness checks

1. Under the identity mapping, daily NAV, execution fees and turnover match the original engine at zero and positive costs.
2. Mappings are nine-sector bijections; every path holds three names at every decision and matches the original adjacent overlap. Seeds reproduce the selections.
3. Independently compare the original scalar fee solver with the batch daily calculation; reconcile NAV changes to price P&L less fees.
4. Changing future prices cannot alter earlier original decisions, random selections or NAV.

## Interpretation boundaries

The controls help distinguish selected industry identities from the historical performance of concentrated three-sector holdings. They do not separately establish economic causality, a strict exchangeable-industry null, significant predictive ability, persistent future alpha or reversal profitability. The inputs have been examined repeatedly; all findings retain their retrospective classification.
