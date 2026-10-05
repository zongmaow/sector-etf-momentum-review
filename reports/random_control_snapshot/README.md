# Three-sector random controls: concentration and industry selection

This is a diagnostic on previously observed history. Path percentiles are neither future profit probabilities nor alpha significance tests.

Fixed sample: 2000–2025; 4096 paths per method; 0/5/10bp per side. The main tables below use 5bp.

| Method | Random CAGR P05 / P50 / P95 | Momentum CAGR historical percentile | Momentum shallower-drawdown percentile | Share beating EW9 |
|---|---|---:|---:|---:|
| Fixed industry-label remapping (primary) | 5.95% / 8.15% / 10.46% | 54.8% | 94.9% | 35.5% |
| Monthly overlap-matched sampling (sensitivity) | 6.25% / 8.14% / 10.09% | 56.2% | 95.7% | 32.6% |

Reference net CAGRs recomputed on the same dates: MOM12−1 8.32%, EW9 8.68%, SPY 8.02%.

## Methods and costs

The primary method draws one nine-sector bijection per path and keeps it fixed throughout the sample. It preserves three holdings, entry/exit topology, adjacent membership overlap and a relabeled version of the original selection frequencies. The sensitivity method randomly retains and adds the same numbers of sectors each month, changing long-run sector preferences and co-holding structure. Neither uses subsequent returns to choose its labels.

Matching membership counts does not match dollar turnover. Each path uses its own weight drift, self-financing trades and cash fees. Annualized fee burden is the sum of fee/pretrade_NAV divided by elapsed years, including formation; it is not the exact reduction in CAGR.

| Portfolio/method | Annualized half-gross turnover P05 / P50 / P95 | Annualized fee burden P05 / P50 / P95 | Maximum drawdown P05 / P50 / P95 |
|---|---|---|---|
| Original momentum | 2.70 | 0.27% | -46.20% |
| Fixed industry-label remapping (primary) | 2.70 / 2.71 / 2.72 | 0.27% / 0.27% / 0.27% | -62.51% / -54.45% / -46.16% |
| Monthly overlap-matched sampling (sensitivity) | 2.70 / 2.71 / 2.72 | 0.27% / 0.27% / 0.27% | -62.99% / -54.20% / -46.39% |

## Assess returns and drawdowns separately

In primary / sensitivity order, momentum CAGR percentiles are 54.8% / 56.2%; shallower-drawdown percentiles are 94.9% / 95.7%. Maximum drawdown was -46.20%, from the 2008-05-20 peak to the 2009-03-09 trough. A higher drawdown percentile means a shallower historical loss, not a probability of future protection.
The return result does not erase this historical risk advantage. However, full-period maximum drawdown is determined by one deepest peak-to-trough episode, here in the 2008–2009 financial crisis. Persistence across different crises and later periods has not been established, so this observation does not establish dependable protection or an enablement condition.

## Interpretation

The percentile describes the historical position of the chosen industry identities, conditional on this market history, three-sector concentration and the original entry/exit schedule. It does not separately identify the economic cause of the price signal: sector correlations, exposures and co-holding structures still differ.

A rule near the middle of these concentrated controls does not provide strong historical evidence of useful ranking. Even a high percentile would not establish future alpha: sectors are not exchangeable, the rule and history were already observed, and all paths share one market history.

The share of random portfolios beating EW9 is not the general success rate of active investing. Compound returns also depend on volatility, sector preferences, rebalancing and costs. Reversal is not tested here and cannot be inferred by negating momentum returns.

## Files and reproduction

- [Methods and timing record](../../research/random_control_protocol.md). The protocol and first results were published together; this remains a retrospective diagnostic.
- [Complete results and settings](summary.json), [distribution table](distribution_summary.csv), [ledger validation](ledger_validation.csv).
- `*_paths.csv.gz` disclose every random path at each cost; `identity_mappings.csv.gz` retains the fixed mappings.
- `*_sample_trades_5bps.csv.gz` retain the first two prespecified random trading paths; `example_daily_nav_5bps.csv.gz` retains the first path from each method. Examples were not selected for performance.
- The [storage manifest](storage_manifest.json) records decompressed CSV hashes. `pandas.read_csv` reads `.csv.gz` directly; gzip can also decompress it. All 0/5/10bp results remain available.

Run from the repository root:

```sh
python -m sector_momentum random-control --prices data/raw/total_return.csv --out reports/random_local
```

Saved price SHA-256: `e03d2506e51d1a5bdbd8dcb37ffd6e80364c88cbb88449ca0866b74b3dcae11c`. A later vendor download may revise history and needs its own hash. Complete 0/10bp results are retained in CSV and JSON.
