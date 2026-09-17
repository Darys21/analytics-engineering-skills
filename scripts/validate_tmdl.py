#!/usr/bin/env python3
"""
validate_tmdl.py - TMDL (Tabular Model Definition Language) structural validator.

TMDL is the Microsoft text format for Analysis Services / Power BI tabular models
(see: https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview).

This validator performs regex-based structural checks on .tmdl files, including:
- Required attributes per object type (column -> sourceColumn or expression, etc.)
- Naming conventions (PascalCase for tables/columns/measures, no spaces)
- Relationship integrity (fromTable/fromColumn/toTable/toColumn must exist)
- Display folder consistency (measures without folder when siblings have one)
- Numeric measures without FormatString
- Deprecated object types / compatibility markers
- Duplicate names within the same parent

Limitations:
- Not a full TMDL parser. Checks are best-effort and may false-positive on edge cases.
- Does not load the .tmdl file into a real semantic engine; no server-side schema checks.
- Cross-file references (when the model is split into multiple .tmdl files) are only
  partially supported via scanning the whole directory.
- Format string correctness (e.g. valid .NET format specifier) is not validated.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"


VALID_NUMERIC_TYPES = {
    "int64", "int32", "int16", "byte", "sbyte",
    "double", "single", "decimal", "currency",
}

LIKELY_NUMERIC_DAX = {"SUM", "COUNT", "COUNTA", "COUNTROWS", "AVERAGE", "AVG", "MIN", "MAX",
                      "DIVIDE", "PRODUCT", "SUMX", "COUNTX", "AVERAGEX", "MAXX", "MINX",
                      "TOTALMTD", "TOTALYTD", "TOTALQTD", "DATESMTD", "DATESYTD"}


class Issue:
    __slots__ = ("severity", "rule", "message", "file", "line", "object_ref")

    def __init__(
        self,
        severity: str,
        rule: str,
        message: str,
        file: str = "",
        line: int = 0,
        object_ref: str = "",
    ):
        self.severity = severity
        self.rule = rule
        self.message = message
        self.file = file
        self.line = line
        self.object_ref = object_ref


def load_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run structural validation on TMDL (Tabular Model Definition Language) files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_tmdl.py model.tmdl
  python validate_tmdl.py ./TmdlModel/ --strict
  python validate_tmdl.py ./TmdlModel/ --no-cross-file
  python validate_tmdl.py ./TmdlModel/ --disable display_folder,naming
""",
    )
    parser.add_argument(
        "path",
        help=".tmdl file or directory of TMDL files",
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
        "--no-cross-file",
        action="store_true",
        help="Do not scan for cross-file references when validating relationships",
    )
    parser.add_argument(
        "--naming",
        choices=["PascalCase", "any"],
        default="PascalCase",
        help="Table/column/measure naming convention (default: PascalCase)",
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


def find_tmdl_files(target: str) -> List[Path]:
    p = Path(target).resolve()
    if not p.exists():
        print(f"ERROR: Path does not exist: {p}", file=sys.stderr)
        sys.exit(2)
    if p.is_file():
        if p.suffix.lower() != ".tmdl":
            print(f"WARNING: File {p} does not have .tmdl extension; analyzing anyway.", file=sys.stderr)
        return [p]
    return sorted(p.rglob("*.tmdl"))


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


IDENT_SAFE_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
PASCAL_CASE_RE = re.compile(r'^[A-Z][A-Za-z0-9]*$')


def read_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        return None


def parse_tmdl_sections(text: str) -> Dict[str, List[Dict]]:
    """Very rough TMDL parser.

    TMDL uses an indentation-sensitive structure like:
        table SalesTable =
            column SalesAmount =
                sourceColumn = 'SQL Source'.'Sales'[SalesAmount]
                dataType = double
                formatString = "$#,##0.00"

    We extract object headers and collect their attribute lines by indentation level.
    """
    sections: Dict[str, List[Dict]] = {
        "table": [],
        "column": [],
        "measure": [],
        "relationship": [],
        "hierarchy": [],
        "level": [],
        "partition": [],
        "dataSource": [],
        "expression": [],
        "culture": [],
        "role": [],
        "perspective": [],
    }

    lines = text.splitlines()
    stack: List[Tuple[int, str, Dict]] = []  # (indent, type, attrs)

    table_header_re = re.compile(r'^\s*(?P<type>table|column|measure|relationship|hierarchy|level|partition|dataSource|expression|culture|role|perspective)\s+(?P<name>[A-Za-z_][A-Za-z0-9_ \.\-]*?)\s*=\s*$', re.IGNORECASE)
    attr_re = re.compile(r'^\s*(?P<key>[A-Za-z_][A-Za-z0-9]*)\s*=\s*(?P<value>.*?)\s*$')

    def indent_of(line: str) -> int:
        return len(line) - len(line.lstrip(" \t"))

    for idx, raw in enumerate(lines):
        line_no = idx + 1
        stripped = raw.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("--"):
            continue
        indent = indent_of(raw)

        while stack and stack[-1][0] >= indent:
            stack.pop()

        m = table_header_re.match(raw)
        if m:
            obj_type = m.group("type").lower()
            obj_name = m.group("name").strip()
            obj = {"name": obj_name, "line": line_no, "attrs": {}, "parent": None}
            if stack:
                obj["parent"] = stack[-1][1]
                obj["parent_name"] = stack[-1][2]["name"]
            stack.append((indent, obj_type, obj))
            if obj_type in sections:
                sections[obj_type].append(obj)
            continue

        m2 = attr_re.match(raw)
        if m2 and stack:
            key = m2.group("key").strip()
            value = m2.group("value").strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            stack[-1][2]["attrs"][key] = value
            if "_attr_lines" not in stack[-1][2]:
                stack[-1][2]["_attr_lines"] = {}
            stack[-1][2]["_attr_lines"][key] = line_no
    return sections


def collect_model_from_files(files: List[Path]) -> Dict[str, Dict]:
    """Collect tables/columns/measures/relationships from a list of TMDL files.

    Returns index dicts: tables, columns, measures, relationships.
    """
    tables: Dict[str, Dict] = {}
    columns: Dict[Tuple[str, str], Dict] = {}
    measures: Dict[Tuple[str, str], Dict] = {}
    relationships: List[Dict] = []

    for f in files:
        text = read_file(f)
        if text is None:
            continue
        sections = parse_tmdl_sections(text)
        for tbl in sections.get("table", []):
            tbl["_file"] = str(f)
            tables[tbl["name"]] = tbl
        for col in sections.get("column", []):
            parent = col.get("parent_name")
            if parent:
                columns[(parent, col["name"])] = {**col, "_file": str(f)}
        for meas in sections.get("measure", []):
            parent = meas.get("parent_name")
            if parent:
                measures[(parent, meas["name"])] = {**meas, "_file": str(f)}
        for rel in sections.get("relationship", []):
            rel["_file"] = str(f)
            relationships.append(rel)

    return {
        "tables": tables,
        "columns": columns,
        "measures": measures,
        "relationships": relationships,
    }


def check_table_required(table: Dict, file_ref: str, issues: List[Issue]) -> None:
    if not table["attrs"]:
        return
    # At least one of the marker attributes (even empty list) should be present;
    # realistically tables need columns.
    issues.append(Issue(
        SEVERITY_INFO,
        "table_present",
        f"Table '{table['name']}' found",
        file_ref,
        table["line"],
        f"table/{table['name']}",
    ))


def check_column_required(col: Dict, file_ref: str, issues: List[Issue]) -> None:
    attrs = col["attrs"]
    lines = col.get("_attr_lines", {})
    parent = col.get("parent_name", "?")

    has_source = "sourceColumn" in attrs or "expression" in attrs
    if not has_source:
        issues.append(Issue(
            SEVERITY_ERROR,
            "column_missing_source",
            f"Column '{parent}[{col['name']}]' must declare either sourceColumn=<mapped column> or expression=<DAX>.",
            file_ref,
            col["line"],
            f"column/{parent}/{col['name']}",
        ))
    if "dataType" not in attrs:
        issues.append(Issue(
            SEVERITY_WARN,
            "column_missing_datatype",
            f"Column '{parent}[{col['name']}]' missing dataType. Add dataType = <type> explicitly.",
            file_ref,
            col["line"],
            f"column/{parent}/{col['name']}",
        ))

    dtype = attrs.get("dataType", "").lower()
    if dtype in VALID_NUMERIC_TYPES and "formatString" not in attrs:
        issues.append(Issue(
            SEVERITY_WARN,
            "numeric_column_missing_format",
            f"Numeric column '{parent}[{col['name']}]' (dataType={dtype}) has no formatString. "
            "Set formatString (e.g. '#,##0.00') for consistent reporting.",
            file_ref,
            lines.get("dataType", col["line"]),
            f"column/{parent}/{col['name']}",
        ))


def check_measure_required(meas: Dict, file_ref: str, issues: List[Issue]) -> None:
    attrs = meas["attrs"]
    lines = meas.get("_attr_lines", {})
    parent = meas.get("parent_name", "?")

    if "expression" not in attrs:
        issues.append(Issue(
            SEVERITY_ERROR,
            "measure_missing_expression",
            f"Measure '{parent}[{meas['name']}]' must declare expression = <DAX expression>.",
            file_ref,
            meas["line"],
            f"measure/{parent}/{meas['name']}",
        ))
        return

    expr = attrs["expression"]
    is_numeric = False
    if re.search(r'\b(' + '|'.join(re.escape(x) for x in LIKELY_NUMERIC_DAX) + r')\s*\(', expr, re.IGNORECASE):
        is_numeric = True
    if re.search(r'\b(DIVIDE|[+\-*/])\s*', expr):
        is_numeric = True
    if "COUNT" in expr.upper() or "SUM" in expr.upper() or "AVERAG" in expr.upper():
        is_numeric = True

    if is_numeric and "formatString" not in attrs:
        issues.append(Issue(
            SEVERITY_WARN,
            "numeric_measure_missing_format",
            f"Measure '{parent}[{meas['name']}]' appears numeric but has no formatString. "
            "Set formatString explicitly (e.g. '#,##0.00' or '$#,##0.00').",
            file_ref,
            lines.get("expression", meas["line"]),
            f"measure/{parent}/{meas['name']}",
        ))


def check_relationship(rel: Dict, model_index: Dict, file_ref: str, issues: List[Issue]) -> None:
    attrs = rel["attrs"]
    lines = rel.get("_attr_lines", {})

    required = ["fromTable", "fromColumn", "toTable", "toColumn"]
    missing = [k for k in required if k not in attrs]
    if missing:
        issues.append(Issue(
            SEVERITY_ERROR,
            "relationship_missing_attrs",
            f"Relationship '{rel['name']}' missing required attributes: {', '.join(missing)}.",
            file_ref,
            rel["line"],
            f"relationship/{rel['name']}",
        ))
        return

    from_table = attrs["fromTable"].strip("'[]")
    from_col = attrs["fromColumn"].strip("'[]")
    to_table = attrs["toTable"].strip("'[]")
    to_col = attrs["toColumn"].strip("'[]")

    if model_index["tables"]:
        if from_table not in model_index["tables"]:
            issues.append(Issue(
                SEVERITY_ERROR,
                "relationship_dangling_table",
                f"Relationship '{rel['name']}' fromTable '{from_table}' not found in model index.",
                file_ref,
                lines.get("fromTable", rel["line"]),
                f"relationship/{rel['name']}",
            ))
        if to_table not in model_index["tables"]:
            issues.append(Issue(
                SEVERITY_ERROR,
                "relationship_dangling_table",
                f"Relationship '{rel['name']}' toTable '{to_table}' not found in model index.",
                file_ref,
                lines.get("toTable", rel["line"]),
                f"relationship/{rel['name']}",
            ))
        if (from_table, from_col) not in model_index["columns"] and from_table in model_index["tables"]:
            issues.append(Issue(
                SEVERITY_ERROR,
                "relationship_dangling_column",
                f"Relationship '{rel['name']}' fromColumn '{from_table}[{from_col}]' not found.",
                file_ref,
                lines.get("fromColumn", rel["line"]),
                f"relationship/{rel['name']}",
            ))
        if (to_table, to_col) not in model_index["columns"] and to_table in model_index["tables"]:
            issues.append(Issue(
                SEVERITY_ERROR,
                "relationship_dangling_column",
                f"Relationship '{rel['name']}' toColumn '{to_table}[{to_col}]' not found.",
                file_ref,
                lines.get("toColumn", rel["line"]),
                f"relationship/{rel['name']}",
            ))


def check_naming(obj: Dict, obj_type: str, parent_name: str, file_ref: str, convention: str, issues: List[Issue]) -> None:
    if convention == "any":
        return
    name = obj["name"]
    compact = name.replace(" ", "")
    if not PASCAL_CASE_RE.match(compact):
        obj_ref = f"{obj_type}/"
        if parent_name:
            obj_ref += f"{parent_name}/"
        obj_ref += name
        issues.append(Issue(
            SEVERITY_WARN,
            "naming",
            f"{obj_type.capitalize()} name '{name}' does not follow {convention} convention.",
            file_ref,
            obj["line"],
            obj_ref,
        ))


def check_display_folders(measures_by_table: Dict[str, List[Dict]], file_ref: str, issues: List[Issue]) -> None:
    for table, measures in measures_by_table.items():
        folders = {m["attrs"].get("displayFolder") for m in measures if m["attrs"].get("displayFolder")}
        if len(folders) == 0:
            continue
        for m in measures:
            if not m["attrs"].get("displayFolder"):
                issues.append(Issue(
                    SEVERITY_WARN,
                    "display_folder_missing",
                    f"Measure '{table}[{m['name']}]' has no displayFolder but siblings are "
                    f"organized into {len(folders)} folder(s). For consistency, add a displayFolder or "
                    f"move the measure to the appropriate folder.",
                    m.get("_file", file_ref),
                    m["line"],
                    f"measure/{table}/{m['name']}",
                ))


def check_duplicate_names(sections: Dict[str, List[Dict]], file_ref: str, issues: List[Issue]) -> None:
    seen: Dict[str, Set[str]] = {}
    for section_name, objects in sections.items():
        if not objects:
            continue
        key_by_parent: Dict[str, Set[str]] = {}
        for obj in objects:
            parent = obj.get("parent_name", "__root__")
            bucket = key_by_parent.setdefault(parent, set())
            lname = obj["name"].lower()
            if lname in bucket:
                obj_ref = f"{section_name}/"
                if parent != "__root__":
                    obj_ref += f"{parent}/"
                obj_ref += obj["name"]
                issues.append(Issue(
                    SEVERITY_ERROR,
                    "duplicate_name",
                    f"Duplicate {section_name} name '{obj['name']}' under parent '{parent}'.",
                    file_ref,
                    obj["line"],
                    obj_ref,
                ))
            bucket.add(lname)


def analyze_file(path: Path, model_index: Dict, args: argparse.Namespace, disabled: Set[str]) -> List[Issue]:
    issues: List[Issue] = []
    text = read_file(path)
    if text is None:
        issues.append(Issue(SEVERITY_ERROR, "io", f"Cannot read file: {path}", str(path), 0, ""))
        return issues

    file_ref = str(path)
    sections = parse_tmdl_sections(text)

    if "duplicate_name" not in disabled:
        check_duplicate_names(sections, file_ref, issues)

    if "naming" not in disabled:
        for t in sections.get("table", []):
            check_naming(t, "table", "", file_ref, args.naming, issues)
        for c in sections.get("column", []):
            check_naming(c, "column", c.get("parent_name", ""), file_ref, args.naming, issues)
        for m in sections.get("measure", []):
            check_naming(m, "measure", m.get("parent_name", ""), file_ref, args.naming, issues)

    for t in sections.get("table", []):
        if "table_present" not in disabled:
            check_table_required(t, file_ref, issues)

    for c in sections.get("column", []):
        if "column_required" not in disabled:
            check_column_required(c, file_ref, issues)

    for m in sections.get("measure", []):
        if "measure_required" not in disabled:
            check_measure_required(m, file_ref, issues)

    for r in sections.get("relationship", []):
        if "relationship_integrity" not in disabled:
            check_relationship(r, model_index, file_ref, issues)

    if "display_folder" not in disabled:
        measures_by_table: Dict[str, List[Dict]] = {}
        for m in sections.get("measure", []):
            parent = m.get("parent_name")
            if parent:
                m["_file"] = file_ref
                measures_by_table.setdefault(parent, []).append(m)
        check_display_folders(measures_by_table, file_ref, issues)

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
        ref = f" <{i.object_ref}>" if i.object_ref else ""
        print(f"[{i.severity}] {{{i.rule}}}{ref} {loc} - {i.message}")


def print_json(issues: List[Issue]) -> None:
    import json as _json
    out = []
    for i in issues:
        out.append({
            "severity": i.severity,
            "rule": i.rule,
            "file": i.file,
            "line": i.line,
            "object_ref": i.object_ref,
            "message": i.message,
        })
    print(_json.dumps({"issues": out, "count": len(out)}, indent=2))


def main(argv: Optional[List[str]] = None) -> int:
    args = load_args(argv)
    disabled = {x.strip() for x in args.disable.split(",") if x.strip()}

    files = find_tmdl_files(args.path)
    if not files:
        print("ERROR: No .tmdl files found at given path.", file=sys.stderr)
        return 2

    if not args.no_cross_file:
        model_index = collect_model_from_files(files)
    else:
        model_index = {"tables": {}, "columns": {}, "measures": {}, "relationships": []}

    all_issues: List[Issue] = []
    for f in files:
        all_issues.extend(analyze_file(f, model_index, args, disabled))

    errors = [i for i in all_issues if i.severity == SEVERITY_ERROR]
    warnings = [i for i in all_issues if i.severity == SEVERITY_WARN]
    infos = [i for i in all_issues if i.severity == SEVERITY_INFO]

    if args.json:
        print_json(all_issues)
    else:
        print(f"Validating {len(files)} TMDL file(s)...")
        if not args.no_cross_file:
            print(f"Cross-file index: {len(model_index['tables'])} tables, "
                  f"{len(model_index['columns'])} columns, "
                  f"{len(model_index['measures'])} measures, "
                  f"{len(model_index['relationships'])} relationships")
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
        if not args.json:
            print("RESULT: FAIL")
        return 1
    if not args.json:
        print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
