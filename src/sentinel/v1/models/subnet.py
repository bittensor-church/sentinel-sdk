from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

from sentinel.v1.dto import HyperparametersDTO
from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.services.extractors.hyperparam import HyperparamExtractor
from sentinel.v1.services.extractors.metagraph.extractor import MetagraphExtractor

if TYPE_CHECKING:
    from bittensor.core.chain_data import MetagraphInfo  # type: ignore[import-untyped]


class Subnet:
    def __init__(self, provider: BlockchainProvider, netuid: int, block_number: int, mech_id: int = 0) -> None:
        self.provider = provider
        self.block_number = block_number
        self.netuid = netuid
        self.mech_id = mech_id

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
    def metagraph(self) -> MetagraphInfo | None:
        """
        Retrieve metagraph for this block.

        Returns:
            Metagraph data for the block

        """
        import bittensor  # type: ignore[import-untyped]  # noqa: PLC0415

        subtensor = bittensor.subtensor()
        extractor = MetagraphExtractor(subtensor, self.block_number, self.netuid, mech_id=self.mech_id)
        return extractor.extract()
