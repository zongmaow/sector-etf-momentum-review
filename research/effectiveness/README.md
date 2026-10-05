# Reproducing the effectiveness study

These scripts reproduce the completed 2026-10-04 retrospective study. They do not search for new rules or download missing data. The published [snapshot](../../reports/effectiveness_snapshot/README.md) retains the original protocol, numerical results, reviews and historical source hashes. The scripts in this directory were subsequently made portable; [integration_manifest.json](../../reports/effectiveness_snapshot/integration_manifest.json) maps the original and integrated script hashes.

Run the commands below from the repository root using Python 3.12 and the versions in [requirements-reproduce.txt](../../requirements-reproduce.txt). `PYTHONPATH=src` selects this checkout's engine. Generated output belongs in the ignored `reports/local/` directory. Do not overwrite the historical public snapshot.

## ETF conditions and actual switching filters

Required saved input: `data/raw/total_return.csv`. The historical price SHA-256 is `e03d2506e51d1a5bdbd8dcb37ffd6e80364c88cbb88449ca0866b74b3dcae11c`. The required trading-session coverage and nine-sector/SPY schema are validated by the project data loader. The frozen protocol defaults to `reports/effectiveness_snapshot/research_protocol_zh.md`; `--protocol` can explicitly select a byte-identical copy.

```sh
PYTHONPATH=src python research/effectiveness/study.py \
  --repo "$PWD" --prices data/raw/total_return.csv \
  --out reports/local/effectiveness

PYTHONPATH=src python research/effectiveness/independent_audit.py \
  --repo "$PWD" --prices data/raw/total_return.csv \
  --out reports/local/effectiveness
```

`study.py` recalculates MOM12−1, EW9 and SPY from the supplied price file; it uses no cached original baseline. It writes the four condition hypotheses, three actual trading filters, all 0/5/10 bp results, daily NAV, trades and dollar P&L, plus a manifest hashing its inputs and implementation. The independent audit reads these regenerated files, independently reconstructs accounting and features, checks HAC/Holm and validates constant-filter degeneration against the original engine. It writes `independent_calculation_audit.json` in the same private output directory. The public snapshot intentionally omits the filter trade/P&L files because this command regenerates them.

## ETF mechanism and realized attribution

Required saved inputs: the same total-return file, `data/raw/risk_free.csv`, and the original engine's daily NAV/decision/trade/P&L outputs. To create those local baseline outputs from saved data:

```sh
PYTHONPATH=src python -m sector_momentum run \
  --prices data/raw/total_return.csv --rf data/raw/risk_free.csv \
  --out reports/local

PYTHONPATH=src python research/effectiveness/analyze_mechanism.py \
  --repo "$PWD" --prices data/raw/total_return.csv \
  --risk-free data/raw/risk_free.csv --baseline-dir reports/local \
  --out reports/local/effectiveness/mechanism
```

The mechanism script requires `daily_nav.csv`, `audit/MOM12_1/decisions.csv`, and each MOM12_1/EW9 account's `trades.csv` and `daily_pnl_dollars.csv`; missing files cause failure. It reconciles 311 complete execution intervals and 312 calendar months, produces realized ranking diagnostics and sector contributions, and records actual input hashes. Its forward ranks/dispersion are explanations after execution, not inputs to a trading rule. The final incomplete execution interval is excluded from interval inference.

## French ten-industry external transfer check

Obtain and preserve the original files from the [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html). The scripts require the unmodified, extracted `10_Industry_Portfolios.csv` and `F-F_Research_Data_Factors.csv` under an explicitly supplied directory such as `data/raw/french/`. They do not accept substitute ETF data or silently download a newer vintage.

Reference 202608 CRSP-vintage CSV hashes:

| Input | SHA-256 |
|---|---|
| `10_Industry_Portfolios.csv` | `18ed376fc42e2327ceaf3d65a02521a6512e7f9e3001007c4da69d7db108aa82` |
| `F-F_Research_Data_Factors.csv` | `d7d7fe37b150b5b15c9c069b3ba101dfe1af568c6d7b5db6e73cd0a6c0c9e5e5` |

```sh
PYTHONPATH=src python research/effectiveness/external/analyze_external.py \
  --repo "$PWD" --raw-dir data/raw/french \
  --out reports/local/effectiveness/external

PYTHONPATH=src python research/effectiveness/external/analyze_conditions.py \
  --raw-dir data/raw/french \
  --protocol reports/effectiveness_snapshot/research_protocol_zh.md \
  --out reports/local/effectiveness/external

PYTHONPATH=src python research/effectiveness/external/write_summary.py \
  --out reports/local/effectiveness/external
```

The first script parses only the **monthly value-weighted industry** section, truncates at 2025-12, validates dates/sentinels/signals/accounting, and creates the continuous 1960–2025 monthly ledger. The second uses the saved factor file to construct the market proxy and applies the unchanged four-condition protocol and fixed calibration periods. The third renders the external memo from their numerical summaries. Raw/script hashes are recorded in generated provenance/conditional results; the narrative's historical date and named CRSP vintage refer to the original study and must be reviewed if a revised input vintage is used.

French industry portfolios are research baskets classified by SIC, not sector ETFs. Their monthly timing allows theoretical prior-month-end formation, not the ETF engine's next-session-close execution. Five basis points are hypothetical outer-basket trading costs; constituent turnover and historically attainable implementation costs are not measured. A changed result cannot be attributed solely to the industry count.

## Verify the regenerated numerical outputs

After running the numerical commands above, compare their outputs with the preserved snapshot:

```sh
python research/effectiveness/verify_reproduction.py \
  --snapshot reports/effectiveness_snapshot \
  --etf-dir reports/local/effectiveness \
  --mechanism-dir reports/local/effectiveness/mechanism \
  --external-dir reports/local/effectiveness/external \
  --out reports/local/effectiveness/comparison.json
```

The offline comparator checks 25 CSV files for ordered schema, row counts, text and numeric equality, and three core JSON files for structure and all non-provenance fields. Only named top-level provenance fields are excluded; actual input and script identities are separately recorded. Missing artifacts, changed fields or differences above `1e-12` fail with a nonzero exit status. The [2026-10-05 check](../../reports/reproduction_check/README.md) found zero numerical differences and retained the regenerated independent audit. Seven synthetic offline smoke tests cover this comparator and known HAC/Holm numerical cases without supplier data.

## What the integration and follow-up verify

Every included historical snapshot file remains byte-identical to its source bundle. Syntax and all six original `--help` paths were checked during integration; these checks perform no data calculation. The completed financial research was not rerun merely to move files. A separate 2026-10-05 numerical rerun subsequently verified the portable calculations, as documented above. Portability changes concern paths, CLI lifecycle, output placement and audit-input provenance, with no changes to thresholds, signals, seeds, test families or trading equations.

The original independent review predates the final source's switch from cached baseline returns to recomputation. Its references to that cache and original local file names are preserved as historical audit observations, not descriptions of the integrated scripts. Original one-machine packaging/report-generation code is excluded; the published main memo and figures are retained as historical artifacts. The two PNG figures were not redrawn by the numerical verification, and the French narrative writer was not rerun in that check. Figure and narrative regeneration therefore remain outside its verified scope. [Snapshot provenance](../../docs/snapshot_provenance.md) explains the historical source hashes and editorial changes.

If vendor history has been revised, new hashes and results are a different data snapshot. Matching the historical raw-input hashes is necessary for an exact numerical comparison; the historical snapshot is not a point-in-time data feed or a prospective validation.
