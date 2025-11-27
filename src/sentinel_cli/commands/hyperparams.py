"""Hyperparameters CLI command."""

from typing import Annotated

import typer

from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.sentinel import sentinel_service


def hyperparams(
    netuid: Annotated[
        int,
        typer.Option("--subnet", "-s", help="Subnet ID to query hyperparameters for."),
    ],
    block_number: Annotated[
        int | None,
        typer.Option("--block", "-b", help="Block number to query. Defaults to current block."),
    ] = None,
    network: Annotated[
        str | None,
        typer.Option("--network", "-n", help="Network URI to connect to."),
    ] = None,
) -> None:
    """Read hyperparameters for a subnet at a specific block."""
    provider = bittensor_provider(network_uri=network)
    service = sentinel_service(provider)

    resolved_block: int
    if block_number is None:
        current = provider.get_current_block()
        if current.number is None:
            typer.echo("Error: Could not determine current block number", err=True)
            raise typer.Exit(1)
        resolved_block = current.number
        typer.echo(f"Using current block: {resolved_block}")
    else:
        resolved_block = block_number

    block = service.ingest_block(resolved_block, netuid)
    hyperparameters_data = block.hyperparameters

    typer.echo(f"\nHyperparameters for subnet {netuid} at block {resolved_block}:")
    typer.echo("-" * 50)

    for field, value in hyperparameters_data.model_dump().items():
        typer.echo(f"{field}: {value}")
