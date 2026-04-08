"""Polyfactory-based factories for sentinel DTOs."""

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

import sentinel.v1.dto as sentinel_dto
from sentinel.v1.services.extractors.metagraph import dto as metagraph_dto

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
