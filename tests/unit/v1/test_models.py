from typing import Any

from sentinel.v1.models.block import Block
from sentinel.v1.providers.base import BlockchainProvider
from tests.fixtures.extrinsics import EXTRINSICS_RESPONSE


def block_with_extrinsics_and_events():
    return EXTRINSICS_RESPONSE


class FakeBlockchainProvider(BlockchainProvider):
    def get_hash_by_block_number(self, block_number: int) -> str | None:
        return "hash_for_block_" + str(block_number)

    def get_subnet_hyperparams(self, block_number: int, netuid: int) -> Any:
        return {"param1": "value1", "param2": "value2"}

    def get_block_info(self, block_number: int | None = None, block_hash: str | None = None) -> Any:
        return {"number": block_number, "hash": block_hash}

    def get_current_block(self) -> int:
        return 1000

    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict[str, Any]]]:
        return {}

    def get_extrinsic_status(self, block_hash: str, extrinsic_index: int) -> tuple[str, dict[str, Any] | None]:
        return "success", None

    def get_block_hash(self, block_number: int) -> str | None:
        return "0xfakeblockhash"

    def get_extrinsics(self, block_hash: str) -> list[dict]:
        return EXTRINSICS_RESPONSE

    def close(self) -> None:
        return None

    def get_events(self, block_hash: str) -> list[dict]:
        return []

    def get_metagraph(self, netuid: int, block_number: int, mechid: int = 0) -> Any:
        return None

    def get_mechanism_count(self, netuid: int) -> int:
        return 0


def test_block_extrinsics_events_association():
    block = Block(
        provider=FakeBlockchainProvider(),
        block_number=100,
    )
    extrinsics = block.extrinsics

    assert len(extrinsics) == len(EXTRINSICS_RESPONSE)
