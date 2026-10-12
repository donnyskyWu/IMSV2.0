"""
Seed runner (FP-H05-01).

Orchestrates all seed operations in correct order.
连接串只从 IMS_DB_URL / DATABASE_URL 读取，由应用配置和 use_db_session 使用。
"""

from typing import Optional

from tools.seed.access import seed_access
from tools.seed.depts import seed_depts
from tools.seed.dicts import seed_dicts
from tools.seed.grants import seed_grants
from tools.seed.menus import seed_menus
from tools.seed.params import seed_params
from tools.seed.roles import seed_roles
from tools.seed.tenant import seed_tenant
from tools.seed.users import seed_users


def run_seeds(
    env: str,
    only: Optional[list[str]] = None,
    dry_run: bool = False,
) -> bool:
    """
    Run all or selected seed operations.

    Order matters:
    1. tenant - Platform tenant must exist first
    2. dicts - Dictionaries for status values
    3. params - System parameters
    4. menus - Menu tree with permission codes
    5. roles - Standard roles with data scope
    6. grants - B1 default role-menu grants (insert-if-absent)
    7. depts - Root, system department, and e2e departments
    8. access - Default package, package menus, R1 role menus
    9. users - E2E accounts when env=e2e

    access 放在菜单和 B1 授权之后，这样新菜单会进默认套餐，/me 才能看见。
    """
    all_seeds = [
        "tenant", "dicts", "params", "menus", "roles", "grants", "depts", "access", "users",
    ]

    seeds_to_run = only if only else all_seeds

    for seed_name in seeds_to_run:
        if seed_name not in all_seeds:
            print(f"ERROR: Unknown seed category: {seed_name}")
            print(f"Valid categories: {', '.join(all_seeds)}")
            return False

    print(f"=== Running seeds for env={env} ===")
    if dry_run:
        print("(DRY RUN - no changes will be made)")
    print(f"Categories: {', '.join(seeds_to_run)}")
    print()

    seed_functions = {
        "tenant": seed_tenant,
        "dicts": seed_dicts,
        "params": seed_params,
        "menus": seed_menus,
        "roles": seed_roles,
        "grants": seed_grants,
        "depts": seed_depts,
        "access": seed_access,
        "users": seed_users,
    }

    from app.db.session import _db_session, init_db, use_db_session

    if not dry_run and _db_session.get() is None:
        init_db()

    def _execute() -> dict[str, int]:
        executed: dict[str, int] = {}
        for name in all_seeds:
            if name not in seeds_to_run:
                continue
            print(f"--- Seeding {name} ---")
            count = seed_functions[name](env=env, dry_run=dry_run)
            executed[name] = count
            print(f"  {name}: {count} records")
        return executed

    try:
        if dry_run:
            results = _execute()
        else:
            with use_db_session():
                results = _execute()
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return False

    print()
    print("=== Seed Summary ===")
    for name, count in results.items():
        print(f"  {name}: {count}")
    print("=== Done ===")
    return True
