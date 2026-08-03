"""Regression tests for BittensorProvider's historical-block workarounds."""

from __future__ import annotations

from datetime import UTC, datetime
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


class _ScaleValue:
    """Stand-in for a substrate SCALE object, which wraps its payload in `.value`."""

    def __init__(self, value: object) -> None:
        self.value = value


class _FakeSubstrate:
    def __init__(self, emission_entries: list[tuple[object, object]] | None = None) -> None:
        self._emission_entries = emission_entries or []
        self.query_map_calls: list[tuple[str, str, object]] = []

    def query_map(self, module, storage_function, block_hash):  # noqa: ANN001, ANN201
        self.query_map_calls.append((module, storage_function, block_hash))
        return list(self._emission_entries)


class _FakeSubnetInfo:
    def __init__(self, netuid: int) -> None:
        self.netuid = netuid


def test_get_block_timestamp_returns_the_sdk_datetime() -> None:
    """The bittensor SDK already returns a tz-aware UTC datetime; pass it through."""
    provider = BittensorProvider(uri="ws://example/")
    expected = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    seen: dict[str, object] = {}

    class FakeSubtensor:
        def get_timestamp(self, **kwargs):  # noqa: ANN003
            seen.update(kwargs)
            return expected

    provider._subtensor = FakeSubtensor()  # type: ignore[assignment]

    assert provider.get_block_timestamp(6_000_000) == expected
    assert seen == {"block": 6_000_000}


def test_get_block_timestamp_returns_none_when_the_block_state_is_gone() -> None:
    """A pruned block is a routine miss, not a crash — the caller decides what to do."""
    provider = BittensorProvider(uri="ws://example/")

    class FakeSubtensor:
        def get_timestamp(self, **kwargs):  # noqa: ANN003
            raise ValueError("State already discarded")

    provider._subtensor = FakeSubtensor()  # type: ignore[assignment]

    assert provider.get_block_timestamp(6_000_000) is None


def test_get_subnet_emission_enabled_defaults_subnets_without_an_entry_to_enabled() -> None:
    """Only disabled subnets carry an explicit storage entry; the rest default to True."""
    provider = BittensorProvider(uri="ws://example/")
    substrate = _FakeSubstrate([(_ScaleValue(2), _ScaleValue(False))])

    class FakeSubtensor:
        substrate = None

        def get_block_hash(self, block_number):  # noqa: ANN001, ANN201
            return "0xabc"

        def get_all_subnets_info(self):  # noqa: ANN201
            return [_FakeSubnetInfo(n) for n in (0, 1, 2, 3)]

    fake = FakeSubtensor()
    fake.substrate = substrate  # type: ignore[assignment]
    provider._subtensor = fake  # type: ignore[assignment]

    # The root subnet is included: filtering it is the caller's policy, not the
    # provider's — this layer reports what the chain holds.
    assert provider.get_subnet_emission_enabled(6_000_000) == {0: True, 1: True, 2: False, 3: True}
    assert substrate.query_map_calls == [("SubtensorModule", "SubnetEmissionEnabled", "0xabc")]


def test_get_subnet_emission_enabled_ignores_entries_for_unregistered_subnets() -> None:
    """A storage entry for a subnet the chain no longer lists must not invent a netuid."""
    provider = BittensorProvider(uri="ws://example/")
    substrate = _FakeSubstrate([(_ScaleValue(2), _ScaleValue(False)), (_ScaleValue(77), _ScaleValue(False))])

    class FakeSubtensor:
        substrate = None

        def get_block_hash(self, block_number):  # noqa: ANN001, ANN201
            return "0xabc"

        def get_all_subnets_info(self):  # noqa: ANN201
            return [_FakeSubnetInfo(n) for n in (1, 2)]

    fake = FakeSubtensor()
    fake.substrate = substrate  # type: ignore[assignment]
    provider._subtensor = fake  # type: ignore[assignment]

    assert provider.get_subnet_emission_enabled(6_000_000) == {1: True, 2: False}


def test_get_subnet_emission_enabled_returns_none_when_the_chain_read_fails() -> None:
    """A half-read map would look like 'everything enabled' — return None instead."""
    provider = BittensorProvider(uri="ws://example/")

    class FakeSubtensor:
        substrate = _FakeSubstrate([(_ScaleValue(2), _ScaleValue(False))])

        def get_block_hash(self, block_number):  # noqa: ANN001, ANN201
            return "0xabc"

        def get_all_subnets_info(self):  # noqa: ANN201
            raise ConnectionError("websocket closed")

    provider._subtensor = FakeSubtensor()  # type: ignore[assignment]

    assert provider.get_subnet_emission_enabled(6_000_000) is None
