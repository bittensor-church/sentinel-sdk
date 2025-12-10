"""Extrinsics CLI command."""

from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table
from rich.text import Text

from sentinel.v1.dto import ExtrinsicDTO
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.extractors.extrinsics import filter_hyperparam_extrinsics, get_hyperparam_info
from sentinel.v1.services.extractors.extrinsics.filters import filter_weight_set_extrinsics
from sentinel.v1.services.sentinel import sentinel_service
from sentinel_cli.blocks import resolve_block_hash, resolve_block_number
from sentinel_cli.output import (
    MAX_ATTR_LENGTH,
    MAX_VALUE_LENGTH,
    build_header_text,
    build_key_value_table,
    build_panel_title,
    console,
    format_block_id,
    is_json_output,
    output_json,
    render_panel,
    truncate,
)

if TYPE_CHECKING:
    from rich.console import RenderableType


def _build_args_table(ext: ExtrinsicDTO) -> Table | None:
    """Build args table for extrinsic."""
    if not ext.call.call_args:
        return None
    return build_key_value_table(
        ((arg.name, arg.value) for arg in ext.call.call_args),
        key_header="Arg",
        value_header="Value",
        max_value_length=MAX_VALUE_LENGTH,
    )


def _build_events_table(ext: ExtrinsicDTO) -> Table | None:
    """Build events table for extrinsic."""
    if not ext.events:
        return None
    return build_key_value_table(
        ((f"{e.module_id}.{e.event_id}", truncate(str(e.attributes or ""), MAX_ATTR_LENGTH)) for e in ext.events),
        key_header="Event",
        value_header="Attributes",
        max_value_length=MAX_ATTR_LENGTH,
    )


def _display_extrinsic(block_number: int, index: int, ext: ExtrinsicDTO) -> None:
    """Display a generic extrinsic as a Rich panel."""
    ext_id = format_block_id(block_number, index)
    label = f"{ext.call.call_module}.{ext.call.call_function}"

    title = build_panel_title(ext_id, label, ext.status)
    header = build_header_text(hash_value=ext.extrinsic_hash or "N/A", signer=ext.address)

    renderables: list[RenderableType] = [header]
    if args_table := _build_args_table(ext):
        renderables.extend([Text(), args_table])
    if events_table := _build_events_table(ext):
        renderables.extend([Text(), events_table])

    render_panel(title, *renderables)


def _display_hyperparam_extrinsic(block_number: int, index: int, ext: ExtrinsicDTO) -> None:
    """Display a hyperparameter change extrinsic."""
    info = get_hyperparam_info(ext)
    if not info:
        return

    ext_id = format_block_id(block_number, index)
    netuid_str = f" (subnet {info['netuid']})" if "netuid" in info else ""
    label = f"{info['function']}{netuid_str}"

    title = build_panel_title(ext_id, label, ext.status)

    # Custom content for hyperparam extrinsics
    content = build_header_text(hash_value=ext.extrinsic_hash or "N/A", signer=ext.address)
    if info["params"]:
        content.append("\n\nChanged params:\n", style="bold")
        for param, value in info["params"].items():
            content.append(f"  {param}: ", style="dim")
            content.append(f"{value}\n")

    render_panel(title, content)


def _output_table(
    block_number: int,
    block_hash: str,
    extrinsics_list: list[ExtrinsicDTO],
    timestamp: int | None,
    *,
    hyperparams_only: bool,
) -> None:
    """Output extrinsics as formatted Rich panels."""
    console.print(f"Block: [cyan]{block_number}[/cyan]")
    console.print(f"Hash: [dim]{block_hash}[/dim]")
    if timestamp is not None:
        console.print(f"Timestamp: [dim]{timestamp}[/dim]")

    label = "Hyperparam changes" if hyperparams_only else "Extrinsics"
    console.print(f"\n{label}: [bold]{len(extrinsics_list)}[/bold] found")

    if not extrinsics_list:
        console.print("[dim]No extrinsics found.[/dim]")
        return

    console.print()
    display_fn = _display_hyperparam_extrinsic if hyperparams_only else _display_extrinsic
    for ext in extrinsics_list:
        display_fn(block_number, ext.index, ext)
        console.print()


def _output_json_format(
    block_number: int,
    block_hash: str,
    extrinsics_list: list[ExtrinsicDTO],
    timestamp: int | None,
) -> None:
    """Output extrinsics as JSON."""
    output_json(
        {
            "block_number": block_number,
            "block_hash": block_hash,
            "timestamp": timestamp,
            "count": len(extrinsics_list),
            "extrinsics": [
                {"id": format_block_id(block_number, ext.index), **ext.model_dump()} for ext in extrinsics_list
            ],
        }
    )


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
    weight_set_only: Annotated[
        bool,
        typer.Option("--weight-sets", "-w", help="Show only weight set extrinsics."),
    ] = False,
) -> None:
    """Read extrinsics from a blockchain block."""
    provider = bittensor_provider(network_uri=network)
    service = sentinel_service(provider)

    resolved_block = resolve_block_number(provider, block_number)
    block_hash = resolve_block_hash(provider, resolved_block)

    block = service.ingest_block(resolved_block)
    extrinsics_list = block.extrinsics

    if hyperparams_only:
        extrinsics_list = filter_hyperparam_extrinsics(extrinsics_list)

    if weight_set_only:
        extrinsics_list = filter_weight_set_extrinsics(extrinsics_list)

    if is_json_output():
        _output_json_format(resolved_block, block_hash, extrinsics_list, block.timestamp)
    else:
        _output_table(resolved_block, block_hash, extrinsics_list, block.timestamp, hyperparams_only=hyperparams_only)
