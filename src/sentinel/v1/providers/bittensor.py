"""Bittensor blockchain provider using the official bittensor SDK (v11)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any

import bittensor as bt
import structlog
from bittensor import Subtensor
from bittensor._transport.errors import StorageFunctionNotFound
from bittensor.hyperparams import RAO_PER_TAO, ratio_fraction
from bittensor.settings import GLOBAL_MAX_SUBNET_COUNT

from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.providers.metagraph import NeuronRecord, SubnetMetagraph

if TYPE_CHECKING:
    from bittensor import BlockInfo

logger = structlog.get_logger()

DEFAULT_NETWORK_URI = "wss://entrypoint-finney.opentensor.ai:443"
ARCHIVE_NODE_URI = "wss://archive.chain.opentensor.ai:443"
BITTENSOR_SS58_FORMAT = 42

# `Timestamp.Now` reads back as 0 when a node holds no state for the block.
UNIX_EPOCH = datetime.fromtimestamp(0, tz=UTC)

# Scores the runtime declares as PerU16 vectors (a u16 fraction over 65535).
PER_U16 = "PerU16"

# v11's `subnet_hyperparameters` read drops the registration and difficulty
# parameters that v10's SubnetHyperparameters carried; they still live in
# storage, so they are read back alongside it.
REGISTRATION_HYPERPARAMS = {
    "rho": bt.storage.SubtensorModule.Rho,
    "difficulty": bt.storage.SubtensorModule.Difficulty,
    "min_difficulty": bt.storage.SubtensorModule.MinDifficulty,
    "max_difficulty": bt.storage.SubtensorModule.MaxDifficulty,
    "adjustment_interval": bt.storage.SubtensorModule.AdjustmentInterval,
    "adjustment_alpha": bt.storage.SubtensorModule.AdjustmentAlpha,
}

# Hyperparameters v11 renamed, mapped back to the names consumers already use.
RENAMED_HYPERPARAMS = {
    "max_weight_limit": "max_weights_limit",
    "commit_reveal_weights_interval": "commit_reveal_period",
}


class BittensorProvider(BlockchainProvider):
    """Provider for interacting with the Bittensor blockchain using official SDK."""

    def __init__(self, uri: str) -> None:
        """
        Initialize the BittensorProvider.

        Args:
            uri: The Bittensor network URI to connect to

        """
        self._uri = uri
        self._subtensor: Subtensor | None = None
        # v11 pins reads by block number, but this provider's interface (and the
        # chain itself) speaks block hashes. Every hash handed out here is
        # remembered so it can be resolved back to the number the SDK wants.
        self._block_number_by_hash: dict[str, int] = {}

    def _get_subtensor(self) -> Subtensor:
        """Get or create a Subtensor instance."""
        if self._subtensor is None:
            self._subtensor = Subtensor(network=self._uri)
        return self._subtensor

    def close(self) -> None:
        """Close the subtensor connection."""
        if self._subtensor:
            self._subtensor.close()
            self._subtensor = None

    def __enter__(self) -> BittensorProvider:
        """Context manager entry."""
        self._get_subtensor()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def get_current_block(self) -> int:
        """
        Retrieve the current block number from the Bittensor blockchain.

        Returns:
            The current block number

        """
        return self._get_subtensor().block

    def get_block_hash(self, block_number: int) -> str | None:
        """
        Retrieve the block hash for a given block number.

        Args:
            block_number: The block number to retrieve the hash for

        Returns:
            The block hash as a string, or None if not found

        """
        block_info = self.get_block_info(block_number=block_number)
        if block_info is None:
            return None
        return block_info.hash

    def get_block_info(
        self,
        block_number: int | None = None,
        block_hash: str | None = None,
    ) -> BlockInfo | None:
        """
        Retrieve complete information about a specific block.

        Args:
            block_number: The block number to retrieve
            block_hash: The block hash to retrieve. Must be a hash this provider
                has previously handed out, since the SDK addresses blocks by number.

        Returns:
            BlockInfo with: number, hash, timestamp, header, extrinsics, explorer_url
            or None if not found

        """
        if block_number is None and block_hash is not None:
            block_number = self._block_number_for_hash(block_hash)

        try:
            block_info = self._get_subtensor().block_info(block_number)
        except Exception:
            logger.warning(
                "Failed to get block info",
                block_number=block_number,
                block_hash=block_hash,
            )
            return None

        if block_info is not None and block_info.hash:
            self._block_number_by_hash[block_info.hash] = block_info.number
        return block_info

    def _block_number_for_hash(self, block_hash: str) -> int:
        """
        Resolve a block hash back to its number.

        The chain offers no hash-to-number lookup, so this only answers for
        hashes this provider itself produced. Callers reach a block hash through
        :meth:`get_block_hash`, which records the mapping.
        """
        block_number = self._block_number_by_hash.get(block_hash)
        if block_number is None:
            msg = (
                f"Unknown block hash {block_hash!r}: the bittensor SDK addresses blocks by "
                f"number, so a hash must come from this provider's get_block_hash()."
            )
            raise ValueError(msg)
        return block_number

    def get_extrinsics(self, block_hash: str) -> list[dict[str, Any]] | None:
        """
        Retrieve extrinsics for a given block hash.

        Args:
            block_hash: The block hash to retrieve extrinsics for

        Returns:
            List of extrinsic dicts with call_module, call_function, call_args, etc.
            or None if not found

        """
        block_number = self._block_number_for_hash(block_hash)
        try:
            block_info = self.get_block_info(block_number=block_number)
            if not block_info:
                return None

            return [
                {
                    "index": idx,
                    "extrinsic_hash": extrinsic.get("extrinsic_hash"),
                    "call_module": call.get("call_module", ""),
                    "call_function": call.get("call_function", ""),
                    "call_args": call.get("call_args", []),
                    "address": extrinsic.get("address"),
                    "signature": extrinsic.get("signature"),
                    "nonce": extrinsic.get("nonce"),
                    "tip": extrinsic.get("tip"),
                }
                for idx, extrinsic in enumerate(block_info.extrinsics)
                for call in [extrinsic.get("call") or {}]
            ]
        except Exception:
            logger.warning("Failed to get extrinsics", block_hash=block_hash)
            return None

    def get_events(self, block_hash: str) -> list[dict[str, Any]]:
        """
        Retrieve serialized events for a given block hash.

        Args:
            block_hash: The block hash to retrieve events for

        Returns:
            List of serialized events in the block

        """
        block_number = self._block_number_for_hash(block_hash)
        try:
            events = self._get_subtensor().query(bt.storage.System.Events, block=block_number)
            return [
                {
                    "phase": event.get("phase"),
                    "extrinsic_idx": event.get("extrinsic_idx"),
                    "event": event.get("event"),
                    "event_index": event.get("event_index"),
                    "module_id": event.get("module_id"),
                    "event_id": event.get("event_id"),
                    "attributes": event.get("attributes"),
                    "topics": event.get("topics"),
                }
                for event in events or []
            ]
        except Exception:
            logger.warning("Failed to get events", block_hash=block_hash)
            return []

    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict[str, Any]]]:
        """
        Get events grouped by extrinsic index.

        Args:
            block_hash: The block hash to query

        Returns:
            Dict mapping extrinsic index to list of events

        """
        events_by_idx: dict[int, list[dict[str, Any]]] = {}

        for event in self.get_events(block_hash):
            # Events raised outside an extrinsic (block initialization and
            # finalization) carry no index and belong to no extrinsic.
            extrinsic_idx = event.get("extrinsic_idx")
            if extrinsic_idx is not None:
                events_by_idx.setdefault(int(extrinsic_idx), []).append(event)

        return events_by_idx

    def get_extrinsic_status(self, block_hash: str, extrinsic_index: int) -> tuple[str, dict[str, Any] | None]:
        """
        Get the status of an extrinsic.

        Args:
            block_hash: The block hash containing the extrinsic
            extrinsic_index: The index of the extrinsic in the block

        Returns:
            Tuple of (status, error_info) where status is "Success", "Failed", or "Unknown"

        """
        events_by_idx = self.get_extrinsic_events(block_hash)
        events = events_by_idx.get(extrinsic_index, [])

        for event in events:
            module_id = event.get("module_id")
            event_id = event.get("event_id")

            if module_id == "System" and event_id == "ExtrinsicSuccess":
                return "Success", None

            if module_id == "System" and event_id == "ExtrinsicFailed":
                return "Failed", event.get("attributes")

        return "Unknown", None

    def get_subnet_hyperparams(
        self,
        block_number: int,
        netuid: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve hyperparameters for a subnet at a specific block.

        Args:
            block_number: The block number to query at
            netuid: The subnet identifier

        Returns:
            Hyperparameters keyed by name, or None if not found. The registration
            and difficulty parameters are read from storage and the two renamed
            keys aliased, so the result carries the same names the v10 SDK's
            ``SubnetHyperparameters`` did.

        """
        try:
            view = self._get_subtensor().at(block_number)
            hyperparams = dict(view.read("subnet_hyperparameters", netuid=netuid))
            for name, item in REGISTRATION_HYPERPARAMS.items():
                hyperparams[name] = view.query(item, [netuid])
        except Exception:
            logger.warning(
                "Failed to fetch subnet hyperparams",
                netuid=netuid,
                block=block_number,
            )
            return None

        # v11 renamed these two; keep the old names so consumers see one shape.
        for old_name, new_name in RENAMED_HYPERPARAMS.items():
            if new_name in hyperparams:
                hyperparams.setdefault(old_name, hyperparams[new_name])

        return hyperparams

    def get_metagraph(
        self,
        netuid: int,
        block_number: int,
        mechid: int = 0,
        *,
        lite: bool = False,
    ) -> SubnetMetagraph | None:
        """
        Get metagraph for a given netuid and block number.

        Args:
            netuid: The subnet identifier
            block_number: The block number to query at
            mechid: The mechanism ID (default: 0)
            lite: If True, skip the weight and bond matrices (default: False)

        Returns:
            A SubnetMetagraph, or None if the subnet does not exist at the block.

        """
        subtensor = self._get_subtensor()
        try:
            graph = subtensor.subnets.metagraph(
                netuid=_mechanism_netuid(netuid, mechid),
                block=block_number,
                commitments=False,
            )
        except Exception:
            logger.warning(
                "Failed to get metagraph",
                netuid=netuid,
                block_number=block_number,
                mechid=mechid,
            )
            return None

        if graph is None:
            return None

        metagraph = _to_subnet_metagraph(graph, netuid=netuid, mechid=mechid, lite=lite)
        self._apply_validator_trust(metagraph, netuid=netuid, block_number=block_number)

        if not lite:
            metagraph.weights = self._read_matrix("weights", netuid, block_number, mechid)
            metagraph.bonds = self._read_matrix("bonds", netuid, block_number, mechid)

        return metagraph

    def _apply_validator_trust(self, metagraph: SubnetMetagraph, netuid: int, block_number: int) -> None:
        """
        Fill in per-neuron ``validator_trust``, which the metagraph call omits.

        The ``get_metagraph`` runtime API does not report validator trust, so it
        comes from the neuron list instead. A failure here leaves the field at
        its 0.0 default rather than losing the whole metagraph.
        """
        try:
            neurons = self._get_subtensor().neurons.all(netuid, block=block_number, lite=True)
        except Exception:
            logger.warning(
                "Failed to read validator trust; leaving it unset",
                netuid=netuid,
                block_number=block_number,
            )
            return

        by_uid = {int(neuron.uid): neuron for neuron in neurons}
        for record in metagraph.neurons:
            neuron = by_uid.get(record.uid)
            if neuron is None:
                continue
            raw_value = int(neuron.raw.get("validator_trust") or 0)
            record.validator_trust = ratio_fraction(PER_U16, raw_value) or 0.0

    def _read_matrix(
        self,
        name: str,
        netuid: int,
        block_number: int,
        mechid: int,
    ) -> dict[int, dict[int, float]] | None:
        """Read the weight or bond matrix, or None when it cannot be fetched."""
        try:
            return self._get_subtensor().at(block_number).read(name, netuid=netuid, mechid=mechid)
        except Exception:
            logger.warning(
                f"Failed to get {name}",
                netuid=netuid,
                block_number=block_number,
                mechid=mechid,
            )
            return None

    def get_mechanism_count(self, netuid: int, block_number: int | None = None) -> int:
        """
        Retrieve the number of mechanisms for a given netuid.

        Args:
            netuid: The subnet identifier
            block_number: Optional block to query at. If None, queries chain head.
                For historical blocks where the `MechanismCountCurrent` storage
                does not yet exist, this provider returns 1.

        Returns:
            The number of mechanisms for the subnet at the given block.

        """
        subtensor = self._get_subtensor()
        view = subtensor.at(block_number) if block_number is not None else subtensor
        try:
            return int(view.read("mechanism_count", netuid=netuid))
        except StorageFunctionNotFound:
            # Before multiple mechanisms were introduced every subnet had one.
            return 1

    def get_all_subnets_netuids(self, exclude_netuids: list[int] | None = None) -> list[int]:
        """
        Retrieve all subnet netuids from the Bittensor blockchain.

        Returns:
            List of subnet netuids

        """
        return [
            subnet.netuid
            for subnet in self._get_subtensor().subnets.all()
            if not exclude_netuids or subnet.netuid not in exclude_netuids
        ]

    def get_runtime_version(self, block_number: int) -> dict[str, Any] | None:
        """
        Retrieve the runtime spec version and name in force at a block.

        Args:
            block_number: The block number to query at

        Returns:
            ``{"spec_version": int, "spec_name": str}``, or None if it could not
            be read. The SDK exposes no block-pinned equivalent of the full
            ``state_getRuntimeVersion`` RPC, so the impl, authoring, transaction
            and state versions are not reported.

        """
        try:
            runtime = self._get_subtensor().query(
                bt.storage.System.LastRuntimeUpgrade,
                block=block_number,
            )
        except Exception:
            logger.warning("Failed to get runtime version", block_number=block_number)
            return None

        if not runtime:
            return None
        return dict(runtime)

    def get_block_timestamp(self, block_number: int) -> datetime | None:
        """
        Retrieve the chain timestamp of a block.

        Args:
            block_number: The block number to query at

        Returns:
            A timezone-aware UTC datetime, or None if it could not be read.

        """
        try:
            timestamp = self._get_subtensor().timestamp(block_number)
        except Exception:
            # The timestamp lives in block state: a pruning node cannot answer
            # for blocks older than its window, which is a routine miss rather
            # than a fault.
            logger.warning("Failed to get block timestamp", block_number=block_number)
            return None

        # Past its state window a node does not necessarily error — the public
        # finney endpoint answers `Timestamp.Now` with the storage default (0) for
        # blocks more than a few thousand back, which decodes to 1970-01-01.
        # Reporting that as a real block time would silently poison anything
        # plotted against it, so treat it as the miss it is.
        if timestamp is None or timestamp <= UNIX_EPOCH:
            logger.warning(
                "Node returned a zero block timestamp; treating the block as unreadable",
                block_number=block_number,
            )
            return None

        return timestamp

    def get_subnet_emission_enabled(self, block_number: int) -> dict[int, bool] | None:
        """
        Retrieve SubtensorModule.SubnetEmissionEnabled for every subnet at a block.

        Args:
            block_number: The block number to query at

        Returns:
            Emission-enabled per netuid, or None if the storage map could not be
            read. Registered subnets with no explicit storage entry are reported
            as enabled, matching the chain's default.

        """
        try:
            view = self._get_subtensor().at(block_number)
            stored = view.query_map(bt.storage.SubtensorModule.SubnetEmissionEnabled)
            explicit = {int(netuid): bool(enabled) for netuid, enabled in stored}
            registered = view.query_map(bt.storage.SubtensorModule.NetworksAdded)
            netuids = [int(netuid) for netuid, exists in registered if bool(exists)]
        except Exception:
            logger.warning("Failed to get subnet emission enabled", block_number=block_number)
            return None

        return {netuid: explicit.get(netuid, True) for netuid in netuids}


def _mechanism_netuid(netuid: int, mechid: int) -> int:
    """
    Address one mechanism of a subnet.

    Per-mechanism state is stored under ``mechid * GLOBAL_MAX_SUBNET_COUNT +
    netuid``, which is just the netuid for mechanism 0 — the only mechanism on
    ordinary subnets.
    """
    return mechid * GLOBAL_MAX_SUBNET_COUNT + netuid


def _balance_amount(value: Any) -> float:
    """Read a Balance as a float in whole units (TAO or alpha), 0.0 when unset."""
    if value is None:
        return 0.0
    return float(getattr(value, "amount", value))


def _to_subnet_metagraph(
    graph: Any,
    netuid: int,
    mechid: int,
    *,
    lite: bool,
) -> SubnetMetagraph:
    """Translate the SDK's Metagraph into sentinel's provider-neutral model."""
    raw = graph.raw or {}
    axons = raw.get("axons") or []

    return SubnetMetagraph(
        netuid=netuid,
        mechid=mechid,
        name=graph.name or "",
        block=int(graph.block or 0),
        tempo=int(graph.tempo or 0),
        immunity_period=int(raw.get("immunity_period") or 0),
        owner_hotkey=graph.owner_hotkey or "",
        owner_coldkey=graph.owner_coldkey or "",
        moving_price=float(graph.moving_price or 0.0),
        # The runtime reports subnet-wide emission in rao; the DTO carries whole units.
        alpha_out_emission=int(raw.get("alpha_out_emission") or 0) / RAO_PER_TAO,
        lite=lite,
        neurons=[
            NeuronRecord(
                uid=neuron.uid,
                hotkey=neuron.hotkey,
                coldkey=neuron.coldkey,
                axon_address=_axon_address(axons[neuron.uid]) if neuron.uid < len(axons) else "",
                active=bool(neuron.active),
                validator_permit=bool(neuron.validator_permit),
                last_update=int(neuron.last_update or 0),
                block_at_registration=int(neuron.block_at_registration or 0),
                rank=float(neuron.rank),
                trust=float(neuron.trust),
                consensus=float(neuron.consensus),
                incentive=float(neuron.incentive),
                dividends=float(neuron.dividends),
                pruning_score=float(neuron.pruning_score),
                emission=_balance_amount(neuron.emission),
                total_stake=_balance_amount(neuron.total_stake),
                alpha_stake=_balance_amount(neuron.alpha_stake),
                tao_stake=_balance_amount(neuron.tao_stake),
                identity_name=_identity_name(neuron.identity),
            )
            for neuron in graph.neurons
        ],
        alpha_dividends_per_hotkey=_dividend_map(raw.get("alpha_dividends_per_hotkey")),
        tao_dividends_per_hotkey=_dividend_map(raw.get("tao_dividends_per_hotkey")),
    )


def _axon_address(axon: dict[str, Any] | None) -> str:
    """Preserve v10's AxonInfo.ip_str(), including unserved endpoints."""
    if axon is None:
        return ""
    ip = ip_address(int(axon.get("ip") or 0))
    return f"/ipv{int(axon.get('ip_type') or 0)}/{ip}:{int(axon.get('port') or 0)}"


def _identity_name(identity: Any) -> str | None:
    """Read a neuron's display name out of its identity record."""
    if isinstance(identity, dict):
        return identity.get("name")
    return getattr(identity, "name", None)


def _dividend_map(pairs: Any) -> dict[str, float]:
    """
    Build a {hotkey: amount} map from the chain's (hotkey, amount) pairs.

    One hotkey may hold several UIDs; the chain pays per hotkey, so a single
    entry covers all of them. Amounts arrive in rao.
    """
    if not pairs:
        return {}
    return {str(hotkey): int(amount or 0) / RAO_PER_TAO for hotkey, amount in pairs}


def bittensor_provider(network_uri: str | None = None) -> BittensorProvider:
    """
    Factory function to create a BittensorProvider instance.

    Args:
        network_uri: The Bittensor network URI. If not provided, reads from
                     BITTENSOR_NETWORK environment variable or uses default.

    Returns:
        BittensorProvider instance

    """
    uri = network_uri or os.getenv("BITTENSOR_NETWORK") or DEFAULT_NETWORK_URI
    return BittensorProvider(uri)
