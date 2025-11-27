"""Block CLI commands."""

from typing import Annotated

import typer

from sentinel.v1.providers.bittensor import bittensor_provider

app = typer.Typer(
    name="block",
    help="Block-related commands.",
    no_args_is_help=True,
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

    resolved_block: int
    if block_number is None:
        current = provider.get_current_block()
        if current.number is None:
            typer.echo("Error: Could not determine current block number", err=True)
            raise typer.Exit(1)
        resolved_block = current.number
        typer.echo(f"Current block: {resolved_block}")
        return

    resolved_block = block_number
    typer.echo(f"Block: {resolved_block}")
    block_hash = provider.get_hash_by_block_number(resolved_block)
    if not block_hash:
        typer.echo(f"Error: Block hash not found for block {resolved_block}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Hash: {block_hash}")
