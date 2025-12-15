from typing import Any

from sentinel.v1.providers.base import BlockchainProvider


class SubnetInfoExtractor:
    def __init__(self, provider: BlockchainProvider, netuid: int, block_number: int) -> None:
        self.provider = provider
        self.netuid = netuid
        self.block_number = block_number

    def extract(self) -> dict[str, Any]:
        """
        Extract subnet information from the blockchain.
        """
        return {
            "netuid": self.netuid,
            "block_number": self.block_number,
            "info": "Subnet information extracted from blockchain provider.",
        }
