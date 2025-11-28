"""Hyperparameters CLI command."""

from typing import Annotated

import typer
from rich.table import Table

from sentinel.v1.dto import HyperparametersDTO
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.sentinel import sentinel_service
from sentinel_cli.blocks import resolve_block_number
from sentinel_cli.output import console, is_json_output, output_json


def _build_hyperparams_table(hyperparams: HyperparametersDTO) -> Table:
    """Build a table displaying hyperparameters."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Parameter", style="dim")
    table.add_column("Value")

    for field, value in hyperparams.model_dump().items():
        table.add_row(field, str(value))

    return table


def _output_table(
    block_number: int,
    netuid: int,
    hyperparams: HyperparametersDTO,
) -> None:
    """Output hyperparameters as formatted Rich table."""
    console.print(f"Block: [cyan]{block_number}[/cyan]")
    console.print(f"Subnet: [cyan]{netuid}[/cyan]")
    console.print()
    console.print(_build_hyperparams_table(hyperparams))


def _output_json_format(
    block_number: int,
    netuid: int,
    hyperparams: HyperparametersDTO,
) -> None:
    """Output hyperparameters as JSON."""
    output_json(
        {
            "block_number": block_number,
            "netuid": netuid,
            **hyperparams.model_dump(),
        },
    )


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

    resolved_block = resolve_block_number(provider, block_number)

    block = service.ingest_block(resolved_block, netuid)
    hyperparams_data = block.hyperparameters

    if is_json_output():
        _output_json_format(resolved_block, netuid, hyperparams_data)
    else:
        _output_table(resolved_block, netuid, hyperparams_data)
