"""
Metagraph Data Transfer Objects (DTOs).

This module defines Pydantic schemas for metagraph data extraction and storage.
Classes follow the Base -> Create -> Full pattern for database operations.

Sections:
    1. Type Aliases & Enums
    2. Primitive Models (Keys, Block, Subnet)
    3. Neuron Models
    4. Snapshot Models (NeuronSnapshot, MechanismMetrics)
    5. Tensor Models (Weight, Bond, Collateral)
    6. Tracking Models (MetagraphDump, EmissionRecord)
    7. Aggregate Models (SubnetSnapshot, FullSubnetSnapshot)
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

__all__ = [
    "Block",
    "BlockBase",
    "BlockNumber",
    "Bond",
    "BondBase",
    "BondCreate",
    "Coldkey",
    "ColdkeyBase",
    "ColdkeyCreate",
    "Collateral",
    "CollateralBase",
    "CollateralCreate",
    "EVMKey",
    "EVMKeyBase",
    "EmissionRecord",
    "EpochPosition",
    "FullSubnetSnapshot",
    "Hotkey",
    "HotkeyBase",
    "HotkeyWithColdkey",
    "MechanismMetrics",
    "MechanismMetricsBase",
    "MechanismMetricsCreate",
    "MetagraphDump",
    "MetagraphDumpBase",
    "MetagraphDumpCreate",
    "Neuron",
    "NeuronBase",
    "NeuronCreate",
    "NeuronSnapshot",
    "NeuronSnapshotBase",
    "NeuronSnapshotCreate",
    "NeuronSnapshotFull",
    "NeuronSnapshotWithMechanisms",
    "NeuronWithRelations",
    "Subnet",
    "SubnetBase",
    "SubnetSnapshotSummary",
    "SubnetWithOwner",
    "TensorRecordBase",
    "Weight",
    "WeightBase",
    "WeightCreate",
]


# Type Aliases & Enums

BlockNumber: TypeAlias = int
"""Type alias for block number."""


class EpochPosition(StrEnum):
    """Position of a block within an epoch."""

    START = "start"
    INSIDE = "inside"
    END = "end"


# Primitive Models: Keys


class ColdkeyBase(BaseModel):
    """Base schema for coldkey (cold wallet address)."""

    coldkey: Annotated[str, Field(max_length=48, description="SS58-encoded coldkey address")]


class ColdkeyCreate(ColdkeyBase):
    """Schema for creating a coldkey."""


class Coldkey(ColdkeyBase):
    """Full coldkey schema with database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class HotkeyBase(BaseModel):
    """Base schema for hotkey (hot wallet address)."""

    hotkey: Annotated[str, Field(max_length=48, description="SS58-encoded hotkey address")]


class Hotkey(HotkeyBase):
    """Full hotkey schema with database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    coldkey_id: int | None = None
    created_at: datetime
    last_seen: datetime


class HotkeyWithColdkey(HotkeyBase):
    """Hotkey with embedded coldkey relation."""

    coldkey: Coldkey | None = None


class EVMKeyBase(BaseModel):
    """Base schema for EVM-compatible address."""

    evm_address: Annotated[
        str,
        Field(max_length=42, pattern=r"^0x[a-fA-F0-9]{40}$", description="EVM-compatible address"),
    ]


class EVMKey(EVMKeyBase):
    """Full EVM key schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# Primitive Models: Block & Subnet


class BlockBase(BaseModel):
    """Base schema for blockchain block."""

    block_number: BlockNumber
    timestamp: datetime = Field(description="Block creation timestamp from chain")


class Block(BlockBase):
    """Full block schema - block_number is the primary key."""

    model_config = ConfigDict(from_attributes=True)


class SubnetBase(BaseModel):
    """Base schema for subnet."""

    netuid: int = Field(ge=0, description="Unique network identifier for the subnet")
    name: str = Field(default="", max_length=255, description="Human-readable subnet name")


class Subnet(SubnetBase):
    """Full subnet schema."""

    model_config = ConfigDict(from_attributes=True)

    owner_hotkey_id: int | None = None
    registered_at: datetime


class SubnetWithOwner(Subnet):
    """Subnet with embedded owner hotkey relation."""

    owner_hotkey: HotkeyWithColdkey | None = None


# Neuron Models


class NeuronBase(BaseModel):
    """Base schema for neuron (subnet participant)."""

    uid: int = Field(ge=0, lt=65536, description="Neuron UID within subnet (16-bit unsigned)")


class NeuronCreate(NeuronBase):
    """Schema for creating a neuron."""

    hotkey_id: int
    subnet_id: int
    evm_key_id: int | None = None


class Neuron(NeuronBase):
    """
    Full neuron schema.

    Neuron is uniquely identified by (hotkey, subnet) pair.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    hotkey_id: int
    subnet_id: int
    evm_key_id: int | None = None


class NeuronWithRelations(Neuron):
    """Neuron with embedded hotkey, subnet, and EVM key relations."""

    hotkey: HotkeyWithColdkey
    subnet: Subnet
    evm_key: EVMKey | None = None


# Snapshot Models: Mechanism Metrics


class MechanismMetricsBase(BaseModel):
    """
    Base schema for per-mechanism metrics.

    Source of truth for mechanism-dependent data:
    - incentive: Miner performance score
    - dividend: Validator reward score
    - consensus: Consensus participation score
    - validator_trust: Trust score from validators
    - weights_sum: Sum of weights this neuron has set
    - last_update: Blocks since last weight update
    """

    mech_id: Annotated[int, Field(ge=0, description="Mechanism ID (0 for default, +1 for additional)")]

    # Performance metrics (all normalized 0.0 - 1.0)
    incentive: Annotated[float, Field(ge=0, le=1, default=0, description="Miner performance score")]
    dividend: Annotated[float, Field(ge=0, le=1, default=0, description="Validator reward score")]
    consensus: Annotated[float, Field(ge=0, le=1, default=0, description="Consensus participation score")]
    validator_trust: Annotated[float, Field(ge=0, le=1, default=0, description="Trust from validators")]

    # Weight metrics
    weights_sum: Annotated[float, Field(ge=0, default=0, description="Sum of weights set by this neuron")]
    last_update: Annotated[int, Field(ge=0, default=0, description="Blocks since last weight update")]


class MechanismMetricsCreate(MechanismMetricsBase):
    """Schema for creating mechanism metrics."""

    snapshot_id: int


class MechanismMetrics(MechanismMetricsBase):
    """
    Full mechanism metrics schema.

    Unique constraint: (snapshot_id, mech_id)
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_id: int  # FK to NeuronSnapshot.id


# Snapshot Models: Neuron Snapshots


class NeuronSnapshotBase(BaseModel):
    """Base schema for neuron snapshot - mechanism-independent data."""

    uid: int = Field(ge=0, lt=65536, description="Neuron UID within subnet (16-bit unsigned)")
    axon_address: str = Field(
        default="",
        max_length=255,
        description="Axon network address (e.g., '/ip4/1.2.3.4/tcp/1234')",
    )

    # Stake metrics
    total_stake: Annotated[float, Field(ge=0, description="Total stake in TAO")]
    normalized_stake: Annotated[
        float,
        Field(ge=0, le=1, description="Stake as fraction of subnet total (0.0 - 1.0)"),
    ]

    # Performance metrics
    rank: Annotated[float, Field(ge=0, le=1, description="Neuron rank within subnet (0.0 - 1.0)")]
    trust: Annotated[float, Field(ge=0, le=1, description="Trust score from other neurons (0.0 - 1.0)")]
    emissions: Annotated[float, Field(ge=0, description="Cumulative emissions received")]

    # Status flags
    is_active: bool = Field(description="Whether the neuron is currently active")
    is_validator: bool = Field(description="Whether the neuron has validator permit")
    is_immune: bool = Field(description="Whether in immunity period (recently registered)")
    has_any_weights: bool = Field(description="Whether any validator has set weights for this neuron")

    # Metadata
    neuron_version: int | None = Field(default=None, description="Version of neuron software")
    block_at_registration: BlockNumber = Field(description="Block number when registered on chain")


class NeuronSnapshotCreate(NeuronSnapshotBase):
    """Schema for creating a neuron snapshot."""

    neuron_id: int
    block_number: BlockNumber


class NeuronSnapshot(NeuronSnapshotBase):
    """Full neuron snapshot schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    neuron_id: int
    block_number: BlockNumber


class NeuronSnapshotWithMechanisms(NeuronSnapshot):
    """Neuron snapshot with all mechanism metrics embedded."""

    mechanisms: list[MechanismMetrics] = Field(
        default_factory=list,
        description="Per-mechanism metrics",
    )


class NeuronSnapshotFull(NeuronSnapshotWithMechanisms):
    """Complete neuron snapshot with all relations."""

    neuron: NeuronWithRelations
    block: Block


# Tensor Models


class TensorRecordBase(BaseModel):
    """Base schema for neuron-to-neuron tensor data (weights, bonds, collateral)."""

    source_neuron_uid: int = Field(description="Source neuron (validator setting weight/bond)")
    target_neuron_uid: int = Field(description="Target neuron (miner receiving weight/bond)")
    block_number: BlockNumber = Field(description="Block number of this record")


class WeightBase(TensorRecordBase):
    """Base schema for weight record."""

    mech_id: int = Field(default=0, description="Mechanism ID (0 for default)")
    weight: Annotated[float, Field(ge=0, le=1, description="Normalized weight value (0-1)")]


class WeightCreate(WeightBase):
    """Schema for creating weight record."""


class Weight(WeightBase):
    """
    Full weight record schema.

    Unique constraint: (source_neuron_uid, target_neuron_uid, block_number, mech_id)

    Storage optimization: Only non-zero weights are stored.
    When querying, assume weight=0 for missing tuples.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class BondBase(TensorRecordBase):
    """Base schema for bond record."""

    mech_id: int = Field(default=0, description="Mechanism ID")
    bond: Annotated[float, Field(ge=0, description="Raw bond value (u16, 0-65535)")]


class BondCreate(BondBase):
    """Schema for creating a bond record."""


class Bond(BondBase):
    """
    Full bond schema.

    Unique constraint: (source_neuron_uid, target_neuron_uid, block_number, mech_id)

    Storage optimization: Only non-zero bonds are stored.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CollateralBase(TensorRecordBase):
    """Base schema for collateral record."""

    amount: Annotated[
        Decimal,
        Field(ge=0, max_digits=32, decimal_places=18, description="Collateral amount in TAO"),
    ]


class CollateralCreate(CollateralBase):
    """Schema for creating a collateral record."""


class Collateral(CollateralBase):
    """
    Full collateral schema.

    Unique constraint: (source_neuron_uid, target_neuron_uid, block_number)
    Note: Collateral is not mechanism-specific.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# Tracking Models


class MetagraphDumpBase(BaseModel):
    """Base schema for metagraph dump tracking."""

    netuid: int = Field(ge=0, description="Subnet ID being dumped")
    block_number: BlockNumber = Field(description="Block number being dumped")
    epoch_position: EpochPosition | None = Field(default=None, description="Position within epoch")


class MetagraphDumpCreate(MetagraphDumpBase):
    """Schema for creating a metagraph dump record."""


class MetagraphDump(MetagraphDumpBase):
    """
    Full metagraph dump schema.

    Unique constraint: (netuid, block_number)
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class EmissionRecord(BaseModel):
    """
    Computed emission record (incentive + dividend).

    This can be a database view or computed on-the-fly.
    """

    model_config = ConfigDict(from_attributes=True)

    neuron_id: int
    block_number: BlockNumber
    mech_id: int
    uid: int
    subnet_id: int
    hotkey: str
    incentive: float
    dividend: float
    emission: float = Field(description="Computed: incentive + dividend")

    @field_validator("emission", mode="before")
    @classmethod
    def compute_emission(cls, v: float | None, info: ValidationInfo) -> float:
        """Auto-compute emission if not provided."""
        if v is None:
            return info.data.get("incentive", 0) + info.data.get("dividend", 0)
        return v


# Aggregate Models


class SubnetSnapshotSummary(BaseModel):
    """Summary of subnet state at a specific block."""

    model_config = ConfigDict(from_attributes=True)

    subnet: SubnetWithOwner
    block: Block
    dump: MetagraphDump | None = None

    # Aggregated metrics
    neuron_count: int
    validator_count: int
    miner_count: int
    total_stake: float
    mechanism_count: int


class FullSubnetSnapshot(SubnetSnapshotSummary):
    """
    Complete subnet snapshot with all neuron data.

    Top-level schema for a full metagraph dump.
    """

    neurons: list[NeuronSnapshotFull] = Field(
        default_factory=list,
        description="All neuron snapshots within this subnet at the given block",
    )

    # Optional tensor data (can be very large)
    weights: list[Weight] | None = Field(
        default=None,
        description="Weight matrix (optional, can be large)",
    )
    bonds: list[Bond] | None = Field(
        default=None,
        description="Bond matrix (optional, can be large)",
    )
    collaterals: list[Collateral] | None = Field(
        default=None,
        description="Collateral records",
    )
