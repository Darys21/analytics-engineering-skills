#!/usr/bin/env python3
"""
validate_project.py - Repository structure and content validator for
Analytics Engineer Agent Skills repository.

Validates:
- Required directories exist (workflows/, references/, templates/, scripts/, evals/, docs/)
- Required files exist (SKILL.md, README.md, etc.)
- Internal markdown links resolve to existing files
- Emits warnings / errors with a summary table
- Non-zero exit code on errors (warnings only -> exit 0 by default, --strict makes warnings fatal)

Limitations:
- Link resolution is grep-based and does not follow URL fragments (#section).
- Does not validate link text, only the target path component.
- Treats paths as relative to the markdown file's containing directory.
- Remote (http/https/mailto) links are skipped entirely.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional


SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_OK = "OK"


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
]

RECOMMENDED_FILES = [
    "docs/architecture.md",
    "docs/workflows.md",
    "docs/contribution-guide.md",
    "docs/design-principles.md",
]

MARKDOWN_LINK_RE = re.compile(
    r'\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)'
)


class Issue:
    def __init__(self, severity: str, category: str, message: str, location: str = ""):
        self.severity = severity
        self.category = category
        self.message = message
        self.location = location

    def key(self) -> Tuple[str, str, str, str]:
        return (self.severity, self.category, self.location, self.message)


def load_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Analytics Engineer Agent Skills repository structure and content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_project.py
  python validate_project.py --repo /path/to/repo --strict
  python validate_project.py --skip-links
  python validate_project.py --strict --no-summary
""",
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
        "--skip-links",
        action="store_true",
        help="Skip internal markdown link resolution checks",
    )
    parser.add_argument(
        "--skip-structure",
        action="store_true",
        help="Skip required directory/file structure checks",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not print the summary table",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print OK entries as well",
    )
    return parser.parse_args(argv)


def repo_path(repo_root: str, relative: str) -> Path:
    return (Path(repo_root) / relative).resolve()


def check_structure(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    if not root.is_dir():
        issues.append(Issue(SEVERITY_ERROR, "structure", f"Repository root does not exist or is not a directory: {root}", str(root)))
        return issues

    for d in REQUIRED_DIRS:
        p = root / d
        if not p.is_dir():
            issues.append(Issue(SEVERITY_ERROR, "structure", f"Required directory missing: {d}/", str(p)))
        else:
            issues.append(Issue(SEVERITY_OK, "structure", f"Directory present: {d}/", str(p)))

    for f in REQUIRED_FILES:
        p = root / f
        if not p.is_file():
            issues.append(Issue(SEVERITY_ERROR, "structure", f"Required file missing: {f}", str(p)))
        else:
            issues.append(Issue(SEVERITY_OK, "structure", f"File present: {f}", str(p)))

    for f in RECOMMENDED_FILES:
        p = root / f
        if not p.is_file():
            issues.append(Issue(SEVERITY_WARN, "structure", f"Recommended file missing: {f}", str(p)))
        else:
            issues.append(Issue(SEVERITY_OK, "structure", f"File present: {f}", str(p)))

    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        required_scripts = [
            "validate_project.py",
            "validate_sql.py",
            "validate_dax.py",
            "validate_tmdl.py",
            "quality_check.py",
        ]
        for s in required_scripts:
            p = scripts_dir / s
            if not p.is_file():
                issues.append(Issue(SEVERITY_ERROR, "structure", f"Required script missing: scripts/{s}", str(p)))
            else:
                issues.append(Issue(SEVERITY_OK, "structure", f"Script present: scripts/{s}", str(p)))

    return issues


def resolve_link_target(md_file: Path, raw_target: str) -> Optional[Path]:
    if raw_target.startswith(("http://", "https://", "mailto:", "ftp://", "ftps://", "#")):
        return None

    target = raw_target
    if "#" in target:
        target = target.split("#", 1)[0]
    if target == "":
        return None
    if target.startswith("/"):
        target = target.lstrip("/")
        base = md_file.anchor if False else md_file
        while base.parent != base:
            base = base.parent
        candidate = base / target
    else:
        candidate = (md_file.parent / target).resolve()

    try:
        return candidate.resolve()
    except (OSError, RuntimeError):
        return candidate


def check_markdown_links(repo_root: str) -> List[Issue]:
    issues: List[Issue] = []
    root = Path(repo_root).resolve()

    md_files = list(root.rglob("*.md"))
    if not md_files:
        issues.append(Issue(SEVERITY_WARN, "links", "No markdown files found to check for internal links", str(root)))
        return issues

    for md_file in md_files:
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            issues.append(Issue(SEVERITY_ERROR, "links", f"Cannot read markdown file: {e}", str(md_file)))
            continue

        rel_md = md_file.relative_to(root) if md_file.is_relative_to(root) else md_file

        for match in MARKDOWN_LINK_RE.finditer(text):
            link_text = match.group(1)
            raw_target = match.group(2).strip()
            lineno = text.count("\n", 0, match.start()) + 1

            resolved = resolve_link_target(md_file, raw_target)
            if resolved is None:
                continue

            if not resolved.exists():
                loc = f"{rel_md}:{lineno}"
                issues.append(Issue(
                    SEVERITY_ERROR,
                    "links",
                    f"Broken internal link [{link_text}]({raw_target}) -> file not found: {resolved}",
                    loc,
                ))
            else:
                loc = f"{rel_md}:{lineno}"
                issues.append(Issue(
                    SEVERITY_OK,
                    "links",
                    f"Link resolves: [{link_text}]({raw_target})",
                    loc,
                ))

    return issues


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

    def fmt_row(cells):
        return " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(cells))

    sep = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    lines = [fmt_row(headers), sep]
    lines.extend(fmt_row(r) for r in rows)
    return "\n".join(lines)


def deduplicate_issues(issues: List[Issue]) -> List[Issue]:
    seen = set()
    out = []
    for iss in issues:
        k = iss.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(iss)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    args = load_args(argv)

    repo_root = os.path.abspath(args.repo)
    all_issues: List[Issue] = []

    if not args.skip_structure:
        all_issues.extend(check_structure(repo_root))
    if not args.skip_links:
        all_issues.extend(check_markdown_links(repo_root))

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
        print(f"Errors          : {len(errors)}")
        print(f"Warnings        : {len(warnings)}")
        print(f"OK checks       : {len(oks)}")
        print()
        print(format_table(all_issues, args.verbose))
        print()
        print("=" * 72)

    fatal = len(errors) > 0 or (args.strict and len(warnings) > 0)

    if fatal:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
