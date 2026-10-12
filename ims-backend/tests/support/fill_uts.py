# tests/support/fill_uts.py - Dispatch a spec UT id to a real assertion
"""Each former ``pass`` body calls ``run`` so the UT id is backed by real checks."""

from tests.support.case_b import CASES as B_CASES
from tests.support.case_rest import CASES as REST_CASES

CASES = {**B_CASES, **REST_CASES}


def run(ut_id: str, db_session=None, test_context=None, fixed_time=None) -> None:
    """Execute the real assertion registered for ``ut_id``."""
    case = CASES[ut_id]
    case(db_session, test_context, fixed_time)
