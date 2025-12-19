"""Bittensor blockchain provider using the official bittensor SDK."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import structlog
from bittensor.core.subtensor import Subtensor

from sentinel.v1.providers.base import BlockchainProvider

if TYPE_CHECKING:
    from bittensor.core.chain_data import SubnetHyperparameters
    from bittensor.core.metagraph import Metagraph
    from bittensor.core.types import BlockInfo

logger = structlog.get_logger()

DEFAULT_NETWORK_URI = "wss://entrypoint-finney.opentensor.ai:443"
BITTENSOR_SS58_FORMAT = 42


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

    def _get_subtensor(self) -> Subtensor:
        """Get or create a Subtensor instance."""
        if self._subtensor is None:
            self._subtensor = Subtensor(network=self._uri)
        return self._subtensor

    @property
    def substrate(self) -> Any:
        """Get the substrate interface from subtensor."""
        return self._get_subtensor().substrate

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
        subtensor = self._get_subtensor()
        return subtensor.get_current_block()

    def get_block_hash(self, block_number: int) -> str | None:
        """
        Retrieve the block hash for a given block number.

        Args:
            block_number: The block number to retrieve the hash for

        Returns:
            The block hash as a string, or None if not found

        """
        try:
            subtensor = self._get_subtensor()
            return subtensor.get_block_hash(block_number)
        except Exception:
            logger.exception("Failed to get block hash", block_number=block_number)
            return None

    def get_hash_by_block_number(self, block_number: int) -> str | None:
        """
        Retrieve the block hash for a given block number.

        Args:
            block_number: The block number to retrieve the hash for

        Returns:
            The block hash as a string, or None if not found

        Raises:
            ConnectionError: If WebSocket connection to the network fails

        """
        try:
            return self.get_block_hash(block_number)
        except Exception as e:
            if "'NoneType' object has no attribute 'send'" in str(e):
                msg = f"WebSocket connection failed - unable to connect to Bittensor network at {self._uri}"
                raise ConnectionError(msg) from e
            raise

    def get_block_info(
        self,
        block_number: int | None = None,
        block_hash: str | None = None,
    ) -> BlockInfo | None:  # type: ignore[name-defined]
        """
        Retrieve complete information about a specific block.

        Args:
            block_number: The block number to retrieve
            block_hash: The block hash to retrieve

        Returns:
            BlockInfo with: number, hash, timestamp, header, extrinsics, explorer
            or None if not found

        """
        try:
            subtensor = self._get_subtensor()
            return subtensor.get_block_info(
                block=block_number,
                block_hash=block_hash,
            )
        except Exception:
            logger.exception(
                "Failed to get block info",
                block_number=block_number,
                block_hash=block_hash,
            )
            return None

    def get_extrinsics(self, block_hash: str) -> list[dict[str, Any]] | None:
        """
        Retrieve extrinsics for a given block hash.

        Args:
            block_hash: The block hash to retrieve extrinsics for

        Returns:
            List of extrinsic dicts with call_module, call_function, call_args, etc.
            or None if not found

        """
        try:
            block_info = self.get_block_info(block_hash=block_hash)
            if not block_info:
                return None

            extrinsics = []
            for idx, ext in enumerate(block_info.extrinsics):
                serialized = ext.value_serialized
                call = serialized.get("call", {})
                extrinsics.append(
                    {
                        "index": idx,
                        "extrinsic_hash": getattr(ext, "extrinsic_hash", None),
                        "call_module": call.get("call_module", ""),
                        "call_function": call.get("call_function", ""),
                        "call_args": call.get("call_args", []),
                        "address": serialized.get("address"),
                        "signature": serialized.get("signature"),
                        "nonce": serialized.get("nonce"),
                        "tip": serialized.get("tip"),
                    }
                )
            return extrinsics
        except Exception:
            logger.exception("Failed to get extrinsics", block_hash=block_hash)
            return None

    def get_events(self, block_hash: str) -> list[dict[str, Any]]:
        """
        Retrieve serialized events for a given block hash.

        Args:
            block_hash: The block hash to retrieve events for

        Returns:
            List of serialized events in the block

        """
        try:
            subtensor = self._get_subtensor()
            events = subtensor.substrate.get_events(block_hash=block_hash)
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
                for event in events
            ]
        except Exception:
            logger.exception("Failed to get events", block_hash=block_hash)
            return []

    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict[str, Any]]]:
        """
        Get events grouped by extrinsic index.

        Args:
            block_hash: The block hash to query

        Returns:
            Dict mapping extrinsic index to list of events

        """
        events = self.get_events(block_hash)
        events_by_idx: dict[int, list[dict[str, Any]]] = {}

        for event in events:
            phase = event.get("phase")
            if isinstance(phase, dict) and "ApplyExtrinsic" in phase:
                idx = phase["ApplyExtrinsic"]
                events_by_idx.setdefault(idx, []).append(event)

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
    ) -> list[Any] | SubnetHyperparameters | None:
        """
        Retrieve hyperparameters for a subnet at a specific block.

        Args:
            block_number: The block number to query at
            netuid: The subnet identifier

        Returns:
            SubnetHyperparameters or None if not found

        """
        try:
            subtensor = self._get_subtensor()
            return subtensor.get_subnet_hyperparameters(
                netuid=netuid,
                block=block_number,
            )
        except Exception:
            logger.exception(
                "Failed to fetch subnet hyperparams",
                netuid=netuid,
                block=block_number,
            )
            return None

    def get_metagraph(
        self,
        netuid: int,
        block_number: int,
        mechid: int = 0,
    ) -> Metagraph | None:
        """
        Get metagraph for a given netuid and block number.
        """
        subtensor = self._get_subtensor()
        return subtensor.metagraph(netuid=netuid, block=block_number, mechid=mechid, lite=False)

    def get_mechanism_count(self, netuid: int) -> int:
        """
        Retrieve available mech IDs for a given netuid.

        Args:
            netuid: The subnet identifier
        Returns:
            List of mech IDs

        """
        subtensor = self._get_subtensor()
        return subtensor.get_mechanism_count(netuid=netuid)

    def get_all_subnets_netuids(self, exclude_netuids: list[int] | None = None) -> list[int]:
        """
        Retrieve all subnet netuids from the Bittensor blockchain.

        Returns:
            List of subnet netuids

        """
        subtensor = self._get_subtensor()
        return [
            subnet.netuid
            for subnet in subtensor.get_all_subnets_info()
            if not exclude_netuids or subnet.netuid not in exclude_netuids
        ]


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
