#!/usr/bin/env python3
"""
UT Traceability Script - Maps UT-xxx IDs from 02-单测用例.md to test functions.

Usage:
    python scripts/ut_traceability.py

Output:
    - Covered UT IDs / Total UT IDs
    - List of uncovered UT IDs
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# Parse UT IDs from spec
def parse_ut_ids_from_spec(spec_path: str) -> set[str]:
    """Extract all UT-xxx IDs from the spec document."""
    ut_ids = set()
    pattern = re.compile(r'\bUT-[A-Z]\d{2}-\d{2}\b')
    
    with open(spec_path, 'r', encoding='utf-8') as f:
        content = f.read()
        matches = pattern.findall(content)
        ut_ids.update(matches)
    
    return ut_ids

# Parse UT IDs from test files
def parse_ut_ids_from_tests(tests_dir: str) -> dict[str, list[str]]:
    """Extract UT-xxx IDs from test function names and docstrings."""
    ut_to_tests = defaultdict(list)
    pattern = re.compile(r'\bUT-[A-Z]\d{2}-\d{2}\b')
    
    for py_file in Path(tests_dir).rglob('test_*.py'):
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all UT references
        for match in pattern.finditer(content):
            ut_id = match.group()
            # Get surrounding context (test function name)
            start = content.rfind('\ndef ', 0, match.start())
            if start != -1:
                end = content.find('(', start)
                func_name = content[start+5:end].strip() if end != -1 else 'unknown'
                ut_to_tests[ut_id].append(f"{py_file.stem}::{func_name}")
            else:
                ut_to_tests[ut_id].append(str(py_file.stem))
    
    return ut_to_tests

def main():
    # Paths
    repo_root = Path(__file__).parent.parent.parent
    spec_path = repo_root / 'docs/ims-v2-rewrite/modules/B0a-框架/02-单测用例.md'
    tests_dir = Path(__file__).parent.parent / 'tests/unit'
    
    if not spec_path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)
    
    if not tests_dir.exists():
        print(f"ERROR: Tests directory not found: {tests_dir}")
        sys.exit(1)
    
    # Parse
    spec_ut_ids = parse_ut_ids_from_spec(str(spec_path))
    test_ut_mapping = parse_ut_ids_from_tests(str(tests_dir))
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
