# tests/unit/test_b1_seed_migration.py - B1 PR1 种子与迁移
"""种子幂等、默认授权不覆盖管理员修改，以及 BG-08 回填。"""

import bcrypt


def _perm_codes(menus: list) -> list[str]:
    found = []
    for menu in menus:
        if menu.get("perm_code"):
            found.append(menu["perm_code"])
        found.extend(_perm_codes(menu.get("children", [])))
    return found


class TestB1SeedCatalog:
    """种子常量与 Q10 / BG-07 对齐。"""

    def test_b1_perm_codes_are_in_menu_seed(self):
        from tools.seed.grants import B1_PERM_ALL
        from tools.seed.menus import MENUS

        present = set(_perm_codes(MENUS))
        for code in B1_PERM_ALL:
            assert code in present

    def test_readonly_grants_are_subset(self):
        from tools.seed.grants import B1_PERM_ALL, B1_PERM_READONLY

        assert set(B1_PERM_READONLY) < set(B1_PERM_ALL)
        assert "ims:system:org-sync:run" not in B1_PERM_READONLY

    def test_b1_dict_types_present(self):
        from tools.seed.dicts import DICT_DATA, DICT_TYPES

        types = {row["dict_type"] for row in DICT_TYPES}
        for name in (
            "dict_org_event_type",
            "dict_reconcile_action",
            "dict_reconcile_trigger",
            "dict_reconcile_status",
            "dict_position_rule_status",
            "dict_login_channel",
        ):
            assert name in types
        actions = [
            row["dict_value"] for row in DICT_DATA
            if row["dict_type"] == "dict_reconcile_action"
        ]
        assert len(actions) == 10
        assert "RETRYING" in {
            row["dict_value"] for row in DICT_DATA
            if row["dict_type"] == "dict_org_sync_status"
        }

    def test_dry_run_does_not_need_database(self):
        from tools.seed.runner import run_seeds

        assert run_seeds(env="test", dry_run=True) is True

    def test_unknown_category_fails(self):
        from tools.seed.runner import run_seeds

        assert run_seeds(env="test", only=["nope"], dry_run=True) is False


class TestSeedIdempotentAndPreserve:
    """FP-H05-01：第二次不新增；管理员改过的字段保持原样。"""

    def test_second_run_inserts_nothing(self, db_session):
        from app.domains.sys.models import DictData, Menu, Role, RoleMenu
        from tools.seed.runner import run_seeds

        assert run_seeds(env="test") is True
        roles = db_session.query(Role).count()
        menus = db_session.query(Menu).count()
        grants = db_session.query(RoleMenu).count()
        dicts = db_session.query(DictData).count()
        assert run_seeds(env="test") is True
        assert db_session.query(Role).count() == roles
        assert db_session.query(Menu).count() == menus
        assert db_session.query(RoleMenu).count() == grants
        assert db_session.query(DictData).count() == dicts

    def test_admin_role_and_menu_edits_survive(self, db_session):
        from app.domains.sys.models import Menu, Role
        from tools.seed.menus import seed_menus
        from tools.seed.roles import seed_roles

        seed_roles(env="test")
        seed_menus(env="test")
        role = db_session.query(Role).filter(Role.role_key == "R2").one()
        role.name = "行政自定义"
        role.data_scope = "ALL"
        menu = db_session.query(Menu).filter(Menu.path == "/ims/auth/org").one()
        menu.name = "组织同步（已改）"
        menu.sort = 42
        db_session.commit()

        assert seed_roles(env="test") == 0
        assert seed_menus(env="test") == 0
        db_session.refresh(role)
        db_session.refresh(menu)
        assert role.name == "行政自定义"
        assert role.data_scope == "ALL"
        assert menu.name == "组织同步（已改）"
        assert menu.sort == 42

    def test_admin_dict_and_param_edits_survive(self, db_session):
        from app.domains.sys.models import DictData, SysParam
        from tools.seed.dicts import seed_dicts
        from tools.seed.params import seed_params

        seed_dicts(env="test")
        seed_params(env="test")
        pending = db_session.query(DictData).filter(
            DictData.dict_type == "dict_org_sync_status",
            DictData.dict_value == "PENDING",
        ).one()
        pending.dict_label = "管理员改的待执行"
        param = db_session.query(SysParam).filter(
            SysParam.param_key == "dingtalk.sync.enabled",
        ).one()
        param.value = "false"
        db_session.commit()

        seed_dicts(env="test")
        seed_params(env="test")
        db_session.refresh(pending)
        db_session.refresh(param)
        assert pending.dict_label == "管理员改的待执行"
        assert param.value == "false"

    def test_default_grants_and_removed_grant_stays_removed(self, db_session):
        from app.domains.sys.models import Menu, Role, RoleMenu
        from tools.seed.grants import seed_grants
        from tools.seed.menus import seed_menus
        from tools.seed.roles import seed_roles

        seed_menus(env="test")
        seed_roles(env="test")
        assert seed_grants(env="test") > 0
        assert seed_grants(env="test") == 0

        def codes(role_key: str) -> set[str]:
            role = db_session.query(Role).filter(Role.role_key == role_key).one()
            rows = db_session.query(Menu).join(
                RoleMenu, RoleMenu.menu_id == Menu.id
            ).filter(RoleMenu.role_id == role.id).all()
            return {row.perm_code for row in rows if row.perm_code}

        assert codes("R2") == {
            "ims:system:org-sync:query",
            "ims:system:org-sync:export",
            "ims:auth:position-rule:query",
        }
        assert "ims:system:org-sync:run" in codes("R1")
        assert "ims:auth:position-rule:refresh" in codes("R1")
        assert "ims:system:org-sync:run" not in codes("R4")

        export = db_session.query(Menu).filter(
            Menu.perm_code == "ims:system:org-sync:export"
        ).one()
        r2 = db_session.query(Role).filter(Role.role_key == "R2").one()
        db_session.query(RoleMenu).filter(
            RoleMenu.role_id == r2.id,
            RoleMenu.menu_id == export.id,
        ).delete()
        extra = db_session.query(Menu).filter(
            Menu.perm_code == "ims:system:user:query"
        ).one()
        db_session.add(RoleMenu(tenant_id=1, role_id=r2.id, menu_id=extra.id))
        db_session.commit()

        assert seed_grants(env="test") == 0
        assert "ims:system:org-sync:export" not in codes("R2")
        assert "ims:system:user:query" in codes("R2")

    def test_untouched_b0a_org_menu_moves(self, db_session):
        from app.domains.sys.models import Menu
        from tools.seed.menus import seed_menus

        db_session.add(Menu(
            tenant_id=1,
            parent_id=0,
            type="MENU",
            name="组织同步",
            path="/system/org-sync",
            perm_code="ims:system:org-sync:query",
            sort=7,
            visible=True,
            status="ENABLED",
        ))
        db_session.commit()
        seed_menus(env="test")
        menu = db_session.query(Menu).filter(
            Menu.perm_code == "ims:system:org-sync:query"
        ).one()
        parent = db_session.query(Menu).filter(Menu.id == menu.parent_id).one()
        assert menu.path == "/ims/auth/org"
        assert menu.name == "组织架构同步"
        assert parent.path == "/ims/auth"
        assert menu.sort == 7

    def test_renamed_org_menu_is_not_moved(self, db_session):
        from app.domains.sys.models import Menu
        from tools.seed.menus import seed_menus

        db_session.add(Menu(
            tenant_id=1,
            parent_id=0,
            type="MENU",
            name="我的同步",
            path="/system/org-sync",
            perm_code="ims:system:org-sync:query",
            sort=7,
            visible=True,
            status="ENABLED",
        ))
        db_session.commit()
        seed_menus(env="test")
        menu = db_session.query(Menu).filter(
            Menu.perm_code == "ims:system:org-sync:query"
        ).one()
        assert menu.path == "/system/org-sync"
        assert menu.name == "我的同步"

    def test_missing_database_url_fails(self, db_session, monkeypatch):
        from app.db.session import _db_session
        from tools.seed.runner import run_seeds

        monkeypatch.delenv("IMS_DB_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        token = _db_session.set(None)
        try:
            assert run_seeds(env="test", only=["tenant"]) is False
        finally:
            _db_session.reset(token)


class TestE2EAccounts:
    """02 §0.2 账号只在 e2e 创建，再次执行不重置密码。"""

    def test_e2e_accounts_once(self, db_session):
        from app.domains.sys.models import Dept, Role, Tenant, User, UserRole
        from tools.seed.runner import run_seeds

        assert run_seeds(env="e2e") is True
        account = db_session.query(User).filter(User.username == "test_xz").one()
        assert account.nickname == "测试行政"
        assert bcrypt.checkpw(b"Test1234", account.password_hash.encode())
        role = db_session.query(Role).filter(Role.id == db_session.query(UserRole).filter(
            UserRole.user_id == account.id
        ).one().role_id).one()
        assert role.role_key == "R2"
        assert role.data_scope == "DEPT"
        dept = db_session.query(Dept).filter(Dept.id == account.main_dept_id).one()
        assert dept.name == "行政部"

        frozen = db_session.query(User).filter(User.username == "test_frozen").one()
        assert frozen.status == "FROZEN"
        reset = db_session.query(User).filter(User.username == "test_reset").one()
        assert reset.pwd_reset_required is True
        no_role = db_session.query(User).filter(User.username == "test_norole").one()
        assert db_session.query(UserRole).filter(UserRole.user_id == no_role.id).count() == 0

        other = db_session.query(User).filter(User.username == "test_t2").one()
        assert other.tenant_id == 2
        tenant = db_session.query(Tenant).filter(Tenant.id == 2).one()
        assert tenant.status == "DISABLED"

        account.password_hash = "changed"
        account.status = "FROZEN"
        db_session.commit()
        assert run_seeds(env="e2e") is True
        db_session.refresh(account)
        assert account.password_hash == "changed"
        assert account.status == "FROZEN"
        assert db_session.query(User).filter(User.username == "test_xz").count() == 1


class TestB1Backfill:
    """FP-B1-BG-08 历史回填只补空值。"""

    def test_backfill_rules_versions_and_events(self, db_session):
        from app.domains.sys.models import (
            DictData,
            OrgSyncEvent,
            PositionRoleRule,
            PositionRuleVersion,
            UserRole,
        )
        from app.services.b1_schema_backfill import backfill_b1_foundations
        from tests.support import rows

        person = rows.user(db_session, "supply_user", position_code="HOST")
        skipped_user = rows.user(db_session, "manual_user", position_code="HOST")
        empty_pos = rows.user(db_session, "empty_pos")
        rows.add(db_session, DictData(
            tenant_id=1, dict_type="dict_position", dict_value="HOST",
            dict_label="主播", color_type="primary", status="ENABLED",
        ))
        disabled = rows.add(db_session, PositionRoleRule(
            tenant_id=1, position_code="HOST", role_id=9, version=3,
            status="DISABLED", archived=False, rule_name=None,
        ))
        enabled = rows.add(db_session, PositionRoleRule(
            tenant_id=1, position_code="HOST", role_id=8, version=1,
            status="ENABLED", archived=False,
        ))
        rows.add(db_session, PositionRoleRule(
            tenant_id=1, position_code="HOST", role_id=11, version=0,
            status="ENABLED", archived=True, rule_name="归档",
        ))
        rows.add(db_session, PositionRoleRule(
            tenant_id=2, position_code="HOST", role_id=8, version=9,
            status="ENABLED", archived=False, rule_name="其他租户",
        ))
        named = rows.add(db_session, PositionRoleRule(
            tenant_id=1, position_code="LOCAL", role_id=4, version=1,
            status="ENABLED", archived=False, rule_name="已有名称",
        ))
        rows.add(db_session, PositionRuleVersion(
            tenant_id=1, rule_id=named.id, version=1, rule_name="已有名称",
            change_type="CREATE",
        ))
        link = rows.add(db_session, UserRole(
            tenant_id=1, user_id=person.id, role_id=8, source="DINGTALK_AUTO",
        ))
        kept = rows.add(db_session, UserRole(
            tenant_id=1, user_id=person.id, role_id=3, source="DINGTALK_AUTO",
            rule_id=named.id, rule_version=4,
        ))
        rows.add(db_session, UserRole(
            tenant_id=1, user_id=skipped_user.id, role_id=5, source="MANUAL",
        ))
        rows.add(db_session, UserRole(
            tenant_id=1, user_id=empty_pos.id, role_id=6, source="DINGTALK_AUTO",
        ))
        preset_version = rows.add(db_session, UserRole(
            tenant_id=1, user_id=skipped_user.id, role_id=8, source="DINGTALK_AUTO",
            rule_version=6,
        ))
        mapped = rows.add(db_session, OrgSyncEvent(
            tenant_id=1, event_id="e-hire", event_type="user_add_org", status="PENDING",
        ))
        unknown = rows.add(db_session, OrgSyncEvent(
            tenant_id=1, event_id="e-unknown", event_type="custom_event", status="PENDING",
        ))
        kept_event = rows.add(db_session, OrgSyncEvent(
            tenant_id=1, event_id="e-kept", event_type="user_leave_org",
            status="SUCCESS", biz_type="TRANSFER",
        ))
        deleted = rows.add(db_session, OrgSyncEvent(
            tenant_id=1, event_id="e-del", event_type="user_add_org", status="PENDING",
        ))
        deleted.deleted = deleted.id
        db_session.flush()

        first = backfill_b1_foundations(db_session)
        assert first["user_roles"] == 2
        assert first["rule_versions"] == 4
        assert first["events"] == 1
        db_session.refresh(link)
        db_session.refresh(enabled)
        db_session.refresh(named)
        db_session.refresh(mapped)
        db_session.refresh(preset_version)
        assert link.rule_id == enabled.id
        assert link.rule_version == 1
        assert kept.rule_id == named.id
        assert kept.rule_version == 4
        assert preset_version.rule_id == enabled.id
        assert preset_version.rule_version == 6
        assert enabled.rule_name == "主播"
        assert named.rule_name == "已有名称"
        version = db_session.query(PositionRuleVersion).filter(
            PositionRuleVersion.rule_id == enabled.id,
            PositionRuleVersion.version == 1,
        ).one()
        assert version.rule_name == "主播"
        assert version.change_type == "CREATE"
        assert mapped.biz_type == "HIRE"
        assert unknown.biz_type is None
        assert kept_event.biz_type == "TRANSFER"
        db_session.refresh(deleted)
        assert deleted.biz_type is None
        assert disabled.id != link.rule_id

        again = backfill_b1_foundations(db_session)
        assert again == {"user_roles": 0, "rule_versions": 0, "events": 0}

    def test_position_code_used_when_dict_missing(self, db_session):
        from app.domains.sys.models import PositionRoleRule
        from app.services.b1_schema_backfill import backfill_b1_foundations
        from tests.support import rows

        blank = rows.add(db_session, PositionRoleRule(
            tenant_id=1, position_code="NO_LABEL", role_id=1, version=1,
            status="ENABLED", archived=True, rule_name="",
        ))
        rows.add(db_session, PositionRoleRule(
            tenant_id=1, position_code="NO_DICT", role_id=2, version=2,
            status="ENABLED", archived=False,
        ))
        # 启用未归档的版本更高，应优先于归档行。上面 NO_DICT 只有一条。
        result = backfill_b1_foundations(db_session)
        assert result["rule_versions"] == 2
        db_session.refresh(blank)
        assert blank.rule_name == "NO_LABEL"

    def test_missing_user_is_skipped(self, db_session):
        from app.domains.sys.models import UserRole
        from app.services.b1_schema_backfill import backfill_b1_foundations
        from tests.support import rows

        rows.add(db_session, UserRole(
            tenant_id=1, user_id=99999, role_id=1, source="DINGTALK_AUTO",
        ))
        assert backfill_b1_foundations(db_session)["user_roles"] == 0

    def test_position_without_rule_is_skipped(self, db_session):
        """岗位没有供给规则时不写 rule_id，也不猜测一条。"""
        from app.domains.sys.models import UserRole
        from app.services.b1_schema_backfill import _pick_rule, backfill_b1_foundations
        from tests.support import rows

        person = rows.user(db_session, "no_rule_user", position_code="MISSING")
        link = rows.add(db_session, UserRole(
            tenant_id=1, user_id=person.id, role_id=1, source="DINGTALK_AUTO",
        ))
        assert backfill_b1_foundations(db_session)["user_roles"] == 0
        db_session.refresh(link)
        assert link.rule_id is None
        assert _pick_rule([], 1, "MISSING") is None
