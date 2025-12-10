"""Base provider classes."""

from __future__ import annotations

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
    def get_subnet_hyperparams(self, block_hash: str, netuid: int) -> Any:
        """Get subnet hyperparameters for a given block hash and netuid."""
        ...

    @abstractmethod
    def get_block_info(
        self,
        block_number: int | None = None,
        block_hash: str | None = None,
    ) -> Any:
        """Get complete block information including extrinsics."""
        ...

    @abstractmethod
    def get_current_block(self) -> int:
        """Get the current block number."""
        ...

    @abstractmethod
    def get_extrinsic_events(self, block_hash: str) -> dict[int, list[dict[str, Any]]]:
        """Get events grouped by extrinsic index."""
        ...

    @abstractmethod
    def get_extrinsic_status(
        self, block_hash: str, extrinsic_index: int
    ) -> tuple[str, dict[str, Any] | None]:
        """Get the status of an extrinsic (Success/Failed/Unknown)."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        ...

    def __enter__(self) -> "BlockchainProvider":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
