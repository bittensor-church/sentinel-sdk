"""Block CLI commands."""

from typing import Annotated

import bittensor
import typer
from bittensor.core.chain_data import MetagraphInfo
from rich.table import Table

from sentinel.v1.models.subnet import Subnet
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel.v1.services.extractors.dividends import DividendRecord, DividendsExtractor
from sentinel_cli.blocks import resolve_block_number
from sentinel_cli.output import console, is_json_output, output_json

HOTKEY_DISPLAY_LENGTH = 16


def _get_identity_name(identity: dict | object | None) -> str | None:
    """Extract name from identity, handling both dict and object types."""
    if not identity:
        return None
    return identity["name"] if isinstance(identity, dict) else identity.name  # type: ignore[union-attr, attr-defined]


subnet = typer.Typer(
    name="subnet",
    help="Subnet-related commands.",
    no_args_is_help=True,
)


@subnet.callback()
def subnet_callback(
    ctx: typer.Context,
    netuid: Annotated[
        int,
        typer.Option("--netuid", "-u", help="Network UID for the subnet.", show_default=True),
    ] = 0,
    block_number: Annotated[
        int | None,
        typer.Option("--block", "-b", help="Block number to query. Defaults to current block."),
    ] = None,
    network: Annotated[
        str | None,
        typer.Option("--network", "-n", help="Network URI to connect to."),
    ] = None,
    mech_id: Annotated[
        int,
        typer.Option("--mech-id", "-m", help="Mechanism ID.", show_default=True),
    ] = 0,
) -> None:
    """Subnet-related commands."""
    ctx.ensure_object(dict)
    ctx.obj["netuid"] = netuid
    ctx.obj["block_number"] = block_number
    ctx.obj["network"] = network
    ctx.obj["mech_id"] = mech_id


def _build_dividends_table(metagraph: MetagraphInfo) -> Table:
    """Build a table displaying dividends by UID with identity info."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("UID", style="cyan", justify="right")
    table.add_column("Identity", style="dim")
    table.add_column("Hotkey")
    table.add_column("Dividend", justify="right")

    for uid, (identity, hotkey, dividend) in enumerate(
        zip(metagraph.identities, metagraph.hotkeys, metagraph.dividends, strict=True),
    ):
        identity_name = _get_identity_name(identity) or "-"
        hotkey_display = hotkey[:HOTKEY_DISPLAY_LENGTH] + "..." if len(hotkey) > HOTKEY_DISPLAY_LENGTH else hotkey
        table.add_row(
            str(uid),
            identity_name,
            hotkey_display,
            f"{dividend:.6f}",
        )

    return table


@subnet.command()
def metagraph(
    ctx: typer.Context,
    view: Annotated[
        str | None,
        typer.Argument(help="View to display: dividends, incentives, etc."),
    ] = None,
) -> None:
    """Display metagraph information about a subnet at a specific block."""
    netuid = ctx.obj["netuid"]
    block_number = ctx.obj["block_number"]
    network = ctx.obj["network"]
    mech_id = ctx.obj["mech_id"]

    provider = bittensor_provider(network_uri=network)
    resolved_block = resolve_block_number(provider, block_number)

    subnet_instance = Subnet(provider, netuid, resolved_block, mech_id)
    metagraph_data = subnet_instance.metagraph

    if metagraph_data is None:
        console.print("[red]Error:[/red] Could not retrieve metagraph data.")
        raise typer.Exit(1)

    console.print(f"Block: [cyan]{resolved_block}[/cyan]")
    console.print(f"Subnet: [cyan]{netuid}[/cyan]")
    console.print()

    if view == "dividends":
        if is_json_output():
            output_json(
                {
                    "block_number": resolved_block,
                    "netuid": netuid,
                    "dividends": [
                        {
                            "uid": uid,
                            "identity": _get_identity_name(identity),
                            "hotkey": hotkey,
                            "dividend": dividend,
                        }
                        for uid, (identity, hotkey, dividend) in enumerate(
                            zip(
                                metagraph_data.identities,
                                metagraph_data.hotkeys,
                                metagraph_data.dividends,
                                strict=True,
                            ),
                        )
                    ],
                }
            )
        else:
            console.print(_build_dividends_table(metagraph_data))
            total_dividends = sum(metagraph_data.dividends)
            console.print()
            console.print(f"Total dividends: [bold]{total_dividends:.6f}[/bold]")
    else:
        console.print(f"Metagraph: [dim]{metagraph_data}[/dim]")


def _build_manual_dividends_table(records: list[DividendRecord]) -> Table:
    """Build a table displaying manually calculated dividends."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("UID", style="cyan", justify="right")
    table.add_column("Identity", style="dim")
    table.add_column("Hotkey")
    table.add_column("Dividend", justify="right")
    table.add_column("Stake", justify="right")

    for record in records:
        identity_name = record.identity_name or "-"
        hotkey_display = (
            record.hotkey[:HOTKEY_DISPLAY_LENGTH] + "..."
            if len(record.hotkey) > HOTKEY_DISPLAY_LENGTH
            else record.hotkey
        )
        table.add_row(
            str(record.uid),
            identity_name,
            hotkey_display,
            f"{record.dividend:.6f}",
            f"{record.stake:.2f}",
        )

    return table


@subnet.command(name="dividends-manual")
def dividends_manual(
    ctx: typer.Context,
) -> None:
    """Calculate dividends manually using Yuma3 formula from bonds and incentives."""
    netuid = ctx.obj["netuid"]
    block_number = ctx.obj["block_number"]
    network = ctx.obj["network"]
    mech_id = ctx.obj["mech_id"]

    provider = bittensor_provider(network_uri=network)
    resolved_block = resolve_block_number(provider, block_number)

    subtensor = bittensor.subtensor(network=network)
    extractor = DividendsExtractor(subtensor, resolved_block, netuid, mech_id)
    result = extractor.extract()

    if not result.records:
        console.print("[yellow]No dividend data found.[/yellow]")
        raise typer.Exit(1)

    yuma_version = "Yuma3" if result.yuma3_enabled else "Yuma2"

    console.print(f"Block: [cyan]{resolved_block}[/cyan]")
    console.print(f"Subnet: [cyan]{netuid}[/cyan]")
    console.print(f"Mech ID: [cyan]{result.mech_id}[/cyan]")
    console.print(f"Consensus: [cyan]{yuma_version}[/cyan]")
    console.print()
    console.print(_build_manual_dividends_table(result.records))
    total_dividends = sum(r.dividend for r in result.records)
    console.print()
    console.print(f"Total dividends: [bold]{total_dividends:.6f}[/bold]")
