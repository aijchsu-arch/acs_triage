import pytest

from acs_triage.rules import RulesEngine


@pytest.fixture(scope="session")
def engine() -> RulesEngine:
    return RulesEngine()
