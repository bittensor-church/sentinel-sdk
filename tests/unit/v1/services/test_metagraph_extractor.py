"""Unit tests for MetagraphExtractor field extraction.

These tests build ``SubnetMetagraph`` values directly and pass them to the
extractor's helpers. The provider is responsible for translating whatever the
bittensor SDK returns into that model, so the extractor is tested against
sentinel's own types rather than the SDK's.
"""

from datetime import UTC, datetime
from typing import cast

import pytest

from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.providers.metagraph import NeuronRecord, SubnetMetagraph
from sentinel.v1.services.extractors.metagraph.dto import Block, MechanismMetrics
from sentinel.v1.services.extractors.metagraph.extractor import MetagraphExtractor


def _neuron(uid: int, **overrides) -> NeuronRecord:
    defaults = {
        "hotkey": f"5HOTKEY{uid}",
        "coldkey": f"5COLDKEY{uid}",
        "axon_address": "0.0.0.0:0",
        "active": True,
        "validator_permit": uid == 0,
        "rank": 0.1 * (uid + 1),
        "trust": 0.5 + 0.1 * uid,
        "emission": 1.0 * (uid + 1),
        "total_stake": 10.0 * (uid + 1),
        "block_at_registration": 100 * (uid + 1),
    }
    return NeuronRecord(uid=uid, **{**defaults, **overrides})


def _metagraph(**overrides) -> SubnetMetagraph:
    defaults = {
        "netuid": 1,
        "name": "test",
        "block": 1234,
        "neurons": [_neuron(0), _neuron(1)],
    }
    return SubnetMetagraph(**{**defaults, **overrides})


def _make_extractor() -> MetagraphExtractor:
    # Provider is unused in the helpers under test.
    return MetagraphExtractor(
        subtensor=cast(BlockchainProvider, None),
        block_number=1234,
        netuid=1,
        lite=True,
    )


def _block() -> Block:
    return Block(block_number=1234, timestamp=datetime.now(tz=UTC))


class TestAlphaFields:
    def test_alpha_stake_is_extracted_per_uid(self):
        mg = _metagraph(
            neurons=[_neuron(0, alpha_stake=7.5), _neuron(1, alpha_stake=9.25)],
        )
        extractor = _make_extractor()

        snapshots = [
            extractor._build_single_neuron_snapshot(
                metagraph=mg,
                neuron=neuron,
                total_subnet_stake=30.0,
                mechanisms=[],
                block=_block(),
            )
            for neuron in mg.neurons
        ]

        assert snapshots[0].alpha_stake == 7.5
        assert snapshots[1].alpha_stake == 9.25

    def test_alpha_stake_defaults_to_zero_when_the_provider_omits_it(self):
        # Pylon does not always report alpha stake; the model defaults it to 0.
        mg = _metagraph()
        extractor = _make_extractor()

        snap = extractor._build_single_neuron_snapshot(
            metagraph=mg,
            neuron=mg.neurons[0],
            total_subnet_stake=30.0,
            mechanisms=[],
            block=_block(),
        )

        assert snap.alpha_stake == 0.0

    def test_alpha_out_emission_is_extracted(self):
        subnet = _make_extractor()._build_subnet(_metagraph(alpha_out_emission=1.234))

        assert subnet.alpha_out_emission == 1.234

    def test_alpha_out_emission_defaults_to_zero_when_absent(self):
        subnet = _make_extractor()._build_subnet(_metagraph())

        assert subnet.alpha_out_emission == 0.0

    def test_existing_total_stake_field_is_unchanged(self):
        # Regression guard: alpha_stake must not affect total_stake.
        mg = _metagraph(neurons=[_neuron(0, alpha_stake=7.5)])
        extractor = _make_extractor()

        snap = extractor._build_single_neuron_snapshot(
            metagraph=mg,
            neuron=mg.neurons[0],
            total_subnet_stake=30.0,
            mechanisms=[],
            block=_block(),
        )

        assert snap.total_stake == 10.0


class TestSparselyPopulatedMetagraph:
    """A provider may not be able to report every field — Pylon carries no
    weights or subnet-level pool state, and historical blocks predate some
    chain storage. The extractor must degrade to defaults, not crash."""

    def test_neuron_defaults_do_not_crash(self):
        mg = SubnetMetagraph(netuid=1, block=7_000_000, neurons=[NeuronRecord(uid=0)])
        block = Block(block_number=7_000_000, timestamp=datetime.now(tz=UTC))

        snap = _make_extractor()._build_single_neuron_snapshot(
            metagraph=mg,
            neuron=mg.neurons[0],
            total_subnet_stake=1.0,
            mechanisms=[],
            block=block,
        )

        assert snap.rank == 0.0
        assert snap.trust == 0.0
        assert snap.total_stake == 0.0
        assert snap.is_immune is False

    def test_mechanism_metrics_default_when_the_uid_is_absent(self):
        mm = MetagraphExtractor._build_mechanism_metrics(
            metagraph=SubnetMetagraph(netuid=1),
            uid=0,
            mech_id=0,
        )

        assert mm.incentive == 0.0
        assert mm.dividend == 0.0
        assert mm.consensus == 0.0
        assert mm.validator_trust == 0.0
        assert mm.weights_sum == 0.0
        assert mm.last_update == 0

    def test_weights_and_bonds_are_none_when_not_fetched(self):
        extractor = _make_extractor()
        mg = _metagraph()

        assert extractor._build_weights(mg) is None
        assert extractor._build_bonds(mg) is None


class TestMechanismMetrics:
    def test_metrics_are_read_from_the_matching_neuron(self):
        mg = _metagraph(
            neurons=[
                _neuron(0, incentive=0.4, dividends=0.7, consensus=0.3, validator_trust=0.9, last_update=42),
                _neuron(1),
            ],
            weights={0: {1: 0.25, 0: 0.75}},
        )

        mm = MetagraphExtractor._build_mechanism_metrics(metagraph=mg, uid=0, mech_id=2)

        assert mm.mech_id == 2
        assert mm.incentive == 0.4
        assert mm.dividend == 0.7
        assert mm.consensus == 0.3
        assert mm.validator_trust == 0.9
        assert mm.last_update == 42
        assert mm.weights_sum == pytest.approx(1.0)


class TestWeightsAndBonds:
    def test_weights_are_flattened_into_rows(self):
        mg = _metagraph(lite=False, weights={0: {1: 0.25}, 1: {0: 0.75}})

        weights = _make_extractor()._build_weights(mg)

        assert weights is not None
        assert {(w.source_neuron_uid, w.target_neuron_uid, w.weight) for w in weights} == {
            (0, 1, 0.25),
            (1, 0, 0.75),
        }

    def test_bonds_are_flattened_into_rows(self):
        mg = _metagraph(lite=False, bonds={0: {1: 0.5}})

        bonds = _make_extractor()._build_bonds(mg)

        assert bonds is not None
        assert (bonds[0].source_neuron_uid, bonds[0].target_neuron_uid, bonds[0].bond) == (0, 1, 0.5)

    def test_zero_valued_entries_are_dropped(self):
        mg = _metagraph(lite=False, weights={0: {1: 0.0}})

        assert _make_extractor()._build_weights(mg) is None

    def test_has_any_weights_tracks_incoming_weights(self):
        mg = _metagraph(lite=False, weights={0: {1: 0.25}})
        extractor = _make_extractor()

        snapshots = [
            extractor._build_single_neuron_snapshot(
                metagraph=mg,
                neuron=neuron,
                total_subnet_stake=30.0,
                mechanisms=[],
                block=_block(),
            )
            for neuron in mg.neurons
        ]

        # uid 1 is weighted by uid 0; nobody weights uid 0.
        assert snapshots[0].has_any_weights is False
        assert snapshots[1].has_any_weights is True


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


class TestDividendDataPoints:
    """alpha/tao dividends are reported per hotkey by the chain and mapped onto
    each neuron by hotkey."""

    @staticmethod
    def _metagraph_with_dividends() -> SubnetMetagraph:
        return _metagraph(
            neurons=[_neuron(0, hotkey="5AAA"), _neuron(1, hotkey="5BBB")],
            alpha_dividends_per_hotkey={"5AAA": 1.5, "5BBB": 2.5},
            tao_dividends_per_hotkey={"5AAA": 0.15, "5BBB": 0.25},
        )

    def test_dividends_mapped_by_hotkey_end_to_end(self):
        neurons = _make_extractor()._build_neuron_snapshots([self._metagraph_with_dividends()], _block())

        assert neurons[0].alpha_dividends == 1.5
        assert neurons[0].tao_dividends == 0.15
        assert neurons[1].alpha_dividends == 2.5
        assert neurons[1].tao_dividends == 0.25

    def test_a_hotkey_holding_several_uids_receives_the_same_dividend(self):
        # The chain pays per hotkey, not per uid slot.
        mg = _metagraph(
            neurons=[_neuron(0, hotkey="5AAA"), _neuron(1, hotkey="5AAA")],
            alpha_dividends_per_hotkey={"5AAA": 1.5},
        )

        neurons = _make_extractor()._build_neuron_snapshots([mg], _block())

        assert neurons[0].alpha_dividends == 1.5
        assert neurons[1].alpha_dividends == 1.5

    def test_dividends_default_zero_when_the_metagraph_omits_them(self):
        neurons = _make_extractor()._build_neuron_snapshots([_metagraph()], _block())

        assert neurons[0].alpha_dividends == 0.0
        assert neurons[0].tao_dividends == 0.0
        assert neurons[1].alpha_dividends == 0.0
        assert neurons[1].tao_dividends == 0.0


class TestSubnetApyFields:
    """moving_price and tempo are read onto the subnet DTO."""

    def test_moving_price_and_tempo_extracted(self):
        subnet = _make_extractor()._build_subnet(_metagraph(moving_price=0.0345, tempo=360))

        assert subnet.moving_price == pytest.approx(0.0345)
        assert subnet.tempo == 360

    def test_moving_price_and_tempo_default_zero_when_absent(self):
        subnet = _make_extractor()._build_subnet(_metagraph())

        assert subnet.moving_price == 0.0
        assert subnet.tempo == 0


class TestImmunity:
    def test_a_recently_registered_neuron_is_immune(self):
        mg = _metagraph(immunity_period=500, neurons=[_neuron(0, block_at_registration=1000)])
        block = Block(block_number=1200, timestamp=datetime.now(tz=UTC))

        snap = _make_extractor()._build_single_neuron_snapshot(
            metagraph=mg,
            neuron=mg.neurons[0],
            total_subnet_stake=10.0,
            mechanisms=[],
            block=block,
        )

        assert snap.is_immune is True

    def test_immunity_lapses_once_the_period_has_passed(self):
        mg = _metagraph(immunity_period=100, neurons=[_neuron(0, block_at_registration=1000)])
        block = Block(block_number=1200, timestamp=datetime.now(tz=UTC))

        snap = _make_extractor()._build_single_neuron_snapshot(
            metagraph=mg,
            neuron=mg.neurons[0],
            total_subnet_stake=10.0,
            mechanisms=[],
            block=block,
        )

        assert snap.is_immune is False
