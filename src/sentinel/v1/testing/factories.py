"""Polyfactory-based factories for sentinel DTOs and provider models."""

from random import Random

from polyfactory import Use
from polyfactory.factories import DataclassFactory
from polyfactory.factories.pydantic_factory import ModelFactory

import sentinel.v1.dto as sentinel_dto
from sentinel.v1.providers import metagraph as provider_metagraph
from sentinel.v1.services.extractors.metagraph import dto as metagraph_dto

# SS58 addresses are base58, so their alphabet drops the ambiguous characters.
_SS58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _ss58_address(random: Random) -> str:
    """An SS58-shaped address: right prefix and length, no valid checksum."""
    return "5" + "".join(random.choices(_SS58_ALPHABET, k=47))


def _score(random: Random) -> float:
    """A normalized 0..1 score, the range the chain reports rank, trust and friends in."""
    return round(random.uniform(0.0, 1.0), 6)


def _stake(random: Random) -> float:
    """A stake or emission amount in whole units."""
    return round(random.uniform(0.0, 1000.0), 9)


# Extrinsic & Event factories


class HyperparametersDTOFactory(ModelFactory[sentinel_dto.HyperparametersDTO]): ...


class CallArgDTOFactory(ModelFactory[sentinel_dto.CallArgDTO]): ...


class CallDTOFactory(ModelFactory[sentinel_dto.CallDTO]):
    call_args = Use(lambda: CallArgDTOFactory.batch(3))


class ExtrinsicDTOFactory(ModelFactory[sentinel_dto.ExtrinsicDTO]):
    call = Use(lambda: CallDTOFactory.build())


class EventDataDTOFactory(ModelFactory[sentinel_dto.EventDataDTO]): ...


class EventDTOFactory(ModelFactory[sentinel_dto.EventDTO]):
    event = Use(lambda: EventDataDTOFactory.build())


class SubnetInfoDTOFactory(ModelFactory[sentinel_dto.SubnetInfoDTO]): ...


# Key factories


class ColdkeyFactory(ModelFactory[metagraph_dto.Coldkey]): ...


class HotkeyFactory(ModelFactory[metagraph_dto.Hotkey]): ...


class HotkeyWithColdkeyFactory(ModelFactory[metagraph_dto.HotkeyWithColdkey]):
    coldkey = Use(lambda: ColdkeyFactory.build())


class EVMKeyFactory(ModelFactory[metagraph_dto.EVMKey]): ...


# Block & Subnet factories


class BlockFactory(ModelFactory[metagraph_dto.Block]): ...


class SubnetFactory(ModelFactory[metagraph_dto.Subnet]): ...


class SubnetWithOwnerFactory(ModelFactory[metagraph_dto.SubnetWithOwner]):
    owner_hotkey = Use(lambda: HotkeyWithColdkeyFactory.build())


# Neuron factories


class NeuronFactory(ModelFactory[metagraph_dto.Neuron]): ...


class NeuronWithRelationsFactory(ModelFactory[metagraph_dto.NeuronWithRelations]):
    hotkey = Use(lambda: HotkeyWithColdkeyFactory.build())
    subnet = Use(lambda: SubnetFactory.build())


# Mechanism metrics factories


class MechanismMetricsFactory(ModelFactory[metagraph_dto.MechanismMetrics]): ...


# Neuron snapshot factories


class NeuronSnapshotFactory(ModelFactory[metagraph_dto.NeuronSnapshot]): ...


class NeuronSnapshotWithMechanismsFactory(ModelFactory[metagraph_dto.NeuronSnapshotWithMechanisms]):
    mechanisms = Use(lambda: MechanismMetricsFactory.batch(1))


class NeuronSnapshotFullFactory(ModelFactory[metagraph_dto.NeuronSnapshotFull]):
    neuron = Use(lambda: NeuronWithRelationsFactory.build())
    block = Use(lambda: BlockFactory.build())
    mechanisms = Use(lambda: MechanismMetricsFactory.batch(1))


# Tensor factories


class WeightFactory(ModelFactory[metagraph_dto.Weight]): ...


class BondFactory(ModelFactory[metagraph_dto.Bond]): ...


class CollateralFactory(ModelFactory[metagraph_dto.Collateral]): ...


# Tracking factories


class MetagraphDumpFactory(ModelFactory[metagraph_dto.MetagraphDump]): ...


class EmissionRecordFactory(ModelFactory[metagraph_dto.EmissionRecord]): ...


# Aggregate factories


class SubnetSnapshotSummaryFactory(ModelFactory[metagraph_dto.SubnetSnapshotSummary]):
    subnet = Use(lambda: SubnetWithOwnerFactory.build())
    block = Use(lambda: BlockFactory.build())
    dump = Use(lambda: MetagraphDumpFactory.build())


class FullSubnetSnapshotFactory(ModelFactory[metagraph_dto.FullSubnetSnapshot]):
    subnet = Use(lambda: SubnetWithOwnerFactory.build())
    block = Use(lambda: BlockFactory.build())
    dump = Use(lambda: MetagraphDumpFactory.build())
    neurons = Use(lambda: NeuronSnapshotFullFactory.batch(3))


# Provider metagraph factories


class NeuronRecordFactory(DataclassFactory[provider_metagraph.NeuronRecord]):
    """
    One row of a subnet's metagraph, as a provider reports it.

    Scores are held to 0..1 and stakes to plausible whole units; polyfactory's
    unconstrained floats would otherwise be negative or astronomically large.
    """

    axon_address = "/ipv4/0.0.0.0:0"
    active = True
    validator_permit = False
    # Stable historical defaults also work when the graph's block is overridden.
    last_update = 0
    block_at_registration = 0

    @classmethod
    def uid(cls) -> int:
        return cls.__random__.randint(0, 255)

    @classmethod
    def hotkey(cls) -> str:
        return _ss58_address(cls.__random__)

    coldkey = hotkey

    @classmethod
    def rank(cls) -> float:
        return _score(cls.__random__)

    trust = rank
    consensus = rank
    incentive = rank
    dividends = rank
    validator_trust = rank
    pruning_score = rank

    @classmethod
    def emission(cls) -> float:
        return _stake(cls.__random__)

    total_stake = emission
    alpha_stake = emission
    tao_stake = emission

    @classmethod
    def batch_with_uids(cls, size: int, start: int = 0, **kwargs) -> list[provider_metagraph.NeuronRecord]:
        """
        Build `size` neurons with sequential uids.

        `SubnetMetagraph.neuron()` looks a neuron up by list position, so a
        metagraph's neurons have to carry uids matching their index. Plain
        `batch()` randomizes uids and breaks that.
        """
        if size < 0 or start < 0:
            raise ValueError("size and start must be non-negative")
        return [cls.build(uid=uid, **kwargs) for uid in range(start, start + size)]


def _even_matrix(size: int) -> dict[int, dict[int, float]]:
    """A sparse matrix where every uid splits a row of 1.0 evenly over the others."""
    if size < 2:
        return {uid: {} for uid in range(size)}
    share = 1.0 / (size - 1)
    return {uid: {other: share for other in range(size) if other != uid} for uid in range(size)}


class SubnetMetagraphFactory(DataclassFactory[provider_metagraph.SubnetMetagraph]):
    """
    A subnet's metagraph at one block, holding 3 neurons with uids 0..2.

    The default is a lite read: no weights or bonds. Use `build_full()` for a
    graph carrying matrices consistent with its neurons.
    """

    netuid = 1
    mechid = 0
    tempo = 360
    immunity_period = 4096
    lite = True
    weights = None
    bonds = None
    alpha_dividends_per_hotkey = Use(dict[str, float])
    tao_dividends_per_hotkey = Use(dict[str, float])

    @classmethod
    def block(cls) -> int:
        return cls.__random__.randint(1, 5_000_000)

    @classmethod
    def owner_hotkey(cls) -> str:
        return _ss58_address(cls.__random__)

    owner_coldkey = owner_hotkey

    @classmethod
    def moving_price(cls) -> float:
        return _score(cls.__random__)

    @classmethod
    def alpha_out_emission(cls) -> float:
        return _stake(cls.__random__)

    @classmethod
    def _build_neurons(cls, size: int, start: int = 0, **kwargs) -> list[provider_metagraph.NeuronRecord]:
        # Share this factory's seeded generators without reseeding the global factory.
        factory = NeuronRecordFactory.create_factory(__random__=cls.__random__, __faker__=cls.__faker__)
        return factory.batch_with_uids(size, start=start, **kwargs)

    @classmethod
    def neurons(cls) -> list[provider_metagraph.NeuronRecord]:
        return cls._build_neurons(3)

    @classmethod
    def build(cls, **kwargs) -> provider_metagraph.SubnetMetagraph:
        """Build a graph with neuron uids matching their list positions."""
        graph = super().build(**kwargs)
        if any(neuron.uid != uid for uid, neuron in enumerate(graph.neurons)):
            raise ValueError("neurons must have sequential uids starting at 0 in list order")
        return graph

    @classmethod
    def build_full(cls, neuron_count: int = 3, **kwargs) -> provider_metagraph.SubnetMetagraph:
        """
        Build a non-lite metagraph of `neuron_count` neurons with matching matrices.

        Weights and bonds are keyed by the graph's own uids, and dividends by its
        own hotkeys, which is what makes the result usable by the extractors.
        """
        if neuron_count < 0:
            raise ValueError("neuron_count must be non-negative")
        if "neurons" not in kwargs:
            kwargs["neurons"] = cls._build_neurons(neuron_count)
        graph = cls.build(**{"lite": False, **kwargs})
        if "weights" not in kwargs:
            graph.weights = _even_matrix(len(graph))
        if "bonds" not in kwargs:
            graph.bonds = _even_matrix(len(graph))
        if "alpha_dividends_per_hotkey" not in kwargs:
            graph.alpha_dividends_per_hotkey = {hotkey: _stake(cls.__random__) for hotkey in graph.hotkeys}
        if "tao_dividends_per_hotkey" not in kwargs:
            graph.tao_dividends_per_hotkey = {hotkey: _stake(cls.__random__) for hotkey in graph.hotkeys}
        return graph

    @classmethod
    def build_with_roles(
        cls, validator_count: int = 2, miner_count: int = 2, **kwargs
    ) -> provider_metagraph.SubnetMetagraph:
        """
        Build active validators bonding to miners, for dividend extraction tests.

        Validators have equal positive stake and no incentive; miners have equal
        incentive and no stake. Override graph fields such as bonds for specific
        calculations. Use build_full(neurons=...) for custom neuron fields.
        """
        if validator_count < 0 or miner_count < 0:
            raise ValueError("validator_count and miner_count must be non-negative")
        if "neurons" in kwargs:
            raise ValueError("use build_full(neurons=...) for custom neurons")
        neurons = [
            *cls._build_neurons(
                validator_count,
                validator_permit=True,
                total_stake=100.0,
                alpha_stake=100.0,
                tao_stake=0.0,
                incentive=0.0,
            ),
            *cls._build_neurons(
                miner_count,
                start=validator_count,
                validator_permit=False,
                total_stake=0.0,
                alpha_stake=0.0,
                tao_stake=0.0,
                incentive=1.0 / miner_count if miner_count else 0.0,
                dividends=0.0,
            ),
        ]
        weights = {
            uid: {target: 1.0 / miner_count for target in range(validator_count, len(neurons))}
            for uid in range(validator_count)
        }
        bonds = {
            uid: {target: 1.0 for target in range(validator_count, len(neurons))} for uid in range(validator_count)
        }
        return cls.build_full(neurons=neurons, **{"weights": weights, "bonds": bonds, **kwargs})
