"""Events CLI command."""

from typing import Annotated

import typer

from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.sentinel import sentinel_service
from sentinel_cli.settings import MAX_VALUE_DISPLAY_LENGTH


def events(
    block_number: Annotated[
        int | None,
        typer.Option("--block", "-b", help="Block number to query. Defaults to current block."),
    ] = None,
    network: Annotated[
        str | None,
        typer.Option("--network", "-n", help="Network URI to connect to."),
    ] = None,
) -> None:
    """Read events from a blockchain block."""
    provider = bittensor_provider(network_uri=network)

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
    service = sentinel_service(provider)
    block = service.ingest_block(resolved_block)
    block_events = block.events
    typer.echo(f"\nTotal events in block: {len(block_events)}")

    if not block_events:
        typer.echo("No events found.")
        return

    for i, event in enumerate(block_events):
        typer.echo(f"\n[{i + 1}] {event.event.module_id}.{event.event.event_id}")
        typer.echo(f"    Phase: {event.phase}")
        if event.extrinsic_idx is not None:
            typer.echo(f"    Extrinsic Index: {event.extrinsic_idx}")
        if event.event.attributes:
            attr_str = str(event.event.attributes)
            if len(attr_str) > MAX_VALUE_DISPLAY_LENGTH:
                attr_str = attr_str[:MAX_VALUE_DISPLAY_LENGTH] + "..."
            typer.echo(f"    Attributes: {attr_str}")
