import pytest

from sentinel.v1.services.extractors.events.extractor import EventsExtractor
from tests.unit.v1.providers import FakeBittensorProvider


def test_event_extractor(fake_provider: FakeBittensorProvider):
    batch_amount = 3
    block_number = 100
    block_hash = "0xabc123"

    fake_provider.with_block(block_number, block_hash).with_events(
        block_hash,
        FakeBittensorProvider.create_mock_events(batch_amount),
    )

    extractor = EventsExtractor(fake_provider, block_number=block_number)
    events = extractor.extract()
    assert len(events) == batch_amount


def test_event_extractor_no_block_hash(fake_provider: FakeBittensorProvider):
    block_number = 999

    extractor = EventsExtractor(fake_provider, block_number=block_number)
    with pytest.raises(ValueError, match=f"Block hash not found for block number {block_number}"):
        extractor.extract()


def test_event_extractor_no_events(fake_provider: FakeBittensorProvider):
    block_number = 200
    block_hash = "0xdef456"

    fake_provider.with_block(block_number, block_hash)

    extractor = EventsExtractor(fake_provider, block_number=block_number)
    events = extractor.extract()
    assert len(events) == 0
