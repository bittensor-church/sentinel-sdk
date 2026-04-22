"""Unit tests for MetagraphExtractor field extraction.

These tests construct a minimal stand-in for ``bittensor.Metagraph`` and pass
it directly to private extractor helpers. The goal is to verify that fields
the extractor previously dropped — ``alpha_stake`` and ``alpha_out_emission``
— are now read into the DTO.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.services.extractors.metagraph.dto import Block, MechanismMetrics
from sentinel.v1.services.extractors.metagraph.extractor import MetagraphExtractor


def _fake_axon(hotkey: str = "5HOTKEY", coldkey: str = "5COLDKEY") -> SimpleNamespace:
    return SimpleNamespace(
        hotkey=hotkey,
        coldkey=coldkey,
        ip_str=lambda: "/ip4/0.0.0.0/tcp/0",
    )


def _fake_metagraph(
    *,
    netuid: int = 1,
    n: int = 2,
    alpha_stake: list[float] | None = None,
    alpha_out_emission: float | None = None,
) -> SimpleNamespace:
    """Build a SimpleNamespace shaped like bittensor.Metagraph for the tested code paths."""
    stakes = [10.0, 20.0]
    return SimpleNamespace(
        netuid=netuid,
        name="test",
        n=n,
        stake=stakes,
        alpha_stake=alpha_stake,
        ranks=[0.1, 0.2],
        trust=[0.5, 0.6],
        emission=[1.0, 2.0],
        active=[True, True],
        validator_permit=[True, False],
        block_at_registration=[100, 200],
        axons=[_fake_axon(), _fake_axon()],
        emissions=(SimpleNamespace(alpha_out_emission=alpha_out_emission) if alpha_out_emission is not None else None),
        block=SimpleNamespace(item=lambda: 1234),
        # Attributes used by helpers but not central to these tests:
        weights=None,
        bonds=None,
        hparams=None,
    )


def _make_extractor() -> MetagraphExtractor:
    # Provider is unused in the helpers under test.
    return MetagraphExtractor(
        subtensor=cast(BlockchainProvider, None),
        block_number=1234,
        netuid=1,
        lite=True,
    )


class TestAlphaFields:
    def test_alpha_stake_is_extracted_per_uid(self):
        mg = _fake_metagraph(alpha_stake=[7.5, 9.25])
        block = Block(block_number=1234, timestamp=datetime.now(tz=UTC))
        extractor = _make_extractor()

        snap_uid_0 = extractor._build_single_neuron_snapshot(
            metagraph=mg,
            uid=0,
            total_subnet_stake=30.0,
            mechanisms=[],
            block=block,
        )
        snap_uid_1 = extractor._build_single_neuron_snapshot(
            metagraph=mg,
            uid=1,
            total_subnet_stake=30.0,
            mechanisms=[],
            block=block,
        )

        assert snap_uid_0.alpha_stake == 7.5
        assert snap_uid_1.alpha_stake == 9.25

    def test_alpha_stake_defaults_to_zero_when_metagraph_omits_it(self):
        # Pylon may not always populate alpha_stake; older bittensor versions don't either.
        mg = _fake_metagraph(alpha_stake=None)
        block = Block(block_number=1234, timestamp=datetime.now(tz=UTC))
        extractor = _make_extractor()

        snap = extractor._build_single_neuron_snapshot(
            metagraph=mg,
            uid=0,
            total_subnet_stake=30.0,
            mechanisms=[],
            block=block,
        )

        assert snap.alpha_stake == 0.0

    def test_alpha_out_emission_is_extracted(self):
        mg = _fake_metagraph(alpha_out_emission=1.234)
        extractor = _make_extractor()

        subnet = extractor._build_subnet(mg)

        assert subnet.alpha_out_emission == 1.234

    def test_alpha_out_emission_defaults_to_zero_when_emissions_object_missing(self):
        mg = _fake_metagraph(alpha_out_emission=None)
        extractor = _make_extractor()

        subnet = extractor._build_subnet(mg)

        assert subnet.alpha_out_emission == 0.0

    def test_existing_total_stake_field_is_unchanged(self):
        # Regression guard: alpha_stake addition must not affect total_stake.
        mg = _fake_metagraph(alpha_stake=[7.5, 9.25])
        block = Block(block_number=1234, timestamp=datetime.now(tz=UTC))
        extractor = _make_extractor()

        snap = extractor._build_single_neuron_snapshot(
            metagraph=mg,
            uid=0,
            total_subnet_stake=30.0,
            mechanisms=[],
            block=block,
        )

        assert snap.total_stake == 10.0


def test_dummy_mechanism_metrics_constructible_for_test_coverage():
    # Sanity: confirms imports work and DTO is constructible
    mm = MechanismMetrics(
        id=1,
        snapshot_id=1,
        mech_id=0,
        incentive=0.0,
        dividend=0.0,
        consensus=0.0,
        validator_trust=0.0,
        weights_sum=0.0,
        last_update=0,
    )
    assert mm.mech_id == 0
