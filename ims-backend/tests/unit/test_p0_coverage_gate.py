# tests/unit/test_p0_coverage_gate.py
"""P0 分支门禁的名单必须指向真实文件，门槛只比较分支覆盖率。"""

from pathlib import Path

from scripts.check_p0_branch_coverage import ROOT, fails_branch_gate, load_p0_files

# 工作包没有逐文件标 P0。这五份是当前 main 上已落地的认证、权限和会话核心。
REQUIRED = {
    "app/services/auth.py",
    "app/api/deps.py",
    "app/services/access.py",
    "app/services/user.py",
    "app/db/session.py",
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
