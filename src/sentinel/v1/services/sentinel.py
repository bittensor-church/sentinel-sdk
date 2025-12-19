from sentinel.v1.models.block import Block
from sentinel.v1.models.subnet import Subnet
from sentinel.v1.providers import BlockchainProvider


class SentinelService:
    """Service for ingesting and processing blockchain blocks."""

    def __init__(self, provider: BlockchainProvider) -> None:
        """
        Initialize the SentinelService with a blockchain provider.

        Args:
            provider: The blockchain provider to use for data retrieval

        """
        self.provider = provider

    def ingest_block(self, block_number: int, netuid: int | None = None) -> Block:
        """
        Ingest a block and return a lazy-loaded Block instance.

        The returned Block object uses lazy loading - data extractors
        are only triggered when their corresponding properties are accessed.

        Args:
            block_number: The blockchain block number to ingest
            netuid: Optional subnet ID for hyperparameter queries

        Returns:
            Block instance with lazy-loaded properties

        """
        return Block(self.provider, block_number, netuid)

    def ingest_subnet(self, netuid: int, block_number: int, mechid: int | None = None) -> Subnet:
        """
        Ingest a subnet-specific block and return a lazy-loaded Block instance.

        The returned Block object uses lazy loading - data extractors
        are only triggered when their corresponding properties are accessed.

        Args:
            netuid: The subnet ID for hyperparameter queries
            block_number: The blockchain block number to ingest
            mechid: The mechanism ID for the subnet (default is 0)

        Returns:
            Block instance with lazy-loaded properties

        """
        return Subnet(self.provider, netuid, block_number, mechid=mechid)


def sentinel_service(provider: BlockchainProvider) -> SentinelService:
    """
    Factory function to create a SentinelService service instance.

    Returns:
        SentinelService service instance

    """
    return SentinelService(provider)
