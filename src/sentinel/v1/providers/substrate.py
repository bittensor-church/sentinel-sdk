"""Substrate blockchain provider."""

from typing import Any

import structlog
from substrateinterface import SubstrateInterface

logger = structlog.get_logger()


class SubstrateProvider:
    """Provider for interacting with Substrate-based blockchains."""

    def __init__(self, url: str, ss58_format: int = 42) -> None:
        """
        Initialize the SubstrateProvider.

        Args:
            url: The Substrate node WebSocket URL
            ss58_format: The SS58 address format (default: 42 for Substrate)

        """
        self._url = url
        self._ss58_format = ss58_format

    def _get_client(self) -> SubstrateInterface:
        return SubstrateInterface(
            url=self._url,
            ss58_format=self._ss58_format,
        )

    def get_chain_head(self) -> str:
        """
        Get the current chain head block hash.

        Returns:
            The block hash of the chain head

        """
        with self._get_client() as client:
            return client.get_chain_head()

    def get_block_header(self, block_hash: str) -> dict[str, Any]:
        """
        Get the block header for a given block hash.

        Args:
            block_hash: The block hash to query

        Returns:
            Block header data including number

        """
        with self._get_client() as client:
            return client.get_block_header(block_hash=block_hash)

    def get_block_hash(self, block_number: int) -> str | None:
        """
        Get the block hash for a given block number.

        Args:
            block_number: The block number to query

        Returns:
            The block hash, or None if not found

        """
        with self._get_client() as client:
            return client.get_block_hash(block_number)

    def get_block(self, block_hash: str) -> dict[str, Any] | None:
        """
        Get full block data for a given block hash.

        Args:
            block_hash: The block hash to query

        Returns:
            Block data including extrinsics, or None if not found

        """
        with self._get_client() as client:
            return client.get_block(block_hash=block_hash)

    def get_events(self, block_hash: str) -> list[Any]:
        """
        Get all events for a given block hash.

        Args:
            block_hash: The block hash to query

        Returns:
            List of events in the block

        """
        with self._get_client() as client:
            return client.get_events(block_hash=block_hash)

    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict[str, Any]]]:
        """
        Get events grouped by extrinsic index.

        This maps each extrinsic to its associated events, useful for
        determining extrinsic success/failure status.

        Args:
            block_hash: The block hash to query

        Returns:
            Dict mapping extrinsic index to list of events

        """
        events = self.get_events(block_hash)
        events_by_idx: dict[int, list[dict[str, Any]]] = {}

        for event in events:
            phase = event.value.get("phase")
            if isinstance(phase, dict) and "ApplyExtrinsic" in phase:
                idx = phase["ApplyExtrinsic"]
                if idx not in events_by_idx:
                    events_by_idx[idx] = []
                events_by_idx[idx].append(
                    {
                        "module_id": event.value.get("module_id"),
                        "event_id": event.value.get("event_id"),
                        "data": event.value.get("attributes"),
                    }
                )

        return events_by_idx

    def get_extrinsic_status(self, block_hash: str, extrinsic_index: int) -> tuple[str, dict | None]:
        """
        Get the status of an extrinsic by its index in a block.

        Args:
            block_hash: The block hash containing the extrinsic
            extrinsic_index: The index of the extrinsic in the block

        Returns:
            Tuple of (status, error_info) where status is "Success", "Failed", or "Unknown"

        """
        events_by_idx = self.get_extrinsic_events(block_hash)
        events = events_by_idx.get(extrinsic_index, [])

        status = "Unknown"
        error_info = None

        for event in events:
            module_id = event.get("module_id")
            event_id = event.get("event_id")

            if module_id == "System" and event_id == "ExtrinsicSuccess":
                status = "Success"
            elif module_id == "System" and event_id == "ExtrinsicFailed":
                status = "Failed"
                error_info = event.get("data")

        return status, error_info
