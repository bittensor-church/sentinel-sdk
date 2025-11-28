"""Main CLI application with Typer."""

from typing import Annotated

import typer

from sentinel_cli.commands import block
from sentinel_cli.commands.events import events
from sentinel_cli.commands.extrinsics import extrinsics
from sentinel_cli.commands.hyperparams import hyperparams
from sentinel_cli.settings import OutputFormat, output_format

app = typer.Typer(
    name="sentinel",
    help="Sentinel CLI - Blockchain data extraction and monitoring tool.",
    no_args_is_help=True,
)


@app.callback()
def main_callback(
    fmt: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format.",
            case_sensitive=False,
        ),
    ] = OutputFormat.TABLE,
) -> None:
    """Global options for all commands."""
    output_format.set(fmt)


# Register subcommand groups
app.add_typer(block.app, name="block")

# Register top-level commands
app.command()(extrinsics)
app.command()(events)
app.command()(hyperparams)


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
