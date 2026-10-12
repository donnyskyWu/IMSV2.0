#!/usr/bin/env python3
"""P0 Service 分支覆盖门禁。

名单只维护在同目录的 p0_services.txt。
pytest 必须带 --cov-branch（或 pyproject 里 branch = true），本脚本只读 .coverage。

coverage report --fail-under 用的是语句和分支加在一起的 Cover 列。
这里只看分支：Numbers.pc_branches = 已执行分支 / 分支总数。
任一文件低于 90，退出码 2。请在 ims-backend 目录下运行。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 与 AGENTS.md / IMS-单元测试Checklist.md 一致，不写进 CI YAML。
FAIL_UNDER = 90.0

ROOT = Path(__file__).resolve().parents[1]
LIST_FILE = Path(__file__).with_name("p0_services.txt")


def load_p0_files(path: Path = LIST_FILE) -> list[str]:
    """读取 P0 名单。空行和井号注释忽略。"""
    files: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            files.append(line)
    return files


def fails_branch_gate(branch_percent: float, fail_under: float = FAIL_UNDER) -> bool:
    """分支覆盖率低于门槛则失败。正好等于门槛通过。"""
    return branch_percent < fail_under


def _load_coverage():
    """读 .coverage，并拒绝没有分支弧的数据。"""
    from coverage import Coverage
    from coverage.exceptions import CoverageException

    try:
        cov = Coverage(data_file=str(ROOT / ".coverage"))
        cov.load()
    except CoverageException as exc:
        print(
            "ERROR: 读不到覆盖率数据（请先在 ims-backend 下跑带 --cov-branch 的 pytest）："
            f"{exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    if not cov.get_data().has_arcs():
        print(
            "ERROR: .coverage 没有分支数据。请用 pytest --cov=app --cov-branch 重新测量。",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return cov


def _measured_by_suffix(cov) -> dict[str, str]:
    """用仓库相对路径的结尾对应 coverage 记录的绝对路径。"""
    found: dict[str, str] = {}
    for name in cov.get_data().measured_files():
        found[Path(name).as_posix()] = name
    return found


def _match(measured: dict[str, str], relative: str) -> str | None:
    suffix = "/" + relative.replace("\\", "/")
    for path, original in measured.items():
        if path.endswith(suffix):
            return original
    return None


def main() -> int:
    """逐个文件检查分支覆盖率。"""
    files = load_p0_files()
    if not files:
        print(f"ERROR: {LIST_FILE} 没有列出任何文件", file=sys.stderr)
        return 1

    missing = [name for name in files if not (ROOT / name).is_file()]
    if missing:
        print("ERROR: 名单中的文件不存在：" + ", ".join(missing), file=sys.stderr)
        return 1

    cov = _load_coverage()
    measured = _measured_by_suffix(cov)
    failed: list[str] = []
    print(f"{'file':<28} {'branches':>8} {'covered':>8} {'branch%':>8}")

    for relative in files:
        original = _match(measured, relative)
        if original is None:
            print(f"{relative:<28} {'—':>8} {'—':>8} {'MISSING':>8}")
            failed.append(relative)
            continue
        numbers = cov._analyze(original).numbers
        percent = numbers.pc_branches
        print(
            f"{relative:<28} {numbers.n_branches:8d} "
            f"{numbers.n_executed_branches:8d} {percent:7.1f}%"
        )
        if fails_branch_gate(percent):
            arcs = cov._analyze(original).missing_branch_arcs()
            print(f"  未覆盖分支: {arcs}", file=sys.stderr)
            failed.append(relative)

    if failed:
        print(
            f"ERROR: P0 分支覆盖未达到 {FAIL_UNDER:.0f}%: " + ", ".join(failed),
            file=sys.stderr,
        )
        return 2
    print(f"P0 Service 分支覆盖率达到 {FAIL_UNDER:.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
