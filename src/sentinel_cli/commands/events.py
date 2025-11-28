"""Events CLI command."""

from typing import Annotated

import typer
from rich.text import Text

from sentinel.v1.dto import EventDTO
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.sentinel import sentinel_service
from sentinel_cli.blocks import resolve_block_hash, resolve_block_number
from sentinel_cli.output import (
    MAX_ATTR_LENGTH,
    build_panel_title,
    console,
    format_block_id,
    is_json_output,
    output_json,
    render_panel,
    truncate,
)


def _display_event(block_number: int, index: int, event: EventDTO) -> None:
    """Display an event as a Rich panel."""
    event_id = format_block_id(block_number, index)
    label = f"{event.module_id}.{event.event_id}"

    title = build_panel_title(event_id, label)

    content = Text()
    content.append("Phase: ", style="dim")
    content.append(f"{event.phase}\n")

    if event.extrinsic_idx is not None:
        content.append("Extrinsic: ", style="dim")
        content.append(f"{format_block_id(block_number, event.extrinsic_idx)}\n")

    if event.attributes:
        content.append("Attributes: ", style="dim")
        content.append(truncate(str(event.attributes), MAX_ATTR_LENGTH))

    render_panel(title, content)


def _output_table(
    block_number: int,
    block_hash: str,
    events_list: list[EventDTO],
) -> None:
    """Output events as formatted Rich panels."""
    console.print(f"Block: [cyan]{block_number}[/cyan]")
    console.print(f"Hash: [dim]{block_hash}[/dim]")
    console.print(f"\nEvents: [bold]{len(events_list)}[/bold] found")

    if not events_list:
        console.print("[dim]No events found.[/dim]")
        return

    console.print()
    for i, event in enumerate(events_list):
        _display_event(block_number, i, event)
        console.print()


def _output_json_format(
    block_number: int,
    block_hash: str,
    events_list: list[EventDTO],
) -> None:
    """Output events as JSON."""
    output_json(
        {
            "block_number": block_number,
            "block_hash": block_hash,
            "count": len(events_list),
            "events": [
                {"id": format_block_id(block_number, i), **event.model_dump()} for i, event in enumerate(events_list)
            ],
        },
    )


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
    service = sentinel_service(provider)

    resolved_block = resolve_block_number(provider, block_number)
    block_hash = resolve_block_hash(provider, resolved_block)

    events_list = service.ingest_block(resolved_block).events

    if is_json_output():
        _output_json_format(resolved_block, block_hash, events_list)
    else:
        _output_table(resolved_block, block_hash, events_list)
