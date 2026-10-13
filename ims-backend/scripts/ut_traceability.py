#!/usr/bin/env python3
"""
UT Traceability Script - Maps UT-xxx IDs from 02-单测用例.md to test functions.

Usage:
    python scripts/ut_traceability.py

Output:
    - Covered UT IDs / Total UT IDs
    - List of uncovered UT IDs
"""

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

UT_PATTERN = re.compile(r'\bUT-[A-Z]\d{2}-\d{2}\b')
# B5 编号是 UT-B5-CO-01，旧正则只认 UT-字母两位-两位。
UT_PATTERN_LOOSE = re.compile(
    r'\b(?:[Uu][Tt]-[A-Za-z]\d{2}-\d{2}|[Uu][Tt]-B5-[A-Za-z]{2}-\d{2}(?:-[A-Za-z0-9]+)*)\b'
)


def _is_pass_only(node: ast.FunctionDef) -> bool:
    """True when the function body is only a docstring and/or `pass`."""
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return len(body) == 1 and isinstance(body[0], ast.Pass)


def _ids_in_text(text: str) -> set[str]:
    return {m.group().upper() for m in UT_PATTERN_LOOSE.finditer(text)}


# Parse UT IDs from spec
def parse_ut_ids_from_spec(spec_path: str) -> set[str]:
    """Extract all UT-xxx IDs from the spec document."""
    with open(spec_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return set(UT_PATTERN.findall(content))


def _function_source(lines: list[str], node: ast.FunctionDef) -> str:
    end = node.end_lineno or node.lineno
    return "\n".join(lines[node.lineno - 1:end])


# Parse UT IDs from test files
def parse_ut_ids_from_tests(tests_dir: str) -> dict[str, list[str]]:
    """Extract UT IDs from tests whose body is not an empty `pass`.

    A function whose executable body is only `pass` does not count as coverage,
    even if its name or docstring mentions a UT ID.
    """
    ut_to_tests = defaultdict(list)

    for py_file in Path(tests_dir).rglob('test_*.py'):
        content = py_file.read_text(encoding='utf-8')
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        lines = content.splitlines()
        pass_ranges: list[tuple[int, int]] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if not node.name.startswith('test_'):
                continue
            if _is_pass_only(node):
                end = node.end_lineno or node.lineno
                pass_ranges.append((node.lineno, end))
                continue
            ids = _ids_in_text(node.name.replace('_', '-'))
            ids |= _ids_in_text(ast.get_docstring(node) or '')
            ids |= _ids_in_text(_function_source(lines, node))
            for ut_id in ids:
                ut_to_tests[ut_id].append(f"{py_file.stem}::{node.name}")

        # Module-level mentions outside pass-only functions still count.
        masked = content
        # Drop pass-only function text so their IDs cannot leak in.
        for start, end in reversed(pass_ranges):
            block = "\n".join(lines[start - 1:end])
            masked = masked.replace(block, "")
        for ut_id in _ids_in_text(masked):
            key = f"{py_file.stem}::module"
            if key not in ut_to_tests[ut_id] and not any(
                item.startswith(f"{py_file.stem}::") for item in ut_to_tests[ut_id]
            ):
                ut_to_tests[ut_id].append(key)

    return ut_to_tests

def main():
    # Paths
    repo_root = Path(__file__).parent.parent.parent
    spec_path = repo_root / 'docs/ims-v2-rewrite/modules/B0a-框架/02-单测用例.md'
    tests_root = Path(__file__).parent.parent / 'tests'

    if not spec_path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)

    if not tests_root.exists():
        print(f"ERROR: Tests directory not found: {tests_root}")
        sys.exit(1)

    # Parse from both unit and integration tests
    spec_ut_ids = parse_ut_ids_from_spec(str(spec_path))
    test_ut_mapping = {}
    for subdir in ['unit', 'integration']:
        subdir_path = tests_root / subdir
        if subdir_path.exists():
            mapping = parse_ut_ids_from_tests(str(subdir_path))
            for ut_id, tests in mapping.items():
                if ut_id not in test_ut_mapping:
                    test_ut_mapping[ut_id] = []
                test_ut_mapping[ut_id].extend(tests)
    covered_ut_ids = set(test_ut_mapping.keys())

    # Calculate
    total = len(spec_ut_ids)
    covered = len(covered_ut_ids & spec_ut_ids)
    uncovered = spec_ut_ids - covered_ut_ids
    extra = covered_ut_ids - spec_ut_ids

    # Report
    print("=" * 60)
    print("UT TRACEABILITY REPORT")
    print("=" * 60)
    print(f"\nTotal UT IDs in spec: {total}")
    print(f"Covered UT IDs: {covered}")
    print(f"Coverage: {covered}/{total} ({100*covered/total:.1f}%)")

    if uncovered:
        print(f"\n--- Uncovered UT IDs ({len(uncovered)}) ---")
        for ut_id in sorted(uncovered):
            print(f"  {ut_id}")

    if extra:
        print(f"\n--- Extra UT IDs in tests (not in spec) ({len(extra)}) ---")
        for ut_id in sorted(extra):
            print(f"  {ut_id}")

    print("\n--- Coverage by Section ---")
    sections = defaultdict(lambda: {"total": 0, "covered": 0})
    for ut_id in spec_ut_ids:
        section = ut_id.split('-')[1][0]  # A, B, C, etc.
        sections[section]["total"] += 1
        if ut_id in covered_ut_ids:
            sections[section]["covered"] += 1

    for section in sorted(sections.keys()):
        s = sections[section]
        pct = 100 * s["covered"] / s["total"] if s["total"] > 0 else 0
        print(f"  Section {section}: {s['covered']}/{s['total']} ({pct:.0f}%)")

    print("\n" + "=" * 60)

    # Return success only if all covered
    return 0 if not uncovered else 1

if __name__ == "__main__":
    sys.exit(main())
