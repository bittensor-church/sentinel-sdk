"""Block CLI commands."""

from typing import Annotated

import bittensor  # type: ignore[import-untyped]
import typer
from bittensor.core.chain_data import MetagraphInfo  # type: ignore[import-untyped]
from rich.table import Table

from sentinel.v1.dto import HyperparametersDTO
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


def _build_metagraph_table(metagraph: MetagraphInfo) -> Table:
    """Build a table displaying metagraph neuron data."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("UID", style="cyan", justify="right")
    table.add_column("Stake", justify="right")
    table.add_column("Trust", justify="right")
    table.add_column("Consensus", justify="right")
    table.add_column("Incentive", justify="right")
    table.add_column("Dividends", justify="right")
    table.add_column("Emission", justify="right")
    table.add_column("VPermit", justify="center")
    table.add_column("Updated", justify="right")
    table.add_column("Active", justify="center")
    table.add_column("Hotkey")

    for uid in range(len(metagraph.hotkeys)):
        stake = metagraph.total_stake[uid]
        trust = metagraph.trust[uid]
        consensus = metagraph.consensus[uid]
        incentive = metagraph.incentives[uid]
        dividend = metagraph.dividends[uid]
        emission = metagraph.emission[uid]
        vpermit = metagraph.validator_permit[uid]
        last_update = metagraph.last_update[uid]
        active = metagraph.active[uid]
        hotkey = metagraph.hotkeys[uid]

        hotkey_display = hotkey[:HOTKEY_DISPLAY_LENGTH] + "..." if len(hotkey) > HOTKEY_DISPLAY_LENGTH else hotkey

        table.add_row(
            str(uid),
            f"{stake.tao:.4f}",
            f"{trust:.5f}",
            f"{consensus:.5f}",
            f"{incentive:.5f}",
            f"{dividend:.5f}",
            f"{emission.tao:.5f}",
            "[green]✓[/green]" if vpermit else "[dim]-[/dim]",
            str(last_update),
            "[green]✓[/green]" if active else "[dim]-[/dim]",
            hotkey_display,
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
    elif is_json_output():
        output_json(
            {
                "block_number": resolved_block,
                "netuid": netuid,
                "name": metagraph_data.name,
                "symbol": metagraph_data.symbol,
                "neurons": [
                    {
                        "uid": uid,
                        "hotkey": metagraph_data.hotkeys[uid],
                        "coldkey": metagraph_data.coldkeys[uid],
                        "stake": float(metagraph_data.total_stake[uid].tao),
                        "trust": metagraph_data.trust[uid],
                        "consensus": metagraph_data.consensus[uid],
                        "incentive": metagraph_data.incentives[uid],
                        "dividends": metagraph_data.dividends[uid],
                        "emission": float(metagraph_data.emission[uid].tao),
                        "validator_permit": metagraph_data.validator_permit[uid],
                        "last_update": metagraph_data.last_update[uid],
                        "active": metagraph_data.active[uid],
                    }
                    for uid in range(len(metagraph_data.hotkeys))
                ],
            },
        )
    else:
        console.print(f"Name: [cyan]{metagraph_data.name}[/cyan] ({metagraph_data.symbol})")
        console.print(f"N: [cyan]{len(metagraph_data.hotkeys)}[/cyan]")
        console.print()
        console.print(_build_metagraph_table(metagraph_data))


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
            str(record.dividend),
            # f"{record.dividend:.6f}",
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


def _build_hyperparams_table(hyperparams_data: HyperparametersDTO) -> Table:
    """Build a table displaying hyperparameters."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Parameter", style="dim")
    table.add_column("Value")

    for field, value in hyperparams_data.model_dump().items():
        table.add_row(field, str(value))

    return table


@subnet.command()
def hyperparams(
    ctx: typer.Context,
) -> None:
    """Read hyperparameters for a subnet at a specific block."""
    netuid = ctx.obj["netuid"]
    block_number = ctx.obj["block_number"]
    network = ctx.obj["network"]

    provider = bittensor_provider(network_uri=network)
    resolved_block = resolve_block_number(provider, block_number)

    subnet_instance = Subnet(provider, netuid, resolved_block)
    hyperparams_data = subnet_instance.hyperparameters

    if is_json_output():
        output_json(
            {
                "block_number": resolved_block,
                "netuid": netuid,
                **hyperparams_data.model_dump(),
            },
        )
    else:
        console.print(f"Block: [cyan]{resolved_block}[/cyan]")
        console.print(f"Subnet: [cyan]{netuid}[/cyan]")
        console.print()
        console.print(_build_hyperparams_table(hyperparams_data))
