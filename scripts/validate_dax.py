#!/usr/bin/env python3
"""
validate_dax.py - DAX (Data Analysis Expressions) static analysis validator.

Scans .dax files, .pbip extracts (json/text), or any text file containing DAX
expressions. Detects common DAX anti-patterns, measure naming, and best
practice violations.

Checks performed:
- Unbalanced parentheses (ERROR, reliable syntax check)
- Nested IF inside CALCULATE (WARN heuristic)
- ALLSELECTED misuse heuristic (WARN)
- FILTER(ALL(...)) where ALLEXCEPT / ALLSELECTED / REMOVEFILTERS may be better (WARN)
- SUMX(Table, Table[Column]) potential SUM() simplification (WARN heuristic)
- CALCULATE(COUNTROWS(Table), ...) pattern note (INFO)
- IF(VALUES(Col) = X, A, B) instead of SELECTEDVALUE (WARN heuristic)
- Missing DIVIDE function (WARN)
- CALCULATE + IF pattern instead of CALCULATE with filter (WARN heuristic)
- Measure name format (optional: PascalCase) (WARN)
- EARLIER usage (WARN: variables preferred, EARLIER remains valid DAX)
- Excessive use of nested CALCULATE (WARN)

LIMITATIONS:
  This validator uses regex heuristics. It cannot parse DAX semantics;
  it flags common patterns for human review and cannot determine correctness.
  Heuristic (WARN) findings require a human reviewer to assess whether the
  flagged pattern is semantically required in the specific context.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple


SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"


MEASURE_DEF_RE = re.compile(
    r'(?P<name>[A-Za-z_][A-Za-z0-9_ ]*?)\s*:?=\s*(?P<body>CALCULATE\b|SUMX\b|SUM\b|COUNTROWS\b|IF\b|CALCULATETABLE\b|ADDCOLUMNS\b|SUMMARIZE\b|VAR\b|RETURN\b|EVALUATE\b|DEFINE\b|SELECTEDVALUE\b|DIVIDE\b|[A-Za-z_])',
    re.IGNORECASE | re.DOTALL,
)

NESTED_IF_IN_CALCULATE_RE = re.compile(
    r'CALCULATE\s*\(\s*IF\s*\(',
    re.IGNORECASE | re.DOTALL,
)

CALCULATE_IF_FILTER_RE = re.compile(
    r'CALCULATE\s*\(\s*[A-Za-z_][A-Za-z0-9_\.\[\]]*\s*,\s*IF\s*\(',
    re.IGNORECASE | re.DOTALL,
)

ALLSELECTED_OUTSIDE_CALC_RE = re.compile(
    r'ALLSELECTED\s*\(',
    re.IGNORECASE,
)

FILTER_ALL_RE = re.compile(
    r'FILTER\s*\(\s*ALL\s*\(',
    re.IGNORECASE | re.DOTALL,
)

SUMX_SIMPLE_RE = re.compile(
    r'SUMX\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*,\s*([A-Za-z_][A-Za-z0-9_\.]*\s*\[[^\]]+\])\s*\)',
    re.IGNORECASE | re.DOTALL,
)

CALC_COUNTROWS_RE = re.compile(
    r'CALCULATE\s*\(\s*COUNTROWS\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*\)\s*,',
    re.IGNORECASE | re.DOTALL,
)

IF_VALUES_RE = re.compile(
    r'IF\s*\(\s*VALUES\s*\(\s*[A-Za-z_][A-Za-z0-9_\.]*\s*\[[^\]]+\]\s*\)\s*=',
    re.IGNORECASE | re.DOTALL,
)

DIVIDE_MISSING_RE = re.compile(
    r'(?<![A-Za-z0-9_])(?:[A-Za-z_][A-Za-z0-9_\.]*\[[^\]]+\]|COUNTROWS\s*\([^)]*\)|SUM\s*\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*/\s*',
    re.IGNORECASE,
)

EARLIER_RE = re.compile(r'\bEARLIER\s*\(', re.IGNORECASE)

NESTED_CALCULATE_RE = re.compile(
    r'CALCULATE\s*\([^)]*CALCULATE\s*\(',
    re.IGNORECASE | re.DOTALL,
)

PASCAL_CASE_RE = re.compile(r'^[A-Z][A-Za-z0-9]*$')


class Issue:
    __slots__ = ("severity", "rule", "message", "file", "line", "measure")

    def __init__(
        self,
        severity: str,
        rule: str,
        message: str,
        file: str = "",
        line: int = 0,
        measure: str = "",
    ):
        self.severity = severity
        self.rule = rule
        self.message = message
        self.file = file
        self.line = line
        self.measure = measure


def load_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run static analysis checks on DAX code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
LIMITATIONS:
  This validator uses regex heuristics. It cannot parse DAX semantics;
  it flags common patterns for human review and cannot determine correctness.
  Heuristic (WARN) findings require a human reviewer to assess whether the
  flagged pattern is semantically required in the specific context.
  ERROR-level findings are limited to regex-detectable syntactic impossibilities
  (e.g., unbalanced parentheses).

Severity levels:
  ERROR  — reliable regex-detected syntax impossibility; review required.
  WARN   — heuristic pattern flag; may be intentional in context. Review.
  INFO   — informational note or alternative pattern suggestion.

Examples:
  python validate_dax.py measures.dax
  python validate_dax.py ./dax_models/ --strict
  python validate_dax.py model.bim --format auto
  python validate_dax.py measures.dax --disable sumx_suggestion,divide_missing
  python validate_dax.py measures.dax --naming PascalCase
""",
    )
    parser.add_argument(
        "path",
        help="DAX file (.dax), Power BI extract (.pbip/.bim/.json), or directory to scan",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit on warnings)",
    )
    parser.add_argument(
        "--disable",
        default="",
        help="Comma-separated list of rule IDs to disable",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "dax", "json", "text"],
        default="auto",
        help="How to parse input (default: auto by extension)",
    )
    parser.add_argument(
        "--naming",
        choices=["PascalCase", "any"],
        default="any",
        help="Measure naming convention to enforce (default: any)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human-readable",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include INFO level output",
    )
    return parser.parse_args(argv)


def find_dax_files(target: str) -> List[Path]:
    p = Path(target).resolve()
    if not p.exists():
        print(f"ERROR: Path does not exist: {p}", file=sys.stderr)
        sys.exit(2)
    if p.is_file():
        return [p]
    supported = {".dax", ".pbip", ".bim", ".json", ".txt", ".md"}
    files = []
    for f in p.rglob("*"):
        if f.is_file() and f.suffix.lower() in supported:
            files.append(f)
    return sorted(files)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def strip_dax_comments(text: str) -> str:
    text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'--.*?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text


def extract_measure_definitions(text: str) -> List[Tuple[str, str, int]]:
    """Return list of (measure_name, body_snippet, start_line) heuristically."""
    measures = []
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_ ]*?)\s*:?=\s*(.+)$', line)
        if m:
            name = m.group(1).strip()
            body = m.group(2).strip()
            measures.append((name, body, idx + 1))
    return measures


def parse_format(path: Path, fmt: str) -> str:
    if fmt != "auto":
        return fmt
    ext = path.suffix.lower()
    if ext in {".dax"}:
        return "dax"
    if ext in {".json", ".bim", ".pbip"}:
        return "json"
    return "text"


def extract_dax_from_json(raw: str) -> List[str]:
    """Extract string snippets that look like DAX from JSON text.

    Heuristic: any long JSON string value containing common DAX keywords.
    """
    dax_snippets: List[str] = []
    try:
        data = json.loads(raw)
        def walk(node):
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
            elif isinstance(node, str):
                s = node
                if len(s) > 20 and re.search(r'\b(CALCULATE|SUMX|COUNTROWS|DIVIDE|SELECTEDVALUE|SUMMARIZE|ADDCOLUMNS)\b', s, re.IGNORECASE):
                    dax_snippets.append(s)
        walk(data)
    except json.JSONDecodeError:
        pass
    if not dax_snippets:
        matches = re.findall(r'"expression"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        for m in matches:
            s = bytes(m, "utf-8").decode("unicode_escape")
            dax_snippets.append(s)
    return dax_snippets


def check_unbalanced_parens(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    stripped_no_strings = re.sub(r'"[^"]*"', '""', text)
    open_count = stripped_no_strings.count("(")
    close_count = stripped_no_strings.count(")")
    diff = open_count - close_count
    if diff != 0:
        direction = "more opening" if diff > 0 else "more closing"
        issues.append(Issue(
            SEVERITY_ERROR,
            "unbalanced_parentheses",
            f"Unbalanced parentheses detected: {abs(diff)} {direction} than closing "
            f"(open={open_count}, close={close_count}). This is a syntax error that must be fixed.",
            file_ref,
            0,
            measure,
        ))


def check_nested_if_in_calculate(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in NESTED_IF_IN_CALCULATE_RE.finditer(text):
        issues.append(Issue(
            SEVERITY_WARN,
            "nested_if_in_calculate",
            "[WARN] Potential CALCULATE+IF nesting. Review: consider moving conditional logic "
            "into a CALCULATE filter argument or using SWITCH/SELECTEDVALUE for clarity. "
            "Current pattern may trigger eager evaluation of both branches.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_calculate_if_filter(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in CALCULATE_IF_FILTER_RE.finditer(text):
        issues.append(Issue(
            SEVERITY_WARN,
            "calculate_if_filter",
            "[WARN] Potential CALCULATE filter optimization review. IF(...) used as a CALCULATE "
            "filter argument. Prefer CALCULATE(<measure>, <condition>) or "
            "CALCULATE(<measure>, KEEPFILTERS(...)) when semantically equivalent, to "
            "leverage storage-engine optimization. Review if IF is semantically required.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_allselected(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in ALLSELECTED_OUTSIDE_CALC_RE.finditer(text):
        start = m.start()
        pre = text[max(0, start - 200):start]
        if re.search(r'CALCULATE\s*\(\s*[A-Za-z_][A-Za-z0-9_\.\[\],\s]*\Z', pre, re.IGNORECASE | re.DOTALL):
            continue
        if re.search(r'CALCULATE\s*\(\s*\Z', pre, re.IGNORECASE | re.DOTALL):
            continue
        issues.append(Issue(
            SEVERITY_WARN,
            "allselected_usage",
            "[WARN] Potential ALLSELECTED misuse. ALLSELECTED() detected outside a typical "
            "CALCULATE modifier position. ALLSELECTED has complex shadow-filter behavior; "
            "consider REMOVEFILTERS or ALLEXCEPT if the sole intent is removing filters. "
            "Review: ALLSELECTED may be intentionally used for visual totals.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_filter_all(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in FILTER_ALL_RE.finditer(text):
        issues.append(Issue(
            SEVERITY_WARN,
            "filter_all",
            "[WARN] Potential FILTER(ALL) simplification. FILTER(ALL(...)) detected. This "
            "materializes the full table into memory before filtering. Review: when the intent is "
            "only to remove/modify filters (not iterate the table), consider ALLEXCEPT, "
            "ALL(<col>), REMOVEFILTERS, or KEEPFILTERS. FILTER(ALL) may be "
            "intentionally used when custom row-level logic is required.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_sumx_simple(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in SUMX_SIMPLE_RE.finditer(text):
        table = m.group(1)
        col_expr = m.group(2).strip()
        col_part = col_expr.split("[")[0].strip() if "[" in col_expr else ""
        if col_part and col_part.lower() == table.lower():
            issues.append(Issue(
                SEVERITY_WARN,
                "sumx_suggestion",
                f"[WARN] Potential SUMX simplification. SUMX({table}, {col_expr}) iterates "
                "a table just to sum a single column. Review whether row context or "
                "expression semantics require SUMX; otherwise SUM() is sufficient: "
                f"SUM({col_expr}). SUMX may be intentionally retained for codebase pattern "
                "consistency or context transition.",
                file_ref,
                line_of(text, m.start()),
                measure,
            ))


def check_calc_countrows(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in CALC_COUNTROWS_RE.finditer(text):
        table = m.group(1)
        issues.append(Issue(
            SEVERITY_INFO,
            "calculate_countrows",
            f"[INFO] CALCULATE(COUNTROWS({table}), ...) pattern detected. Prefer "
            f"COUNTROWS(FILTER({table}, ...)) when filters modify the table directly, "
            f"or leave as-is if CALCULATE removes external filters intentionally.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_if_values(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in IF_VALUES_RE.finditer(text):
        issues.append(Issue(
            SEVERITY_WARN,
            "if_values",
            "[WARN] Potential SELECTEDVALUE replacement. IF(VALUES(Column) = value, ...) pattern "
            "detected. Review IF/VALUES may not handle multi-value filter context safely. "
            "Consider SELECTEDVALUE(Column, default) or HASONEVALUE + VALUES for explicit "
            "multi-value guard. IF/VALUES may be required in edge cases.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_divide_missing(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in DIVIDE_MISSING_RE.finditer(text):
        issues.append(Issue(
            SEVERITY_WARN,
            "divide_missing",
            "[WARN] Division operator review. Use of '/' without DIVIDE detected. If denominator "
            "is 0 or BLANK the result is NaN/Infinity or unexpected BLANK. Prefer "
            "DIVIDE(numerator, denominator, alternateResult) for safe division. Review "
            "if denominator is provably non-zero from upstream constraints.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))
        break


def check_earlier(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in EARLIER_RE.finditer(text):
        issues.append(Issue(
            SEVERITY_WARN,
            "earlier_usage",
            "[WARN] EARLIER review. EARLIER() detected: variables are almost always preferred "
            "over EARLIER for readability. EARLIER remains valid DAX. EARLIER/EARLIEST "
            "access an outer row context; variables (VAR x = <expr> outside the inner "
            "iterator) achieve the same result and are clearer. Review and consider a "
            "variable-based replacement before committing.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_nested_calculate(text: str, file_ref: str, measure: str, issues: List[Issue]) -> None:
    for m in NESTED_CALCULATE_RE.finditer(text):
        issues.append(Issue(
            SEVERITY_WARN,
            "nested_calculate",
            "[WARN] Nested CALCULATE review. Nested CALCULATE(CALCULATE(...)) detected. Verify "
            "filter semantics are intended. Prefer combining filter arguments in a single "
            "CALCULATE when semantically equivalent. Nested CALCULATE may be intentionally "
            "used to create specific filter-context layering.",
            file_ref,
            line_of(text, m.start()),
            measure,
        ))


def check_measure_naming(measures: List[Tuple[str, str, int]], file_ref: str, convention: str, issues: List[Issue]) -> None:
    if convention == "any":
        return
    for name, _body, line in measures:
        compact = name.replace(" ", "")
        if not PASCAL_CASE_RE.match(compact):
            issues.append(Issue(
                SEVERITY_WARN,
                "measure_naming",
                f"Measure name '{name}' does not follow {convention} convention "
                f"(e.g. TotalSales, AvgDiscount).",
                file_ref,
                line,
                name,
            ))


def analyze_text(full_text: str, file_ref: str, disabled: Set[str], naming: str) -> List[Issue]:
    issues: List[Issue] = []
    stripped = strip_dax_comments(full_text)
    measures = extract_measure_definitions(full_text)

    if "unbalanced_parentheses" not in disabled:
        check_unbalanced_parens(stripped, file_ref, "(global)", issues)

    if "measure_naming" not in disabled:
        check_measure_naming(measures, file_ref, naming, issues)

    for name, body, line in measures:
        body_stripped = strip_dax_comments(body)
        if "nested_if_in_calculate" not in disabled:
            check_nested_if_in_calculate(body_stripped, file_ref, name, issues)
        if "calculate_if_filter" not in disabled:
            check_calculate_if_filter(body_stripped, file_ref, name, issues)
        if "allselected_usage" not in disabled:
            check_allselected(body_stripped, file_ref, name, issues)
        if "filter_all" not in disabled:
            check_filter_all(body_stripped, file_ref, name, issues)
        if "sumx_suggestion" not in disabled:
            check_sumx_simple(body_stripped, file_ref, name, issues)
        if "calculate_countrows" not in disabled:
            check_calc_countrows(body_stripped, file_ref, name, issues)
        if "if_values" not in disabled:
            check_if_values(body_stripped, file_ref, name, issues)
        if "divide_missing" not in disabled:
            check_divide_missing(body_stripped, file_ref, name, issues)
        if "earlier_usage" not in disabled:
            check_earlier(body_stripped, file_ref, name, issues)
        if "nested_calculate" not in disabled:
            check_nested_calculate(body_stripped, file_ref, name, issues)

    # If no measure definitions were found (e.g. raw expression file), check the whole file
    if not measures:
        name = "(global)"
        if "nested_if_in_calculate" not in disabled:
            check_nested_if_in_calculate(stripped, file_ref, name, issues)
        if "calculate_if_filter" not in disabled:
            check_calculate_if_filter(stripped, file_ref, name, issues)
        if "allselected_usage" not in disabled:
            check_allselected(stripped, file_ref, name, issues)
        if "filter_all" not in disabled:
            check_filter_all(stripped, file_ref, name, issues)
        if "sumx_suggestion" not in disabled:
            check_sumx_simple(stripped, file_ref, name, issues)
        if "calculate_countrows" not in disabled:
            check_calc_countrows(stripped, file_ref, name, issues)
        if "if_values" not in disabled:
            check_if_values(stripped, file_ref, name, issues)
        if "divide_missing" not in disabled:
            check_divide_missing(stripped, file_ref, name, issues)
        if "earlier_usage" not in disabled:
            check_earlier(stripped, file_ref, name, issues)
        if "nested_calculate" not in disabled:
            check_nested_calculate(stripped, file_ref, name, issues)

    return issues


def analyze_file(path: Path, args: argparse.Namespace, disabled: Set[str]) -> List[Issue]:
    issues: List[Issue] = []
    fmt = parse_format(path, args.format)

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        issues.append(Issue(SEVERITY_ERROR, "io", f"Cannot read file: {e}", str(path), 0, ""))
        return issues

    file_ref = str(path)

    if fmt == "json":
        snippets = extract_dax_from_json(raw)
        if not snippets:
            issues.append(Issue(
                SEVERITY_INFO,
                "parse",
                f"No DAX expressions extracted from JSON file {path.name}. Review file contents manually.",
                file_ref,
                0,
                "",
            ))
        for i, snippet in enumerate(snippets, start=1):
            sub_issues = analyze_text(snippet, f"{file_ref}#snippet{i}", disabled, args.naming)
            issues.extend(sub_issues)
    else:
        issues.extend(analyze_text(raw, file_ref, disabled, args.naming))

    return issues


def print_human(issues: List[Issue], verbose: bool) -> None:
    for i in issues:
        if i.severity == SEVERITY_INFO and not verbose:
            continue
        loc = ""
        if i.file:
            loc = i.file
            if i.line:
                loc += f":{i.line}"
        measure = f" ({i.measure})" if i.measure else ""
        print(f"[{i.severity}] {{{i.rule}}}{measure} {loc} - {i.message}")


def print_json(issues: List[Issue]) -> None:
    import json as _json
    out = []
    for i in issues:
        out.append({
            "severity": i.severity,
            "rule": i.rule,
            "file": i.file,
            "line": i.line,
            "measure": i.measure,
            "message": i.message,
        })
    print(_json.dumps({"issues": out, "count": len(out)}, indent=2))


def main(argv: Optional[List[str]] = None) -> int:
    args = load_args(argv)
    disabled = {x.strip() for x in args.disable.split(",") if x.strip()}

    files = find_dax_files(args.path)
    if not files:
        print("ERROR: No supported DAX/JSON/text files found at given path.", file=sys.stderr)
        return 2

    all_issues: List[Issue] = []
    for f in files:
        all_issues.extend(analyze_file(f, args, disabled))

    errors = [i for i in all_issues if i.severity == SEVERITY_ERROR]
    warnings = [i for i in all_issues if i.severity == SEVERITY_WARN]
    infos = [i for i in all_issues if i.severity == SEVERITY_INFO]

    if args.json:
        print_json(all_issues)
    else:
        print(f"Validating {len(files)} DAX/JSON/text file(s)...")
        print()
        print_human(all_issues, args.verbose)
        print()
        print("=" * 72)
        print(f"Files analyzed : {len(files)}")
        print(f"Errors         : {len(errors)}")
        print(f"Warnings       : {len(warnings)}")
        if args.verbose:
            print(f"Info           : {len(infos)}")
        print("=" * 72)

    show_limitations = args.verbose or len(warnings) > 0
    if not args.json and show_limitations:
        print()
        print("LIMITATIONS:")
        print("  This validator uses regex heuristics. It cannot parse DAX semantics;")
        print("  it flags common patterns for human review and cannot determine correctness.")
        print("  WARN-level findings are heuristics — they may be intentionally required")
        print("  in the specific context (e.g. CALCULATE context transition inside an")
        print("  iterator, SUMX used for deliberate row-context semantics, ALLSELECTED")
        print("  for visual-total logic). Every WARN requires a human reviewer to assess.")
        print("  ERROR-level findings are limited to regex-detectable syntactic issues.")

    fatal = len(errors) > 0 or (args.strict and len(warnings) > 0)
    if fatal:
        if not args.json:
            print("RESULT: FAIL")
        return 1
    if not args.json:
        print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
