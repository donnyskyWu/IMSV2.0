# tools/e2e_seed/__init__.py - E2E test data seeding
"""
E2E test data seeding utilities.

Each module provides seed_<module>_data and clear_<module>_data functions.
Fixed ID ranges per module for isolation:
- B21: 90001~90099
"""

from tools.e2e_seed.b21 import FIXTURE as B21_FIXTURE
from tools.e2e_seed.b21 import clear_b21_data, seed_b21_data

__all__ = [
    "B21_FIXTURE",
    "seed_b21_data",
    "clear_b21_data",
]
