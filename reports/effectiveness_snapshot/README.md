# Effectiveness research snapshot — 2026-10-04

Read [行业轮动何时有效：收益机制、事前条件与证据强度](industry_rotation_effectiveness_zh.md) for the completed study. It evaluates realized return mechanisms, four information-available-at-decision conditions and three actual switching filters. The original frozen protocol and numerical results are preserved; this publication adds no successful rule or new inference.

The ETF study did not confirm a stable, cost-adjusted enable/disable rule. Realized forward ranking and dispersion explain outcomes after the fact; they do not predict them. The French transfer check uses different research baskets and execution timing, and does not turn the ETF result into a universal claim about momentum or active investing.

## Included evidence

| Artifact | Purpose |
|---|---|
| [Frozen protocol](research_protocol_zh.md) | H1–H4, F1–F3, calibration periods, costs, fixed statistical families and reporting threshold |
| [Method review](protocol_audit_zh.md) | Literature, identification limits and review of the frozen protocol |
| [Independent calculation audit](independent_calculation_audit_zh.md) / [JSON](independent_calculation_audit.json) | Independent features, self-financing ledgers, HAC and Holm checks |
| [ETF condition tests](etf_condition_tests.csv) | All four hypotheses and all three costs; monthly arithmetic units |
| [Monthly features](etf_monthly_features.csv) | Observable information, labels and subsequent net active returns; H3/H4 calibration applies after 2009 |
| [Time checks](etf_condition_time_checks.csv) / [leave-one-year-out](etf_leave_one_year_out.csv) | Direction stability and concentration in particular years |
| [Filter summary](filter_summary.csv) / [inference](filter_inference.csv) | Actual switching portfolios and the separate six-comparison test family |
| [Filter NAV](filters_daily_nav_5bps.csv) / [ledger validation](ledger_validation.csv) | Actual daily performance and constant-filter accounting checks |
| [Mechanism review](mechanism/mechanism_review_zh.md) / [statistics](mechanism/mechanism_statistics.json) | 311 execution intervals, 312 calendar months, realized ranks and attribution |
| [French validation](external/external_validation_zh.md) / [provenance](external/provenance.json) | External industry classification/timing/cost limits, results and original source hashes |
| [Original ETF manifest](etf_study_manifest.json) | Original price, protocol, engine, signal and script hashes |
| [Integration manifest](integration_manifest.json) | Byte-identical snapshot files; original/integrated script hashes and portability changes |

The included monthly return/ledger/attribution tables support tracing the narrative without publishing original vendor data. Raw ETF prices, risk-free input, French supplier downloads, and parsed raw French return/factor histories are excluded. Full filter trades/P&L can be regenerated locally instead of duplicating them in the public snapshot.

## Reproduce and interpret

[Portable scripts and exact input requirements](../../research/effectiveness/README.md) cover ETF conditions/filters, independent numerical auditing, mechanism attribution and the French external analysis. They require saved input files and fail when inputs are missing; no script downloads missing data. Run them into the ignored `reports/local/` directory.

The original baseline report uses **2,000 draws, seed 2026, six-month blocks**. This effectiveness extension uses **20,000 draws, seed 20261004**, six/twelve-month condition intervals and three/six/twelve-month mechanism/transfer checks. These are separately disclosed analyses rather than interchangeable intervals. Percentile block intervals are not multiplicity-adjusted simultaneous intervals; HAC p-values and Holm adjustments are reported separately. Annualized arithmetic active means are monthly means multiplied by twelve, not CAGR differences or forecasts.

H1 has only five ETF months in one episode. Six/twelve-month bootstraps omit 18.15%/24.29% of draws with missing conditional groups; its retained-draw intervals are fragile descriptions, not reliable general crisis-recovery evidence. Original histories were already explored, so neither the calendar splits nor the external history is genuinely untouched prospective data.

Historical review text and original manifests retain original file names and source hashes. The integrated scripts have different hashes after portability changes; the integration manifest makes this difference explicit. During integration, only syntax/CLI/hash checks were run. The complete underlying financial calculation and independent audit date remains 2026-10-04.
