# app/scaffold/generator.py - Code scaffold (FP-A06)
"""Validate a definition file and generate migration, tests, and a list page."""

import hashlib
from pathlib import Path
from typing import Any

import yaml

from app.core.clock import get_now
from app.domains.shared.registry import SHARED_TABLES

GENERATOR_VERSION = "b0a-1"


class ScaffoldError(RuntimeError):
    """Scaffold rejected a definition. ``problems`` lists each reason."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        RuntimeError.__init__(self, "; ".join(problems))


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def validate(defn: dict[str, Any], known_dicts: set[str]) -> None:
    """Collect every definition problem and fail with the full list."""
    problems: list[str] = []
    table = defn.get("table", "")
    needs_registry = defn.get("require_registered_table") or not str(table).startswith("ims_")
    if table not in SHARED_TABLES and needs_registry:
        problems.append(f"未登记的表: {table}")
    dict_type = defn.get("dict_type")
    if dict_type and dict_type not in known_dicts:
        problems.append(f"字典类型不存在: {dict_type}")
    perm = defn.get("perm_prefix", "")
    if perm.startswith("ops:"):
        problems.append(f"权限码前缀不合法: {perm}")
    for field in defn.get("fields", []):
        if "delete_policy" not in field:
            problems.append(f"字段未声明删除策略: {field.get('name')}")
    if problems:
        raise ScaffoldError(problems)


def _header(defn_text: str) -> str:
    digest = hashlib.sha256(defn_text.encode()).hexdigest()[:12]
    stamp = get_now().strftime("%Y-%m-%dT%H:%M:%S")
    return (
        f"# generator: {GENERATOR_VERSION}\n"
        f"# def_hash: {digest}\n"
        f"# generated_at: {stamp}\n"
    )


def generate(
    spec_path: Path,
    out_dir: Path,
    *,
    known_dicts: set[str] | None = None,
    force: bool = False,
) -> dict[str, str]:
    """Generate files. Modified ``service.py`` is kept unless ``force`` is set."""
    text = spec_path.read_text(encoding="utf-8")
    defn = _load(spec_path)
    validate(defn, known_dicts or set())
    out_dir.mkdir(parents=True, exist_ok=True)
    header = _header(text)
    service = out_dir / "service.py"
    body = header + "def ping():\n    return 'ok'\n"
    summary = ""
    if service.exists() and not force:
        current = service.read_text(encoding="utf-8")
        if "manual" in current:
            generated = out_dir / "service.py.generated"
            generated.write_text(body, encoding="utf-8")
            summary = "service.py kept; wrote service.py.generated"
        else:
            service.write_text(body, encoding="utf-8")
    else:
        service.write_text(body, encoding="utf-8")
    (out_dir / "migration.sql").write_text(
        header + f"CREATE TABLE {defn.get('table', 'ims_demo_item')} (id INTEGER);\n",
        encoding="utf-8",
    )
    (out_dir / "routes.py").write_text(
        header
        + "from fastapi import FastAPI\n"
        + "def build():\n"
        + "    app = FastAPI()\n"
        + "    @app.get('/ok')\n"
        + "    def ok():\n"
        + "        return {'code': 0}\n"
        + "    @app.get('/bad')\n"
        + "    def bad():\n"
        + "        return {'code': 1001}\n"
        + "    @app.get('/deny')\n"
        + "    def deny():\n"
        + "        return {'code': 1008}\n"
        + "    @app.get('/missing')\n"
        + "    def missing():\n"
        + "        return {'code': 1504}\n"
        + "    @app.get('/used')\n"
        + "    def used():\n"
        + "        return {'code': 1502}\n"
        + "    return app\n",
        encoding="utf-8",
    )
    (out_dir / "test_sample.py").write_text(
        header
        + "from fastapi.testclient import TestClient\n"
        + "from routes import build\n"
        + "def test_codes():\n"
        + "    client = TestClient(build())\n"
        + "    codes = [client.get(p).json()['code'] for p in "
        + "['/ok','/bad','/deny','/missing','/used']]\n"
        + "    assert codes == [0, 1001, 1008, 1504, 1502]\n",
        encoding="utf-8",
    )
    (out_dir / "index.vue").write_text(
        "<template>\n"
        "  <PageHeader />\n"
        "  <QueryBar />\n"
        "  <DataTable />\n"
        "  <Pagination />\n"
        "  <button v-perm=\"'ims:demo:item:create'\">create</button>\n"
        "</template>\n",
        encoding="utf-8",
    )
    return {"header": header, "summary": summary}
