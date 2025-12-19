from typing import Any

from sentinel.v1.providers.base import BlockchainProvider
from tests.unit.v1.factories import EventDTOFactory, ExtrinsicDTOFactory


class FakeBittensorProvider(BlockchainProvider):
    """Fake provider that uses factories to generate test data."""

    def __init__(self):
        self.block_hashes: dict[int, str] = {}
        self.events: dict[str, list[dict[str, Any]]] = {}
        self.extrinsics: dict[str, list[dict[str, Any]]] = {}
        self.hyperparams: dict[tuple[int, int], dict[str, Any]] = {}

    def get_block_hash(self, block_number: int) -> str | None:
        return self.block_hashes.get(block_number)

    def get_hash_by_block_number(self, block_number: int) -> str | None:
        return self.block_hashes.get(block_number)

    def get_events(self, block_hash: str) -> list[dict[str, Any]]:
        return self.events.get(block_hash, [])

    def get_extrinsics(self, block_hash: str) -> list[dict[str, Any]] | None:
        return self.extrinsics.get(block_hash)

    def get_subnet_hyperparams(
        self,
        block_number: int,
        netuid: int,
    ) -> Any:
        """Get subnet hyperparameters for a given block number and netuid."""
        return self.hyperparams.get((block_number, netuid))

    def get_block_info(
        self,
        block_number: int | None = None,
        block_hash: str | None = None,
    ) -> Any:
        """Get block info."""
        return None

    def get_current_block(self) -> int:
        """Get current block number."""
        return 0

    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict[str, Any]]]:
        """Get events grouped by extrinsic index."""
        return {}

    def get_extrinsic_status(self, block_hash: str, extrinsic_index: int) -> tuple[str, dict[str, Any] | None]:
        """Get the status of an extrinsic."""
        return "Unknown", None

    def close(self) -> None:
        """Close any open connections."""
        pass

    def get_metagraph(self, netuid: int, block_number: int, mechid: int = 0) -> Any:
        """Get metagraph for a given netuid and block number."""
        return None

    def get_mechanism_count(self, netuid: int) -> int:
        """Get the number of mechanisms for a given netuid."""
        return 0

    def with_block(self, block_number: int, block_hash: str) -> "FakeBittensorProvider":
        """Add a block mapping."""
        self.block_hashes[block_number] = block_hash
        return self

    def with_events(self, block_hash: str, events: list[dict[str, Any]]) -> "FakeBittensorProvider":
        """Add events for a block hash."""
        self.events[block_hash] = events
        return self

    def with_extrinsics(self, block_hash: str, extrinsics: list[dict[str, Any]]) -> "FakeBittensorProvider":
        """Add extrinsics for a block hash."""
        self.extrinsics[block_hash] = extrinsics
        return self

    def with_hyperparams(
        self,
        block_number: int,
        netuid: int,
        hyperparams: dict[str, Any],
    ) -> "FakeBittensorProvider":
        """Add hyperparameters for a block number and netuid."""
        self.hyperparams[(block_number, netuid)] = hyperparams
        return self

    @staticmethod
    def create_mock_events(count: int = 1, **overrides: Any) -> list[dict[str, Any]]:
        """Create mock events using the EventDTOFactory."""
        return [EventDTOFactory.build(**overrides).model_dump() for _ in range(count)]

    @staticmethod
    def create_mock_extrinsics(count: int = 1, **overrides: Any) -> list[dict[str, Any]]:
        """Create mock extrinsics using the ExtrinsicDTOFactory."""
        return [ExtrinsicDTOFactory.build(**overrides).model_dump() for _ in range(count)]
