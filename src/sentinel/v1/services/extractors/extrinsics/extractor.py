"""Extrinsic extractor."""

from sentinel.v1.dto import ExtrinsicDTO
from sentinel.v1.providers.bittensor import BittensorProvider


class ExtrinsicExtractor:
    """Extracts extrinsics from a blockchain block."""

    def __init__(self, provider: BittensorProvider, block_number: int) -> None:
        """
        Initialize the extrinsic extractor.

        Args:
            provider: The blockchain provider to use for data retrieval
            block_number: The block number to extract extrinsics from

        """
        self.provider = provider
        self.block_number = block_number

    def extract(self) -> list[ExtrinsicDTO]:
        """
        Extract extrinsics from the blockchain block.

        Returns:
            List of ExtrinsicDTO containing all extracted extrinsics

        """
        block_hash = self.provider.get_hash_by_block_number(self.block_number)
        if not block_hash:
            msg = f"Block hash not found for block number {self.block_number}"
            raise ValueError(msg)

        extrinsics_json = self.provider.get_extrinsics(block_hash=block_hash)
        if extrinsics_json is None:
            return []

        return [ExtrinsicDTO.model_validate(ext) for ext in extrinsics_json]
