"""Runtime CLI commands."""

from typing import Annotated

import typer

from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel_cli.blocks import resolve_block_hash, resolve_block_number
from sentinel_cli.output import console, is_json_output, output_json

app = typer.Typer(
    name="runtime",
    help="Runtime version commands.",
    no_args_is_help=True,
)


def _output_table(runtime_version: dict, block_number: int, block_hash: str) -> None:
    """Output runtime version as formatted Rich output."""
    console.print(f"Block: [cyan]{block_number}[/cyan]")
    console.print(f"Hash: [dim]{block_hash}[/dim]")
    console.print()
    console.print(f"Spec Name: [bold]{runtime_version.get('specName', 'N/A')}[/bold]")
    console.print(f"Spec Version: [green]{runtime_version.get('specVersion', 'N/A')}[/green]")
    console.print(f"Impl Name: {runtime_version.get('implName', 'N/A')}")
    console.print(f"Impl Version: {runtime_version.get('implVersion', 'N/A')}")
    console.print(f"Authoring Version: {runtime_version.get('authoringVersion', 'N/A')}")
    console.print(f"Transaction Version: {runtime_version.get('transactionVersion', 'N/A')}")
    console.print(f"State Version: {runtime_version.get('stateVersion', 'N/A')}")


def _output_json_format(runtime_version: dict, block_number: int, block_hash: str) -> None:
    """Output runtime version as JSON."""
    output_json(
        {
            "block_number": block_number,
            "block_hash": block_hash,
            "spec_name": runtime_version.get("specName"),
            "spec_version": runtime_version.get("specVersion"),
            "impl_name": runtime_version.get("implName"),
            "impl_version": runtime_version.get("implVersion"),
            "authoring_version": runtime_version.get("authoringVersion"),
            "transaction_version": runtime_version.get("transactionVersion"),
            "state_version": runtime_version.get("stateVersion"),
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
    """Display runtime version information at a specific block."""
    provider = bittensor_provider(network_uri=network)

    resolved_block = resolve_block_number(provider, block_number)
    block_hash = resolve_block_hash(provider, resolved_block)

    runtime_version = provider.substrate.get_runtime_version(block_hash)

    if is_json_output():
        _output_json_format(runtime_version, resolved_block, block_hash)
    else:
        _output_table(runtime_version, resolved_block, block_hash)


@app.command()
def version(
    block_number: Annotated[
        int | None,
        typer.Option("--block", "-b", help="Block number to query. Defaults to current block."),
    ] = None,
    network: Annotated[
        str | None,
        typer.Option("--network", "-n", help="Network URI to connect to."),
    ] = None,
) -> None:
    """Display only the spec version number."""
    provider = bittensor_provider(network_uri=network)

    resolved_block = resolve_block_number(provider, block_number)
    block_hash = resolve_block_hash(provider, resolved_block)

    spec_version = provider.substrate.get_spec_version(block_hash)

    if is_json_output():
        output_json(
            {
                "block_number": resolved_block,
                "block_hash": block_hash,
                "spec_version": spec_version,
            },
        )
    else:
        console.print(f"Block: [cyan]{resolved_block}[/cyan]")
        console.print(f"Spec Version: [green]{spec_version}[/green]")
