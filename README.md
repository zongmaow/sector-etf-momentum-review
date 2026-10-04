# Sector ETF Momentum Review

A hypothetical US equity portfolio manager is considering a sector rotation sleeve. This project asks whether a fixed momentum rule adds enough **net value over sector equal-weighting** to justify its trading and active risk.

The first historical run does **not** support adopting the primary rule: over 2000–2025, MOM12−1 earned an 8.32% net CAGR versus 8.68% for nine-sector equal-weighting, at an assumed 5 bps per side. Its arithmetic annualized mean active return was −0.28%, with a six-month block bootstrap 95% interval of [−2.76%, 2.05%]. The full-history result is retained alongside an exploratory analysis of favorable and unfavorable periods.

***REMOVED***[Manager memo](reports/snapshot/manager_memo.md) · [Snapshot statistics](reports/snapshot/analysis.json) · [Investment case (中文)](docs/investment_case_zh.md) · [Period and sector comparison (中文)](reports/exploratory_snapshot/regime_comparison_zh.md)

## Favorable and unfavorable paths

The unchanged nine-sector rule produces all four outcomes: 2022 gained **9.48%** and beat EW9; 2011 lost **2.16%** and lagged EW9; 2006 made money but lagged EW9; 2002 lost money but lost less than EW9. These are net calendar-year returns, rather than CAGRs. Energy holdings contributed +18.58 percentage points in 2022 and −4.75 points in 2023; these are portfolio P&L contributions, not XLE buy-and-hold returns.

A separate **2020–2025 common-start test** adds XLRE and XLC to cover all eleven sector products. Both universes are formed from cash on the same date, using unchanged signals, execution and costs. Eleven-sector momentum earned **16.48% CAGR**, versus **11.97%** for EW11 and **14.80%** for SPY; the comparable nine-sector momentum account earned **14.55%**. The expanded strategy still lagged EW11 in 2021 and 2023, and both added sectors had negative contribution years.

The [exploratory snapshot](reports/exploratory_snapshot) discloses all 26 calendar years, five non-overlapping five-year blocks plus the remaining year, and all 277 overlapping three-year windows. Highlighted examples are chosen after observing this grid. They describe historical conditions; they do not provide a tested rule for recognizing a favorable regime in advance or change the primary full-history conclusion.

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

Synthetic output is marked throughout and is not historical ETF performance. Tests run offline and do not require Yahoo, network access, or matplotlib. All 57 tests passed locally. GitHub Actions runs the offline suite on every push to main and on pull requests ([workflow](.github/workflows/tests.yml)). The initial verified run's direct package versions are in [requirements-reproduce.txt](requirements-reproduce.txt); they are not a complete transitive lockfile.

To reproduce the complete period grid and the eleven-sector sensitivity test:

```bash
python -m sector_momentum explore --prices data/raw/total_return.csv --download-extra --out reports/exploration
```

The additional products are downloaded only over their available history. Their adjusted levels are combined with the saved original nine/SPY snapshot; base data are not silently replaced. To reuse the saved expansion, replace `--download-extra` with `--expanded-prices data/raw/extended/universe11.csv`. Omitting both options generates the original nine-sector period diagnostics only. Source changes require reinstalling the package.

## Evidence and limits

The published [snapshot](reports/snapshot) contains derived tables, figures, provenance and a manager memo. The [data quality record](reports/snapshot/data_quality.json) includes a supplier XLU split spot-check and daily P&L reconciliation. Raw vendor prices/actions and local audit files are excluded from Git. Download again to reproduce locally; a different vendor revision can produce different hashes and results.

![Net wealth and drawdowns](reports/snapshot/wealth_drawdown.png)

The 20% momentum account's full-period tracking error versus SPY is 1.60%, below the illustrative 2% budget. Passing that risk check does not rescue weak net-return evidence. The manager can retain the baseline allocation and request prospective evidence before reconsidering the rule.

This is retrospective research with known historical events, simulated close fills and flat fee assumptions. Yahoo adjusted levels are a supplier total-return proxy; dividends must not be added again. ETF operating expenses are already reflected in the historical fund path; the bps scenarios add trading costs. They do not independently verify corporate actions or model tax, historical spreads, market impact, auction fills or $100m capacity. The original nine ETF products also change their underlying sector exposures over time. The MOM-versus-EW9 comparison mixes selection and concentration; a CAPM intercept does not establish causal alpha. Multi-factor analysis, matched-concentration random controls and prospective paper trading remain further work.

***REMOVED***
