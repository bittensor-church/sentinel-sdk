"""Bittensor blockchain provider."""

import os

import structlog
from asgiref.sync import async_to_sync
from turbobt import Bittensor
from turbobt.block import Block
from turbobt.subnet import SubnetHyperparams
from turbobt.substrate.pallets.chain import Extrinsic

from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.providers.substrate import SubstrateProvider

logger = structlog.get_logger()

DEFAULT_NETWORK_URI = "wss://entrypoint-finney.opentensor.ai:443"
BITTENSOR_SS58_FORMAT = 42


class BittensorProvider(BlockchainProvider):
    """Provider for interacting with the Bittensor blockchain."""

    def __init__(self, uri: str) -> None:
        """
        Initialize the BittensorProvider.

        Args:
            uri: The Bittensor network URI to connect to

        """
        self._uri = uri
        self._substrate: SubstrateProvider | None = None

    @property
    def substrate(self) -> SubstrateProvider:
        """Get the underlying SubstrateProvider for low-level access."""
        if self._substrate is None:
            self._substrate = SubstrateProvider(self._uri, ss58_format=BITTENSOR_SS58_FORMAT)
        return self._substrate

    def _get_client(self) -> Bittensor:
        return Bittensor(self._uri)

    @async_to_sync
    async def get_block_hash(self, block_number: int) -> str | None:
        """
        Retrieve the block hash for a given block number.

        Args:
            block_number: The block number to retrieve the hash for
        Returns:
            The block hash as a string, or None if not found

        """
        async with self._get_client() as client:
            return await client.subtensor.chain.getBlockHash(block_number)

    @async_to_sync
    async def get_current_block(self) -> Block:
        """
        Retrieve the current block from the Bittensor blockchain.

        Returns:
            Current Block instance

        """
        async with self._get_client() as client:
            return await client.head.get()

    @async_to_sync
    async def get_subnet_hyperparams(self, block_hash: str, netuid: int) -> SubnetHyperparams | None:
        """
        Retrieve hyperparameters for a subnet at a specific block.

        Args:
            block_hash: The block hash to query at
            netuid: The subnet identifier

        Returns:
            SubnetHyperparams or None if not found

        """
        try:
            async with self._get_client() as client:
                return await client.subnet(netuid).get_hyperparameters(block_hash)
        except Exception:
            logger.exception("Failed to fetch subnet hyperparams", netuid=netuid, block_hash=block_hash)
            return None

    @async_to_sync
    async def get_hash_by_block_number(self, block_number: int) -> str | None:
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
            async with self._get_client() as client:
                return await client.subtensor.chain.getBlockHash(block_number)
        except AttributeError as e:
            if "'NoneType' object has no attribute 'send'" in str(e):
                msg = f"WebSocket connection failed - unable to connect to Bittensor network at {self._uri}"
                raise ConnectionError(msg) from e
            raise

    @async_to_sync
    async def get_extrinsics(self, block_hash: str) -> list[Extrinsic] | None:
        """
        Retrieve extrinsics for a given block hash.

        Args:
            block_hash: The block hash to retrieve extrinsics for

        Returns:
            Extrinsics data, or None if not found

        """
        try:
            async with self._get_client() as client:
                signed_block = await client.subtensor.chain.getBlock(block_hash)
                if not signed_block:
                    return None
                return signed_block["block"]["extrinsics"]
        except Exception:
            logger.exception("Failed to fetch extrinsics", block_hash=block_hash)
            return None

    def get_events(self, block_hash: str) -> list[dict]:
        """
        Retrieve serialized events for a given block hash.

        Args:
            block_hash: The block hash to retrieve events for

        Returns:
            List of serialized events in the block

        """
        raw_events = self.substrate.get_events(block_hash)
        return [event.serialize() for event in raw_events]

    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict]]:
        """
        Get events grouped by extrinsic index.

        Args:
            block_hash: The block hash to query

        Returns:
            Dict mapping extrinsic index to list of events

        """
        return self.substrate.get_extrinsic_events(block_hash)

    def get_extrinsic_status(self, block_hash: str, extrinsic_index: int) -> tuple[str, dict | None]:
        """
        Get the status of an extrinsic.

        Args:
            block_hash: The block hash containing the extrinsic
            extrinsic_index: The index of the extrinsic in the block

        Returns:
            Tuple of (status, error_info)

        """
        return self.substrate.get_extrinsic_status(block_hash, extrinsic_index)


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
