# app/integrations/adapters.py - Select real or mock adapters from config (FP-H04)
"""Mode ``real`` selects the real implementation without a code edit."""


class MockFootballWeb:
    """Mock football web adapter."""

    name = "mock"


class RealFootballWeb:
    """Real football web adapter selected by configuration."""

    name = "real"


def build_football_web(mode: str) -> MockFootballWeb | RealFootballWeb:
    if mode == "real":
        return RealFootballWeb()
    return MockFootballWeb()
