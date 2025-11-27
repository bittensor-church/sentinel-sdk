"""Main CLI application with Typer."""

import typer

from sentinel_cli.commands import block

app = typer.Typer(
    name="sentinel",
    help="Sentinel CLI - Blockchain data extraction and monitoring tool.",
    no_args_is_help=True,
)

# Register subcommand groups
app.add_typer(block.app, name="block")


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
