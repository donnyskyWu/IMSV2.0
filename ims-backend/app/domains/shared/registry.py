# app/domains/shared/registry.py - Reference registry vs ER and table catalog (FP-B05)
"""Load the reference registry and compare it with docs/ER.md and the table catalog."""

from pathlib import Path

SHARED_TABLES: dict[str, str] = {
    "ims_org_company": "公司",
    "ims_master_realname": "实名人",
    "ims_master_sim_card": "手机卡",
    "ims_master_phone": "手机",
    "ims_master_cert": "证件",
    "ims_account_platform": "平台账号",
    "ims_account_personal": "个人账号",
    "ims_ipg_group": "IP组",
    "ims_ipg_member": "IP组成员",
    "ims_master_author": "作者",
    "ims_live_session": "场次",
    "ims_comp_account": "外部账号",
}

ALLOWED_PREFIXES = (
    "ims_org_",
    "ims_master_",
    "ims_account_",
    "ims_ipg_",
    "ims_live_",
    "ims_comp_",
)

# Relations that delete-protection and the ER document must agree on.
RELATIONS: set[tuple[str, str]] = {
    ("ims_ipg_member.group_id", "ims_ipg_group.id"),
    ("ims_master_realname.user_id", "ims_sys_user.id"),
    ("ims_master_phone.sim_card_id", "ims_master_sim_card.id"),
    ("ims_master_cert.realname_id", "ims_master_realname.id"),
    ("ims_account_personal.realname_id", "ims_master_realname.id"),
    ("ims_master_author.realname_id", "ims_master_realname.id"),
    ("ims_live_session.author_id", "ims_master_author.id"),
    ("ims_account_platform.author_id", "ims_master_author.id"),
    ("ims_comp_account.company_id", "ims_org_company.id"),
}

EXTERNAL_FIELDS = {
    "football_room_id": True,
}


def repo_root() -> Path:
    """Workspace root (parent of ims-backend)."""
    return Path(__file__).resolve().parents[4]


def parse_er(path: Path | None = None) -> set[tuple[str, str]]:
    """Parse ``source -> target`` lines from docs/ER.md."""
    er_path = path or (repo_root() / "docs" / "ER.md")
    relations: set[tuple[str, str]] = set()
    for raw in er_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("-").strip()
        if "->" not in line:
            continue
        left, right = [part.strip() for part in line.split("->", 1)]
        relations.add((left, right))
    return relations


def parse_catalog(path: Path | None = None) -> dict[str, str]:
    """Parse ``table | label`` rows from the table catalog."""
    catalog = path or (repo_root() / "docs" / "表名登记册.md")
    found: dict[str, str] = {}
    for raw in catalog.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or not cells[0].startswith("ims_"):
            continue
        found[cells[0]] = cells[1]
    return found


def assert_er_matches_registry(path: Path | None = None) -> None:
    """Every ER relation is registered, and every registration is in the ER."""
    documented = parse_er(path)
    if documented != RELATIONS:
        missing = RELATIONS - documented
        extra = documented - RELATIONS
        raise AssertionError(f"ER mismatch missing={missing} extra={extra}")


def assert_catalog(path: Path | None = None) -> None:
    """The 12 shared tables are catalogued and use an allowed prefix."""
    found = parse_catalog(path)
    missing = [name for name in SHARED_TABLES if name not in found]
    if missing:
        raise AssertionError(f"catalog missing {missing}")
    for name in SHARED_TABLES:
        if not name.startswith(ALLOWED_PREFIXES):
            raise AssertionError(f"prefix not allowed: {name}")
