from datetime import UTC, datetime

import numpy as np
import structlog
from bittensor.core.metagraph import Metagraph

from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.services.extractors.metagraph.dto import (
    Block,
    BlockNumber,
    Bond,
    Coldkey,
    FullSubnetSnapshot,
    HotkeyWithColdkey,
    MechanismMetrics,
    NeuronSnapshotFull,
    NeuronWithRelations,
    Subnet,
    SubnetWithOwner,
    Weight,
)

logger = structlog.get_logger()


class MetagraphExtractor:
    """Extracts metagraph data and builds structured DTO objects."""

    def __init__(
        self,
        subtensor: BlockchainProvider,
        block_number: BlockNumber,
        netuid: int,
        mechid: int | None = None,
    ) -> None:
        self.subtensor = subtensor
        self.block_number = block_number
        self.netuid = netuid
        self.mechid = mechid

    def extract(self) -> FullSubnetSnapshot | None:
        """
        Extract metagraph for the given block number and netuid.

        Returns a FullSubnetSnapshot with all neuron data and optional tensor data.
        """
        if self.mechid is not None:
            metagraphs = [self.extract_by_mech_id(mechid=self.mechid)]
            metagraphs = [m for m in metagraphs if m is not None]
        else:
            metagraphs = self.extract_all_mechids()

        if not metagraphs:
            logger.warning(
                "MetagraphExtractor.extract: No metagraphs found",
                netuid=self.netuid,
                block_number=self.block_number,
            )
            return None

        return self._build_full_snapshot(metagraphs)

    def extract_raw(self) -> list[Metagraph]:
        """
        Extract raw metagraph objects without DTO conversion.

        Returns list of Metagraph objects for all mechanisms.
        """
        if self.mechid is not None:
            metagraph = self.extract_by_mech_id(mechid=self.mechid)
            return [metagraph] if metagraph else []
        return self.extract_all_mechids()

    def extract_by_mech_id(self, mechid: int) -> Metagraph | None:
        """
        Extract metagraph for the given block number, netuid, and mechid.
        """
        metagraph = self.subtensor.get_metagraph(
            netuid=self.netuid,
            block_number=self.block_number,
            mechid=mechid,
        )
        if not metagraph:
            logger.warning(
                "MetagraphExtractor.extract_by_mech_id: No metagraph found",
                netuid=self.netuid,
                block_number=self.block_number,
                mechid=mechid,
            )
        return metagraph

    def extract_all_mechids(self) -> list[Metagraph]:
        """
        Extract metagraphs for all mechids for the given block number and netuid.
        """
        mechanism_counter = self.subtensor.get_mechanism_count(self.netuid)
        metagraphs = []
        for mech_id in range(mechanism_counter):
            metagraph = self.extract_by_mech_id(mechid=mech_id)
            if metagraph:
                metagraphs.append(metagraph)
        return metagraphs

    def _build_full_snapshot(self, metagraphs: list[Metagraph]) -> FullSubnetSnapshot:
        """
        Build a FullSubnetSnapshot from extracted metagraph data.

        Args:
            metagraphs: List of Metagraph objects (one per mechanism)

        Returns:
            FullSubnetSnapshot with all neuron data

        """
        # Use the first metagraph as the base (contains shared data)
        base_metagraph = metagraphs[0]

        # Build block info
        block = self._build_block(base_metagraph)

        # Build subnet info
        subnet = self._build_subnet(base_metagraph)

        # Build neuron snapshots with mechanism metrics
        neurons = self._build_neuron_snapshots(metagraphs, block)

        # Calculate aggregated metrics
        validator_count = sum(1 for n in neurons if n.is_validator)
        miner_count = len(neurons) - validator_count
        total_stake = sum(n.total_stake for n in neurons)

        # Build weights and bonds if available (from base metagraph)
        weights = self._build_weights(base_metagraph) if not base_metagraph.lite else None
        bonds = self._build_bonds(base_metagraph) if not base_metagraph.lite else None

        return FullSubnetSnapshot(
            subnet=subnet,
            block=block,
            dump=None,
            neuron_count=len(neurons),
            validator_count=validator_count,
            miner_count=miner_count,
            total_stake=total_stake,
            mechanism_count=len(metagraphs),
            neurons=neurons,
            weights=weights,
            bonds=bonds,
            collaterals=None,
        )

    def _build_block(self, metagraph: Metagraph) -> Block:
        """Build Block DTO from metagraph."""
        block_number = int(metagraph.block.item()) if hasattr(metagraph.block, "item") else int(metagraph.block)

        # Get block timestamp from provider if available
        block_info = self.subtensor.get_block_info(block_number=block_number)
        timestamp = datetime.now(tz=UTC)
        if block_info and hasattr(block_info, "timestamp"):
            timestamp = block_info.timestamp

        return Block(
            block_number=block_number,
            timestamp=timestamp,
        )

    def _build_subnet(self, metagraph: Metagraph) -> SubnetWithOwner:
        """Build SubnetWithOwner DTO from metagraph."""
        # Get subnet name from metagraph if available
        subnet_name = getattr(metagraph, "name", "") or ""

        # Build owner hotkey if available
        owner_hotkey = None
        if hasattr(metagraph, "owner_hotkey") and metagraph.owner_hotkey:
            owner_coldkey = None
            if hasattr(metagraph, "owner_coldkey") and metagraph.owner_coldkey:
                owner_coldkey = Coldkey(
                    id=0,  # Placeholder - would come from DB
                    coldkey=metagraph.owner_coldkey,
                    created_at=datetime.now(tz=UTC),
                )
            owner_hotkey = HotkeyWithColdkey(
                hotkey=metagraph.owner_hotkey,
                coldkey=owner_coldkey,
            )

        return SubnetWithOwner(
            netuid=metagraph.netuid,
            name=subnet_name,
            owner_hotkey_id=None,
            registered_at=datetime.now(tz=UTC),  # Would come from chain
            owner_hotkey=owner_hotkey,
        )

    def _build_neuron_snapshots(
        self,
        metagraphs: list[Metagraph],
        block: Block,
    ) -> list[NeuronSnapshotFull]:
        """
        Build NeuronSnapshotFull DTOs from metagraph data.

        Combines data from all mechanism metagraphs into unified neuron snapshots.
        """
        base_metagraph = metagraphs[0]
        n_neurons = int(base_metagraph.n.item()) if hasattr(base_metagraph.n, "item") else int(base_metagraph.n[0])

        # Calculate total stake for normalization
        stakes = self._to_list(base_metagraph.stake)
        total_subnet_stake = sum(stakes) if stakes else 1.0

        neurons: list[NeuronSnapshotFull] = []

        for uid in range(n_neurons):
            # Build mechanism metrics from all metagraphs
            mechanisms = []
            for mech_idx, mg in enumerate(metagraphs):
                mech_metrics = self._build_mechanism_metrics(mg, uid, mech_idx)
                mechanisms.append(mech_metrics)

            # Get base neuron data from first metagraph
            neuron_snapshot = self._build_single_neuron_snapshot(
                metagraph=base_metagraph,
                uid=uid,
                total_subnet_stake=total_subnet_stake,
                mechanisms=mechanisms,
                block=block,
            )
            neurons.append(neuron_snapshot)

        return neurons

    def _build_single_neuron_snapshot(
        self,
        metagraph: Metagraph,
        uid: int,
        total_subnet_stake: float,
        mechanisms: list[MechanismMetrics],
        block: Block,
    ) -> NeuronSnapshotFull:
        """Build a single NeuronSnapshotFull for a given UID."""
        # Extract arrays as lists
        stakes = self._to_list(metagraph.stake)
        ranks = self._to_list(metagraph.ranks)
        trusts = self._to_list(metagraph.trust)
        emissions = self._to_list(metagraph.emission)
        active = self._to_list(metagraph.active)
        validator_permits = self._to_list(metagraph.validator_permit)
        block_at_registration = getattr(metagraph, "block_at_registration", [])

        # Get axon info
        axon = metagraph.axons[uid] if uid < len(metagraph.axons) else None
        hotkey = axon.hotkey if axon else ""
        coldkey = axon.coldkey if axon else ""
        axon_address = axon.ip_str() if axon else ""

        # Calculate normalized stake
        stake = stakes[uid] if uid < len(stakes) else 0.0
        normalized_stake = stake / total_subnet_stake if total_subnet_stake > 0 else 0.0

        # Determine immunity status
        reg_block = block_at_registration[uid] if uid < len(block_at_registration) else 0
        immunity_period = getattr(metagraph, "hparams", None)
        immunity_period = immunity_period.immunity_period if immunity_period else 0
        is_immune = (block.block_number - reg_block) < immunity_period if reg_block else False

        # Check if any weights are set for this neuron
        has_any_weights = self._check_has_weights(metagraph, uid)

        # Build related objects
        hotkey_dto = HotkeyWithColdkey(
            hotkey=hotkey,
            coldkey=Coldkey(
                id=0,
                coldkey=coldkey,
                created_at=datetime.now(tz=UTC),
            )
            if coldkey
            else None,
        )

        subnet_dto = Subnet(
            netuid=metagraph.netuid,
            name=getattr(metagraph, "name", "") or "",
            owner_hotkey_id=None,
            registered_at=datetime.now(tz=UTC),
        )

        neuron_dto = NeuronWithRelations(
            uid=uid,
            id=uid,  # Placeholder
            hotkey_id=0,
            subnet_id=metagraph.netuid,
            evm_key_id=None,
            hotkey=hotkey_dto,
            subnet=subnet_dto,
            evm_key=None,
        )

        return NeuronSnapshotFull(
            uid=uid,
            axon_address=axon_address,
            total_stake=float(stake),
            normalized_stake=float(normalized_stake),
            rank=float(ranks[uid]) if uid < len(ranks) else 0.0,
            trust=float(trusts[uid]) if uid < len(trusts) else 0.0,
            emissions=float(emissions[uid]) if uid < len(emissions) else 0.0,
            is_active=bool(active[uid]) if uid < len(active) else False,
            is_validator=bool(validator_permits[uid]) if uid < len(validator_permits) else False,
            is_immune=is_immune,
            has_any_weights=has_any_weights,
            neuron_version=None,
            block_at_registration=reg_block,
            id=uid,  # Placeholder
            neuron_id=uid,
            block_number=block.block_number,
            mechanisms=mechanisms,
            neuron=neuron_dto,
            block=block,
        )

    def _build_mechanism_metrics(
        self,
        metagraph: Metagraph,
        uid: int,
        mech_id: int,
    ) -> MechanismMetrics:
        """Build MechanismMetrics for a neuron from a specific mechanism's metagraph."""
        incentives = self._to_list(metagraph.incentive)
        dividends = self._to_list(metagraph.dividends)
        consensus = self._to_list(metagraph.consensus)
        validator_trusts = self._to_list(metagraph.validator_trust)
        last_updates = self._to_list(metagraph.last_update)

        # Calculate weights sum for this neuron
        weights_sum = 0.0
        if hasattr(metagraph, "weights") and metagraph.weights is not None:
            weights = metagraph.weights
            if hasattr(weights, "shape") and len(weights.shape) == 2 and uid < weights.shape[0]:
                weights_sum = float(np.sum(weights[uid]))

        return MechanismMetrics(
            id=0,  # Placeholder
            snapshot_id=0,  # Placeholder
            mech_id=mech_id,
            incentive=float(incentives[uid]) if uid < len(incentives) else 0.0,
            dividend=float(dividends[uid]) if uid < len(dividends) else 0.0,
            consensus=float(consensus[uid]) if uid < len(consensus) else 0.0,
            validator_trust=float(validator_trusts[uid]) if uid < len(validator_trusts) else 0.0,
            weights_sum=weights_sum,
            last_update=int(last_updates[uid]) if uid < len(last_updates) else 0,
        )

    def _build_weights(self, metagraph: Metagraph) -> list[Weight] | None:
        """Build Weight DTOs from metagraph weight matrix."""
        if not hasattr(metagraph, "weights") or metagraph.weights is None:
            return None

        weights = metagraph.weights
        if not hasattr(weights, "shape") or len(weights.shape) != 2:
            return None

        weight_records: list[Weight] = []
        n = weights.shape[0]

        for src_uid in range(n):
            for tgt_uid in range(weights.shape[1]):
                weight_val = float(weights[src_uid, tgt_uid])
                if weight_val > 0:  # Only store non-zero weights
                    weight_records.append(
                        Weight(
                            id=len(weight_records),
                            source_neuron_uid=src_uid,
                            target_neuron_uid=tgt_uid,
                            block_number=self.block_number,
                            mech_id=0,
                            weight=weight_val,
                            created_at=datetime.now(tz=UTC),
                        )
                    )

        return weight_records if weight_records else None

    def _build_bonds(self, metagraph: Metagraph) -> list[Bond] | None:
        """Build Bond DTOs from metagraph bond matrix."""
        if not hasattr(metagraph, "bonds") or metagraph.bonds is None:
            return None

        bonds = metagraph.bonds
        if not hasattr(bonds, "shape") or len(bonds.shape) != 2:
            return None

        bond_records: list[Bond] = []
        n = bonds.shape[0]

        for src_uid in range(n):
            for tgt_uid in range(bonds.shape[1]):
                bond_val = float(bonds[src_uid, tgt_uid])
                if bond_val > 0:  # Only store non-zero bonds
                    bond_records.append(
                        Bond(
                            id=len(bond_records),
                            source_neuron_uid=src_uid,
                            target_neuron_uid=tgt_uid,
                            block_number=self.block_number,
                            mech_id=0,
                            bond=bond_val,
                            created_at=datetime.now(tz=UTC),
                        )
                    )

        return bond_records if bond_records else None

    def _check_has_weights(self, metagraph: Metagraph, uid: int) -> bool:
        """Check if any validator has set weights for this neuron."""
        if not hasattr(metagraph, "weights") or metagraph.weights is None:
            return False

        weights = metagraph.weights
        if not hasattr(weights, "shape") or len(weights.shape) != 2:
            return False

        # Check if any row (validator) has non-zero weight for this uid (column)
        if uid < weights.shape[1]:
            return bool(np.any(weights[:, uid] > 0))
        return False

    @staticmethod
    def _to_list(tensor) -> list:
        """Convert tensor/array to Python list safely."""
        if tensor is None:
            return []
        if hasattr(tensor, "tolist"):
            return tensor.tolist()
        if hasattr(tensor, "numpy"):
            return tensor.numpy().tolist()
        if isinstance(tensor, (list, tuple)):
            return list(tensor)
        return []
