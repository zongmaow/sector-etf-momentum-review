# Sector ETF Momentum Review

A hypothetical US equity portfolio manager is considering a sector rotation sleeve. This project asks whether a fixed momentum rule adds enough **net value over sector equal-weighting** to justify its trading and active risk.

The first historical run does **not** support adopting the primary rule: over 2000–2025, MOM12−1 earned an 8.32% net CAGR versus 8.68% for nine-sector equal-weighting, at an assumed 5 bps per side. Its arithmetic annualized mean active return was −0.28%, with a six-month block bootstrap 95% interval of [−2.76%, 2.05%]. This is a useful investment rejection case; a negative result is retained rather than replaced by the best variant.

***REMOVED***[Manager memo](reports/snapshot/manager_memo.md) · [Snapshot statistics](reports/snapshot/analysis.json)***REMOVED***

## The decision and the rules

The simulated manager starts with a SPY reference account and considers a 20% sector sleeve. Every month, the primary rule selects three of the nine original Select Sector SPDR ETFs: XLK, XLF, XLE, XLY, XLP, XLV, XLI, XLB and XLU. The selected ETFs receive equal target weights.

At month-end `m`, the signals are:

| Fixed rule | Adjusted-level ratio | Purpose |
|---|---|---|
| MOM12−1 (primary) | `P[m−1] / P[m−12] − 1` | Eleven monthly returns, skipping the latest month |
| MOM12−0 | `P[m] / P[m−12] − 1` | Check whether omitting the latest month matters |
| MOM1 | `P[m] / P[m−1] − 1` | Compare with short-horizon rotation |
| Buffer12−1 | Same primary signal; retain incumbents ranked ≤4 | Test trading savings and delayed replacement together |

Monthly trading is separate from the signal horizon. A December 1999 decision is executed at the first January 2000 trading day's **close**. Old holdings earn execution-day returns; new holdings start earning returns on the following session. A $1m initial cash baseline includes formation fees, and the final holdings are valued without liquidation.

Benchmarks use the same accounting engine: monthly EW9 and buy-and-hold SPY. Full accounts include 80% SPY / 20% MOM, 80% SPY / 20% EW9, 80% SPY / 20% buffer, and a fixed 10% momentum sensitivity case. They are simulated directly, including drift and rebalancing costs.

## What is implemented

- Strict adjusted-level inputs, preserved supplier action fields, snapshot hashes, and full XNYS trading-session coverage checks.
- Daily position drift and self-financing costs charged on actual purchases plus sales; fixed 0/5/10 bps scenarios.
- Continuous backtests with development (2000–2010), confirmation (2011–2017), and final historical (2018–2025) summaries.
- Paired active-return block bootstrap, tracking error/IR, worst rolling twelve-month outcomes, and SPY-proxy CAPM with French monthly RF and HAC uncertainty.
- Four diagnostic episodes: dot-com decline, financial crisis decline, COVID decline/rebound, and 2022 inflation/rate shock.
- Auditable signal dates/endpoints/ranks, execution dates, pretrade/target weights, fees, daily weights, and dollar P&L by ETF. P&L contributions reconcile to wealth changes; they are not factor attribution.

The skip-month convention comes from individual-stock momentum research; it is a testable choice here, not an established optimum for sector ETFs. See [French's momentum definition](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_mom_factor.html) and [AQR's discussion of style implementation](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/JOIM-Investing-With-Style.pdf).

## Reproduce

Python 3.12 is recommended. From this repository's root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install '.[download,plots]'
python -m unittest discover -s tests -v
python -m sector_momentum download --out data/raw
python -m sector_momentum run --prices data/raw/total_return.csv --rf data/raw/risk_free.csv --out reports/local
```

Inputs are downloaded from Yahoo Finance via yfinance and the French data library. The required warm-up starts on 1998-12-31; the trading sample ends on 2025-12-31. Missing observations cause a failure, not interpolation or forward-filling. The supplier end date is exclusive (`2026-01-01`).

To use your own licensed data, provide `date` plus the ten ticker columns as **positive adjusted levels**, not returns. Monthly RF is a separate `date,rf` CSV in decimal units. Without `--rf`, the report explicitly labels a zero-RF market regression rather than a fully specified CAPM.

Offline synthetic demonstration:

```bash
python -m sector_momentum demo --out reports/demo
```

Synthetic output is marked throughout and is not historical ETF performance. Tests run offline and do not require Yahoo, network access, or matplotlib. All 44 tests passed locally. A [GitHub Actions configuration example](docs/ci_workflow_example.yml) is included but has not been activated, because the publishing credential does not have workflow permission. The initial verified run's direct package versions are in [requirements-reproduce.txt](requirements-reproduce.txt); they are not a complete transitive lockfile.

## Evidence and limits

The published [snapshot](reports/snapshot) contains derived tables, figures, provenance and a manager memo. The [data quality record](reports/snapshot/data_quality.json) includes a supplier XLU split spot-check and daily P&L reconciliation. Raw vendor prices/actions and local audit files are excluded from Git. Download again to reproduce locally; a different vendor revision can produce different hashes and results.

![Net wealth and drawdowns](reports/snapshot/wealth_drawdown.png)

The 20% momentum account's full-period tracking error versus SPY is 1.60%, below the illustrative 2% budget. Passing that risk check does not rescue weak net-return evidence. The manager can retain the baseline allocation and request prospective evidence before reconsidering the rule.

This is retrospective research with known historical events, simulated close fills and flat fee assumptions. Yahoo adjusted levels are a supplier total-return proxy; dividends must not be added again. ETF operating expenses are already reflected in the historical fund path; the bps scenarios add trading costs. They do not independently verify corporate actions or model tax, historical spreads, market impact, auction fills or $100m capacity. The original nine ETF products also change their underlying sector exposures over time. The MOM-versus-EW9 comparison mixes selection and concentration; a CAPM intercept does not establish causal alpha. Multi-factor analysis, matched-concentration random controls and prospective paper trading remain further work.

***REMOVED***
