"""Extrinsics CLI command."""

from typing import Annotated

import typer

from sentinel.v1.dto import ExtrinsicDTO
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.extractors.extrinsics import filter_hyperparam_extrinsics, get_hyperparam_info
from sentinel.v1.services.sentinel import sentinel_service
from sentinel_cli.settings import MAX_VALUE_DISPLAY_LENGTH


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


def _display_extrinsic(
    index: int,
    ext: ExtrinsicDTO,
    status: str | None = None,
) -> None:
    """Display a generic extrinsic."""
    status_str = f" [{status}]" if status else ""
    typer.echo(f"\n[{index}] {ext.call.call_module}.{ext.call.call_function}{status_str}")
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
    extrinsics_list = block.extrinsics

    if hyperparams_only:
        extrinsics_list = filter_hyperparam_extrinsics(extrinsics_list)
        typer.echo(f"\nHyperparam changes in block {resolved_block}: {len(extrinsics_list)} found")
    else:
        typer.echo(f"\nExtrinsics for block {resolved_block}: {len(extrinsics_list)} found")
    typer.echo("-" * 50)

    if not extrinsics_list:
        typer.echo("No extrinsics found.")
        return

    # Get statuses for all extrinsics (only works correctly for unfiltered list)
    statuses: dict[int, str] = {}
    if not hyperparams_only:
        events_by_idx = provider.get_extrinsic_events(block_hash)
        for idx in events_by_idx:
            status_str, _ = provider.get_extrinsic_status(block_hash, idx)
            statuses[idx] = status_str

    for i, ext in enumerate(extrinsics_list):
        if hyperparams_only:
            _display_hyperparam_extrinsic(i + 1, ext)
        else:
            _display_extrinsic(i + 1, ext, statuses.get(i))
