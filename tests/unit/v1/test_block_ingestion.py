from sentinel.v1.services.sentinel import sentinel_service
from tests.unit.v1.providers import FakeBittensorProvider


def test_block_ingestion(fake_provider: FakeBittensorProvider):
    batch_amount = 5
    block_number = 1000000
    block_hash = "0xabc123"
    fake_provider.with_block(block_number, block_hash).with_extrinsics(
        block_hash,
        FakeBittensorProvider.create_mock_extrinsics(batch_amount),
    )
    service = sentinel_service(fake_provider)
    block = service.ingest_block(block_number)

    assert len(block.extrinsics) == batch_amount
