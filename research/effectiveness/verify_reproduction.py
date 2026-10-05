"""Compare regenerated numerical research with the preserved public snapshot.

This offline check reads outputs only; it never runs research or downloads data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


CSV_FILES = {
    "etf": [
        "etf_condition_tests.csv", "etf_condition_time_checks.csv",
        "etf_leave_one_year_out.csv", "etf_monthly_features.csv",
        "filter_inference.csv", "filter_summary.csv", "filter_time_checks.csv",
        "filters_daily_nav_5bps.csv", "filters_monthly_0bps.csv",
        "filters_monthly_5bps.csv", "filters_monthly_10bps.csv",
        "ledger_validation.csv", "recomputed_baseline_monthly.csv",
    ],
    "external": [
        "basic_summary.csv", "comparison_returns.csv", "conditional_results.csv",
        "conditions_and_outcomes.csv", "ew10_monthly_ledger.csv",
        "ff10_holding_month_scores.csv", "leave_one_year_out.csv",
        "mom12_1_monthly_ledger.csv",
    ],
    "mechanism": [
        "calendar_month_active_attribution.csv", "calendar_year_active_attribution.csv",
        "execution_intervals.csv", "interval_sector_gross_active.csv",
    ],
}
# Exact top-level metadata exclusions, not a general rule to ignore hash-like keys.
# Compare raw/script identities separately in the reproduction record.
JSON_FILES = {
    "external/basic_summary.json": (),
    "external/conditional_results.json": ("raw_input_sha256", "script_sha256"),
    "mechanism/mechanism_statistics.json": ("input_sha256",),
}


class ComparisonError(ValueError):
    """A missing artifact, changed schema or unequal value."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _numeric_equal(left, right, atol: float) -> bool:
    if math.isnan(left) or math.isnan(right):
        return math.isnan(left) and math.isnan(right)
    if not math.isfinite(left) or not math.isfinite(right):
        return left == right
    return abs(left - right) <= atol


def compare_csv(reference: Path, actual: Path, atol: float = 1e-12) -> dict:
    with reference.open(newline="", encoding="utf-8-sig") as f:
        expected = list(csv.reader(f))
    with actual.open(newline="", encoding="utf-8-sig") as f:
        observed = list(csv.reader(f))
    if not expected or not observed or expected[0] != observed[0]:
        raise ComparisonError("CSV column names/order differ")
    if len(expected) != len(observed):
        raise ComparisonError("CSV row counts differ")
    columns = len(expected[0])
    numeric_count, max_error = 0, 0.0
    for row_index, (left_row, right_row) in enumerate(zip(expected[1:], observed[1:]), 2):
        if len(left_row) != columns or len(right_row) != columns:
            raise ComparisonError(f"CSV row {row_index} has invalid width")
        for column, left, right in zip(expected[0], left_row, right_row):
            try:
                a, b = float(left), float(right)
            except ValueError:
                if left != right:
                    raise ComparisonError(f"CSV row {row_index}, {column}: text/type differs")
                continue
            numeric_count += 1
            if not _numeric_equal(a, b, atol):
                raise ComparisonError(f"CSV row {row_index}, {column}: numeric value differs ({left} vs {right})")
            if math.isfinite(a) and math.isfinite(b):
                max_error = max(max_error, abs(a - b))
    return {"rows": len(expected) - 1, "columns": columns,
            "schema_and_text_equal": True, "numeric_cell_count": numeric_count,
            "max_abs_numeric_difference": max_error}


def compare_json(reference: Path, actual: Path, excluded_top_keys=(), atol: float = 1e-12) -> dict:
    left, right = json.loads(reference.read_text()), json.loads(actual.read_text())
    for value in (left, right):
        if not isinstance(value, dict):
            raise ComparisonError("Core JSON must be a top-level object")
        for key in excluded_top_keys:
            value.pop(key, None)
    numeric_count, max_error = 0, 0.0

    def visit(a, b, location):
        nonlocal numeric_count, max_error
        numbers = (int, float)
        if isinstance(a, numbers) and not isinstance(a, bool) and isinstance(b, numbers) and not isinstance(b, bool):
            numeric_count += 1
            if not _numeric_equal(a, b, atol):
                raise ComparisonError(f"JSON {location}: numeric value differs ({a} vs {b})")
            if math.isfinite(a) and math.isfinite(b):
                max_error = max(max_error, abs(a - b))
        elif type(a) is not type(b):
            raise ComparisonError(f"JSON {location}: value type differs")
        elif isinstance(a, dict):
            if a.keys() != b.keys():
                raise ComparisonError(f"JSON {location}: keys differ")
            for key in a:
                visit(a[key], b[key], f"{location}.{key}")
        elif isinstance(a, list):
            if len(a) != len(b):
                raise ComparisonError(f"JSON {location}: list lengths differ")
            for index, (first, second) in enumerate(zip(a, b)):
                visit(first, second, f"{location}[{index}]")
        elif a != b:
            raise ComparisonError(f"JSON {location}: text/boolean/null differs")

    visit(left, right, "$")
    return {"numeric_leaf_count": numeric_count, "max_abs_numeric_difference": max_error,
            "non_numeric_fields_equal": True, "excluded_top_level_keys": list(excluded_top_keys)}


def verify(snapshot: Path, directories: dict[str, Path], atol: float = 1e-12) -> dict:
    csv_results, json_results, failures = [], [], []
    for group, names in CSV_FILES.items():
        for name in names:
            relative = Path(name) if group == "etf" else Path(group) / name
            reference, actual = snapshot / relative, directories[group] / name
            try:
                result = compare_csv(reference, actual, atol)
                csv_results.append({"file": relative.as_posix(), "reference_sha256": sha256(reference),
                                    "regenerated_sha256": sha256(actual), **result})
            except (ComparisonError, OSError, ValueError) as error:
                failures.append({"file": relative.as_posix(), "reason": str(error).replace(str(actual), relative.as_posix()).replace(str(reference), relative.as_posix())})
    for name, exclusions in JSON_FILES.items():
        relative = Path(name)
        reference, actual = snapshot / relative, directories[relative.parts[0]] / relative.name
        try:
            result = compare_json(reference, actual, exclusions, atol)
            json_results.append({"file": name, "reference_sha256": sha256(reference),
                                 "regenerated_sha256": sha256(actual), **result})
        except (ComparisonError, OSError, ValueError) as error:
            failures.append({"file": name, "reason": str(error).replace(str(actual), name).replace(str(reference), name)})
    return {"passed": not failures, "absolute_numeric_tolerance": atol,
            "csv_files_compared": len(csv_results), "core_json_files_compared": len(json_results),
            "csv_results": csv_results, "json_results": json_results, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=Path("reports/effectiveness_snapshot"))
    parser.add_argument("--etf-dir", type=Path, required=True)
    parser.add_argument("--mechanism-dir", type=Path, required=True)
    parser.add_argument("--external-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--atol", type=float, default=1e-12)
    args = parser.parse_args()
    if not math.isfinite(args.atol) or args.atol < 0:
        parser.error("--atol must be finite and nonnegative")
    result = verify(args.snapshot, {"etf": args.etf_dir, "mechanism": args.mechanism_dir,
                                    "external": args.external_dir}, args.atol)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{'PASS' if result['passed'] else 'FAIL'}: {result['csv_files_compared']} CSV, "
          f"{result['core_json_files_compared']} core JSON; {len(result['failures'])} failures")
    if not result["passed"]:
        for failure in result["failures"]:
            print(f"{failure['file']}: {failure['reason']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
