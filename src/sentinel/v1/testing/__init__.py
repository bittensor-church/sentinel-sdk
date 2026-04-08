"""
Testing utilities for the sentinel SDK.

Provides factories and fake providers for writing tests against sentinel DTOs
and the BlockchainProvider interface.

Install with: pip install bittensor-sentinel[testing]
"""

from sentinel.v1.testing.extrinsics import (
    AnnounceColdkeySwapCallDTOFactory,
    AnnounceColdkeySwapExtrinsicDTOFactory,
    ClearColdkeySwapCallDTOFactory,
    ClearColdkeySwapExtrinsicDTOFactory,
    ColdkeySwapCallDTOFactory,
    ColdkeySwapExtrinsicDTOFactory,
    DisputeColdkeySwapCallDTOFactory,
    DisputeColdkeySwapExtrinsicDTOFactory,
    HyperparamCallDTOFactory,
    HyperparamExtrinsicDTOFactory,
    RegisterNetworkCallDTOFactory,
    RegisterNetworkExtrinsicDTOFactory,
    RegisterNetworkWithIdentityCallDTOFactory,
    RegisterNetworkWithIdentityExtrinsicDTOFactory,
    ResetColdkeySwapCallDTOFactory,
    ResetColdkeySwapExtrinsicDTOFactory,
)
from sentinel.v1.testing.factories import (
    # Block & Subnet
    BlockFactory,
    # Tensor
    BondFactory,
    # Extrinsic & Event
    CallArgDTOFactory,
    CallDTOFactory,
    # Key
    ColdkeyFactory,
    CollateralFactory,
    # Tracking
    EmissionRecordFactory,
    EventDataDTOFactory,
    EventDTOFactory,
    EVMKeyFactory,
    ExtrinsicDTOFactory,
    # Aggregate
    FullSubnetSnapshotFactory,
    HotkeyFactory,
    HotkeyWithColdkeyFactory,
    HyperparametersDTOFactory,
    # Mechanism metrics
    MechanismMetricsFactory,
    MetagraphDumpFactory,
    # Neuron
    NeuronFactory,
    # Neuron snapshot
    NeuronSnapshotFactory,
    NeuronSnapshotFullFactory,
    NeuronSnapshotWithMechanismsFactory,
    NeuronWithRelationsFactory,
    SubnetFactory,
    SubnetInfoDTOFactory,
    SubnetSnapshotSummaryFactory,
    SubnetWithOwnerFactory,
    WeightFactory,
)
from sentinel.v1.testing.providers import FakeBlockchainProvider

__all__ = [
    # Extrinsic & Event
    "CallArgDTOFactory",
    "CallDTOFactory",
    "EventDataDTOFactory",
    "EventDTOFactory",
    "ExtrinsicDTOFactory",
    "HyperparametersDTOFactory",
    "SubnetInfoDTOFactory",
    # Hyperparam presets
    "HyperparamCallDTOFactory",
    "HyperparamExtrinsicDTOFactory",
    # Coldkey swap presets
    "AnnounceColdkeySwapCallDTOFactory",
    "AnnounceColdkeySwapExtrinsicDTOFactory",
    "ColdkeySwapCallDTOFactory",
    "ColdkeySwapExtrinsicDTOFactory",
    "DisputeColdkeySwapCallDTOFactory",
    "DisputeColdkeySwapExtrinsicDTOFactory",
    "ClearColdkeySwapCallDTOFactory",
    "ClearColdkeySwapExtrinsicDTOFactory",
    "ResetColdkeySwapCallDTOFactory",
    "ResetColdkeySwapExtrinsicDTOFactory",
    # Register network presets
    "RegisterNetworkCallDTOFactory",
    "RegisterNetworkExtrinsicDTOFactory",
    "RegisterNetworkWithIdentityCallDTOFactory",
    "RegisterNetworkWithIdentityExtrinsicDTOFactory",
    # Key
    "ColdkeyFactory",
    "HotkeyFactory",
    "HotkeyWithColdkeyFactory",
    "EVMKeyFactory",
    # Block & Subnet
    "BlockFactory",
    "SubnetFactory",
    "SubnetWithOwnerFactory",
    # Neuron
    "NeuronFactory",
    "NeuronWithRelationsFactory",
    # Mechanism metrics
    "MechanismMetricsFactory",
    # Neuron snapshot
    "NeuronSnapshotFactory",
    "NeuronSnapshotWithMechanismsFactory",
    "NeuronSnapshotFullFactory",
    # Tensor
    "WeightFactory",
    "BondFactory",
    "CollateralFactory",
    # Tracking
    "MetagraphDumpFactory",
    "EmissionRecordFactory",
    # Aggregate
    "SubnetSnapshotSummaryFactory",
    "FullSubnetSnapshotFactory",
    # Providers
    "FakeBlockchainProvider",
]
