"""Subnet CLI commands."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Annotated, NoReturn

import bittensor
import typer
from rich.table import Table

if TYPE_CHECKING:
    from sentinel.v1.dto import HyperparametersDTO
    from sentinel.v1.services.extractors.metagraph.dto import FullSubnetSnapshot

from async_substrate_interface.errors import StateDiscardedError  # type: ignore[import-untyped]
from pylon_client.artanis import BasePylonException

from sentinel.v1.models.subnet import Subnet
from sentinel.v1.providers.base import BlockchainProvider
from sentinel.v1.providers.bittensor import ARCHIVE_NODE_URI, bittensor_provider
from sentinel.v1.providers.pylon import pylon_provider
from sentinel.v1.services.extractors.dividends import DividendRecord, DividendsExtractor
from sentinel_cli.blocks import resolve_block_number
from sentinel_cli.output import console, is_json_output, is_raw_output, output_json

PROVIDER_BITTENSOR = "bittensor"
PROVIDER_PYLON = "pylon"

HOTKEY_DISPLAY_LENGTH = 16


subnet = typer.Typer(
    name="subnet",
    help="Subnet-related commands.",
    no_args_is_help=True,
)


def _handle_pylon_error(exc: BasePylonException) -> NoReturn:
    """Display a clean error message for Pylon connection/request failures."""
    cause = exc.__cause__
    if cause:
        console.print(f"[red]Error:[/red] Failed to connect to Pylon: {cause}")
    else:
        console.print(f"[red]Error:[/red] Pylon request failed: {exc}")
    console.print()
    console.print("Make sure the Pylon service is running and the URL is correct.")
    console.print("  [dim]--network http://localhost:8090[/dim]")
    raise typer.Exit(1) from None


def _create_provider(provider_type: str, network: str | None) -> BlockchainProvider:
    """Create the appropriate blockchain provider based on type."""
    if provider_type == PROVIDER_PYLON:
        return pylon_provider(url=network)
    return bittensor_provider(network_uri=network)


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
    mechid: Annotated[
        int | None,
        typer.Option("--mech-id", "-m", help="Mechanism ID.", show_default=True),
    ] = None,
    lite: Annotated[
        bool,
        typer.Option("--lite", "-l", help="Use lite metagraph (excludes weights and bonds)."),
    ] = False,
    provider: Annotated[
        str,
        typer.Option("--provider", "-p", help="Blockchain provider to use (bittensor or pylon)."),
    ] = PROVIDER_BITTENSOR,
) -> None:
    """Subnet-related commands."""
    ctx.ensure_object(dict)
    ctx.obj["netuid"] = netuid
    ctx.obj["block_number"] = block_number
    ctx.obj["network"] = network
    ctx.obj["mechid"] = mechid
    ctx.obj["lite"] = lite
    ctx.obj["provider"] = _create_provider(provider, network)


def _print_elapsed_time(start_time: float) -> None:
    """Print elapsed time since start_time."""
    elapsed = time.perf_counter() - start_time
    console.print(f"\n[dim]Completed in {elapsed:.2f}s[/dim]")


def _build_snapshot_dividends_table(snapshot: FullSubnetSnapshot) -> Table:
    """Build a table displaying dividends by UID from FullSubnetSnapshot."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("UID", style="cyan", justify="right")
    table.add_column("Hotkey")
    table.add_column("Dividend", justify="right")

    for neuron in snapshot.neurons:
        hotkey = neuron.neuron.hotkey.hotkey if neuron.neuron.hotkey else ""
        hotkey_display = hotkey[:HOTKEY_DISPLAY_LENGTH] + "..." if len(hotkey) > HOTKEY_DISPLAY_LENGTH else hotkey

        # Sum dividends across all mechanisms
        total_dividend = sum(m.dividend for m in neuron.mechanisms)

        table.add_row(
            str(neuron.uid),
            hotkey_display,
            f"{total_dividend:.6f}",
        )

    return table


def _build_snapshot_metagraph_table(snapshot: FullSubnetSnapshot) -> Table:
    """Build a table displaying metagraph neuron data from FullSubnetSnapshot."""
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
    table.add_column("Registered", justify="right")
    table.add_column("Active", justify="center")
    table.add_column("Hotkey")

    for neuron in snapshot.neurons:
        hotkey = neuron.neuron.hotkey.hotkey if neuron.neuron.hotkey else ""
        hotkey_display = hotkey[:HOTKEY_DISPLAY_LENGTH] + "..." if len(hotkey) > HOTKEY_DISPLAY_LENGTH else hotkey

        # Get mechanism 0 metrics (or sum across mechanisms)
        mech = neuron.mechanisms[0] if neuron.mechanisms else None
        incentive = mech.incentive if mech else 0.0
        dividend = mech.dividend if mech else 0.0
        consensus = mech.consensus if mech else 0.0
        last_update = mech.last_update if mech else 0

        table.add_row(
            str(neuron.uid),
            f"{neuron.total_stake:.4f}",
            f"{neuron.trust:.5f}",
            f"{consensus:.5f}",
            f"{incentive:.5f}",
            f"{dividend:.5f}",
            f"{neuron.emissions:.5f}",
            "[green]✓[/green]" if neuron.is_validator else "[dim]-[/dim]",
            str(last_update),
            str(neuron.block_at_registration),
            "[green]✓[/green]" if neuron.is_active else "[dim]-[/dim]",
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
    start_time = time.perf_counter()

    netuid = ctx.obj["netuid"]
    block_number = ctx.obj["block_number"]
    mechid = ctx.obj["mechid"]
    lite = ctx.obj["lite"]
    provider: BlockchainProvider = ctx.obj["provider"]

    try:
        resolved_block = resolve_block_number(provider, block_number)
    except BasePylonException as e:
        _handle_pylon_error(e)

    try:
        subnet_instance = Subnet(provider, netuid, resolved_block, mechid, lite=lite)
        snapshot = subnet_instance.metagraph
    except BasePylonException as e:
        _handle_pylon_error(e)
    except StateDiscardedError:
        console.print(
            f"[red]Error:[/red] Block [cyan]{resolved_block}[/cyan] is too old and its state has been discarded.",
        )
        console.print()
        console.print("To query historical blocks, use an archive node:")
        console.print(f"  [dim]--network {ARCHIVE_NODE_URI}[/dim]")
        console.print()
        console.print("Example:")
        console.print(
            f"  [dim]sentinel subnet --netuid {netuid} --block {resolved_block} "
            f"--network {ARCHIVE_NODE_URI} metagraph[/dim]",
        )
        raise typer.Exit(1) from None

    if not snapshot:
        console.print("[red]Error:[/red] Could not retrieve metagraph data.")
        raise typer.Exit(1)

    console.print(f"Block: [cyan]{resolved_block}[/cyan]")
    console.print(f"Subnet: [cyan]{netuid}[/cyan] - {snapshot.subnet.name}")
    console.print(
        f"Neurons: [cyan]{snapshot.neuron_count}[/cyan] "
        f"(Validators: {snapshot.validator_count}, Miners: {snapshot.miner_count})",
    )
    console.print(f"Mechanisms: [cyan]{snapshot.mechanism_count}[/cyan]")
    console.print()

    if view == "dividends":
        if is_json_output():
            output_json(
                {
                    "block_number": resolved_block,
                    "netuid": netuid,
                    "dividends": [
                        {
                            "uid": neuron.uid,
                            "hotkey": neuron.neuron.hotkey.hotkey if neuron.neuron.hotkey else "",
                            "dividend": sum(m.dividend for m in neuron.mechanisms),
                        }
                        for neuron in snapshot.neurons
                    ],
                }
            )
        else:
            console.print(_build_snapshot_dividends_table(snapshot))
            total_dividends = sum(sum(m.dividend for m in n.mechanisms) for n in snapshot.neurons)
            console.print()
            console.print(f"Total dividends: [bold]{total_dividends:.6f}[/bold]")
    elif is_json_output():
        output_json(
            {
                "block_number": resolved_block,
                "netuid": netuid,
                "subnet_name": snapshot.subnet.name,
                "neuron_count": snapshot.neuron_count,
                "validator_count": snapshot.validator_count,
                "miner_count": snapshot.miner_count,
                "total_stake": snapshot.total_stake,
                "mechanism_count": snapshot.mechanism_count,
                "neurons": [
                    {
                        "uid": neuron.uid,
                        "hotkey": neuron.neuron.hotkey.hotkey if neuron.neuron.hotkey else "",
                        "coldkey": (
                            neuron.neuron.hotkey.coldkey.coldkey
                            if neuron.neuron.hotkey and neuron.neuron.hotkey.coldkey
                            else ""
                        ),
                        "stake": neuron.total_stake,
                        "normalized_stake": neuron.normalized_stake,
                        "trust": neuron.trust,
                        "rank": neuron.rank,
                        "emissions": neuron.emissions,
                        "is_validator": neuron.is_validator,
                        "is_active": neuron.is_active,
                        "is_immune": neuron.is_immune,
                        "axon_address": neuron.axon_address,
                        "mechanisms": [
                            {
                                "mech_id": m.mech_id,
                                "incentive": m.incentive,
                                "dividend": m.dividend,
                                "consensus": m.consensus,
                                "validator_trust": m.validator_trust,
                                "weights_sum": m.weights_sum,
                                "last_update": m.last_update,
                            }
                            for m in neuron.mechanisms
                        ],
                    }
                    for neuron in snapshot.neurons
                ],
            },
        )
    elif is_raw_output():
        console.print(snapshot.model_dump_json(indent=2))
    else:
        console.print(_build_snapshot_metagraph_table(snapshot))
        console.print()
        console.print(f"Total stake: [bold]{snapshot.total_stake:.4f}[/bold] TAO")

    _print_elapsed_time(start_time)


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
    start_time = time.perf_counter()

    netuid = ctx.obj["netuid"]
    block_number = ctx.obj["block_number"]
    network = ctx.obj["network"]
    mechid = ctx.obj["mechid"]
    provider: BlockchainProvider = ctx.obj["provider"]

    try:
        resolved_block = resolve_block_number(provider, block_number)
    except BasePylonException as e:
        _handle_pylon_error(e)

    subtensor = bittensor.Subtensor(network=network)
    extractor = DividendsExtractor(subtensor, resolved_block, netuid, mechid)
    result = extractor.extract()

    if not result.records:
        console.print("[yellow]No dividend data found.[/yellow]")
        raise typer.Exit(1)

    yuma_version = "Yuma3" if result.yuma3_enabled else "Yuma2"

    console.print(f"Block: [cyan]{resolved_block}[/cyan]")
    console.print(f"Subnet: [cyan]{netuid}[/cyan]")
    console.print(f"Mech ID: [cyan]{result.mechid}[/cyan]")
    console.print(f"Consensus: [cyan]{yuma_version}[/cyan]")
    console.print()
    console.print(_build_manual_dividends_table(result.records))
    total_dividends = sum(r.dividend for r in result.records)
    console.print()
    console.print(f"Total dividends: [bold]{total_dividends:.6f}[/bold]")

    _print_elapsed_time(start_time)


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
    start_time = time.perf_counter()

    netuid = ctx.obj["netuid"]
    block_number = ctx.obj["block_number"]
    provider: BlockchainProvider = ctx.obj["provider"]

    try:
        resolved_block = resolve_block_number(provider, block_number)
    except BasePylonException as e:
        _handle_pylon_error(e)

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

    _print_elapsed_time(start_time)
