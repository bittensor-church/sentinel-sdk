"""Block CLI commands."""

from typing import Annotated

import typer
from bittensor.core.chain_data import MetagraphInfo
from rich.table import Table

from sentinel.v1.models.subnet import Subnet
from sentinel.v1.providers.bittensor import bittensor_provider
from sentinel_cli.blocks import resolve_block_number
from sentinel_cli.output import console, is_json_output, output_json

HOTKEY_DISPLAY_LENGTH = 16


def _get_identity_name(identity: dict | object | None) -> str | None:
    """Extract name from identity, handling both dict and object types."""
    if not identity:
        return None
    return identity["name"] if isinstance(identity, dict) else identity.name  # type: ignore[union-attr]

subnet = typer.Typer(
    name="subnet",
    help="Subnet-related commands.",
    no_args_is_help=True,
)


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
    view: Annotated[
        str | None,
        typer.Argument(help="View to display: dividends, incentives, etc."),
    ] = None,
    block_number: Annotated[
        int | None,
        typer.Option("--block", "-b", help="Block number to query. Defaults to current block."),
    ] = None,
    network: Annotated[
        str | None,
        typer.Option("--network", "-n", help="Network URI to connect to."),
    ] = None,
    netuid: Annotated[
        int,
        typer.Option("--netuid", "-u", help="Network UID for the subnet.", show_default=True),
    ] = 0,
    mech_id: Annotated[
        int,
        typer.Option("--mech-id", "-m", help="Mechanism ID for the metagraph extraction.", show_default=True),
    ] = 0,
) -> None:
    """Display metagraph information about a subnet at a specific block."""
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
            output_json({
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
            })
        else:
            console.print(_build_dividends_table(metagraph_data))
            total_dividends = sum(metagraph_data.dividends)
            console.print()
            console.print(f"Total dividends: [bold]{total_dividends:.6f}[/bold]")
    else:
        console.print(f"Metagraph: [dim]{metagraph_data}[/dim]")
