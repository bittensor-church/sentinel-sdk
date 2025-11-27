"""Block-related CLI commands."""

from typing import Annotated

import typer

from sentinel.v1.dto import ExtrinsicDTO
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.extractors.extrinsics import filter_hyperparam_extrinsics, get_hyperparam_info
from sentinel.v1.services.sentinel import sentinel_service

app = typer.Typer(
    name="block",
    help="Block-related commands for querying blockchain data.",
    no_args_is_help=True,
)

MAX_VALUE_DISPLAY_LENGTH = 60


def _display_hyperparam_extrinsic(index: int, ext: ExtrinsicDTO) -> None:
    """Display a hyperparameter change extrinsic."""
    info = get_hyperparam_info(ext)
    if not info:
        return
    netuid_str = f" (subnet {info['netuid']})" if "netuid" in info else ""
    typer.echo(f"\n[{index}] {info['function']}{netuid_str}")
    typer.echo(f"    Hash: {ext.extrinsic_hash}")
    if ext.address:
        typer.echo(f"    Signer: {ext.address}")
    if info["params"]:
        typer.echo("    Changed params:")
        for param, value in info["params"].items():
            typer.echo(f"      {param}: {value}")


def _display_extrinsic(index: int, ext: ExtrinsicDTO) -> None:
    """Display a generic extrinsic."""
    typer.echo(f"\n[{index}] {ext.call.call_module}.{ext.call.call_function}")
    typer.echo(f"    Hash: {ext.extrinsic_hash}")
    if ext.address:
        typer.echo(f"    Signer: {ext.address}")
    if ext.call.call_args:
        typer.echo("    Args:")
        for arg in ext.call.call_args:
            value_str = str(arg.value)
            if len(value_str) > MAX_VALUE_DISPLAY_LENGTH:
                value_str = value_str[:MAX_VALUE_DISPLAY_LENGTH] + "..."
            typer.echo(f"      {arg.name}: {value_str}")


@app.command()
def extrinsics(
    block_number: Annotated[
        int | None,
        typer.Option("--block", "-b", help="Block number to query. Defaults to current block."),
    ] = None,
    network: Annotated[
        str | None,
        typer.Option("--network", "-n", help="Network URI to connect to."),
    ] = None,
    *,
    hyperparams_only: Annotated[
        bool,
        typer.Option("--hyperparams", "-p", help="Show only hyperparameter change extrinsics."),
    ] = False,
) -> None:
    """Read extrinsics from a blockchain block."""
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

    block_hash = provider.get_hash_by_block_number(resolved_block)
    if not block_hash:
        typer.echo(f"Error: Block hash not found for block {resolved_block}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Block: {resolved_block}")
    typer.echo(f"Hash: {block_hash}")

    block = service.ingest_block(resolved_block)
    extrinsics_list = block.extrinsics()

    if hyperparams_only:
        extrinsics_list = filter_hyperparam_extrinsics(extrinsics_list)
        typer.echo(f"\nHyperparam changes in block {resolved_block}: {len(extrinsics_list)} found")
    else:
        typer.echo(f"\nExtrinsics for block {resolved_block}: {len(extrinsics_list)} found")
    typer.echo("-" * 50)

    if not extrinsics_list:
        typer.echo("No extrinsics found.")
        return

    display_fn = _display_hyperparam_extrinsic if hyperparams_only else _display_extrinsic
    for i, ext in enumerate(extrinsics_list):
        display_fn(i + 1, ext)


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

    if block_number is None:
        current = provider.get_current_block()
        block_number = current.number
        typer.echo(f"Current block: {block_number}")
        return

    typer.echo(f"Block: {block_number}")
    block_hash = provider.get_hash_by_block_number(block_number)
    if not block_hash:
        typer.echo(f"Error: Block hash not found for block {block_number}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Hash: {block_hash}")


@app.command()
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

    if block_number is None:
        current = provider.get_current_block()
        block_number = current.number
        typer.echo(f"Using current block: {block_number}")

    block = service.ingest_block(block_number, netuid)
    hyperparameters = block.hyperparameters

    typer.echo(f"\nHyperparameters for subnet {netuid} at block {block_number}:")
    typer.echo("-" * 50)

    for field, value in hyperparameters.model_dump().items():
        typer.echo(f"{field}: {value}")
