from typing import Any

import pytest

from tests.unit.v1.factories import ExtrinsicDTOFactory, HyperparamExtrinsicDTOFactory
from tests.unit.v1.providers import FakeBittensorProvider


@pytest.fixture
def fake_provider() -> FakeBittensorProvider:
    """Provide a fresh FakeBittensorProvider instance for each test."""
    return FakeBittensorProvider()


@pytest.fixture
def extrinsics_response() -> list[dict[str, Any]]:
    extrinsics = ExtrinsicDTOFactory.batch(5)
    hyperparam_extrinsics = [
        HyperparamExtrinsicDTOFactory.build_for_function(
            "sudo_set_rho",
            netuid=5,
            rho=100,
        ),
        HyperparamExtrinsicDTOFactory.build_for_function(
            "sudo_set_alpha_values",
            netuid=1,
            alpha_low=100,
            alpha_high=900,
        ),
    ]

    extrinsics += hyperparam_extrinsics
    return [ext.model_dump() for ext in extrinsics]
