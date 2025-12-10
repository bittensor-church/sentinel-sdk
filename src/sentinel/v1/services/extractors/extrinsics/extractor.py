"""Extrinsic extractor."""

from typing import Any

from sentinel.v1.dto import CallArgDTO, CallDTO, ExtrinsicDTO
from sentinel.v1.providers import BlockchainProvider


class ExtrinsicExtractor:
    """Extracts extrinsics from a blockchain block."""

    def __init__(self, provider: BlockchainProvider, block_number: int) -> None:
        """
        Initialize the extrinsic extractor.

        Args:
            provider: The blockchain provider to use for data retrieval
            block_number: The block number to extract extrinsics from

        """
        self.provider = provider
        self.block_number = block_number

    def _convert_extrinsic_hash(self, hash_value: bytes | str | None) -> str | None:
        """Convert extrinsic hash from bytes to hex string."""
        if hash_value is None:
            return None
        if isinstance(hash_value, bytes):
            return "0x" + hash_value.hex()
        return hash_value

    def _build_call_dto(self, ext: dict[str, Any]) -> CallDTO:
        """Build a CallDTO from the flattened extrinsic data."""
        call_args = [
            CallArgDTO(
                name=arg.get("name", ""),
                type=arg.get("type", ""),
                value=arg.get("value"),
            )
            for arg in ext.get("call_args", [])
        ]
        return CallDTO(
            call_function=ext.get("call_function", ""),
            call_module=ext.get("call_module", ""),
            call_args=call_args,
        )

    def _build_extrinsic_dto(self, ext: dict[str, Any]) -> ExtrinsicDTO:
        """Build an ExtrinsicDTO from raw provider data."""
        return ExtrinsicDTO(
            index=ext.get("index", 0),
            extrinsic_hash=self._convert_extrinsic_hash(ext.get("extrinsic_hash")),
            call=self._build_call_dto(ext),
            address=ext.get("address"),
            signature=ext.get("signature"),
            nonce=ext.get("nonce"),
            tip=ext.get("tip"),
        )

    def extract(self) -> list[ExtrinsicDTO]:
        """
        Extract extrinsics from the blockchain block.

        Returns:
            List of ExtrinsicDTO containing all extracted extrinsics

        """
        block_hash = self.provider.get_hash_by_block_number(self.block_number)
        if not block_hash:
            msg = f"Block hash not found for block number {self.block_number}"
            raise ValueError(msg)

        extrinsics_json = self.provider.get_extrinsics(block_hash=block_hash)
        if extrinsics_json is None:
            return []

        return [self._build_extrinsic_dto(ext) for ext in extrinsics_json]
