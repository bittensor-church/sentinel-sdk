from functools import cached_property

from sentinel.v1.dto import HyperparametersDTO
from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.services.extractors.hyperparam import HyperparamExtractor


class Subnet:

    def __init__(self, provider: BlockchainProvider, netuid: int, block_number: int) -> None:
        self.provider = provider
        self.block_number = block_number
        self.netuid = netuid

    @cached_property
    def hyperparameters(self) -> HyperparametersDTO:
        """
        Lazily extract and return hyperparameters for this block.

        The extraction only happens on first access, then cached.
        Requires netuid to be set during Block initialization.

        Returns:
            HyperparametersDTO containing the block's hyperparameters

        Raises:
            ValueError: If netuid was not provided during initialization

        """
        extractor = HyperparamExtractor(self.provider, self.block_number, self.netuid)
        return extractor.extract()

    def metagraph(self) -> dict:
        """
        Retrieve metagraph for this block.

        Returns:
            Metagraph data for the block

        """
        msg = "Metagraph extraction not yet implemented"
        raise NotImplementedError(msg)
