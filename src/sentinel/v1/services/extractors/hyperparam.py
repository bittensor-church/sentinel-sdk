"""Hyperparameter extractor."""

from sentinel.v1.dto import HyperparametersDTO
from sentinel.v1.providers.base import BlockchainProvider


class HyperparamExtractor:
    """Extracts hyperparameters from a blockchain block."""

    def __init__(self, provider: BlockchainProvider, block_number: int, netuid: int) -> None:
        """
        Initialize the hyperparameter extractor.

        Args:
            provider: The blockchain provider to use for data retrieval
            block_number: The block number to extract hyperparameters from
            netuid: The subnet identifier to extract hyperparameters for

        """
        self.provider = provider
        self.block_number = block_number
        self.netuid = netuid

    def extract(self) -> HyperparametersDTO:
        """
        Extract hyperparameters from the blockchain block.

        This method should query the blockchain and extract all relevant
        hyperparameter values for the given block number.

        Returns:
            HyperparametersDTO containing all extracted hyperparameters

        """
        hyperparameters_json = self.provider.get_subnet_hyperparams(block_number=self.block_number, netuid=self.netuid)
        if hyperparameters_json is None:
            msg = f"Hyperparameters not found for block {self.block_number} and netuid {self.netuid}"
            raise ValueError(msg)

        return HyperparametersDTO.model_validate(hyperparameters_json)
