"""Block CLI commands."""

from typing import Annotated

import typer

from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel_cli.blocks import resolve_block_hash, resolve_block_number
from sentinel_cli.output import console, is_json_output, output_json

app = typer.Typer(
    name="block",
    help="Block-related commands.",
    no_args_is_help=True,
)


def _output_table(block_number: int, block_hash: str) -> None:
    """Output block info as formatted Rich output."""
    console.print(f"Block: [cyan]{block_number}[/cyan]")
    console.print(f"Hash: [dim]{block_hash}[/dim]")


def _output_json_format(block_number: int, block_hash: str) -> None:
    """Output block info as JSON."""
    output_json(
        {
            "block_number": block_number,
            "block_hash": block_hash,
        },
    )


@app.command()
def info(
    block_number: Annotated[
        int | None,
        typer.Option("--block", "-b", help="Block number to query. Defaults to current block."),
    ] = None,
    network: Annotated[
        str | None,
        typer.Option("--network", "-n", help="Network URI to connect to."),
    ] = None,
) -> None:
    """Display information about a block."""
    provider = bittensor_provider(network_uri=network)

    resolved_block = resolve_block_number(provider, block_number)
    block_hash = resolve_block_hash(provider, resolved_block)

    if is_json_output():
        _output_json_format(resolved_block, block_hash)
    else:
        _output_table(resolved_block, block_hash)
