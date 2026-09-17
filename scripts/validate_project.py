#!/usr/bin/env python3
"""
validate_project.py - Repository structure and content validator for
Analytics Engineer Agent Skills repository.

Validates (12 checks):
  1. STRUCTURE      - Required root files and directories present
  2. INVENTORY      - Enumerate files in key dirs into known_sets
  3. SKILL FRONTMATTER - SKILL.md YAML frontmatter (name + description)
  4. BROKEN MD LINKS   - Broken relative links in markdown files
  5. REF NONEEXISTENT  - References to missing workflow/ref/template/script/doc/eval files
  6. OBSOLETE NAMES    - Outdated filenames from older architecture
  7. DUPLICATE FILES   - Duplicate basenames within folders or across category dirs
  8. EVALS SCHEMA      - evals/evals.json structure and per-case keys
  9. SCRIPTS SYNTAX    - .py in scripts/ compile cleanly via py_compile
 10. DATA-CONTRACT YAML - templates/data-contract.yml parseable structure
 11. COMPLETENESS      - Expected workflows / references / templates / scripts present
 12. LIMITATIONS       - Clear statement at end of run

Exit codes:
  0  PASS (no errors; warnings only ok unless --strict)
  1+ FAIL (errors exist, or --strict and warnings exist)

Stdlib only. PyYAML is used if installed; otherwise a minimal fallback parser
is used for frontmatter (heuristic limitation noted in output).
"""

import argparse
import json
import os
import py_compile
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_OK = "OK"

CATEGORY_STRUCTURE = "structure"
CATEGORY_INVENTORY = "inventory"
CATEGORY_FRONTMATTER = "frontmatter"
CATEGORY_LINKS = "links"
CATEGORY_REFS = "references"
CATEGORY_OBSOLETE = "obsolete"
CATEGORY_DUPES = "duplicates"
CATEGORY_EVALS = "evals"
CATEGORY_SYNTAX = "syntax"
CATEGORY_YAML = "yaml"
CATEGORY_COMPLETENESS = "completeness"

REQUIRED_DIRS = [
    "workflows",
    "references",
    "templates",
    "scripts",
    "evals",
    "docs",
]

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    ".gitignore",
]

INVENTORY_DIRS = REQUIRED_DIRS

EXPECTED_SKILL_NAME = "analytics-engineering-skills"

DESCRIPTION_MIN_LEN = 50

OBSOLETE_FILENAMES = [
    "onboard_source_system.md",
    "profile_source_data.md",
    "create_staging_sql.md",
    "star_schema_design.md",
    "create_tmdl_model.md",
    "sql_style.md",
    "naming_conventions.md",
    "iqr_outliers.md",
    "tmdl_table_template.tmdl",
]

OBSOLETE_REPLACEMENTS = {
    "onboard_source_system.md":
        "workflows/data-discovery.md + workflows/data-quality.md",
    "profile_source_data.md":
        "workflows/data-discovery.md + references/statistics.md",
    "create_staging_sql.md":
        "workflows/analytics-engineering.md + workflows/sql-analysis.md + references/sql.md",
    "star_schema_design.md":
        "workflows/data-modeling.md + references/data-modeling.md",
    "create_tmdl_model.md":
        "workflows/tmdl-analysis.md + references/tmdl.md + workflows/dax-analysis.md",
    "sql_style.md":
        "references/sql.md",
    "naming_conventions.md":
        "references/data-modeling.md + templates/CONTEXT.md",
    "iqr_outliers.md":
        "references/statistics.md + workflows/data-quality.md",
    "tmdl_table_template.tmdl":
        "templates/data-contract.yml + references/tmdl.md",
}

EXCLUDE_FILES_FROM_OBSOLETE_SCAN = {
    "scripts/validate_project.py",
    "CONTRIBUTING.md",
    "docs/contribution-guide.md",
    "docs/workflows.md",
    "Analytics Engineering Skills — V0.2 Audit & Remediation Prompt.md",
    "Mega Prompt — Analytics Engineering Skills Repository.md",
}

EXPECTED_WORKFLOWS = [
    "grill.md",
    "business-analysis.md",
    "data-discovery.md",
    "data-quality.md",
    "data-modeling.md",
    "analytics-engineering.md",
    "sql-analysis.md",
    "python-analysis.md",
    "dax-analysis.md",
    "tmdl-analysis.md",
    "statistics.md",
    "data-science.md",
    "visualization.md",
    "dashboard-ux.md",
    "pipeline.md",
    "diagnose.md",
    "optimize.md",
    "review.md",
    "delivery.md",
]

EXPECTED_REFERENCES = [
    "sql.md",
    "python.md",
    "dax.md",
    "tmdl.md",
    "data-modeling.md",
    "analytics-engineering.md",
    "statistics.md",
    "data-science.md",
    "visualization.md",
    "power-bi.md",
    "testing.md",
    "performance.md",
    "observability.md",
    "security.md",
    "ci-cd.md",
]

EXPECTED_TEMPLATES = [
    "CONTEXT.md",
    "ADR.md",
    "business-question.md",
    "analysis-report.md",
    "data-contract.yml",
    "project-structure.md",
    "definition-of-done.md",
]

EXPECTED_SCRIPTS = [
    "validate_project.py",
    "validate_sql.py",
    "validate_dax.py",
    "validate_tmdl.py",
    "quality_check.py",
]

MARKDOWN_LINK_RE = re.compile(
    r'\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)'
)

REF_PATH_PATTERNS: Dict[str, List[str]] = {
    "workflows": [r"workflows/[A-Za-z0-9_\-]+\.md"],
    "references": [r"references/[A-Za-z0-9_\-]+\.md"],
    "templates": [
        r"templates/[A-Za-z0-9_\-]+\.md",
        r"templates/[A-Za-z0-9_\-]+\.yml",
        r"templates/[A-Za-z0-9_\-]+\.yaml",
    ],
    "scripts": [r"scripts/[A-Za-z0-9_\-]+\.py"],
    "docs": [r"docs/[A-Za-z0-9_\-]+\.md"],
    "evals": [r"evals/[A-Za-z0-9_\-]+\.json"],
}

COMBINED_REF_RE = re.compile(
    r"(?P<path>"
    r"workflows/[A-Za-z0-9_\-]+\.md|"
    r"references/[A-Za-z0-9_\-]+\.md|"
    r"templates/[A-Za-z0-9_\-]+\.(?:md|yml|yaml)|"
    r"scripts/[A-Za-z0-9_\-]+\.py|"
    r"docs/[A-Za-z0-9_\-]+\.md|"
    r"evals/[A-Za-z0-9_\-]+\.json"
    r")"
)


class Issue:
    __slots__ = ("severity", "category", "message", "location")

    def __init__(self, severity: str, category: str, message: str, location: str = ""):
        self.severity = severity
        self.category = category
        self.message = message
        self.location = location

    def key(self) -> Tuple[str, str, str, str]:
        return (self.severity, self.category, self.location, self.message)

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "location": self.location,
            "message": self.message,
        }


def load_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Analytics Engineer Agent Skills repository structure and content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_project.py
  python validate_project.py /path/to/repo --strict
  python validate_project.py --repo /path/to/repo --strict
  python validate_project.py --json --verbose
  python validate_project.py --no-check-obsolete
  python validate_project.py --no-py-compile
""",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path to repository root (positional, overrides --repo if given)",
    )
    parser.add_argument(
        "--repo",
        "-r",
        default=".",
        help="Path to repository root (default: current working directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit code on warnings)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit results as JSON to stdout",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print OK entries as well",
    )
    parser.add_argument(
        "--no-check-obsolete",
        action="store_true",
        help="Skip obsolete filename scan (check runs by default)",
    )
    parser.add_argument(
        "--check-obsolete",
        dest="check_obsolete",
        action="store_true",
        default=True,
        help="Enable obsolete filename scan (default: True)",
    )
    parser.add_argument(
        "--no-py-compile",
        action="store_true",
        help="Skip Python syntax compilation check for scripts/",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not print the human-readable summary table",
    )
    return parser.parse_args(argv)


def repo_path(repo_root: str, relative: str) -> Path:
    return (Path(repo_root) / relative).resolve()


def resolve_repo_root(args: argparse.Namespace) -> str:
    if args.path is not None:
        return os.path.abspath(args.path)
    return os.path.abspath(args.repo)


# ---------------------------------------------------------------------------
# CHECK 1 + 2: STRUCTURE + INVENTORY
# ---------------------------------------------------------------------------

def check_structure_and_inventory(
    repo_root: str,
) -> Tuple[List[Issue], Dict[str, Set[str]]]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    known_sets: Dict[str, Set[str]] = {d: set() for d in INVENTORY_DIRS}

    if not root.is_dir():
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_STRUCTURE,
            f"Repository root does not exist or is not a directory: {root}",
            str(root),
        ))
        return issues, known_sets

    for d in REQUIRED_DIRS:
        p = root / d
        if not p.is_dir():
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_STRUCTURE,
                f"Required directory missing: {d}/",
                str(p),
            ))
        else:
            issues.append(Issue(
                SEVERITY_OK,
                CATEGORY_STRUCTURE,
                f"Directory present: {d}/",
                str(p),
            ))
            try:
                for entry in p.iterdir():
                    if entry.is_file():
                        known_sets[d].add(entry.name)
                issues.append(Issue(
                    SEVERITY_OK,
                    CATEGORY_INVENTORY,
                    f"Inventory for {d}/: {len(known_sets[d])} file(s)",
                    str(p),
                ))
            except OSError as e:
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_INVENTORY,
                    f"Cannot read directory {d}/: {e}",
                    str(p),
                ))

    for f in REQUIRED_FILES:
        p = root / f
        if not p.is_file():
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_STRUCTURE,
                f"Required file missing: {f}",
                str(p),
            ))
        else:
            issues.append(Issue(
                SEVERITY_OK,
                CATEGORY_STRUCTURE,
                f"File present: {f}",
                str(p),
            ))

    return issues, known_sets


# ---------------------------------------------------------------------------
# CHECK 3: SKILL.md FRONTMATTER YAML
# ---------------------------------------------------------------------------

def _minimal_frontmatter_parse(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1]
        if key:
            data[key] = value
    return data


def _extract_frontmatter(text: str) -> Optional[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end_idx: Optional[int] = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None
    return "\n".join(lines[1:end_idx])


def check_skill_frontmatter(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()
    skill_path = root / "SKILL.md"

    if not skill_path.is_file():
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_FRONTMATTER,
            "SKILL.md missing; cannot check frontmatter",
            str(skill_path),
        ))
        return issues

    try:
        text = skill_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_FRONTMATTER,
            f"Cannot read SKILL.md: {e}",
            str(skill_path),
        ))
        return issues

    if not text.startswith("---"):
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_FRONTMATTER,
            "SKILL.md does not start with YAML frontmatter delimiter '---'",
            str(skill_path),
        ))
        return issues

    fm_text = _extract_frontmatter(text)
    if fm_text is None:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_FRONTMATTER,
            "SKILL.md frontmatter not closed (missing second '---' delimiter)",
            str(skill_path),
        ))
        return issues

    parser_used = "PyYAML" if HAVE_YAML else "minimal fallback parser"
    heuristic_note = "" if HAVE_YAML else (
        " [heuristic: PyYAML not installed, using minimal fallback parser]"
    )

    try:
        if HAVE_YAML:
            fm_data = yaml.safe_load(fm_text)
            if not isinstance(fm_data, dict):
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_FRONTMATTER,
                    f"SKILL.md frontmatter is not a YAML mapping/object{heuristic_note}",
                    str(skill_path),
                ))
                return issues
        else:
            fm_data = _minimal_frontmatter_parse(fm_text)
    except Exception as e:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_FRONTMATTER,
            f"Invalid YAML in SKILL.md frontmatter: {e}{heuristic_note}",
            str(skill_path),
        ))
        return issues

    issues.append(Issue(
        SEVERITY_OK,
        CATEGORY_FRONTMATTER,
        f"SKILL.md frontmatter present and parseable (via {parser_used}){heuristic_note}",
        str(skill_path),
    ))

    if "name" not in fm_data:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_FRONTMATTER,
            "SKILL.md frontmatter missing required key 'name'",
            str(skill_path),
        ))
    else:
        name_val = fm_data.get("name")
        if not isinstance(name_val, str):
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_FRONTMATTER,
                f"SKILL.md frontmatter 'name' is not a string: {name_val!r}",
                str(skill_path),
            ))
        elif name_val != EXPECTED_SKILL_NAME:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_FRONTMATTER,
                f"SKILL.md frontmatter 'name' value {name_val!r} does not match "
                f"expected exactly {EXPECTED_SKILL_NAME!r}",
                str(skill_path),
            ))
        else:
            issues.append(Issue(
                SEVERITY_OK,
                CATEGORY_FRONTMATTER,
                f"SKILL.md frontmatter 'name' == {EXPECTED_SKILL_NAME!r}",
                str(skill_path),
            ))

    if "description" not in fm_data:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_FRONTMATTER,
            "SKILL.md frontmatter missing required key 'description'",
            str(skill_path),
        ))
    else:
        desc_val = fm_data.get("description")
        if not isinstance(desc_val, str) or desc_val.strip() == "":
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_FRONTMATTER,
                "SKILL.md frontmatter 'description' must be a non-empty string",
                str(skill_path),
            ))
        else:
            desc_len = len(desc_val.strip())
            if desc_len < DESCRIPTION_MIN_LEN:
                issues.append(Issue(
                    SEVERITY_WARN,
                    CATEGORY_FRONTMATTER,
                    f"SKILL.md frontmatter 'description' too short: {desc_len} chars "
                    f"(recommend >= {DESCRIPTION_MIN_LEN})",
                    str(skill_path),
                ))
            else:
                issues.append(Issue(
                    SEVERITY_OK,
                    CATEGORY_FRONTMATTER,
                    f"SKILL.md frontmatter 'description' present ({desc_len} chars)",
                    str(skill_path),
                ))

    return issues


# ---------------------------------------------------------------------------
# CHECK 4: BROKEN RELATIVE LINKS IN MARKDOWN
# ---------------------------------------------------------------------------

def resolve_link_target(md_file: Path, raw_target: str) -> Optional[Path]:
    if raw_target.startswith((
        "http://", "https://", "mailto:", "ftp://", "ftps://", "#",
    )):
        return None

    target = raw_target
    if "#" in target:
        target = target.split("#", 1)[0]
    if target == "":
        return None
    if target.startswith("/"):
        target = target.lstrip("/")
        base = md_file
        while base.parent != base:
            base = base.parent
        candidate = base / target
    else:
        candidate = (md_file.parent / target)

    try:
        return candidate.resolve()
    except (OSError, RuntimeError):
        return candidate


def check_markdown_links(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    md_files = list(root.rglob("*.md"))
    if not md_files:
        issues.append(Issue(
            SEVERITY_WARN,
            CATEGORY_LINKS,
            "No markdown files found to check for internal links",
            str(root),
        ))
        return issues

    for md_file in md_files:
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_LINKS,
                f"Cannot read markdown file: {e}",
                str(md_file),
            ))
            continue

        try:
            rel_md = md_file.relative_to(root)
        except ValueError:
            rel_md = md_file

        for match in MARKDOWN_LINK_RE.finditer(text):
            link_text = match.group(1)
            raw_target = match.group(2).strip()
            lineno = text.count("\n", 0, match.start()) + 1

            resolved = resolve_link_target(md_file, raw_target)
            if resolved is None:
                continue

            loc = f"{rel_md}:{lineno}"
            if not resolved.exists():
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_LINKS,
                    f"Broken internal link [{link_text}]({raw_target}) "
                    f"-> file not found: {resolved}",
                    loc,
                ))
            else:
                issues.append(Issue(
                    SEVERITY_OK,
                    CATEGORY_LINKS,
                    f"Link resolves: [{link_text}]({raw_target})",
                    loc,
                ))

    return issues


# ---------------------------------------------------------------------------
# CHECK 5: REFERENCES TO NONEXISTENT WORKFLOWS / REFERENCES / TEMPLATES / SCRIPTS
# ---------------------------------------------------------------------------

def check_nonexistent_refs(
    repo_root: str,
    known_sets: Dict[str, Set[str]],
) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    files_to_scan: List[Path] = []
    files_to_scan.extend(root.rglob("*.md"))
    files_to_scan.extend(root.rglob("*.json"))

    dir_to_prefix = {
        "workflows": "workflows/",
        "references": "references/",
        "templates": "templates/",
        "scripts": "scripts/",
        "docs": "docs/",
        "evals": "evals/",
    }

    for file_path in files_to_scan:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            issues.append(Issue(
                SEVERITY_WARN,
                CATEGORY_REFS,
                f"Cannot read file for ref scan: {e}",
                str(file_path),
            ))
            continue

        try:
            rel_path = file_path.relative_to(root)
        except ValueError:
            rel_path = file_path

        for match in COMBINED_REF_RE.finditer(text):
            start = match.start()
            prefix = text[max(0, start - 9):start]
            if (
                prefix.endswith("http://")
                or prefix.endswith("https://")
                or prefix.endswith("mailto:")
            ):
                continue
            ref_path = match.group("path")
            lineno = text.count("\n", 0, start) + 1

            for category, prefix in dir_to_prefix.items():
                if ref_path.startswith(prefix):
                    basename = ref_path[len(prefix):]
                    if basename not in known_sets.get(category, set()):
                        loc = f"{rel_path}:{lineno}"
                        issues.append(Issue(
                            SEVERITY_ERROR,
                            CATEGORY_REFS,
                            f"Reference to nonexistent file: {ref_path} "
                            f"(no file named '{basename}' under {category}/)",
                            loc,
                        ))
                    break

    return issues


# ---------------------------------------------------------------------------
# CHECK 6: OBSOLETE DOCUMENTED FILENAMES
# ---------------------------------------------------------------------------

def check_obsolete_filenames(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    files_to_scan: List[Path] = []
    for ext in ("*.md", "*.json", "*.yml", "*.yaml", "*.py"):
        files_to_scan.extend(root.rglob(ext))

    audit_name = "Analytics Engineering Skills"
    for file_path in list(files_to_scan):
        if audit_name in file_path.name and "Audit" in file_path.name:
            files_to_scan.remove(file_path)

    for file_path in files_to_scan:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            issues.append(Issue(
                SEVERITY_WARN,
                CATEGORY_OBSOLETE,
                f"Cannot read file for obsolete scan: {e}",
                str(file_path),
            ))
            continue

        try:
            rel_path = file_path.relative_to(root)
        except ValueError:
            rel_path = file_path

        rel_path_str = str(rel_path).replace(os.sep, "/")
        if rel_path_str in EXCLUDE_FILES_FROM_OBSOLETE_SCAN:
            continue

        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            for obs_name in OBSOLETE_FILENAMES:
                if obs_name in raw_line:
                    replacement = OBSOLETE_REPLACEMENTS.get(obs_name, "")
                    loc = f"{rel_path}:{lineno}"
                    hint_msg = ""
                    if replacement:
                        hint_msg = (
                            f" — nearest current equivalent(s): {replacement}"
                        )
                    issues.append(Issue(
                        SEVERITY_ERROR,
                        CATEGORY_OBSOLETE,
                        f"Obsolete filename reference: '{obs_name}' is not part of "
                        f"the current architecture{hint_msg}",
                        loc,
                    ))

    return issues


# ---------------------------------------------------------------------------
# CHECK 7: DUPLICATE FILENAMES
# ---------------------------------------------------------------------------

def check_duplicate_filenames(
    repo_root: str,
    known_sets: Dict[str, Set[str]],
) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    for d in INVENTORY_DIRS:
        dir_path = root / d
        if not dir_path.is_dir():
            continue
        seen: Dict[str, List[Path]] = {}
        try:
            for entry in dir_path.iterdir():
                if not entry.is_file():
                    continue
                seen.setdefault(entry.name, []).append(entry)
        except OSError as e:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_DUPES,
                f"Cannot scan {d}/ for duplicates: {e}",
                str(dir_path),
            ))
            continue

        for name, paths in seen.items():
            if len(paths) > 1:
                loc_str = ", ".join(str(p) for p in paths)
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_DUPES,
                    f"Duplicate filename '{name}' within {d}/ directory "
                    f"({len(paths)} occurrences): {loc_str}",
                    str(dir_path),
                ))
            else:
                issues.append(Issue(
                    SEVERITY_OK,
                    CATEGORY_DUPES,
                    f"No duplicate for '{name}' in {d}/",
                    str(paths[0]),
                ))

    return issues


# ---------------------------------------------------------------------------
# CHECK 8: EVALS SCHEMA VALIDATION
# ---------------------------------------------------------------------------

def check_evals_schema(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()
    evals_path = root / "evals" / "evals.json"

    if not evals_path.is_file():
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_EVALS,
            "evals/evals.json missing; cannot validate schema",
            str(evals_path),
        ))
        return issues

    try:
        text = evals_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_EVALS,
            f"Cannot read evals/evals.json: {e}",
            str(evals_path),
        ))
        return issues

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_EVALS,
            f"evals/evals.json is not valid JSON: {e}",
            str(evals_path),
        ))
        return issues

    if not isinstance(data, dict):
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_EVALS,
            "evals/evals.json top-level value must be a JSON object/dict",
            str(evals_path),
        ))
        return issues

    top_keys = set(data.keys())
    for opt_key in ("schema_version", "format"):
        if opt_key in top_keys:
            issues.append(Issue(
                SEVERITY_OK,
                CATEGORY_EVALS,
                f"Top-level key present: {opt_key}",
                str(evals_path),
            ))

    if "cases" not in data:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_EVALS,
            "evals/evals.json missing required top-level key 'cases'",
            str(evals_path),
        ))
        return issues

    cases = data["cases"]
    if not isinstance(cases, list):
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_EVALS,
            "evals/evals.json 'cases' must be a list/array",
            str(evals_path),
        ))
        return issues

    issues.append(Issue(
        SEVERITY_OK,
        CATEGORY_EVALS,
        f"evals/evals.json contains {len(cases)} case(s)",
        str(evals_path),
    ))

    required_nonempty = ["id", "title", "difficulty", "type", "input"]
    required_list_keys = [
        "expected_workflow_routing",
        "expected_behaviors",
        "expected_not",
    ]
    optional_list_keys = ["references_loaded"]

    for idx, case in enumerate(cases):
        case_label = f"cases[{idx}]"
        if not isinstance(case, dict):
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_EVALS,
                f"{case_label} is not a JSON object/dict",
                str(evals_path),
            ))
            continue

        case_id = case.get("id", case_label)
        for key in required_nonempty:
            val = case.get(key, None)
            if val is None:
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_EVALS,
                    f"Case id={case_id!r}: missing required non-empty key '{key}'",
                    str(evals_path),
                ))
            elif isinstance(val, str) and val.strip() == "":
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_EVALS,
                    f"Case id={case_id!r}: required key '{key}' is empty string",
                    str(evals_path),
                ))
            else:
                issues.append(Issue(
                    SEVERITY_OK,
                    CATEGORY_EVALS,
                    f"Case id={case_id!r}: key '{key}' present",
                    str(evals_path),
                ))

        for key in required_list_keys:
            val = case.get(key, None)
            if val is None:
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_EVALS,
                    f"Case id={case_id!r}: missing required list key '{key}'",
                    str(evals_path),
                ))
            elif not isinstance(val, list):
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_EVALS,
                    f"Case id={case_id!r}: key '{key}' must be a list/array, "
                    f"got {type(val).__name__}",
                    str(evals_path),
                ))
            else:
                issues.append(Issue(
                    SEVERITY_OK,
                    CATEGORY_EVALS,
                    f"Case id={case_id!r}: list key '{key}' present "
                    f"({len(val)} item(s))",
                    str(evals_path),
                ))

        for key in optional_list_keys:
            if key in case:
                val = case[key]
                if not isinstance(val, list):
                    issues.append(Issue(
                        SEVERITY_ERROR,
                        CATEGORY_EVALS,
                        f"Case id={case_id!r}: optional key '{key}' must be a "
                        f"list/array if present, got {type(val).__name__}",
                        str(evals_path),
                    ))
                else:
                    issues.append(Issue(
                        SEVERITY_OK,
                        CATEGORY_EVALS,
                        f"Case id={case_id!r}: optional list key '{key}' present "
                        f"({len(val)} item(s))",
                        str(evals_path),
                    ))

    return issues


# ---------------------------------------------------------------------------
# CHECK 9: SCRIPTS SYNTAX CHECK (py_compile)
# ---------------------------------------------------------------------------

def check_scripts_syntax(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()
    scripts_dir = root / "scripts"

    if not scripts_dir.is_dir():
        issues.append(Issue(
            SEVERITY_WARN,
            CATEGORY_SYNTAX,
            "scripts/ directory missing; cannot perform syntax check",
            str(scripts_dir),
        ))
        return issues

    py_files = list(scripts_dir.glob("*.py"))
    if not py_files:
        issues.append(Issue(
            SEVERITY_WARN,
            CATEGORY_SYNTAX,
            "No .py files found in scripts/ to syntax-check",
            str(scripts_dir),
        ))
        return issues

    for py_file in py_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
            issues.append(Issue(
                SEVERITY_OK,
                CATEGORY_SYNTAX,
                f"Syntax OK: {py_file.name}",
                str(py_file),
            ))
        except py_compile.PyCompileError as e:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_SYNTAX,
                f"Syntax error in {py_file.name}: {e}",
                str(py_file),
            ))
        except OSError as e:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_SYNTAX,
                f"Cannot compile {py_file.name}: {e}",
                str(py_file),
            ))

    return issues


# ---------------------------------------------------------------------------
# CHECK 10: YAML LINT templates/data-contract.yml
# ---------------------------------------------------------------------------

def _minimal_yaml_is_dict(text: str) -> Tuple[bool, Optional[str]]:
    lines = text.splitlines()
    toplevel_keys: List[str] = []
    for raw_line in lines:
        stripped = raw_line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        if stripped.startswith(" ") or stripped.startswith("\t"):
            continue
        if stripped.startswith("- "):
            return False, "Top-level is a list, expected mapping/object"
        if ":" in stripped:
            key_part = stripped.split(":", 1)[0].strip()
            if key_part == "":
                return False, "Top-level has empty key name"
            toplevel_keys.append(key_part)
    if not toplevel_keys:
        return False, "No top-level keys found"
    return True, None


def check_data_contract_yaml(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()
    dc_path = root / "templates" / "data-contract.yml"

    if not dc_path.is_file():
        issues.append(Issue(
            SEVERITY_WARN,
            CATEGORY_YAML,
            "templates/data-contract.yml missing; skipping YAML lint",
            str(dc_path),
        ))
        return issues

    try:
        text = dc_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        issues.append(Issue(
            SEVERITY_ERROR,
            CATEGORY_YAML,
            f"Cannot read templates/data-contract.yml: {e}",
            str(dc_path),
        ))
        return issues

    heuristic_note = "" if HAVE_YAML else (
        " [heuristic: PyYAML not installed; using basic structural check]"
    )

    if HAVE_YAML:
        try:
            data = yaml.safe_load(text)
            if not isinstance(data, dict):
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_YAML,
                    f"templates/data-contract.yml top-level is not a YAML "
                    f"mapping/object{heuristic_note}",
                    str(dc_path),
                ))
                return issues
            empty_keys = [k for k in data.keys() if isinstance(k, str) and k.strip() == ""]
            if empty_keys:
                issues.append(Issue(
                    SEVERITY_ERROR,
                    CATEGORY_YAML,
                    f"templates/data-contract.yml contains empty top-level key names{heuristic_note}",
                    str(dc_path),
                ))
            else:
                issues.append(Issue(
                    SEVERITY_OK,
                    CATEGORY_YAML,
                    f"templates/data-contract.yml is valid YAML with "
                    f"{len(data)} top-level key(s): {sorted(str(k) for k in data.keys())}{heuristic_note}",
                    str(dc_path),
                ))
        except yaml.YAMLError as e:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_YAML,
                f"templates/data-contract.yml invalid YAML: {e}{heuristic_note}",
                str(dc_path),
            ))
    else:
        ok, err = _minimal_yaml_is_dict(text)
        if not ok:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_YAML,
                f"templates/data-contract.yml basic structural check failed: "
                f"{err}{heuristic_note}",
                str(dc_path),
            ))
        else:
            issues.append(Issue(
                SEVERITY_OK,
                CATEGORY_YAML,
                f"templates/data-contract.yml basic structural check passed "
                f"(non-empty mapping-like top-level){heuristic_note}",
                str(dc_path),
            ))

    return issues


# ---------------------------------------------------------------------------
# CHECK 11: COMPLETENESS CROSS-CHECK
# ---------------------------------------------------------------------------

def check_completeness(
    repo_root: str,
    known_sets: Dict[str, Set[str]],
) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    checks = [
        ("workflows", EXPECTED_WORKFLOWS, CATEGORY_COMPLETENESS),
        ("references", EXPECTED_REFERENCES, CATEGORY_COMPLETENESS),
        ("templates", EXPECTED_TEMPLATES, CATEGORY_COMPLETENESS),
    ]

    for folder, expected, category in checks:
        actual = known_sets.get(folder, set())
        for name in expected:
            p = root / folder / name
            if name in actual:
                issues.append(Issue(
                    SEVERITY_OK,
                    category,
                    f"Expected {folder.rstrip('s')} present: {folder}/{name}",
                    str(p),
                ))
            else:
                issues.append(Issue(
                    SEVERITY_ERROR,
                    category,
                    f"Expected {folder.rstrip('s')} MISSING: {folder}/{name}",
                    str(p),
                ))
        extras = actual - set(expected)
        for name in extras:
            issues.append(Issue(
                SEVERITY_OK,
                category,
                f"Additional {folder.rstrip('s')} (allowed): {folder}/{name}",
                str(root / folder / name),
            ))

    scripts_actual = known_sets.get("scripts", set())
    for name in EXPECTED_SCRIPTS:
        p = root / "scripts" / name
        if name in scripts_actual:
            issues.append(Issue(
                SEVERITY_OK,
                CATEGORY_COMPLETENESS,
                f"Expected script present: scripts/{name}",
                str(p),
            ))
        else:
            issues.append(Issue(
                SEVERITY_ERROR,
                CATEGORY_COMPLETENESS,
                f"Expected script MISSING: scripts/{name}",
                str(p),
            ))

    return issues


# ---------------------------------------------------------------------------
# FORMATTERS
# ---------------------------------------------------------------------------

def format_table(issues: List[Issue], verbose: bool) -> str:
    rows = []
    headers = ["Severity", "Category", "Location", "Message"]
    for iss in issues:
        if not verbose and iss.severity == SEVERITY_OK:
            continue
        rows.append([iss.severity, iss.category, iss.location, iss.message])

    if not rows:
        return "(no issues to display)"

    col_widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells: List[Any]) -> str:
        return " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(cells))

    sep = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    lines = [fmt_row(headers), sep]
    lines.extend(fmt_row(r) for r in rows)
    return "\n".join(lines)


def deduplicate_issues(issues: List[Issue]) -> List[Issue]:
    seen: Set[Tuple[str, str, str, str]] = set()
    out: List[Issue] = []
    for iss in issues:
        k = iss.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(iss)
    return out


LIMITATIONS_TEXT = (
    "LIMITATIONS: Validator does not parse natural language semantic meaning, "
    "can only check structure/filenames/syntax. Heuristic checks may miss "
    "issues; human review still required. YAML frontmatter parsing may use "
    "minimal fallback parser if PyYAML not installed."
)


def print_limitations() -> None:
    print()
    print("=" * 72)
    print(LIMITATIONS_TEXT)
    print("=" * 72)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    args = load_args(argv)

    repo_root = resolve_repo_root(args)
    all_issues: List[Issue] = []

    structure_issues, known_sets = check_structure_and_inventory(repo_root)
    all_issues.extend(structure_issues)

    all_issues.extend(check_skill_frontmatter(repo_root))
    all_issues.extend(check_markdown_links(repo_root))
    all_issues.extend(check_nonexistent_refs(repo_root, known_sets))

    if args.check_obsolete and not args.no_check_obsolete:
        all_issues.extend(check_obsolete_filenames(repo_root))

    all_issues.extend(check_duplicate_filenames(repo_root, known_sets))
    all_issues.extend(check_evals_schema(repo_root))

    if not args.no_py_compile:
        all_issues.extend(check_scripts_syntax(repo_root))

    all_issues.extend(check_data_contract_yaml(repo_root))
    all_issues.extend(check_completeness(repo_root, known_sets))

    all_issues = deduplicate_issues(all_issues)
    all_issues.sort(key=lambda i: (
        0 if i.severity == SEVERITY_ERROR else 1 if i.severity == SEVERITY_WARN else 2,
        i.category,
        i.location,
        i.message,
    ))

    errors = [i for i in all_issues if i.severity == SEVERITY_ERROR]
    warnings = [i for i in all_issues if i.severity == SEVERITY_WARN]
    oks = [i for i in all_issues if i.severity == SEVERITY_OK]

    if args.json:
        payload = {
            "repo_root": repo_root,
            "strict_mode": args.strict,
            "yaml_available": HAVE_YAML,
            "counts": {
                "errors": len(errors),
                "warnings": len(warnings),
                "ok": len(oks),
                "total": len(all_issues),
            },
            "issues": [i.to_dict() for i in all_issues],
            "limitations": LIMITATIONS_TEXT,
        }
        print(json.dumps(payload, indent=2))
    else:
        for iss in all_issues:
            if iss.severity == SEVERITY_OK and not args.verbose:
                continue
            prefix = f"[{iss.severity}]"
            loc = f" {iss.location}" if iss.location else ""
            print(f"{prefix}{loc} {iss.message}")

        if not args.no_summary:
            print()
            print("=" * 72)
            print("VALIDATION SUMMARY")
            print("=" * 72)
            print(f"Repository root : {repo_root}")
            print(f"Strict mode     : {'enabled' if args.strict else 'disabled'}")
            print(f"PyYAML available: {'yes' if HAVE_YAML else 'no (using fallbacks)'}")
            print(f"Errors          : {len(errors)}")
            print(f"Warnings        : {len(warnings)}")
            print(f"OK checks       : {len(oks)}")
            print()
            print(format_table(all_issues, args.verbose))
            print()
            print("=" * 72)
            print(f"TOTALS: Errors={len(errors)}  Warnings={len(warnings)}  OK={len(oks)}")
            print("=" * 72)

        print_limitations()

    fatal = len(errors) > 0 or (args.strict and len(warnings) > 0)

    if not args.json:
        if fatal:
            print("RESULT: FAIL")
        else:
            print("RESULT: PASS")

    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
