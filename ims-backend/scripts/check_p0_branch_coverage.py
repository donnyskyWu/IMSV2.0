#!/usr/bin/env python3
"""P0 Service 分支覆盖门禁。

名单只维护在同目录的 p0_services.txt。
pytest 必须带 --cov-branch（或 pyproject 里 branch = true）。

本脚本调用公开命令 `coverage json`，只读
files[].summary.covered_branches / num_branches。
不使用 coverage 的私有分析接口。

coverage report --fail-under 用的是语句和分支加在一起的 Cover 列。
语句 100%、分支 80% 时合计列仍可能高于 90，这里必须失败。
任一文件的分支覆盖率低于 90，退出码 2。

文件按解析后的绝对路径相等匹配，不用路径后缀。
请在 ims-backend 目录下运行。
"""

from __future__ import annotations

import json
import subprocess
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


def branch_percent(summary: dict) -> float:
    """分支覆盖率 = covered_branches / num_branches。没有分支时视为 100。"""
    num = int(summary["num_branches"])
    covered = int(summary["covered_branches"])
    if num == 0:
        return 100.0
    return 100.0 * covered / num


def resolve_report_path(key: str, root: Path = ROOT) -> Path:
    """把 coverage JSON 的文件键解析成绝对路径。相对键相对 ims-backend 根目录。"""
    path = Path(key)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def index_report_files(report: dict, root: Path = ROOT) -> dict[Path, dict]:
    """按绝对路径索引 JSON 里的文件。同路径后者覆盖前者。"""
    indexed: dict[Path, dict] = {}
    for key, payload in (report.get("files") or {}).items():
        indexed[resolve_report_path(str(key), root)] = payload
    return indexed


def load_coverage_report() -> dict:
    """用公开的 coverage json 读 .coverage。--fail-under=0 避免把 80% 行门槛算进本脚本。"""
    data_file = ROOT / ".coverage"
    if not data_file.is_file():
        print(
            "ERROR: 读不到覆盖率数据（请先在 ims-backend 下跑带 --cov-branch 的 pytest）",
            file=sys.stderr,
        )
        raise SystemExit(1)

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "--data-file",
            str(data_file),
            "-o",
            "-",
            "-q",
            "--fail-under=0",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        detail = (proc.stderr or proc.stdout).strip()
        print(f"ERROR: coverage json 失败：{detail}", file=sys.stderr)
        raise SystemExit(1)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"ERROR: coverage json 输出不是 JSON：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if not isinstance(report, dict):
        print("ERROR: coverage json 根节点不是对象", file=sys.stderr)
        raise SystemExit(1)
    return report


def evaluate_report(report: dict, relatives: list[str], root: Path = ROOT) -> int:
    """按分支覆盖率检查名单。返回 0 通过，1 数据无效，2 未达门槛。"""
    meta = report.get("meta") or {}
    if not meta.get("branch_coverage"):
        print(
            "ERROR: coverage JSON 没有分支数据。请用 pytest --cov=app --cov-branch 重新测量。",
            file=sys.stderr,
        )
        return 1

    measured = index_report_files(report, root)
    failed: list[str] = []
    print(f"{'file':<28} {'branches':>8} {'covered':>8} {'branch%':>8}")

    for relative in relatives:
        expected = (root / relative).resolve()
        payload = measured.get(expected)
        if payload is None:
            print(f"{relative:<28} {'—':>8} {'—':>8} {'MISSING':>8}")
            failed.append(relative)
            continue

        summary = payload.get("summary") or {}
        if "num_branches" not in summary or "covered_branches" not in summary:
            print(
                f"ERROR: {relative} 的 summary 缺少 num_branches/covered_branches",
                file=sys.stderr,
            )
            return 1

        percent = branch_percent(summary)
        num = int(summary["num_branches"])
        covered = int(summary["covered_branches"])
        print(f"{relative:<28} {num:8d} {covered:8d} {percent:7.1f}%")
        if fails_branch_gate(percent):
            missing = payload.get("missing_branches") or []
            print(f"  未覆盖分支: {missing}", file=sys.stderr)
            failed.append(relative)

    if failed:
        print(
            f"ERROR: P0 分支覆盖未达到 {FAIL_UNDER:.0f}%: " + ", ".join(failed),
            file=sys.stderr,
        )
        return 2
    print(f"P0 Service 分支覆盖率达到 {FAIL_UNDER:.0f}%")
    return 0


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

    return evaluate_report(load_coverage_report(), files)


if __name__ == "__main__":
    raise SystemExit(main())
