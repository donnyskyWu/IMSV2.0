"""菜单按钮权限码：种子、真实库、/me 与 01 功能点清单逐字对齐。

不替换 get_db，也不伪造登录。权限码从清单原文解析，不在测试里手写期望集合。
叶子 path 保持清单写出的 /ims/auth/org、/ims/auth/position。
"""

import re
from pathlib import Path

from tests.integration.test_real_db_api import (
    _connect,
    _login_me,
    _prepare_real_db,
    _release_real_db,
    _walk_menus,
)

# B0a FP-B04-02：ims:<域>:<资源>[:<动作>]
PERM_CODE = re.compile(r"`(ims:[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*){1,2})`")
# 路径推导出来的别名，清单没有这两个码。
FORBIDDEN = frozenset({"ims:auth:org:query", "ims:auth:position:query"})
REPO_ROOT = Path(__file__).resolve().parents[3]
FEATURE_LISTS = REPO_ROOT / "docs" / "ims-v2-rewrite" / "modules"


def _feature_texts() -> list[tuple[str, str]]:
    """各模块 01 功能点清单的原文。"""
    paths = sorted(FEATURE_LISTS.glob("*/01-功能点清单.md"))
    assert paths, f"找不到 01 功能点清单: {FEATURE_LISTS}"
    # 父目录名用来区分模块。三个文件本身都叫 01-功能点清单.md。
    return [(path.parent.name, path.read_text(encoding="utf-8")) for path in paths]


def parse_feature_list_perm_codes() -> set[str]:
    """清单反引号里的权限码，格式与 FP-B04-02 一致。"""
    found: set[str] = set()
    for _name, text in _feature_texts():
        found.update(PERM_CODE.findall(text))
    return found


def _b1_text() -> str:
    matches = [text for name, text in _feature_texts() if name.startswith("B1-M01")]
    assert len(matches) == 1
    return matches[0]


def parse_b1_perm_table() -> list[str]:
    """01 §0.3 表格第一列。这是本批菜单和按钮的权限码。"""
    text = _b1_text()
    start = text.index("### 0.3")
    end = text.index("### 0.4")
    rows = re.findall(r"^\| `(ims:[^`]+)` \|", text[start:end], flags=re.M)
    assert rows, "§0.3 没有解析出权限码"
    return rows


def parse_leaf_paths() -> tuple[str, str]:
    """BG-07 写出的两个叶子 path。裁定要求保持这两条，不改成别的路径。"""
    text = _b1_text()
    match = re.search(
        r"菜单“组织架构同步”`(/ims/auth/org)`、“岗位-角色供给规则”`(/ims/auth/position)`",
        text,
    )
    assert match, "清单里没有组织同步 / 岗位叶子 path"
    return match.group(1), match.group(2)


def parse_readonly_perm_codes() -> list[str]:
    """BG-07：R2、R4 的默认授权，按清单原文顺序。"""
    text = _b1_text()
    match = re.search(r"R2、R4：((?:`ims:[^`]+`、)*`ims:[^`]+`)", text)
    assert match, "清单里没有 R2、R4 默认授权"
    return PERM_CODE.findall(match.group(1))


def _walk_seed(menus: list) -> list[dict]:
    found: list[dict] = []
    for item in menus:
        found.append(item)
        found.extend(_walk_seed(item.get("children") or []))
    return found


def seed_menu_button_codes() -> list[str]:
    """种子里菜单和按钮的权限码，按树的先序。目录没有权限码。"""
    from tools.seed.menus import MENUS

    codes: list[str] = []
    for item in _walk_seed(MENUS):
        if item.get("type") in {"MENU", "BUTTON"}:
            code = item.get("perm_code")
            assert code, f"菜单或按钮缺少权限码: {item.get('name')}"
            codes.append(code)
    return codes


def _find_by_path(menus: list, path: str) -> dict | None:
    """按 path 找菜单。子树没有时返回 None，不把下一支路当成缺失。"""
    for item in menus:
        if item.get("path") == path:
            return item
        found = _find_by_path(item.get("children") or [], path)
        if found is not None:
            return found
    return None


def _button_codes(menu: dict) -> list[str]:
    return [
        child["perm_code"]
        for child in menu.get("children") or []
        if child.get("type") == "BUTTON"
    ]


def _near_misses(seed_codes: set[str], catalog: set[str]) -> list[tuple[str, str]]:
    """种子码不在清单里，但去掉下划线后和某条清单码相同。这是逐字不一致。"""

    def norm(code: str) -> str:
        return code.replace("_", "-")

    catalog_by_norm = {norm(code): code for code in catalog}
    misses: list[tuple[str, str]] = []
    for code in sorted(seed_codes - catalog):
        other = catalog_by_norm.get(norm(code))
        if other is not None and other != code:
            misses.append((code, other))
    return misses


def test_seed_db_me_perm_codes_match_feature_lists(tmp_path):
    """种子、真实库、/me 的权限码与 01 清单逐字相同。

    组织同步叶子用 ims:system:org-sync:query，岗位叶子用 ims:auth:position-rule:query。
    """
    from app.domains.sys.models import Menu
    from tools.seed.grants import B1_PERM_ALL, B1_PERM_READONLY
    from tools.seed.menus import MENUS
    from tools.seed.users import E2E_PASSWORD

    catalog = parse_feature_list_perm_codes()
    table_codes = parse_b1_perm_table()
    org_path, position_path = parse_leaf_paths()
    readonly = parse_readonly_perm_codes()
    seed_codes = seed_menu_button_codes()
    seed_set = set(seed_codes)

    # 清单 §0.3 与默认授权逐字相同，顺序也按表格。
    assert table_codes == list(B1_PERM_ALL)
    assert readonly == list(B1_PERM_READONLY)
    assert set(table_codes) <= catalog
    assert set(readonly) < set(table_codes)
    assert FORBIDDEN.isdisjoint(catalog)
    assert FORBIDDEN.isdisjoint(seed_set)

    org_menu = _find_by_path(MENUS, org_path)
    position_menu = _find_by_path(MENUS, position_path)
    assert org_menu is not None, f"种子没有 path={org_path}"
    assert position_menu is not None, f"种子没有 path={position_path}"
    org_query = next(code for code in table_codes if code.endswith(":query") and "org-sync" in code)
    position_query = next(
        code for code in table_codes if code.endswith(":query") and "position-rule" in code
    )
    org_buttons = [code for code in table_codes if code.startswith("ims:system:org-sync:") and code != org_query]
    position_buttons = [
        code for code in table_codes
        if code.startswith("ims:auth:position-rule:") and code != position_query
    ]
    assert org_path == "/ims/auth/org"
    assert position_path == "/ims/auth/position"
    assert org_menu["perm_code"] == org_query == "ims:system:org-sync:query"
    assert position_menu["perm_code"] == position_query == "ims:auth:position-rule:query"
    assert org_menu["type"] == "MENU"
    assert position_menu["type"] == "MENU"
    assert _button_codes(org_menu) == org_buttons
    assert _button_codes(position_menu) == position_buttons
    auth_codes = {org_query, position_query, *org_buttons, *position_buttons}
    assert auth_codes == set(table_codes)

    # 种子里已经写进清单的码必须原样存在；近形别名不算一致。
    assert _near_misses(seed_set, catalog) == []
    spelled = seed_set & catalog
    assert spelled
    assert org_query in spelled
    assert position_query in spelled

    db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        engine, session = _connect(db_url)
        try:
            rows = session.query(Menu).filter(Menu.deleted == 0).all()
            db_codes = {
                row.perm_code
                for row in rows
                if row.type in {"MENU", "BUTTON"} and row.perm_code
            }
            db_org = next(row for row in rows if row.path == org_path and row.deleted == 0)
            db_position = next(
                row for row in rows if row.path == position_path and row.deleted == 0
            )
            db_org_code = db_org.perm_code
            db_position_code = db_position.perm_code
            db_org_path = db_org.path
            db_position_path = db_position.path
            db_org_buttons = sorted(
                row.perm_code
                for row in rows
                if row.parent_id == db_org.id and row.type == "BUTTON" and row.perm_code
            )
            db_position_buttons = sorted(
                row.perm_code
                for row in rows
                if row.parent_id == db_position.id and row.type == "BUTTON" and row.perm_code
            )
        finally:
            session.close()
            engine.dispose()

        assert db_org_code == org_query
        assert db_position_code == position_query
        assert db_org_path == "/ims/auth/org"
        assert db_position_path == "/ims/auth/position"
        assert db_org_buttons == sorted(org_buttons)
        assert db_position_buttons == sorted(position_buttons)
        assert FORBIDDEN.isdisjoint(db_codes)

        from app.main import app

        with _client(app) as client:
            admin = _login_me(client, "test_admin", E2E_PASSWORD)
            admin_codes = set(admin["data"]["permCodes"])
            nodes = _walk_menus(admin["data"]["menus"])
            me_org = next(item for item in nodes if item.get("path") == org_path)
            me_position = next(item for item in nodes if item.get("path") == position_path)
            assert me_org["permCode"] == org_query
            assert me_position["permCode"] == position_query
            assert me_org["path"] == "/ims/auth/org"
            assert me_position["path"] == "/ims/auth/position"
            assert me_org["name"] == "组织架构同步"
            assert me_position["name"] == "岗位-角色供给规则"
            tree_codes = {item["permCode"] for item in nodes if item.get("permCode")}
            assert "BUTTON" not in {item["type"] for item in nodes}
            assert org_buttons[0] not in tree_codes
            assert set(org_buttons) <= admin_codes
            assert set(position_buttons) <= admin_codes

            readonly_user = _login_me(client, "test_xz", E2E_PASSWORD)
            readonly_codes = set(readonly_user["data"]["permCodes"])

        # 三处：种子常量、真实库菜单按钮、管理员 /me。
        # §0.3 的菜单按钮码必须原样出现在这三处。
        assert seed_set == db_codes == admin_codes
        assert set(table_codes) <= seed_set
        assert set(table_codes) <= admin_codes
        assert tree_codes <= admin_codes
        assert me_org["permCode"] in catalog
        assert me_position["permCode"] in catalog
        # R2 只读授权与清单 BG-07 逐字相同，并且 /me 返回的就是这组码。
        assert readonly_codes == set(readonly)
        assert "ims:system:org-sync:run" not in readonly_codes
        assert "ims:auth:position-rule:create" not in readonly_codes
        assert FORBIDDEN.isdisjoint(admin_codes)
        assert FORBIDDEN.isdisjoint(readonly_codes)
    finally:
        _release_real_db(original_url, context_token)


def _client(app):
    """真实 TestClient。不用 dependency_overrides。"""
    from fastapi.testclient import TestClient

    assert app.dependency_overrides == {}
    return TestClient(app)
