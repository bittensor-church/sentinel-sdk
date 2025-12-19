from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

from sentinel.v1.services.extractors.hyperparam import HyperparamExtractor
from sentinel.v1.services.extractors.metagraph.extractor import MetagraphExtractor
from sentinel.v1.services.extractors.subnet.extractor import SubnetInfoExtractor

if TYPE_CHECKING:
    from sentinel.v1.dto import HyperparametersDTO
    from sentinel.v1.providers.base import BlockchainProvider
    from sentinel.v1.services.extractors.metagraph.dto import FullSubnetSnapshot


class Subnet:
    def __init__(
        self,
        provider: BlockchainProvider,
        netuid: int,
        block_number: int,
        mechid: int | None = None,
    ) -> None:
        self.provider = provider
        self.block_number = block_number
        self.netuid = netuid
        self.mechid = mechid

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

    @cached_property
    def metagraph(self) -> FullSubnetSnapshot | None:
        """
        Retrieve metagraph snapshot for this block.

        Returns:
            FullSubnetSnapshot with all neuron data and metrics

        """
        extractor = MetagraphExtractor(self.provider, self.block_number, self.netuid, mechid=self.mechid)
        return extractor.extract()

    @cached_property
    def info(self) -> dict[str, Any]:
        """
        Get a summary of subnet information.

        Returns:
            Dictionary with subnet summary information

        """
        extractor = SubnetInfoExtractor(self.provider, self.netuid, self.block_number)
        return extractor.extract()
