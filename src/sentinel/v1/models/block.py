"""Block model with lazy loading."""

from functools import cached_property

from sentinel.v1.dto import EventDTO, ExtrinsicDTO, HyperparametersDTO
from sentinel.v1.providers.bittensor import BittensorProvider
from sentinel.v1.services.extractors.events.extractor import EventsExtractor
from sentinel.v1.services.extractors.extrinsics import ExtrinsicExtractor
from sentinel.v1.services.extractors.hyperparam import HyperparamExtractor


class Block:
    """
    Lazy-loading block model that extracts data on-demand.

    Data is extracted only when accessed via properties, implementing
    the lazy loading pattern to avoid unnecessary computation.
    """

    def __init__(self, provider: BittensorProvider, block_number: int, netuid: int | None = None) -> None:
        """
        Initialize a Block instance.

        Args:
            provider: The blockchain provider to use for data retrieval
            block_number: The blockchain block number to process
            netuid: Optional subnet ID for hyperparameter queries

        """
        self.provider = provider
        self.block_number = block_number
        self.netuid = netuid

    @cached_property
    def extrinsics(self) -> list[ExtrinsicDTO]:
        """
        Retrieve extrinsics for this block with associated events.

        Returns:
            List of ExtrinsicDTO containing the block's extrinsics

        """
        extractor = ExtrinsicExtractor(self.provider, self.block_number)
        raw_extrinsics = extractor.extract()

        # Attach events to extrinsics
        events = self.events
        if not events:
            return raw_extrinsics

        return [
            ext.model_copy(update={"events": [e for e in events if e.extrinsic_idx == idx]})
            for idx, ext in enumerate(raw_extrinsics)
        ]

    def transactions(self) -> list[dict]:
        """
        Retrieve transactions for this block.

        Returns:
            List of transactions in the block

        """
        msg = "Transaction extraction not yet implemented"
        raise NotImplementedError(msg)

    @cached_property
    def events(self) -> list[EventDTO]:
        """
        Retrieve events for this block.

        Returns:
            List of EventDTO containing the block's events

        """
        extractor = EventsExtractor(self.provider, self.block_number)
        return extractor.extract()

    def metagraph(self) -> dict:
        """
        Retrieve metagraph for this block.

        Returns:
            Metagraph data for the block

        """
        msg = "Metagraph extraction not yet implemented"
        raise NotImplementedError(msg)

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
        if self.netuid is None:
            msg = "netuid must be provided to access hyperparameters"
            raise ValueError(msg)
        extractor = HyperparamExtractor(self.provider, self.block_number, self.netuid)
        return extractor.extract()
