"""Regression tests for BittensorProvider's handling of the bittensor SDK."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from sentinel.v1.providers.bittensor import BittensorProvider


class _FakeSnapshot:
    """Stand-in for the SDK's block-pinned snapshot (``Subtensor.at(block)``)."""

    def __init__(self, block: int | None, owner: _FakeSubtensor) -> None:
        self.block = block
        self._owner = owner

    def read(self, name: str, **params: Any) -> Any:
        self._owner.reads.append((name, self.block, params))
        return self._owner.read_results[name]

    def query(self, item: Any, params: list | None = None) -> Any:
        self._owner.query_calls.append((item.name, self.block, params))
        return self._owner.storage[item.name]

    def query_map(self, item: Any) -> list[tuple[Any, Any]]:
        self._owner.query_map_calls.append((item.container, item.name, self.block))
        result = self._owner.storage[item.name]
        if isinstance(result, Exception):
            raise result
        return list(result)


class _FakeSubtensor:
    """Minimal stand-in for ``bittensor.Subtensor`` covering the paths under test."""

    def __init__(
        self,
        *,
        storage: dict[str, Any] | None = None,
        read_results: dict[str, Any] | None = None,
        timestamp: Any = None,
    ) -> None:
        self.storage = storage or {}
        self.read_results = read_results or {}
        self._timestamp = timestamp
        self.reads: list[tuple[str, int | None, dict[str, Any]]] = []
        self.query_map_calls: list[tuple[str, str, int | None]] = []
        self.query_calls: list[tuple[str, int | None, list | None]] = []
        self.timestamp_calls: list[int | None] = []

    def at(self, block: int | None = None) -> _FakeSnapshot:
        return _FakeSnapshot(block, self)

    def read(self, name: str, **params: Any) -> Any:
        self.reads.append((name, None, params))
        return self.read_results[name]

    def timestamp(self, block: int | None = None) -> Any:
        self.timestamp_calls.append(block)
        if isinstance(self._timestamp, Exception):
            raise self._timestamp
        return self._timestamp


def _provider_with(subtensor: _FakeSubtensor) -> BittensorProvider:
    provider = BittensorProvider(uri="ws://example/")
    provider._subtensor = subtensor  # type: ignore[assignment]
    return provider


def test_get_mechanism_count_pins_the_read_to_the_block() -> None:
    """`block_number` must pin the read so historical blocks return the count that
    applied then (1 before `MechanismCountCurrent` storage existed)."""
    subtensor = _FakeSubtensor(read_results={"mechanism_count": 1})
    provider = _provider_with(subtensor)

    assert provider.get_mechanism_count(netuid=78, block_number=6_000_000) == 1
    assert subtensor.reads == [("mechanism_count", 6_000_000, {"netuid": 78})]


def test_get_mechanism_count_without_a_block_reads_chain_head() -> None:
    """Omitting the block must query head rather than pinning to block None."""
    subtensor = _FakeSubtensor(read_results={"mechanism_count": 3})
    provider = _provider_with(subtensor)

    assert provider.get_mechanism_count(netuid=78) == 3
    assert subtensor.reads == [("mechanism_count", None, {"netuid": 78})]


def test_get_block_timestamp_returns_the_sdk_datetime() -> None:
    """The bittensor SDK already returns a tz-aware UTC datetime; pass it through."""
    expected = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    subtensor = _FakeSubtensor(timestamp=expected)
    provider = _provider_with(subtensor)

    assert provider.get_block_timestamp(6_000_000) == expected
    assert subtensor.timestamp_calls == [6_000_000]


def test_get_block_timestamp_returns_none_when_the_block_state_is_gone() -> None:
    """A pruned block is a routine miss, not a crash — the caller decides what to do."""
    provider = _provider_with(_FakeSubtensor(timestamp=ValueError("State already discarded")))

    assert provider.get_block_timestamp(6_000_000) is None


def test_get_block_timestamp_rejects_the_zero_storage_default() -> None:
    """Past its state window the public finney node answers `Timestamp.Now` with the
    storage default (0) instead of erroring. Decoded that is 1970-01-01 — reporting it
    as a real block time would silently poison anything plotted against it."""
    provider = _provider_with(_FakeSubtensor(timestamp=datetime.fromtimestamp(0, tz=UTC)))

    assert provider.get_block_timestamp(6_000_000) is None


def test_get_subnet_emission_enabled_defaults_subnets_without_an_entry_to_enabled() -> None:
    """Only disabled subnets carry an explicit storage entry; the rest default to True."""
    provider = _provider_with(
        _FakeSubtensor(
            storage={
                "SubnetEmissionEnabled": [(2, False)],
                "NetworksAdded": [(0, True), (1, True), (2, True), (3, True)],
            },
        ),
    )

    # The root subnet is included: filtering it is the caller's policy, not the
    # provider's — this layer reports what the chain holds.
    assert provider.get_subnet_emission_enabled(6_000_000) == {0: True, 1: True, 2: False, 3: True}


def test_get_subnet_emission_enabled_pins_both_reads_to_the_block() -> None:
    """Reading either map at head would mix two different chain states together."""
    subtensor = _FakeSubtensor(
        storage={"SubnetEmissionEnabled": [], "NetworksAdded": [(1, True)]},
    )
    provider = _provider_with(subtensor)

    provider.get_subnet_emission_enabled(6_000_000)

    assert subtensor.query_map_calls == [
        ("SubtensorModule", "SubnetEmissionEnabled", 6_000_000),
        ("SubtensorModule", "NetworksAdded", 6_000_000),
    ]


def test_get_subnet_emission_enabled_excludes_subnet_registered_after_historical_block() -> None:
    """A subnet present at head but absent at the requested block must not be invented."""
    provider = _provider_with(
        _FakeSubtensor(
            storage={"SubnetEmissionEnabled": [], "NetworksAdded": [(1, True)]},
        ),
    )

    assert provider.get_subnet_emission_enabled(6_000_000) == {1: True}


def test_get_subnet_emission_enabled_includes_subnet_deregistered_after_historical_block() -> None:
    """A subnet absent at head but registered at the requested block must remain in the snapshot."""
    provider = _provider_with(
        _FakeSubtensor(
            storage={
                "SubnetEmissionEnabled": [(1, False)],
                "NetworksAdded": [(1, True), (2, True)],
            },
        ),
    )

    assert provider.get_subnet_emission_enabled(6_000_000) == {1: False, 2: True}


def test_get_subnet_emission_enabled_returns_none_when_the_chain_read_fails() -> None:
    """A half-read map would look like 'everything enabled' — return None instead."""
    provider = _provider_with(
        _FakeSubtensor(
            storage={
                "SubnetEmissionEnabled": [(2, False)],
                "NetworksAdded": ConnectionError("websocket closed"),
            },
        ),
    )

    assert provider.get_subnet_emission_enabled(6_000_000) is None


def test_get_events_rejects_a_hash_the_provider_never_issued() -> None:
    """v11 addresses blocks by number, so an unknown hash cannot be resolved — say so
    rather than silently reporting a block with no events."""
    provider = _provider_with(_FakeSubtensor())

    with pytest.raises(ValueError, match="Unknown block hash"):
        provider.get_events("0xdeadbeef")


def test_get_events_groups_by_extrinsic_index() -> None:
    """Events raised outside an extrinsic (block initialization/finalization) carry no
    index and belong to no extrinsic."""
    provider = _provider_with(_FakeSubtensor())
    provider._block_number_by_hash["0xabc"] = 42

    events: list[dict[str, Any]] = [
        {"phase": "Initialization", "extrinsic_idx": None, "module_id": "Balances", "event_id": "Issued"},
        {"phase": "ApplyExtrinsic", "extrinsic_idx": 0, "module_id": "System", "event_id": "ExtrinsicSuccess"},
        {"phase": "ApplyExtrinsic", "extrinsic_idx": 1, "module_id": "System", "event_id": "ExtrinsicFailed"},
        {"phase": "ApplyExtrinsic", "extrinsic_idx": 1, "module_id": "Balances", "event_id": "Withdraw"},
    ]

    def query(item: Any, block: int | None = None) -> list[dict[str, Any]]:
        assert block == 42
        return events

    provider._subtensor.query = query  # type: ignore[union-attr,method-assign]

    grouped = provider.get_extrinsic_events("0xabc")

    assert sorted(grouped) == [0, 1]
    assert len(grouped[1]) == 2
    assert provider.get_extrinsic_status("0xabc", 0) == ("Success", None)
    assert provider.get_extrinsic_status("0xabc", 1)[0] == "Failed"
    assert provider.get_extrinsic_status("0xabc", 7) == ("Unknown", None)


def test_get_block_hash_records_the_number_so_events_can_be_read_back() -> None:
    """The extractors resolve a number to a hash, then read events by that hash; the
    provider has to remember the pairing to answer the second call."""
    provider = _provider_with(_FakeSubtensor())
    block_info = SimpleNamespace(number=42, hash="0xabc", timestamp=None, extrinsics=[])
    provider._subtensor.block_info = lambda block=None: block_info  # type: ignore[union-attr,method-assign]

    assert provider.get_block_hash(42) == "0xabc"
    assert provider._block_number_for_hash("0xabc") == 42


def test_get_extrinsics_flattens_the_call_into_each_record() -> None:
    """v11 returns extrinsics as plain dicts with the call nested; consumers expect
    call_module/call_function alongside the signing fields."""
    provider = _provider_with(_FakeSubtensor())
    block_info = SimpleNamespace(
        number=42,
        hash="0xabc",
        timestamp=None,
        extrinsics=[
            {
                "extrinsic_hash": "0xext",
                "address": "5Signer",
                "signature": {"Sr25519": "0xsig"},
                "nonce": 7,
                "tip": 0,
                "call": {
                    "call_module": "SubtensorModule",
                    "call_function": "set_weights",
                    "call_args": [{"name": "netuid", "value": 1}],
                },
            },
        ],
    )
    provider._subtensor.block_info = lambda block=None: block_info  # type: ignore[union-attr,method-assign]

    provider.get_block_hash(42)
    extrinsics = provider.get_extrinsics("0xabc")

    assert extrinsics == [
        {
            "index": 0,
            "extrinsic_hash": "0xext",
            "call_module": "SubtensorModule",
            "call_function": "set_weights",
            "call_args": [{"name": "netuid", "value": 1}],
            "address": "5Signer",
            "signature": {"Sr25519": "0xsig"},
            "nonce": 7,
            "tip": 0,
        },
    ]


_REGISTRATION_STORAGE = {
    "Rho": 10,
    "Difficulty": 10_000_000,
    "MinDifficulty": 10_000_000,
    "MaxDifficulty": 10**18,
    "AdjustmentInterval": 112,
    "AdjustmentAlpha": 17_893_341_751_498_265_066,
}


def test_get_subnet_hyperparams_pins_the_read_to_the_block() -> None:
    """Hyperparameters change over time, so the block must reach the SDK."""
    subtensor = _FakeSubtensor(
        read_results={"subnet_hyperparameters": {"tempo": 360}},
        storage=dict(_REGISTRATION_STORAGE),
    )
    provider = _provider_with(subtensor)

    hyperparams = provider.get_subnet_hyperparams(block_number=6_000_000, netuid=1)

    assert hyperparams is not None
    assert hyperparams["tempo"] == 360
    assert subtensor.reads == [("subnet_hyperparameters", 6_000_000, {"netuid": 1})]
    # Every storage read must be pinned to the same block as the main read.
    assert {block for _, block, _ in subtensor.query_calls} == {6_000_000}


def test_get_subnet_hyperparams_restores_the_fields_v11_dropped() -> None:
    """v11's `subnet_hyperparameters` read no longer carries the registration and
    difficulty parameters, but consumers (and HyperparametersDTO) still require
    them, so the provider reads them back from storage."""
    provider = _provider_with(
        _FakeSubtensor(
            read_results={"subnet_hyperparameters": {"tempo": 360}},
            storage=dict(_REGISTRATION_STORAGE),
        ),
    )

    hyperparams = provider.get_subnet_hyperparams(block_number=6_000_000, netuid=1)

    assert hyperparams is not None
    assert hyperparams["rho"] == 10
    assert hyperparams["difficulty"] == 10_000_000
    assert hyperparams["min_difficulty"] == 10_000_000
    assert hyperparams["max_difficulty"] == 10**18
    assert hyperparams["adjustment_interval"] == 112
    assert hyperparams["adjustment_alpha"] == 17_893_341_751_498_265_066


def test_get_subnet_hyperparams_aliases_the_renamed_fields() -> None:
    """v11 renamed two hyperparameters; consumers still ask for the old names."""
    provider = _provider_with(
        _FakeSubtensor(
            read_results={
                "subnet_hyperparameters": {"max_weights_limit": 65535, "commit_reveal_period": 1},
            },
            storage=dict(_REGISTRATION_STORAGE),
        ),
    )

    hyperparams = provider.get_subnet_hyperparams(block_number=6_000_000, netuid=1)

    assert hyperparams is not None
    assert hyperparams["max_weight_limit"] == 65535
    assert hyperparams["commit_reveal_weights_interval"] == 1
    # The v11 names stay too — nothing is renamed away.
    assert hyperparams["max_weights_limit"] == 65535
    assert hyperparams["commit_reveal_period"] == 1


def test_get_subnet_hyperparams_returns_none_when_the_read_fails() -> None:
    """A partial set would fail DTO validation downstream with a confusing error."""
    provider = _provider_with(
        _FakeSubtensor(read_results={"subnet_hyperparameters": {"tempo": 360}}, storage={}),
    )

    assert provider.get_subnet_hyperparams(block_number=6_000_000, netuid=1) is None
