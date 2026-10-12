# tools/seed - Seed data management (FP-H05-01)
"""
Seed script for IMS framework data.

Usage:
    python -m tools.seed --env <dev|test|e2e|prod> [--only menus,dicts,...]

Per FP-H05-01:
- Standard roles R1-R11 with permissions, menus, data scope
- Menu tree with all ims:* permission codes
- Dictionaries per FP-B07-02
- System parameters per FP-B07-02
- Platform tenant (id=1) and super admin
- Root department and "待分配" system department

Rules:
- Upsert by unique business key, idempotent
- Does not overwrite admin-modified fields (name, sort, color)
- E2E accounts use --env e2e with "测试-" prefix
"""
