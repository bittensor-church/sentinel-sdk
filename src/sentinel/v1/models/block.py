"""Block model with lazy loading."""

from functools import cached_property

from sentinel.v1.dto import EventDTO, ExtrinsicDTO
from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.services.extractors.events.extractor import EventsExtractor
from sentinel.v1.services.extractors.extrinsics import ExtrinsicExtractor
from sentinel.v1.services.extractors.extrinsics.filters import filter_timestamp_extrinsic


class Block:
    """
    Lazy-loading block model that extracts data on-demand.

    Data is extracted only when accessed via properties, implementing
    the lazy loading pattern to avoid unnecessary computation.
    """

    def __init__(self, provider: BlockchainProvider, block_number: int, netuid: int | None = None) -> None:
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

    def transactions(self) -> list[dict]:
        """
        Retrieve transactions for this block.

        Returns:
            List of transactions in the block

        """
        msg = "Transaction extraction not yet implemented"
        raise NotImplementedError(msg)

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
            ext.model_copy(update={"events": [e for e in events if e.extrinsic_idx == ext.index]})
            for ext in raw_extrinsics
        ]

    @cached_property
    def timestamp(self) -> int | None:
        """
        Retrieve the timestamp of this block.

        Returns:
            Block timestamp as an integer

        """
        timestampt_extrinsic = filter_timestamp_extrinsic(self.extrinsics)

        try:
            value = timestampt_extrinsic[0].call.call_args[0].value
            timestamp = int(value) if isinstance(value, (int, str)) else None
        except (IndexError, AttributeError, ValueError, TypeError):
            timestamp = None
        return timestamp

    @cached_property
    def events(self) -> list[EventDTO]:
        """
        Retrieve events for this block.

        Returns:
            List of EventDTO containing the block's events

        """
        extractor = EventsExtractor(self.provider, self.block_number)
        return extractor.extract()
