"""Base provider classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    from bittensor.core.chain_data import SubnetHyperparameters
    from bittensor.core.metagraph import Metagraph


class BlockchainProvider(ABC):
    """Abstract base class defining the interface for blockchain providers."""

    @abstractmethod
    def get_block_hash(self, block_number: int) -> str | None:
        """Get block hash by block number."""
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
    def get_metagraph(self, netuid: int, block_number: int, mechid: int = 0, *, lite: bool = False) -> Metagraph | None:
        """
        Get metagraph for a given netuid and block number.

        Args:
            netuid: The subnet identifier
            block_number: The block number to query at
            mechid: The mechanism ID (default: 0)
            lite: If True, fetch lightweight metagraph without weights/bonds (default: False)

        """
        ...

    @abstractmethod
    def get_mechanism_count(self, netuid: int, block_number: int | None = None) -> int:
        """Get the number of mechanisms for a given netuid at the given block (or chain head)."""
        ...

    @abstractmethod
    def get_all_subnets_netuids(self, exclude_netuids: list[int] | None = None) -> list[int]:
        """
        Get the netuids of every subnet registered on the chain.

        Args:
            exclude_netuids: Netuids to leave out of the result.

        """
        ...

    @abstractmethod
    def get_block_timestamp(self, block_number: int) -> datetime | None:
        """
        Get the chain timestamp of a block, or None if it could not be read.

        Note that the timestamp lives in block state, so a node that prunes
        state cannot answer for blocks older than its pruning window — use an
        archive node for those.
        """
        ...

    @abstractmethod
    def get_subnet_emission_enabled(self, block_number: int) -> dict[int, bool] | None:
        """
        Get ``SubtensorModule.SubnetEmissionEnabled`` per netuid at a block.

        Covers every registered subnet, including the root subnet: subnets with
        no explicit storage entry are reported as enabled, which is the chain's
        default. Returns None if the storage map could not be read.
        """
        ...
