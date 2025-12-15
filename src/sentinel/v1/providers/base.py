"""Base provider classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bittensor.core.chain_data import SubnetHyperparameters
    from bittensor.core.metagraph import Metagraph


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
    def get_subnet_hyperparams(self, block_number: int, netuid: int) -> list[Any] | SubnetHyperparameters | None:
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
    def get_extrinsic_status(self, block_hash: str, extrinsic_index: int) -> tuple[str, dict[str, Any] | None]:
        """Get the status of an extrinsic (Success/Failed/Unknown)."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        ...

    def __enter__(self) -> BlockchainProvider:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: object | None, exc_val: object | None, exc_tb: object | None) -> None:
        """Context manager exit."""
        self.close()

    @abstractmethod
    def get_metagraph(self, netuid: int, block_number: int, mechid: int = 0) -> Metagraph | None:
        """Get metagraph for a given netuid and block number."""
        ...

    @abstractmethod
    def get_mechanism_count(self, netuid: int) -> int:
        """Get the number of mechanisms for a given netuid."""
        ...
