from sentinel.v1.dto import EventDTO
from sentinel.v1.providers import BlockchainProvider


class EventsExtractor:
    """Extractor for events from blocks."""

    def __init__(
        self,
        provider: BlockchainProvider,
        block_number: int,
    ) -> None:
        self.provider = provider
        self.block_number = block_number

    def extract(self) -> list[EventDTO]:
        """Extract events from the block."""
        block_hash = self.provider.get_block_hash(self.block_number)
        if block_hash is None:
            msg = f"Block hash not found for block number {self.block_number}"
            raise ValueError(msg)

        events = self.provider.get_events(block_hash)
        return [EventDTO.model_validate(event) for event in events]
