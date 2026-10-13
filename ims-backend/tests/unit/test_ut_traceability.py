"""ut_traceability 规格正则认 UT-B5-CO-01，空 pass 不算覆盖。"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[2] / "scripts" / "ut_traceability.py"
    spec = importlib.util.spec_from_file_location("ut_traceability", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_spec_pattern_accepts_b5_and_legacy(tmp_path):
    """规格扫描同时认出 UT-B5-CO-01 和旧编号 UT-A01-10。"""
    module = _load()
    spec = tmp_path / "spec.md"
    spec.write_text("覆盖 UT-B5-CO-01、UT-A01-10 与 UT-B5-CO-05-1222。\n", encoding="utf-8")
    assert module.parse_ut_ids_from_spec(str(spec)) == {
        "UT-B5-CO-01",
        "UT-A01-10",
        "UT-B5-CO-05-1222",
    }


def test_pass_only_body_does_not_count(tmp_path):
    """函数体只有 pass 时，docstring 里的编号不算覆盖。"""
    module = _load()
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_shell.py").write_text(
        'def test_empty():\n'
        '    """UT-B5-CO-01"""\n'
        '    pass\n'
        '\n'
        'def test_real():\n'
        '    """UT-B5-SM-04-1504"""\n'
        '    assert True\n',
        encoding="utf-8",
    )
    mapping = module.parse_ut_ids_from_tests(str(tests))
    assert "UT-B5-CO-01" not in mapping
    assert any(item.endswith("::test_real") for item in mapping["UT-B5-SM-04-1504"])
