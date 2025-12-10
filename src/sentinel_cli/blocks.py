"""Block resolution utilities for CLI commands."""

import typer

from sentinel.v1.providers.bittensor import BittensorProvider
from sentinel_cli.output import console, is_json_output, output_error


def resolve_block_number(provider: BittensorProvider, block_number: int | None) -> int:
    """
    Resolve block number, using current block if not specified.

    Args:
        provider: Blockchain provider instance
        block_number: Optional block number, None means current block

    Returns:
        Resolved block number

    Raises:
        typer.Exit: If block number cannot be determined

    """
    if block_number is not None:
        return block_number

    current = provider.get_current_block()
    if current is None:
        output_error("Could not determine current block number")
        raise typer.Exit(1)

    if not is_json_output():
        console.print(f"Using current block: [cyan]{current}[/cyan]")
    return current


def resolve_block_hash(provider: BittensorProvider, block_number: int) -> str:
    """
    Resolve block hash for the given block number.

    Args:
        provider: Blockchain provider instance
        block_number: Block number to get hash for

    Returns:
        Block hash string

    Raises:
        typer.Exit: If block hash cannot be found

    """
    block_hash = provider.get_hash_by_block_number(block_number)
    if not block_hash:
        output_error(f"Block hash not found for block {block_number}")
        raise typer.Exit(1)
    return block_hash
