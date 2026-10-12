"""
Seed runner (FP-H05-01).

Orchestrates all seed operations in correct order.
"""

from typing import Optional

from tools.seed.dicts import seed_dicts
from tools.seed.params import seed_params
from tools.seed.tenant import seed_tenant
from tools.seed.depts import seed_depts
from tools.seed.menus import seed_menus
from tools.seed.roles import seed_roles


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
    5. roles - Standard roles with menu assignments
    6. depts - Root and system departments
    
    Args:
        env: Environment (dev/test/e2e/prod)
        only: List of seed categories to run, or None for all
        dry_run: If True, show what would be done without executing
        
    Returns:
        True if all seeds succeeded
    """
    all_seeds = ["tenant", "dicts", "params", "menus", "roles", "depts"]
    
    # Determine which seeds to run
    seeds_to_run = only if only else all_seeds
    
    # Validate
    for s in seeds_to_run:
        if s not in all_seeds:
            print(f"ERROR: Unknown seed category: {s}")
            print(f"Valid categories: {', '.join(all_seeds)}")
            return False
    
    print(f"=== Running seeds for env={env} ===")
    if dry_run:
        print("(DRY RUN - no changes will be made)")
    print(f"Categories: {', '.join(seeds_to_run)}")
    print()
    
    # Run seeds in order
    seed_functions = {
        "tenant": seed_tenant,
        "dicts": seed_dicts,
        "params": seed_params,
        "menus": seed_menus,
        "roles": seed_roles,
        "depts": seed_depts,
    }
    
    results = {}
    for seed_name in all_seeds:
        if seed_name not in seeds_to_run:
            continue
            
        print(f"--- Seeding {seed_name} ---")
        try:
            func = seed_functions[seed_name]
            count = func(env=env, dry_run=dry_run)
            results[seed_name] = count
            print(f"  {seed_name}: {count} records")
        except Exception as e:
            print(f"  ERROR: {e}")
            return False
    
    print()
    print("=== Seed Summary ===")
    for name, count in results.items():
        print(f"  {name}: {count}")
    print("=== Done ===")
    
    return True
