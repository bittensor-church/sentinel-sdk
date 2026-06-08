"""Regression tests for BittensorProvider's historical-block workarounds."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sentinel.v1.providers.bittensor import BittensorProvider


@pytest.mark.parametrize(
    "raised",
    [
        ValueError("Invalid type for list data"),
        # New scalecodec versions raise TypeError from U16.process_encode when the
        # bittensor SDK passes [[netuid]] to the legacy `get_metagraph` runtime
        # call. See sentinel-sdk #ISSUE — at historical blocks where mech_id
        # didn't yet exist, the fallback path needs to catch this too.
        TypeError("int() argument must be a string, a bytes-like object or a real number, not 'list'"),
    ],
)
def test_get_metagraph_falls_back_to_legacy_on_known_sdk_errors(raised: Exception) -> None:
    """Both the old (ValueError) and new (TypeError) bittensor-SDK error shapes
    for the [[netuid]] vs [netuid] runtime-call bug must trigger the legacy
    fallback path."""
    provider = BittensorProvider(uri="ws://example/")
    sentinel_obj = object()

    class FakeSubtensor:
        def metagraph(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise raised

    provider._subtensor = FakeSubtensor()  # type: ignore[assignment]

    with patch.object(
        BittensorProvider,
        "_get_metagraph_legacy",
        return_value=sentinel_obj,
    ) as legacy:
        result = provider.get_metagraph(netuid=78, block_number=6_000_000, mechid=0)

    assert result is sentinel_obj
    legacy.assert_called_once_with(78, 6_000_000, 0, lite=False)


def test_get_metagraph_reraises_unrelated_errors() -> None:
    """Errors that don't match the known SDK-bug fingerprints should propagate."""
    provider = BittensorProvider(uri="ws://example/")

    class FakeSubtensor:
        def metagraph(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise ValueError("connection refused")

    provider._subtensor = FakeSubtensor()  # type: ignore[assignment]

    with pytest.raises(ValueError, match="connection refused"):
        provider.get_metagraph(netuid=1, block_number=1, mechid=0)


def test_get_mechanism_count_passes_block_through() -> None:
    """`block_number` must propagate to the SDK so historical blocks return the
    correct count (1 when MechanismCountCurrent storage doesn't yet exist)."""
    provider = BittensorProvider(uri="ws://example/")
    seen: dict[str, object] = {}

    class FakeSubtensor:
        def get_mechanism_count(self, **kwargs):  # noqa: ANN003
            seen.update(kwargs)
            return 1

    provider._subtensor = FakeSubtensor()  # type: ignore[assignment]

    assert provider.get_mechanism_count(netuid=78, block_number=6_000_000) == 1
    assert seen == {"netuid": 78, "block": 6_000_000}
