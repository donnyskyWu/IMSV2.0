# tests/unit/test_p0_coverage_gate.py
"""P0 分支门禁的名单必须指向真实文件，门槛只比较分支覆盖率。"""

from pathlib import Path

from scripts.check_p0_branch_coverage import (
    ROOT,
    evaluate_report,
    fails_branch_gate,
    load_p0_files,
    main,
)

# B0a 的认证、权限依赖、字典、角色，加上已落地的权限判定、用户和会话。
REQUIRED = {
    "app/services/auth.py",
    "app/api/deps.py",
    "app/services/access.py",
    "app/services/user.py",
    "app/db/session.py",
    "app/services/dict.py",
    "app/services/role.py",
}


def _file_summary(
    *,
    statements: int,
    covered_lines: int,
    branches: int,
    covered_branches: int,
) -> dict:
    """构造 coverage JSON 的 summary。percent_covered 是语句+分支的合计列。"""
    missing_lines = statements - covered_lines
    missing_branches = branches - covered_branches
    denominator = statements + branches
    combined = 100.0 * (covered_lines + covered_branches) / denominator
    return {
        "covered_lines": covered_lines,
        "num_statements": statements,
        "missing_lines": missing_lines,
        "percent_covered": combined,
        "num_branches": branches,
        "covered_branches": covered_branches,
        "missing_branches": missing_branches,
    }


def test_p0_list_points_at_existing_core_services():
    """名单非空，路径都存在，核心文件都在。"""
    files = load_p0_files()
    assert files
    assert set(files) >= REQUIRED
    missing = [name for name in files if not (ROOT / name).is_file()]
    assert missing == []
    assert Path(ROOT / "scripts" / "p0_services.txt").is_file()


def test_branch_gate_ignores_the_combined_total():
    """89.9 失败，正好 90 通过。合计列再高也不能代替这次比较。"""
    assert fails_branch_gate(87.2)
    assert fails_branch_gate(89.9)
    assert fails_branch_gate(90) is False
    assert fails_branch_gate(100) is False


def test_full_line_coverage_with_low_branch_coverage_fails():
    """语句 100%、分支 80% 必须失败。合计列约 98%，按合计列会误放行。"""
    summary = _file_summary(
        statements=100, covered_lines=100, branches=10, covered_branches=8,
    )
    assert summary["missing_lines"] == 0
    assert summary["covered_lines"] == summary["num_statements"]
    assert summary["percent_covered"] > 90
    assert 100.0 * summary["covered_branches"] / summary["num_branches"] < 90

    target = (ROOT / "app/services/dict.py").resolve()
    report = {
        "meta": {"branch_coverage": True},
        "files": {
            str(target): {
                "summary": summary,
                "missing_branches": [[1, 2], [1, -1]],
            },
        },
    }
    assert evaluate_report(report, ["app/services/dict.py"]) == 2


def test_exact_90_branch_percent_passes():
    """分支正好 90% 通过，相对路径的 JSON 键也能对上绝对路径。"""
    summary = _file_summary(
        statements=100, covered_lines=100, branches=10, covered_branches=9,
    )
    report = {
        "meta": {"branch_coverage": True},
        "files": {
            "app/services/role.py": {"summary": summary, "missing_branches": []},
        },
    }
    assert evaluate_report(report, ["app/services/role.py"]) == 0


def test_suffix_path_does_not_count_as_the_listed_file():
    """只和名单后缀相同的路径不能充数。100% 的替身文件不能把真文件放过。"""
    decoy = "/tmp/other-tree/app/services/role.py"
    summary = _file_summary(
        statements=20, covered_lines=20, branches=18, covered_branches=18,
    )
    report = {
        "meta": {"branch_coverage": True},
        "files": {
            decoy: {"summary": summary, "missing_branches": []},
            "nested/app/services/role.py": {"summary": summary, "missing_branches": []},
        },
    }
    assert evaluate_report(report, ["app/services/role.py"]) == 2


def test_script_fails_when_lines_are_complete_but_branches_are_short(monkeypatch):
    """入口同样失败：不读合计列，也不把后缀路径当成名单文件。"""
    summary = _file_summary(
        statements=100, covered_lines=100, branches=10, covered_branches=8,
    )
    real = (ROOT / "app/services/auth.py").resolve()
    report = {
        "meta": {"branch_coverage": True},
        "files": {
            "/tmp/other-tree/app/services/auth.py": {
                "summary": _file_summary(
                    statements=10, covered_lines=10, branches=4, covered_branches=4,
                ),
            },
            str(real): {
                "summary": summary,
                "missing_branches": [[4, 5]],
            },
        },
    }
    monkeypatch.setattr(
        "scripts.check_p0_branch_coverage.load_p0_files",
        lambda path=None: ["app/services/auth.py"],
    )
    monkeypatch.setattr(
        "scripts.check_p0_branch_coverage.load_coverage_report",
        lambda: report,
    )
    assert main() == 2


def test_no_branch_data_fails():
    """coverage JSON 没有打开分支测量时，门禁直接失败。"""
    assert evaluate_report({}, ["app/services/auth.py"]) == 1
    assert evaluate_report(
        {"meta": {"branch_coverage": False}, "files": {}},
        ["app/services/auth.py"],
    ) == 1


def test_missing_branch_field_fails():
    """summary 缺 num_branches 或 covered_branches 时失败，不拿合计列凑数。"""
    target = str((ROOT / "app/services/auth.py").resolve())
    without_num = {
        "meta": {"branch_coverage": True},
        "files": {target: {"summary": {"covered_branches": 1}}},
    }
    without_covered = {
        "meta": {"branch_coverage": True},
        "files": {target: {"summary": {"num_branches": 4}}},
    }
    assert evaluate_report(without_num, ["app/services/auth.py"]) == 1
    assert evaluate_report(without_covered, ["app/services/auth.py"]) == 1


def test_gate_reads_public_json_and_not_private_analyze():
    """门禁源码走 coverage json，不再调用私有分析接口。"""
    source = (ROOT / "scripts" / "check_p0_branch_coverage.py").read_text(encoding="utf-8")
    assert "_analyze" not in source
    assert "coverage" in source
    assert "json" in source
    assert "covered_branches" in source
    assert "num_branches" in source
