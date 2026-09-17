#!/usr/bin/env python3
"""
quality_check.py - Basic data quality / profiling tool for CSV and Parquet files.

Runs the following checks and outputs a summary:
- Column completeness (% of non-null values per column)
- Uniqueness check (% unique, duplicate values, PK candidate warning)
- Null counts per column
- Duplicate rows (full row duplicates)
- Numeric outlier detection using the IQR method (Q1 - 1.5*IQR, Q3 + 1.5*IQR)
- Datetime gap detection (large gaps between sorted consecutive timestamps)
- Numeric min/max / expected range checks (via --min/--max / --range config)
- Basic stats summary: count, mean, std, min, 25%, 50%, 75%, max

If pandas is installed, both CSV and Parquet are supported. Otherwise CSV only
via the standard library csv module (stats limited to: nulls, completeness,
duplicates, uniqueness, string length, integer-only min/max for simple columns).

Limitations:
- Large files are loaded into memory when possible. Chunking is not used.
  Set --sample N to limit rows on large CSVs.
- Datetime gap detection runs on datetime-dtype columns only (pandas) or
  columns whose header contains "date"/"time"/"ts" (csv fallback).
- Outlier detection is heuristic; IQR works well for unimodal bell-like
  distributions but is inappropriate for skewed or bounded data.
- Range checks are specified globally, not per-column. For per-column ranges,
  run --json and post-process.
"""

import argparse
import csv
import json as _json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"


HAS_PANDAS = False
try:
    import pandas as pd  # type: ignore
    HAS_PANDAS = True
except Exception:  # pragma: no cover
    pd = None  # type: ignore


def load_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile CSV/Parquet data and run basic data quality checks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python quality_check.py data.csv
  python quality_check.py partition.snappy.parquet --json
  python quality_check.py data.csv --null-threshold 0.90 --fail-on-warnings
  python quality_check.py data.csv --range sales_amount:0:10000 --range qty:0:10000
  python quality_check.py data.csv --sample 50000
  python quality_check.py data.csv --datetime-gap-hours 48
""",
    )
    parser.add_argument("path", help="Path to CSV or Parquet file")
    parser.add_argument(
        "--format",
        choices=["auto", "csv", "parquet"],
        default="auto",
        help="File format (default: auto by extension)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human-readable table summary",
    )
    parser.add_argument(
        "--csv-delimiter",
        default=",",
        help="CSV delimiter (default: ,)",
    )
    parser.add_argument(
        "--csv-encoding",
        default="utf-8-sig",
        help="CSV encoding (default: utf-8-sig)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Read only first N rows (0 = all rows, default)",
    )
    parser.add_argument(
        "--null-threshold",
        type=float,
        default=0.7,
        help="Warn when completeness (non-null ratio) drops below this threshold (default 0.7)",
    )
    parser.add_argument(
        "--iqr-multiplier",
        type=float,
        default=1.5,
        help="IQR multiplier for outlier fences (default: 1.5)",
    )
    parser.add_argument(
        "--datetime-gap-hours",
        type=float,
        default=0,
        help="If > 0, warn when consecutive sorted timestamps differ by more than N hours",
    )
    parser.add_argument(
        "--range",
        action="append",
        default=[],
        metavar="COL:MIN:MAX",
        help="Range check as 'column:min:max'. Repeatable for multiple columns.",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with non-zero code on warnings as well as errors (alias of --strict)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero code on warnings as well as errors",
    )
    parser.add_argument(
        "--primary-key",
        default="",
        help="Comma-separated list of columns expected to be unique (PK).",
    )
    return parser.parse_args(argv)


def detect_format(path: Path, fmt: str) -> str:
    if fmt != "auto":
        return fmt
    ext = path.suffix.lower()
    if ext in {".parquet", ".pq"}:
        return "parquet"
    return "csv"


def load_data_pandas(path: Path, fmt: str, args: argparse.Namespace):
    if fmt == "parquet":
        df = pd.read_parquet(path)
    else:
        read_kwargs = {
            "delimiter": args.csv_delimiter,
            "encoding": args.csv_encoding,
            "low_memory": False,
        }
        if args.sample > 0:
            read_kwargs["nrows"] = args.sample
        df = pd.read_csv(path, **read_kwargs)
    if args.sample > 0 and fmt == "parquet":
        df = df.head(args.sample)
    return df


def load_data_csv_stdlib(path: Path, args: argparse.Namespace) -> Tuple[List[str], List[List[str]]]:
    with open(path, "r", encoding=args.csv_encoding, newline="") as f:
        reader = csv.reader(f, delimiter=args.csv_delimiter)
        try:
            headers = next(reader)
        except StopIteration:
            return [], []
        rows: List[List[str]] = []
        for i, row in enumerate(reader, start=1):
            if args.sample > 0 and i > args.sample:
                break
            rows.append(row)
    return headers, rows


def is_null_value(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def compute_stats_pandas(df: "pd.DataFrame", args: argparse.Namespace) -> Tuple[Dict, List[Dict]]:
    issues: List[Dict] = []
    n_rows = len(df)
    col_results: Dict[str, Any] = {}

    null_ratios = df.isna().mean()
    non_null_ratios = 1 - null_ratios

    for col in df.columns:
        series = df[col]
        n_null = int(series.isna().sum())
        completeness = 1.0 - (n_null / n_rows) if n_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))
        unique_ratio = (unique_count / (n_rows - n_null)) if (n_rows - n_null) > 0 else 0.0

        col_res: Dict[str, Any] = {
            "dtype": str(series.dtype),
            "total_rows": n_rows,
            "non_null": int(n_rows - n_null),
            "nulls": n_null,
            "completeness": round(completeness, 6),
            "unique_count": unique_count,
            "unique_ratio": round(unique_ratio, 6),
        }

        if completeness < args.null_threshold:
            issues.append({
                "severity": SEVERITY_WARN,
                "rule": "completeness_below_threshold",
                "column": col,
                "message": (
                    f"Column '{col}' completeness={completeness:.2%} below "
                    f"threshold {args.null_threshold:.0%} ({n_null} nulls)."
                ),
            })

        if unique_ratio >= 0.999 and n_rows > 1 and n_null == 0:
            issues.append({
                "severity": SEVERITY_INFO,
                "rule": "pk_candidate",
                "column": col,
                "message": (
                    f"Column '{col}' appears to be a primary-key candidate "
                    f"(unique_ratio={unique_ratio:.2%}, no nulls)."
                ),
            })

        if pd.api.types.is_numeric_dtype(series):
            try:
                desc = series.describe(percentiles=[0.25, 0.5, 0.75]).to_dict()
                cleaned = {k: (None if (isinstance(v, float) and math.isnan(v)) else v)
                           for k, v in desc.items()}
                col_res["stats"] = cleaned

                q1 = cleaned.get("25%")
                q3 = cleaned.get("75%")
                if q1 is not None and q3 is not None and not (math.isnan(q1) or math.isnan(q3)):
                    iqr = q3 - q1
                    lower_fence = q1 - args.iqr_multiplier * iqr
                    upper_fence = q3 + args.iqr_multiplier * iqr
                    outlier_mask = (series < lower_fence) | (series > upper_fence)
                    outlier_mask &= series.notna()
                    n_outliers = int(outlier_mask.sum())
                    col_res["outliers"] = {
                        "method": "IQR",
                        "iqr_multiplier": args.iqr_multiplier,
                        "lower_fence": lower_fence,
                        "upper_fence": upper_fence,
                        "count": n_outliers,
                    }
                    if n_outliers > 0:
                        issues.append({
                            "severity": SEVERITY_WARN,
                            "rule": "numeric_outliers",
                            "column": col,
                            "message": (
                                f"Column '{col}' has {n_outliers} outlier values via IQR "
                                f"(fences: [{lower_fence:.4g}, {upper_fence:.4g}])."
                            ),
                        })
            except Exception as e:
                col_res["stats_error"] = str(e)
        elif pd.api.types.is_datetime64_any_dtype(series):
            sorted_vals = series.dropna().sort_values()
            if len(sorted_vals) > 1:
                col_res["stats"] = {
                    "min": str(sorted_vals.min()),
                    "max": str(sorted_vals.max()),
                }
                if args.datetime_gap_hours > 0:
                    diffs = sorted_vals.diff().dropna()
                    threshold_ns = int(args.datetime_gap_hours * 3600 * 1e9)
                    large_gaps = diffs[diffs.astype("int64") > threshold_ns]
                    if len(large_gaps) > 0:
                        issues.append({
                            "severity": SEVERITY_WARN,
                            "rule": "datetime_gap",
                            "column": col,
                            "message": (
                                f"Column '{col}' has {len(large_gaps)} gap(s) greater "
                                f"than {args.datetime_gap_hours}h between consecutive sorted timestamps."
                            ),
                        })

        col_results[col] = col_res

    duplicates = int(df.duplicated().sum())
    row_level = {
        "rows": n_rows,
        "columns": len(df.columns),
        "duplicate_rows": duplicates,
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
    }
    if duplicates > 0:
        issues.append({
            "severity": SEVERITY_WARN,
            "rule": "duplicate_rows",
            "column": None,
            "message": f"Found {duplicates} fully duplicated rows across all columns.",
        })

    if args.primary_key:
        pk_cols = [c.strip() for c in args.primary_key.split(",") if c.strip()]
        missing = [c for c in pk_cols if c not in df.columns]
        if missing:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "pk_missing_columns",
                "column": None,
                "message": f"Primary key columns not found: {', '.join(missing)}",
            })
        else:
            if len(pk_cols) == 1:
                dup_pk = int(df[pk_cols[0]].duplicated().sum())
            else:
                dup_pk = int(df.duplicated(subset=pk_cols).sum())
            if dup_pk > 0:
                issues.append({
                    "severity": SEVERITY_ERROR,
                    "rule": "pk_not_unique",
                    "column": ",".join(pk_cols),
                    "message": f"Primary key ({', '.join(pk_cols)}) has {dup_pk} duplicate values.",
                })
            else:
                issues.append({
                    "severity": SEVERITY_INFO,
                    "rule": "pk_unique",
                    "column": ",".join(pk_cols),
                    "message": f"Primary key ({', '.join(pk_cols)}) is unique.",
                })

    return {
        "columns": col_results,
        "rows": row_level,
    }, issues


def apply_range_checks_pandas(df: "pd.DataFrame", args: argparse.Namespace) -> List[Dict]:
    issues: List[Dict] = []
    for spec in args.range:
        parts = spec.split(":")
        if len(parts) != 3:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "range_config_error",
                "column": None,
                "message": f"Invalid --range spec '{spec}'. Expected COL:MIN:MAX.",
            })
            continue
        col, lo, hi = parts
        if col not in df.columns:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "range_column_missing",
                "column": col,
                "message": f"--range column '{col}' not found in dataset.",
            })
            continue
        try:
            lo_f = float(lo)
            hi_f = float(hi)
        except ValueError:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "range_config_error",
                "column": col,
                "message": f"--range bounds for '{col}' are not numeric: lo={lo}, hi={hi}.",
            })
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        n_low = int((series < lo_f).sum())
        n_high = int((series > hi_f).sum())
        if n_low or n_high:
            issues.append({
                "severity": SEVERITY_WARN,
                "rule": "range_violation",
                "column": col,
                "message": (
                    f"Column '{col}' has {n_low} value(s) below min={lo_f} and "
                    f"{n_high} value(s) above max={hi_f}."
                ),
            })
    return issues


def compute_stats_csv_stdlib(
    headers: List[str],
    rows: List[List[str]],
    args: argparse.Namespace,
) -> Tuple[Dict, List[Dict]]:
    issues: List[Dict] = []
    n_rows = len(rows)
    col_results: Dict[str, Any] = {}

    for idx, col in enumerate(headers):
        values = [row[idx] if idx < len(row) else "" for row in rows]
        n_null = sum(1 for v in values if is_null_value(v))
        completeness = 1.0 - (n_null / n_rows) if n_rows > 0 else 0.0
        non_null = [v for v in values if not is_null_value(v)]
        unique_set = set(non_null)
        unique_count = len(unique_set)
        unique_ratio = (unique_count / len(non_null)) if len(non_null) > 0 else 0.0

        col_res: Dict[str, Any] = {
            "dtype": "string",
            "total_rows": n_rows,
            "non_null": len(non_null),
            "nulls": n_null,
            "completeness": round(completeness, 6),
            "unique_count": unique_count,
            "unique_ratio": round(unique_ratio, 6),
        }

        if completeness < args.null_threshold:
            issues.append({
                "severity": SEVERITY_WARN,
                "rule": "completeness_below_threshold",
                "column": col,
                "message": (
                    f"Column '{col}' completeness={completeness:.2%} below "
                    f"threshold {args.null_threshold:.0%} ({n_null} nulls)."
                ),
            })

        if unique_ratio >= 0.999 and n_rows > 1 and n_null == 0:
            issues.append({
                "severity": SEVERITY_INFO,
                "rule": "pk_candidate",
                "column": col,
                "message": (
                    f"Column '{col}' appears to be a primary-key candidate "
                    f"(unique_ratio={unique_ratio:.2%}, no nulls)."
                ),
            })

        numeric_values: List[float] = []
        for v in non_null:
            try:
                numeric_values.append(float(v))
            except ValueError:
                pass
        if numeric_values and len(numeric_values) >= max(1, len(non_null) * 0.95):
            col_res["dtype"] = "numeric (inferred)"
            numeric_values.sort()
            n = len(numeric_values)
            mean = sum(numeric_values) / n
            std = 0.0
            if n > 1:
                var = sum((x - mean) ** 2 for x in numeric_values) / (n - 1)
                std = math.sqrt(var)

            def quantile(p: float) -> float:
                if n == 0:
                    return float("nan")
                idx = (n - 1) * p
                lo = int(math.floor(idx))
                hi = int(math.ceil(idx))
                if lo == hi:
                    return numeric_values[lo]
                frac = idx - lo
                return numeric_values[lo] * (1 - frac) + numeric_values[hi] * frac

            q1 = quantile(0.25)
            q3 = quantile(0.75)
            iqr = q3 - q1
            lower_fence = q1 - args.iqr_multiplier * iqr
            upper_fence = q3 + args.iqr_multiplier * iqr
            n_outliers = sum(1 for x in numeric_values if x < lower_fence or x > upper_fence)
            col_res["stats"] = {
                "count": n,
                "mean": mean,
                "std": std,
                "min": numeric_values[0],
                "25%": q1,
                "50%": quantile(0.5),
                "75%": q3,
                "max": numeric_values[-1],
            }
            col_res["outliers"] = {
                "method": "IQR",
                "iqr_multiplier": args.iqr_multiplier,
                "lower_fence": lower_fence,
                "upper_fence": upper_fence,
                "count": n_outliers,
            }
            if n_outliers > 0:
                issues.append({
                    "severity": SEVERITY_WARN,
                    "rule": "numeric_outliers",
                    "column": col,
                    "message": (
                        f"Column '{col}' has {n_outliers} outlier values via IQR "
                        f"(fences: [{lower_fence:.4g}, {upper_fence:.4g}])."
                    ),
                })

        col_lower = col.lower()
        if args.datetime_gap_hours > 0 and (
            "date" in col_lower or "time" in col_lower or col_lower.endswith("ts") or "dt" in col_lower
        ):
            import datetime as _dt
            parsed: List[_dt.datetime] = []
            fmts = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
            ]
            for v in non_null:
                for f in fmts:
                    try:
                        parsed.append(_dt.datetime.strptime(v, f))
                        break
                    except ValueError:
                        continue
            if len(parsed) > max(1, len(non_null) * 0.5):
                parsed.sort()
                col_res["stats"] = {
                    "min": str(parsed[0]),
                    "max": str(parsed[-1]),
                }
                threshold = _dt.timedelta(hours=args.datetime_gap_hours)
                gaps = 0
                for i in range(1, len(parsed)):
                    if parsed[i] - parsed[i - 1] > threshold:
                        gaps += 1
                if gaps > 0:
                    issues.append({
                        "severity": SEVERITY_WARN,
                        "rule": "datetime_gap",
                        "column": col,
                        "message": (
                            f"Column '{col}' has {gaps} gap(s) greater "
                            f"than {args.datetime_gap_hours}h between consecutive sorted timestamps."
                        ),
                    })

        col_results[col] = col_res

    seen_rows = set()
    duplicates = 0
    for r in rows:
        key = tuple(r)
        if key in seen_rows:
            duplicates += 1
        else:
            seen_rows.add(key)
    row_level = {
        "rows": n_rows,
        "columns": len(headers),
        "duplicate_rows": duplicates,
        "memory_bytes": None,
    }
    if duplicates > 0:
        issues.append({
            "severity": SEVERITY_WARN,
            "rule": "duplicate_rows",
            "column": None,
            "message": f"Found {duplicates} fully duplicated rows across all columns.",
        })

    if args.primary_key:
        pk_cols = [c.strip() for c in args.primary_key.split(",") if c.strip()]
        missing = [c for c in pk_cols if c not in headers]
        if missing:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "pk_missing_columns",
                "column": None,
                "message": f"Primary key columns not found: {', '.join(missing)}",
            })
        else:
            pk_idx = [headers.index(c) for c in pk_cols]
            seen_pk = set()
            dup_pk = 0
            for r in rows:
                key = tuple(r[i] if i < len(r) else "" for i in pk_idx)
                if key in seen_pk:
                    dup_pk += 1
                else:
                    seen_pk.add(key)
            if dup_pk > 0:
                issues.append({
                    "severity": SEVERITY_ERROR,
                    "rule": "pk_not_unique",
                    "column": ",".join(pk_cols),
                    "message": f"Primary key ({', '.join(pk_cols)}) has {dup_pk} duplicate values.",
                })
            else:
                issues.append({
                    "severity": SEVERITY_INFO,
                    "rule": "pk_unique",
                    "column": ",".join(pk_cols),
                    "message": f"Primary key ({', '.join(pk_cols)}) is unique.",
                })

    return {"columns": col_results, "rows": row_level}, issues


def apply_range_checks_stdlib(headers: List[str], rows: List[List[str]], args: argparse.Namespace) -> List[Dict]:
    issues: List[Dict] = []
    for spec in args.range:
        parts = spec.split(":")
        if len(parts) != 3:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "range_config_error",
                "column": None,
                "message": f"Invalid --range spec '{spec}'. Expected COL:MIN:MAX.",
            })
            continue
        col, lo, hi = parts
        if col not in headers:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "range_column_missing",
                "column": col,
                "message": f"--range column '{col}' not found in dataset.",
            })
            continue
        try:
            lo_f = float(lo)
            hi_f = float(hi)
        except ValueError:
            issues.append({
                "severity": SEVERITY_ERROR,
                "rule": "range_config_error",
                "column": col,
                "message": f"--range bounds for '{col}' are not numeric: lo={lo}, hi={hi}.",
            })
            continue
        idx = headers.index(col)
        n_low = n_high = 0
        for row in rows:
            v = row[idx] if idx < len(row) else ""
            if is_null_value(v):
                continue
            try:
                x = float(v)
            except ValueError:
                continue
            if x < lo_f:
                n_low += 1
            elif x > hi_f:
                n_high += 1
        if n_low or n_high:
            issues.append({
                "severity": SEVERITY_WARN,
                "rule": "range_violation",
                "column": col,
                "message": (
                    f"Column '{col}' has {n_low} value(s) below min={lo_f} and "
                    f"{n_high} value(s) above max={hi_f}."
                ),
            })
    return issues


def print_human(result: Dict, issues: List[Dict]) -> None:
    rows = result["rows"]
    print("DATA QUALITY SUMMARY")
    print("=" * 72)
    print(f"Rows          : {rows['rows']}")
    print(f"Columns       : {rows['columns']}")
    print(f"Duplicate rows: {rows['duplicate_rows']}")
    if rows.get("memory_bytes") is not None:
        mb = rows["memory_bytes"] / (1024 * 1024)
        print(f"Memory (est.) : {mb:.2f} MB")
    print()

    col_names = list(result["columns"].keys())
    headers = ["column", "dtype", "non_null", "nulls", "completeness", "unique%", "outliers"]
    widths = [max(len(h), 8) for h in headers]

    str_rows = []
    for col in col_names:
        c = result["columns"][col]
        outliers = c.get("outliers", {}).get("count", "-")
        row_str = [
            col,
            c.get("dtype", "-"),
            str(c["non_null"]),
            str(c["nulls"]),
            f"{c['completeness']*100:.1f}%",
            f"{c['unique_ratio']*100:.1f}%",
            str(outliers),
        ]
        str_rows.append(row_str)
        for i in range(len(headers)):
            widths[i] = max(widths[i], len(row_str[i]))

    def fmt_row(cells):
        return " | ".join(str(cells[i]).ljust(widths[i]) for i in range(len(headers)))
    sep = "-+-".join("-" * w for w in widths)
    print(fmt_row(headers))
    print(sep)
    for r in str_rows:
        print(fmt_row(r))

    print()
    print("ISSUES")
    print("=" * 72)
    if not issues:
        print("(no issues)")
    else:
        for iss in issues:
            col = f" [{iss.get('column')}]" if iss.get("column") else ""
            print(f"[{iss['severity']}] {{{iss['rule']}}}{col}: {iss['message']}")


def main(argv: Optional[List[str]] = None) -> int:
    args = load_args(argv)
    path = Path(args.path).resolve()
    if not path.is_file():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 2

    fmt = detect_format(path, args.format)

    if fmt == "parquet" and not HAS_PANDAS:
        print("ERROR: Parquet format requires pandas+pyarrow. Install pandas or use CSV.", file=sys.stderr)
        return 2

    issues: List[Dict] = []
    result: Dict[str, Any] = {}

    if HAS_PANDAS:
        df = load_data_pandas(path, fmt, args)
        result, compute_issues = compute_stats_pandas(df, args)
        issues.extend(compute_issues)
        issues.extend(apply_range_checks_pandas(df, args))
    else:
        if fmt != "csv":
            print("WARNING: pandas not installed; forcing CSV fallback parsing.", file=sys.stderr)
        headers, rows = load_data_csv_stdlib(path, args)
        result, compute_issues = compute_stats_csv_stdlib(headers, rows, args)
        issues.extend(compute_issues)
        issues.extend(apply_range_checks_stdlib(headers, rows, args))

    errors = [i for i in issues if i["severity"] == SEVERITY_ERROR]
    warnings = [i for i in issues if i["severity"] == SEVERITY_WARN]
    infos = [i for i in issues if i["severity"] == SEVERITY_INFO]

    if args.json:
        payload = {
            "file": str(path),
            "format": fmt,
            "pandas_available": HAS_PANDAS,
            "result": result,
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
        }
        print(_json.dumps(payload, indent=2, default=str))
    else:
        print(f"File            : {path}")
        print(f"Format          : {fmt}")
        print(f"Pandas available: {HAS_PANDAS}")
        print()
        print_human(result, issues)
        print()
        print("=" * 72)
        print(f"Errors   : {len(errors)}")
        print(f"Warnings : {len(warnings)}")
        print(f"Info     : {len(infos)}")
        print("=" * 72)

    strict = args.strict or args.fail_on_warnings
    fatal = len(errors) > 0 or (strict and len(warnings) > 0)
    if fatal:
        if not args.json:
            print("RESULT: FAIL")
        return 1
    if not args.json:
        print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
