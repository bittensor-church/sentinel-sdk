from sentinel.v1.dto import EventDTO
from sentinel.v1.providers.bittensor import BittensorProvider


class EventsExtractor:
    """Extractor for events from blocks."""

    def __init__(
        self,
        provider: BittensorProvider,
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

        raw_events = self.provider.get_events(block_hash)
        return [EventDTO.model_validate(event.serialize()) for event in raw_events]
