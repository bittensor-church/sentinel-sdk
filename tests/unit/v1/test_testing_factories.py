"""Tests for the provider metagraph factories shipped in sentinel.v1.testing."""

import pytest

from sentinel.v1.providers.metagraph import NeuronRecord, SubnetMetagraph
from sentinel.v1.services.extractors.dividends import DividendsExtractor
from sentinel.v1.services.extractors.metagraph.extractor import MetagraphExtractor
from sentinel.v1.testing import FakeBlockchainProvider, NeuronRecordFactory, SubnetMetagraphFactory


class TestNeuronRecordFactory:
    def test_build_produces_a_neuron_with_normalized_scores(self):
        neuron = NeuronRecordFactory.build()

        assert isinstance(neuron, NeuronRecord)
        for score in (
            neuron.rank,
            neuron.trust,
            neuron.consensus,
            neuron.incentive,
            neuron.dividends,
            neuron.validator_trust,
            neuron.pruning_score,
        ):
            assert 0.0 <= score <= 1.0
        assert neuron.total_stake >= 0.0

    def test_addresses_are_ss58_shaped_and_distinct(self):
        neurons = NeuronRecordFactory.batch_with_uids(5)

        for neuron in neurons:
            assert neuron.hotkey.startswith("5")
            assert len(neuron.hotkey) == 48
            assert neuron.hotkey != neuron.coldkey
        assert len({neuron.hotkey for neuron in neurons}) == 5

    def test_batch_with_uids_numbers_neurons_sequentially(self):
        assert [n.uid for n in NeuronRecordFactory.batch_with_uids(4)] == [0, 1, 2, 3]
        assert [n.uid for n in NeuronRecordFactory.batch_with_uids(2, start=10)] == [10, 11]

    def test_batch_with_uids_applies_overrides(self):
        neurons = NeuronRecordFactory.batch_with_uids(3, validator_permit=True, total_stake=5.0)

        assert all(n.validator_permit and n.total_stake == 5.0 for n in neurons)


class TestSubnetMetagraphFactory:
    def test_build_produces_a_lite_metagraph(self):
        mg = SubnetMetagraphFactory.build()

        assert isinstance(mg, SubnetMetagraph)
        assert mg.lite is True
        assert mg.weights is None
        assert mg.bonds is None
        assert [n.uid for n in mg.neurons] == [0, 1, 2]

    def test_neuron_lookup_matches_uids(self):
        mg = SubnetMetagraphFactory.build()

        assert all(mg.neuron(uid).uid == uid for uid in range(len(mg)))
        assert mg.neuron(len(mg)) is None

    def test_build_full_keys_matrices_by_the_graphs_own_uids(self):
        mg = SubnetMetagraphFactory.build_full(4)

        assert mg.lite is False
        assert set(mg.weights) == {0, 1, 2, 3}
        assert set(mg.bonds) == {0, 1, 2, 3}
        assert mg.weights is not mg.bonds
        for uid in range(4):
            assert mg.weights_sum(uid) == 1.0
            assert uid not in mg.weights[uid]
            assert mg.has_incoming_weights(uid)

    def test_build_full_keys_dividends_by_the_graphs_own_hotkeys(self):
        mg = SubnetMetagraphFactory.build_full(3)

        assert set(mg.alpha_dividends_per_hotkey) == set(mg.hotkeys)
        assert set(mg.tao_dividends_per_hotkey) == set(mg.hotkeys)

    def test_build_full_accepts_explicit_neurons(self):
        neurons = NeuronRecordFactory.batch_with_uids(2, validator_permit=True)
        mg = SubnetMetagraphFactory.build_full(neurons=neurons)

        assert mg.neurons == neurons
        assert set(mg.weights) == {0, 1}

    @pytest.mark.parametrize("kwargs", [{"neurons": []}, {"neuron_count": 0}])
    def test_build_full_preserves_an_empty_subnet(self, kwargs):
        mg = SubnetMetagraphFactory.build_full(**kwargs)
        provider = FakeBlockchainProvider().with_metagraph(mg, block_number=mg.block)

        assert mg.neurons == []
        assert mg.weights == mg.bonds == {}
        assert mg.alpha_dividends_per_hotkey == mg.tao_dividends_per_hotkey == {}
        assert DividendsExtractor(provider, mg.block, mg.netuid).extract().records == []

    def test_single_neuron_has_no_self_weights_or_bonds(self):
        mg = SubnetMetagraphFactory.build_full(neuron_count=1)

        assert mg.weights == mg.bonds == {0: {}}
        assert mg.weights_sum(0) == 0.0
        assert not mg.has_incoming_weights(0)

    @pytest.mark.parametrize("uids", [[1], [1, 0], [0, 0]])
    @pytest.mark.parametrize("build", [SubnetMetagraphFactory.build, SubnetMetagraphFactory.build_full])
    def test_rejects_neurons_that_break_uid_lookup(self, uids, build):
        neurons = [NeuronRecordFactory.build(uid=uid) for uid in uids]

        with pytest.raises(ValueError, match="sequential uids starting at 0"):
            build(neurons=neurons)

    @pytest.mark.parametrize("matrix", [None, {}, {0: {1: 0.75}}])
    def test_full_graph_preserves_explicit_tensor_and_dividend_overrides(self, matrix):
        mg = SubnetMetagraphFactory.build_full(
            weights=matrix, bonds=matrix, alpha_dividends_per_hotkey={}, tao_dividends_per_hotkey={}
        )

        assert mg.weights == mg.bonds == matrix
        assert mg.alpha_dividends_per_hotkey == mg.tao_dividends_per_hotkey == {}

    def test_default_neuron_history_does_not_postdate_the_snapshot(self):
        mg = SubnetMetagraphFactory.build_full(block=100)

        assert all(0 <= n.block_at_registration <= mg.block for n in mg.neurons)
        assert all(0 <= n.last_update <= mg.block for n in mg.neurons)

    def test_overrides_are_applied(self):
        mg = SubnetMetagraphFactory.build(netuid=7, mechid=2, block=100)

        assert (mg.netuid, mg.mechid, mg.block) == (7, 2, 100)

    def test_dividend_maps_are_not_shared_between_builds(self):
        first = SubnetMetagraphFactory.build()

        first.alpha_dividends_per_hotkey["hotkey"] = 1.0

        assert SubnetMetagraphFactory.build().alpha_dividends_per_hotkey == {}


@pytest.mark.parametrize(
    ("factory", "method"),
    [
        (NeuronRecordFactory, "build"),
        (SubnetMetagraphFactory, "build"),
        (SubnetMetagraphFactory, "build_full"),
        (SubnetMetagraphFactory, "build_with_roles"),
    ],
)
def test_seed_random_reproduces_all_generated_fields(factory, method):
    factory.seed_random(42)
    first = getattr(factory, method)()
    factory.seed_random(42)
    second = getattr(factory, method)()

    assert first == second
    assert getattr(factory, method)() != second


class TestValidatorMinerScenario:
    def test_yuma3_pays_validators_and_not_miners(self):
        mg = SubnetMetagraphFactory.build_with_roles(validator_count=2, miner_count=3, block=100, mechid=1)
        provider = FakeBlockchainProvider().with_metagraph(mg, block_number=100)

        result = DividendsExtractor(provider, 100, mg.netuid, mechid=1).extract()

        assert result.yuma3_enabled is True
        assert result.mechid == 1
        assert [record.dividend for record in result.records] == pytest.approx([0.5, 0.5, 0.0, 0.0, 0.0])
        assert set(mg.weights) == set(mg.bonds) == {0, 1}
        assert all(set(row) == {2, 3, 4} for row in mg.weights.values())

    @pytest.mark.parametrize(("validators", "miners"), [(0, 0), (0, 2), (2, 0)])
    def test_missing_roles_produce_zero_dividends(self, validators, miners):
        mg = SubnetMetagraphFactory.build_with_roles(validators, miners)
        provider = FakeBlockchainProvider().with_metagraph(mg, block_number=mg.block)

        records = DividendsExtractor(provider, mg.block, mg.netuid).extract().records

        assert len(records) == validators + miners
        assert all(record.dividend == 0.0 for record in records)

    def test_custom_bonds_exercise_asymmetric_dividends(self):
        mg = SubnetMetagraphFactory.build_with_roles(bonds={0: {2: 1.0}, 1: {2: 0.5, 3: 1.0}})
        provider = FakeBlockchainProvider().with_metagraph(mg, block_number=mg.block)

        records = DividendsExtractor(provider, mg.block, mg.netuid).extract().records

        assert [record.dividend for record in records] == pytest.approx([1 / 3, 2 / 3, 0.0, 0.0])

    def test_graph_feeds_the_public_metagraph_extractor(self):
        mg = SubnetMetagraphFactory.build_with_roles(netuid=7, block=100)
        provider = FakeBlockchainProvider().with_metagraph(mg, block_number=100)

        snapshot = MetagraphExtractor(provider, block_number=100, netuid=7).extract()

        assert snapshot is not None
        assert snapshot.block.block_number == 100
        assert snapshot.subnet.netuid == 7
        assert snapshot.neuron_count == 4
        assert snapshot.validator_count == snapshot.miner_count == 2
        assert snapshot.weights is not None and len(snapshot.weights) == 4
        assert snapshot.bonds is not None and all(b.bond == 65535 for b in snapshot.bonds)
        assert [n.has_any_weights for n in snapshot.neurons] == [False, False, True, True]
        for neuron in snapshot.neurons:
            assert neuron.alpha_dividends == mg.alpha_dividends_per_hotkey[mg.neuron(neuron.uid).hotkey]


@pytest.mark.parametrize(
    ("build", "kwargs"),
    [
        (NeuronRecordFactory.batch_with_uids, {"size": -1}),
        (NeuronRecordFactory.batch_with_uids, {"size": 1, "start": -1}),
        (SubnetMetagraphFactory.build_full, {"neuron_count": -1}),
        (SubnetMetagraphFactory.build_with_roles, {"validator_count": -1}),
        (SubnetMetagraphFactory.build_with_roles, {"miner_count": -1}),
    ],
)
def test_negative_counts_are_rejected(build, kwargs):
    with pytest.raises(ValueError, match="non-negative"):
        build(**kwargs)
