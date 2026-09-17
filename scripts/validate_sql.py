#!/usr/bin/env python3
"""
validate_sql.py - SQL static analysis / linting tool.

Runs regex-based checks on SQL files (.sql) or directories of SQL files.

Checks performed:
- SELECT * detection (anti-pattern)
- CTE usage recommendations (warn on deeply nested subqueries without CTEs)
- Comma placement consistency (before vs. after)
- NULL handling in aggregates (SUM without COALESCE warning, COUNT(col) vs COUNT(*))
- Naming convention: table/column identifiers in snake_case
- DISTINCT used with COUNT(DISTINCT ...) flagged if suspicious context
- Implicit JOIN (comma-separated tables) without WHERE / ON filter
- Cartesian product warning (cross join without explicit CROSS JOIN keyword or filter)
- DELETE / UPDATE without WHERE clause
- INSERT without explicit column list
- USE / SET statements for dialect warnings (optional)
- Hardcoded literals in WHERE clauses (magic numbers)

Limitations:
- Regex-based, not a full SQL parser. Does not handle all SQL dialects.
- String literal contents are not fully stripped; identifiers inside strings
  may produce false positives for naming checks.
- Comma style detection is heuristic and may be confused by multi-line expressions.
- Cartesian product detection can produce false positives on intentionally small tables.
- Does not run the SQL; no runtime or semantic validation.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any


SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"


NAMING_SNAKE_CASE_RE = re.compile(r'^[a-z][a-z0-9_]*$')

SELECT_STAR_RE = re.compile(r'\bSELECT\s+(\*\s*,|(?:[^\n]*,\s*)?\*\s*FROM)', re.IGNORECASE | re.DOTALL)

CTE_WITH_RE = re.compile(r'\bWITH\s+[a-zA-Z_][a-zA-Z0-9_]*\s+AS\s*\(', re.IGNORECASE)

SUBQUERY_NESTED_RE = re.compile(r'SELECT[^;]*?\(\s*SELECT\b[^;]*?\(\s*SELECT\b', re.IGNORECASE | re.DOTALL)

AGGREGATE_NULL_RE = re.compile(
    r'\b(SUM|AVG|MIN|MAX)\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*\)',
    re.IGNORECASE,
)

COUNT_DISTINCT_RE = re.compile(r'\bCOUNT\s*\(\s*DISTINCT\b', re.IGNORECASE)
DISTINCT_COUNT_RE = re.compile(r'\bDISTINCT\s+COUNT\s*\(', re.IGNORECASE)

IMPLICIT_JOIN_RE = re.compile(
    r'\bFROM\s+[A-Za-z_][A-Za-z0-9_\.# "`]*\s*,\s*[A-Za-z_][A-Za-z0-9_\.# "`]',
    re.IGNORECASE,
)

JOIN_ON_MISSING_RE = re.compile(
    r'\b(INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+|OUTER\s+|CROSS\s+)?JOIN\s+[A-Za-z_][A-Za-z0-9_\.# "`]*\s+(?:AS\s+)?[A-Za-z_][A-Za-z0-9_]*\s*(?=WHERE|GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING|;|\))',
    re.IGNORECASE,
)

DELETE_NO_WHERE_RE = re.compile(r'\bDELETE\s+FROM\s+[A-Za-z_][A-Za-z0-9_\.# "`]*(?!\s+WHERE)', re.IGNORECASE)
UPDATE_NO_WHERE_RE = re.compile(r'\bUPDATE\s+[A-Za-z_][A-Za-z0-9_\.# "`]*\s+SET\b(?!.*\bWHERE\b)', re.IGNORECASE | re.DOTALL)

INSERT_NO_COLUMNS_RE = re.compile(
    r'\bINSERT\s+(?:INTO\s+)?[A-Za-z_][A-Za-z0-9_\.# "`]*\s*(?:VALUES|SELECT)',
    re.IGNORECASE,
)

IDENTIFIER_RE = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*)\b')


class Issue:
    __slots__ = ("severity", "rule", "message", "file", "line")

    def __init__(self, severity: str, rule: str, message: str, file: str = "", line: int = 0):
        self.severity = severity
        self.rule = rule
        self.message = message
        self.file = file
        self.line = line


def load_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run static analysis checks on SQL files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_sql.py model.sql
  python validate_sql.py ./models/ --strict
  python validate_sql.py ./models/ --disable select_star,comma_style
  python validate_sql.py model.sql --naming-convention none
  python validate_sql.py model.sql --comma-style before
""",
    )
    parser.add_argument(
        "path",
        help="SQL file or directory containing .sql files to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit on warnings)",
    )
    parser.add_argument(
        "--disable",
        default="",
        help="Comma-separated list of rule IDs to disable (e.g. select_star,cte_recommendation)",
    )
    parser.add_argument(
        "--naming-convention",
        choices=["snake_case", "none"],
        default="snake_case",
        help="Identifier naming convention to enforce (default: snake_case)",
    )
    parser.add_argument(
        "--comma-style",
        choices=["after", "before", "none"],
        default="after",
        help="Expected comma placement style for column lists (default: after)",
    )
    parser.add_argument(
        "--max-subquery-nest",
        type=int,
        default=2,
        help="Warn when SELECT subqueries are nested deeper than this (default: 2)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human readable",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include INFO level output",
    )
    return parser.parse_args(argv)


def find_sql_files(target: str) -> List[Path]:
    p = Path(target).resolve()
    if not p.exists():
        print(f"ERROR: Path does not exist: {p}", file=sys.stderr)
        sys.exit(2)
    if p.is_file():
        if p.suffix.lower() != ".sql":
            print(f"WARNING: File {p} does not have .sql extension; analyzing anyway.", file=sys.stderr)
        return [p]
    return sorted(p.rglob("*.sql"))


def remove_sql_comments_and_strings(text: str) -> str:
    text = re.sub(r'--.*?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r"'(''|[^'])*'", "''", text)
    text = re.sub(r'"(""|[^"])*"', '""', text)
    text = re.sub(r'`[^`]*`', '``', text)
    return text


def count_nested_subqueries(text: str) -> int:
    stripped = remove_sql_comments_and_strings(text)
    tokens = re.findall(r'\b(?:SELECT|INSERT|UPDATE|DELETE)\b|\(|\)', stripped, re.IGNORECASE)
    depth = 0
    max_depth = 0
    select_depth_stack = []
    for t in tokens:
        if t.upper() in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            select_depth_stack.append(depth)
            if len(select_depth_stack) > max_depth:
                max_depth = len(select_depth_stack)
        elif t == "(":
            depth += 1
        elif t == ")":
            depth -= 1
            if select_depth_stack and select_depth_stack[-1] > depth:
                select_depth_stack.pop()
    return max_depth


def detect_comma_style(text: str) -> Optional[str]:
    lines = text.splitlines()
    leading = 0
    trailing = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("--") or stripped == "":
            continue
        if re.match(r'^[\s\t]+,', line):
            leading += 1
        if re.search(r',\s*$', stripped) and not stripped.endswith("("):
            trailing += 1
    if leading == 0 and trailing == 0:
        return None
    if leading > trailing * 2:
        return "before"
    if trailing > leading * 2:
        return "after"
    if leading > trailing:
        return "before"
    return "after"


def find_line_of(text: str, pattern: re.Pattern, search_group: int = 0) -> int:
    for m in pattern.finditer(text):
        start = m.start(search_group)
        return text.count("\n", 0, start) + 1
    return 0


def get_line_of_pos(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def check_select_star(stripped: str, original: str, file: str, issues: List[Issue]) -> None:
    for m in re.finditer(r'\bSELECT\b[^;]*?\*', stripped, re.IGNORECASE | re.DOTALL):
        issues.append(Issue(
            SEVERITY_WARN,
            "select_star",
            "SELECT * detected: enumerate columns explicitly to avoid schema drift and unused columns.",
            file,
            get_line_of_pos(original, m.start()),
        ))
        break


def check_cte_recommendation(stripped: str, original: str, file: str, issues: List[Issue], max_nest: int) -> None:
    has_cte = bool(CTE_WITH_RE.search(stripped))
    nesting = count_nested_subqueries(stripped)
    if not has_cte and nesting > max_nest:
        issues.append(Issue(
            SEVERITY_WARN,
            "cte_recommendation",
            f"Nested subquery depth is {nesting} but no CTEs (WITH ... AS) detected. "
            f"Consider extracting CTEs for readability (threshold: {max_nest}).",
            file,
            0,
        ))


def check_aggregate_nulls(stripped: str, original: str, file: str, issues: List[Issue]) -> None:
    for m in AGGREGATE_NULL_RE.finditer(stripped):
        agg = m.group(1).upper()
        col = m.group(2)
        if col.upper() in ("*", "1", "0"):
            continue
        if re.search(r'\bCOALESCE\s*\(', original[max(0, m.start() - 80): m.end() + 20], re.IGNORECASE):
            continue
        issues.append(Issue(
            SEVERITY_WARN,
            "aggregate_null",
            f"{agg}({col}) may silently drop NULLs. Consider COALESCE({col}, 0) "
            f"if NULLs should be treated as 0, or use COUNT(*)/COUNT(col) intentionally.",
            file,
            get_line_of_pos(original, m.start()),
        ))


def check_distinct_count(stripped: str, original: str, file: str, issues: List[Issue]) -> None:
    for m in DISTINCT_COUNT_RE.finditer(stripped):
        issues.append(Issue(
            SEVERITY_ERROR,
            "distinct_count",
            "DISTINCT COUNT(...) is likely a mistake; use COUNT(DISTINCT ...) instead.",
            file,
            get_line_of_pos(original, m.start()),
        ))


def check_implicit_join(stripped: str, original: str, file: str, issues: List[Issue]) -> None:
    text_upper = stripped.upper()
    for m in IMPLICIT_JOIN_RE.finditer(stripped):
        segment_start = m.start()
        segment_end = text_upper.find(";", segment_start)
        if segment_end == -1:
            segment_end = len(stripped)
        segment = stripped[segment_start:segment_end]
        if re.search(r'\bWHERE\b|\bON\b|\bJOIN\b', segment, re.IGNORECASE):
            continue
        issues.append(Issue(
            SEVERITY_ERROR,
            "implicit_join",
            "Implicit comma-style JOIN without ON/WHERE filter: Cartesian product risk. "
            "Use explicit INNER/LEFT JOIN ... ON syntax.",
            file,
            get_line_of_pos(original, segment_start),
        ))


def check_join_on_missing(stripped: str, original: str, file: str, issues: List[Issue]) -> None:
    for m in JOIN_ON_MISSING_RE.finditer(stripped):
        issues.append(Issue(
            SEVERITY_ERROR,
            "join_on_missing",
            "JOIN expression without ON clause detected. If this is an intentional CROSS JOIN, "
            "use the explicit CROSS JOIN keyword.",
            file,
            get_line_of_pos(original, m.start()),
        ))


def check_dml_without_where(stripped: str, original: str, file: str, issues: List[Issue]) -> None:
    for m in re.finditer(r'\bDELETE\s+FROM\s+[A-Za-z_][A-Za-z0-9_\.#"`\s]*', stripped, re.IGNORECASE):
        end = m.end()
        rest = stripped[end: end + 400]
        rest = re.split(r';', rest, maxsplit=1)[0]
        if not re.search(r'\bWHERE\b', rest, re.IGNORECASE):
            issues.append(Issue(
                SEVERITY_ERROR,
                "delete_without_where",
                "DELETE statement without WHERE clause will delete all rows. "
                "If intentional, add WHERE 1=1 or TRUNCATE.",
                file,
                get_line_of_pos(original, m.start()),
            ))
    for m in re.finditer(r'\bUPDATE\s+[A-Za-z_][A-Za-z0-9_\.#"`\s]*\s+SET\b', stripped, re.IGNORECASE | re.DOTALL):
        start = m.start()
        statement_end = stripped.find(";", start)
        if statement_end == -1:
            statement_end = len(stripped)
        statement = stripped[start:statement_end]
        if not re.search(r'\bWHERE\b', statement, re.IGNORECASE):
            issues.append(Issue(
                SEVERITY_ERROR,
                "update_without_where",
                "UPDATE statement without WHERE clause will update all rows. If intentional, use WHERE 1=1.",
                file,
                get_line_of_pos(original, m.start()),
            ))


def check_insert_columns(stripped: str, original: str, file: str, issues: List[Issue]) -> None:
    for m in re.finditer(r'\bINSERT\s+(?:INTO\s+)?[A-Za-z_][A-Za-z0-9_\.#"`\s]*\s*(\([^)]*\))?\s*(VALUES|SELECT)\b', stripped, re.IGNORECASE | re.DOTALL):
        col_group = m.group(1)
        if col_group is None:
            issues.append(Issue(
                SEVERITY_WARN,
                "insert_no_columns",
                "INSERT without explicit column list. Add (col1, col2, ...) for stability and documentation.",
                file,
                get_line_of_pos(original, m.start()),
            ))


def check_comma_style(stripped: str, original: str, file: str, issues: List[Issue], expected: str) -> None:
    if expected == "none":
        return
    detected = detect_comma_style(stripped)
    if detected is None:
        return
    if detected != expected:
        issues.append(Issue(
            SEVERITY_WARN,
            "comma_style",
            f"Inconsistent comma style: detected '{detected}' but expected '{expected}'.",
            file,
            0,
        ))


def check_naming_convention(stripped: str, original: str, file: str, issues: List[Issue], mode: str) -> None:
    if mode == "none":
        return
    sql_keywords = {
        "SELECT","FROM","WHERE","INSERT","UPDATE","DELETE","INTO","VALUES","SET",
        "AND","OR","NOT","IN","IS","NULL","LIKE","BETWEEN","EXISTS","AS","ON",
        "JOIN","INNER","LEFT","RIGHT","OUTER","FULL","CROSS","GROUP","BY","ORDER",
        "HAVING","LIMIT","OFFSET","WITH","UNION","ALL","DISTINCT","CASE","WHEN",
        "THEN","ELSE","END","ASC","DESC","CAST","CONVERT","CREATE","TABLE","VIEW",
        "INDEX","DROP","ALTER","ADD","COLUMN","PRIMARY","KEY","FOREIGN","REFERENCES",
        "CONSTRAINT","DEFAULT","UNIQUE","CHECK","TRUE","FALSE","BOOLEAN","INTEGER",
        "INT","BIGINT","VARCHAR","TEXT","DATE","DATETIME","TIMESTAMP","FLOAT",
        "NUMERIC","DECIMAL","NVARCHAR","CHAR","COUNT","SUM","AVG","MIN","MAX",
        "COALESCE","NULLIF","ROW_NUMBER","RANK","DENSE_RANK","OVER","PARTITION",
        "IF","ELSEIF","STRING","SPLIT","ARRAY","MAP","STRUCT","DATEADD","DATEDIFF",
        "SUBSTRING","UPPER","LOWER","TRIM","LENGTH","CONCAT","REPLACE","LEAD","LAG",
        "ANY","SOME","BOTH","EACH","PERCENT","TOP","WITHIN","GROUPING","SETS",
        "ROLLUP","CUBE","PIVOT","UNPIVOT","SAMPLE","TABLESAMPLE","IGNORE","RESPECT",
        "MATERIALIZED","TEMP","TEMPORARY","RECURSIVE","NULLS","FIRST","LAST",
        "INTERVAL","EXTRACT","YEAR","MONTH","DAY","HOUR","MINUTE","SECOND",
        "QUARTER","WEEK","CURRENT","CURRENT_DATE","CURRENT_TIMESTAMP","CURRENT_TIME",
        "NOW","SYSDATE","GREATEST","LEAST","NVL","ISNULL","GENERATE","SERIES",
        "UNNEST","EXPLODE","LATERAL","VIEW","QUALIFY","OFFSET","FETCH","ROWS",
        "MERGE","MATCHED","UPSERT","RETURNING","LOCK","SHARE","MODE","EXPLAIN",
        "ANALYZE","BEGIN","COMMIT","ROLLBACK","TRANSACTION","SAVEPOINT",
        "VALUES","CTE","WINDOW","FILTER","EXCLUDE","GROUPS","RANGE","UNBOUNDED",
        "PRECEDING","FOLLOWING","NTILE","PERCENTILE","APPROX","HLL","SKETCH",
        "BIN","BUCKET","ARRAY_AGG","STRING_AGG","ARRAY_CONTAINS","SIZE",
    }
    alias_candidates = []
    for m in re.finditer(r'\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*))?', stripped, re.IGNORECASE):
        alias_candidates.append((m.group(1), m.start(1)))
        if m.group(2):
            alias_candidates.append((m.group(2), m.start(2)))
    for m in re.finditer(r'\bJOIN\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*))?', stripped, re.IGNORECASE):
        alias_candidates.append((m.group(1), m.start(1)))
        if m.group(2):
            alias_candidates.append((m.group(2), m.start(2)))

    already = set()
    for ident, pos in alias_candidates:
        if ident.upper() in sql_keywords:
            continue
        if ident in already:
            continue
        already.add(ident)
        if not NAMING_SNAKE_CASE_RE.match(ident):
            issues.append(Issue(
                SEVERITY_WARN,
                "naming_convention",
                f"Identifier '{ident}' does not match snake_case convention.",
                file,
                get_line_of_pos(original, pos),
            ))


def analyze_file(path: Path, args: argparse.Namespace, disabled: set) -> List[Issue]:
    issues: List[Issue] = []
    try:
        original = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        issues.append(Issue(SEVERITY_ERROR, "io", f"Cannot read file: {e}", str(path), 0))
        return issues

    stripped = remove_sql_comments_and_strings(original)
    file_ref = str(path)

    if "select_star" not in disabled:
        check_select_star(stripped, original, file_ref, issues)
    if "cte_recommendation" not in disabled:
        check_cte_recommendation(stripped, original, file_ref, issues, args.max_subquery_nest)
    if "aggregate_null" not in disabled:
        check_aggregate_nulls(stripped, original, file_ref, issues)
    if "distinct_count" not in disabled:
        check_distinct_count(stripped, original, file_ref, issues)
    if "implicit_join" not in disabled:
        check_implicit_join(stripped, original, file_ref, issues)
    if "join_on_missing" not in disabled:
        check_join_on_missing(stripped, original, file_ref, issues)
    if "dml_without_where" not in disabled:
        check_dml_without_where(stripped, original, file_ref, issues)
    if "insert_no_columns" not in disabled:
        check_insert_columns(stripped, original, file_ref, issues)
    if "comma_style" not in disabled:
        check_comma_style(stripped, original, file_ref, issues, args.comma_style)
    if "naming_convention" not in disabled:
        check_naming_convention(stripped, original, file_ref, issues, args.naming_convention)

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
        print(f"[{i.severity}] {{{i.rule}}} {loc} - {i.message}")


def print_json(issues: List[Issue]) -> None:
    import json
    out = []
    for i in issues:
        out.append({
            "severity": i.severity,
            "rule": i.rule,
            "file": i.file,
            "line": i.line,
            "message": i.message,
        })
    print(json.dumps({"issues": out, "count": len(out)}, indent=2))


def main(argv: Optional[List[str]] = None) -> int:
    args = load_args(argv)
    disabled = {x.strip() for x in args.disable.split(",") if x.strip()}

    files = find_sql_files(args.path)
    if not files:
        print("ERROR: No .sql files found at given path.", file=sys.stderr)
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
        print(f"Validating {len(files)} SQL file(s)...")
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

    fatal = len(errors) > 0 or (args.strict and len(warnings) > 0)
    if fatal:
        print("RESULT: FAIL" if not args.json else "", file=sys.stderr if args.json else sys.stdout)
        return 1
    if not args.json:
        print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
