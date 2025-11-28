"""Base provider classes."""

from abc import ABC, abstractmethod
from typing import Any


class BlockchainProvider(ABC):
    """Abstract base class defining the interface for blockchain providers."""

    @abstractmethod
    def get_block_hash(self, block_number: int) -> str | None:
        """Get block hash by block number."""
        ...

    @abstractmethod
    def get_hash_by_block_number(self, block_number: int) -> str | None:
        """Get block hash by block number (alias)."""
        ...

    @abstractmethod
    def get_events(self, block_hash: str) -> list[dict[str, Any]]:
        """Get serialized events for a block hash."""
        ...

    @abstractmethod
    def get_extrinsics(self, block_hash: str) -> list[dict[str, Any]] | None:
        """Get extrinsics for a block hash."""
        ...

    @abstractmethod
    def get_subnet_hyperparams(self, block_hash: str, netuid: int) -> dict[str, Any] | None:
        """Get subnet hyperparameters for a given block hash and netuid."""
        ...
