# Numerical reproduction check — 2026-10-05

This record verifies the portable effectiveness research published in `dd1c4a9` against the preserved 2026-10-04 snapshot. It adds calculation evidence, not a new parameter search or investment conclusion.

| Check | Result |
|---|---|
| ETF condition/filter CSV tables | 13 matched |
| French external CSV tables | 8 matched |
| ETF mechanism CSV tables | 4 matched |
| Core JSON summaries | 3 matched; 4,601 numeric leaves (booleans checked separately) |
| CSV schemas, row counts and text | Equal |
| Maximum absolute numeric difference | 0 |
| Independent audit | All primary checks valid; maximum relative NAV error below `4.2e-15` |

The [comparison](comparison.json) records every compared file's reference and regenerated SHA-256, dimensions/counts and maximum difference. JSON metadata can change between runs, so full-file hashes need not agree: only the explicit provenance fields in [verification_manifest.json](verification_manifest.json) are excluded from comparison. Every other JSON field, including text, booleans, settings and numeric values, is checked. The [independent audit](independent_calculation_audit.json) separately checks features, fees, ledgers, HAC and Holm against independent calculations.

## Executed calculations

The following are repository-relative, path-normalized forms of the executed numerical commands. The verification used the original saved supplier files and freshly rebuilt baseline audit outputs. Local file placement has been normalized to the documented `reports/local/` layout; these are the same CLI operations, not a claim that vendor inputs are bundled here.

The protocol path below uses the current English filename. The recorded run used its prior filename and original text hash, retained in the verification manifest. Translation changes that text identity without changing the frozen settings or financial results; see the [English documentation record](../english_documentation_manifest.json).

```sh
PYTHONPATH=src python -m sector_momentum run \
  --prices data/raw/total_return.csv --rf data/raw/risk_free.csv \
  --out reports/local --no-plots

PYTHONPATH=src python research/effectiveness/study.py \
  --repo "$PWD" --prices data/raw/total_return.csv \
  --out reports/local/effectiveness

PYTHONPATH=src python research/effectiveness/independent_audit.py \
  --repo "$PWD" --prices data/raw/total_return.csv \
  --out reports/local/effectiveness

PYTHONPATH=src python research/effectiveness/analyze_mechanism.py \
  --repo "$PWD" --prices data/raw/total_return.csv \
  --risk-free data/raw/risk_free.csv --baseline-dir reports/local \
  --out reports/local/effectiveness/mechanism

PYTHONPATH=src python research/effectiveness/external/analyze_external.py \
  --repo "$PWD" --raw-dir data/raw/french \
  --out reports/local/effectiveness/external

PYTHONPATH=src python research/effectiveness/external/analyze_conditions.py \
  --raw-dir data/raw/french \
  --protocol reports/effectiveness_snapshot/research_protocol.md \
  --out reports/local/effectiveness/external

python research/effectiveness/verify_reproduction.py \
  --snapshot reports/effectiveness_snapshot \
  --etf-dir reports/local/effectiveness \
  --mechanism-dir reports/local/effectiveness/mechanism \
  --external-dir reports/local/effectiveness/external \
  --out reports/local/effectiveness/comparison.json
```

The baseline command was also executed for this check; the mechanism comparison uses its freshly rebuilt daily NAV, decisions, trades and both dollar-P&L files. Their six hashes are recorded in the verification manifest. This does not extend the verification claim to every primary-snapshot output. The comparison utility reads outputs only, fails on missing files, changed schemas/text or numeric differences beyond the fixed absolute tolerance `1e-12`, and returns a nonzero exit status on failure. It does not download or run a backtest. The recorded zero differences are stronger than merely being within tolerance.

## Limits

Supplier inputs remain private; matching their hashes is necessary for exact numerical reproduction. The manifest records the ETF prices, risk-free file and both French CSV identities, portable-script identities, imported engine identities and the frozen protocol. New vendor revisions are a new snapshot.

The historical PNG figures were not redrawn: the old one-machine builder is not part of the portable pipeline. The French narrative writer was not run in this numeric check. Accordingly this verifies the numerical results and independent accounting/statistical audit, with no claim of complete image or narrative regeneration. See [snapshot provenance](../../docs/snapshot_provenance.md) for the source/version history.
