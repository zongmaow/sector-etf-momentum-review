# Initial historical research snapshot

The tables and figures use Yahoo supplier-adjusted ETF levels for 2000–2025, with a 1998-12-31 warm-up and French monthly risk-free returns. These are historical market inputs with simulated holdings, next-close fills and costs. They are not a live investment record.

- `manager_memo.md`: investment interpretation, retained even though the primary rule fails the net increment test.
- `summary.csv`: fixed strategy, cost and time-period results; 0 bps is the gross comparison.
- `episodes.csv`: diagnostics, including exact period dollar-P&L return decomposition.
- `monthly_returns.csv`: derived monthly portfolio returns for checking comparisons; not raw ETF prices.
- `analysis.json`: parameters, input/config hashes, coverage, versions, active statistics, block intervals and SPY-proxy CAPM/HAC results.
- `manifest.json`, `rf_manifest.json`: input provenance and snapshot identities.
- `data_quality.json`: the initial XLU supplier split spot-check and dollar P&L reconciliation.
- `source_hashes.json`: source file identities for this snapshot.

Local reproduction also writes daily NAV and detailed audit files, which are intentionally excluded from this Git snapshot. Different vendor revisions can change results. Never use synthetic demo output as historical evidence.
