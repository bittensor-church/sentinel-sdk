from datetime import UTC, datetime
from typing import Any

import structlog

from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.providers.metagraph import NeuronRecord, SubnetMetagraph
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
        *,
        lite: bool = False,
        skip_timestamp: bool = False,
    ) -> None:
        self.subtensor = subtensor
        self.block_number = block_number
        self.netuid = netuid
        self.mechid = mechid
        self.lite = lite
        self.skip_timestamp = skip_timestamp

    def extract(self) -> FullSubnetSnapshot | None:
        """
        Extract metagraph for the given block number and netuid.

        Returns a FullSubnetSnapshot with all neuron data and optional tensor data.
        """
        if self.mechid is not None:
            metagraph = self.extract_by_mech_id(mechid=self.mechid)
            metagraphs = [metagraph] if metagraph else []
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

    def extract_raw(self) -> list[SubnetMetagraph]:
        """
        Extract raw metagraph objects without DTO conversion.

        Returns list of SubnetMetagraph objects for all mechanisms.
        """
        if self.mechid is not None:
            metagraph = self.extract_by_mech_id(mechid=self.mechid)
            return [metagraph] if metagraph else []
        return self.extract_all_mechids()

    def extract_by_mech_id(self, mechid: int) -> SubnetMetagraph | None:
        """
        Extract metagraph for the given block number, netuid, and mechid.
        """
        metagraph = self.subtensor.get_metagraph(
            netuid=self.netuid,
            block_number=self.block_number,
            mechid=mechid,
            lite=self.lite,
        )
        if not metagraph:
            logger.warning(
                "MetagraphExtractor.extract_by_mech_id: No metagraph found",
                netuid=self.netuid,
                block_number=self.block_number,
                mechid=mechid,
            )
        return metagraph

    def extract_all_mechids(self) -> list[SubnetMetagraph]:
        """
        Extract metagraphs for all mechids for the given block number and netuid.
        """
        mechanism_counter = self.subtensor.get_mechanism_count(self.netuid, block_number=self.block_number)
        metagraphs = []
        for mech_id in range(mechanism_counter):
            metagraph = self.extract_by_mech_id(mechid=mech_id)
            if metagraph:
                metagraphs.append(metagraph)
        return metagraphs

    def _build_full_snapshot(self, metagraphs: list[SubnetMetagraph]) -> FullSubnetSnapshot:
        """
        Build a FullSubnetSnapshot from extracted metagraph data.

        Args:
            metagraphs: List of SubnetMetagraph objects (one per mechanism)

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

    def _build_block(self, metagraph: SubnetMetagraph) -> Block:
        """Build Block DTO from metagraph."""
        block_number = int(metagraph.block)

        timestamp = datetime.now(tz=UTC)
        if not self.skip_timestamp:
            # Get block timestamp from provider (adds extra RPC call)
            block_info = self.subtensor.get_block_info(block_number=block_number)
            if block_info and getattr(block_info, "timestamp", None):
                timestamp = block_info.timestamp

        return Block(
            block_number=block_number,
            timestamp=timestamp,
        )

    def _build_subnet(self, metagraph: SubnetMetagraph) -> SubnetWithOwner:
        """Build SubnetWithOwner DTO from metagraph."""
        owner_hotkey = None
        if metagraph.owner_hotkey:
            owner_coldkey = None
            if metagraph.owner_coldkey:
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
            name=metagraph.name,
            alpha_out_emission=metagraph.alpha_out_emission,
            moving_price=metagraph.moving_price,
            tempo=metagraph.tempo,
            owner_hotkey_id=None,
            registered_at=datetime.now(tz=UTC),  # Would come from chain
            owner_hotkey=owner_hotkey,
        )

    def _build_neuron_snapshots(
        self,
        metagraphs: list[SubnetMetagraph],
        block: Block,
    ) -> list[NeuronSnapshotFull]:
        """
        Build NeuronSnapshotFull DTOs from metagraph data.

        Combines data from all mechanism metagraphs into unified neuron snapshots.
        """
        base_metagraph = metagraphs[0]

        # Calculate total stake for normalization
        total_subnet_stake = base_metagraph.total_stake_sum() or 1.0

        neurons: list[NeuronSnapshotFull] = []

        for neuron in base_metagraph.neurons:
            # Build mechanism metrics from all metagraphs
            mechanisms = [
                self._build_mechanism_metrics(mg, neuron.uid, mech_idx) for mech_idx, mg in enumerate(metagraphs)
            ]

            neurons.append(
                self._build_single_neuron_snapshot(
                    metagraph=base_metagraph,
                    neuron=neuron,
                    total_subnet_stake=total_subnet_stake,
                    mechanisms=mechanisms,
                    block=block,
                ),
            )

        return neurons

    def _build_single_neuron_snapshot(
        self,
        metagraph: SubnetMetagraph,
        neuron: NeuronRecord,
        total_subnet_stake: float,
        mechanisms: list[MechanismMetrics],
        block: Block,
    ) -> NeuronSnapshotFull:
        """Build a single NeuronSnapshotFull for a given neuron."""
        uid = neuron.uid

        alpha_dividends = metagraph.alpha_dividends_per_hotkey.get(neuron.hotkey, 0.0)
        tao_dividends = metagraph.tao_dividends_per_hotkey.get(neuron.hotkey, 0.0)

        normalized_stake = neuron.total_stake / total_subnet_stake if total_subnet_stake > 0 else 0.0

        # Determine immunity status
        reg_block = neuron.block_at_registration
        is_immune = (block.block_number - reg_block) < metagraph.immunity_period if reg_block else False

        hotkey_dto = HotkeyWithColdkey(
            hotkey=neuron.hotkey,
            coldkey=Coldkey(
                id=0,
                coldkey=neuron.coldkey,
                created_at=datetime.now(tz=UTC),
            )
            if neuron.coldkey
            else None,
        )

        subnet_dto = Subnet(
            netuid=metagraph.netuid,
            name=metagraph.name,
            alpha_out_emission=metagraph.alpha_out_emission,
            moving_price=metagraph.moving_price,
            tempo=metagraph.tempo,
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
            axon_address=neuron.axon_address,
            total_stake=neuron.total_stake,
            alpha_stake=neuron.alpha_stake,
            normalized_stake=normalized_stake,
            alpha_dividends=alpha_dividends,
            tao_dividends=tao_dividends,
            rank=neuron.rank,
            trust=neuron.trust,
            emissions=neuron.emission,
            is_active=neuron.active,
            is_validator=neuron.validator_permit,
            is_immune=is_immune,
            has_any_weights=metagraph.has_incoming_weights(uid),
            neuron_version=None,
            block_at_registration=reg_block,
            id=uid,  # Placeholder
            neuron_id=uid,
            block_number=block.block_number,
            mechanisms=mechanisms,
            neuron=neuron_dto,
            block=block,
        )

    @staticmethod
    def _build_mechanism_metrics(
        metagraph: SubnetMetagraph,
        uid: int,
        mech_id: int,
    ) -> MechanismMetrics:
        """Build MechanismMetrics for a neuron from a specific mechanism's metagraph."""
        neuron = metagraph.neuron(uid)

        return MechanismMetrics(
            id=0,  # Placeholder
            snapshot_id=0,  # Placeholder
            mech_id=mech_id,
            incentive=neuron.incentive if neuron else 0.0,
            dividend=neuron.dividends if neuron else 0.0,
            consensus=neuron.consensus if neuron else 0.0,
            validator_trust=neuron.validator_trust if neuron else 0.0,
            weights_sum=metagraph.weights_sum(uid),
            last_update=neuron.last_update if neuron else 0,
        )

    def _build_weights(self, metagraph: SubnetMetagraph) -> list[Weight] | None:
        """Build Weight DTOs from the metagraph's weight matrix."""
        return self._build_matrix_records(metagraph.weights, Weight, "weight")

    def _build_bonds(self, metagraph: SubnetMetagraph) -> list[Bond] | None:
        """Build Bond DTOs from the metagraph's bond matrix."""
        return self._build_matrix_records(metagraph.bonds, Bond, "bond")

    def _build_matrix_records(
        self,
        matrix: dict[int, dict[int, float]] | None,
        dto_cls: type,
        value_field: str,
    ) -> list | None:
        """
        Flatten a sparse ``{source: {target: value}}`` matrix into DTO rows.

        The matrix is already sparse, so only the non-zero entries the chain
        stores are emitted. None (matrix never fetched) and an all-zero matrix
        both yield None, matching how the caller treats "nothing to record".
        """
        if not matrix:
            return None

        records: list[Any] = []
        for source_uid, row in matrix.items():
            for target_uid, value in row.items():
                if value > 0:
                    records.append(
                        dto_cls(
                            id=len(records),
                            source_neuron_uid=source_uid,
                            target_neuron_uid=target_uid,
                            block_number=self.block_number,
                            mech_id=0,
                            created_at=datetime.now(tz=UTC),
                            **{value_field: value},
                        ),
                    )

        return records or None
