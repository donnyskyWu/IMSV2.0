#!/usr/bin/env python3
"""
Seed script entry point (FP-H05-01).

Usage:
    python -m tools.seed --env dev [--only dicts,params,menus,roles,tenant]
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Seed IMS framework data (FP-H05-01)"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "test", "e2e", "prod"],
        help="Target environment"
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated list: dicts,params,menus,roles,tenant,depts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be seeded without executing"
    )

    args = parser.parse_args()

    # 先写环境再导入种子，避免 get_settings() 按旧环境缓存。
    os.environ["IMS_ENV"] = args.env
    from tools.seed.runner import run_seeds

    # Parse --only list
    only = None
    if args.only:
        only = [s.strip() for s in args.only.split(",")]

    # Run seeds
    success = run_seeds(
        env=args.env,
        only=only,
        dry_run=args.dry_run,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
