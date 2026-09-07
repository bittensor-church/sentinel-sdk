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
    console.print(f"Spec Name: [bold]{runtime_version.get('spec_name', 'N/A')}[/bold]")
    console.print(f"Spec Version: [green]{runtime_version.get('spec_version', 'N/A')}[/green]")


def _output_json_format(runtime_version: dict, block_number: int, block_hash: str) -> None:
    """Output runtime version as JSON."""
    output_json(
        {
            "block_number": block_number,
            "block_hash": block_hash,
            "spec_name": runtime_version.get("spec_name"),
            "spec_version": runtime_version.get("spec_version"),
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

    runtime_version = provider.get_runtime_version(resolved_block)
    if runtime_version is None:
        console.print(f"[red]Error:[/red] Runtime version not found for block {resolved_block}")
        raise typer.Exit(1)

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

    runtime_version = provider.get_runtime_version(resolved_block)
    if runtime_version is None:
        console.print(f"[red]Error:[/red] Runtime version not found for block {resolved_block}")
        raise typer.Exit(1)

    spec_version = runtime_version.get("spec_version")

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
