import pytest

from tests.unit.v1.providers import FakeBittensorProvider


@pytest.fixture
def fake_provider() -> FakeBittensorProvider:
    """Provide a fresh FakeBittensorProvider instance for each test."""
    return FakeBittensorProvider()
