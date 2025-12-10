"""Shared output utilities for CLI commands."""

import json
from collections.abc import Iterable
from typing import Any

import typer
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sentinel_cli.settings import OutputFormat, output_format

# Shared console instance
console = Console()

# Display constants
MAX_VALUE_LENGTH = 80
MAX_ATTR_LENGTH = 60


def is_json_output() -> bool:
    """Check if JSON output format is selected."""
    return output_format.get() == OutputFormat.JSON


def is_raw_output() -> bool:
    """Check if raw output format is selected."""
    return output_format.get() == OutputFormat.RAW


def output_json(data: dict) -> None:
    """Output data as formatted JSON."""
    typer.echo(json.dumps(data, indent=2, default=str))


def output_error(message: str) -> None:
    """Output error message in appropriate format."""
    if is_json_output():
        output_json({"error": message})
    else:
        console.print(f"[red]Error:[/red] {message}")


def truncate(value: str, max_length: int = MAX_VALUE_LENGTH) -> str:
    """Truncate string if it exceeds max length."""
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value


def format_block_id(block_number: int, index: int) -> str:
    """Format a block-relative ID (e.g., '6978898-0005')."""
    return f"{block_number}-{index:04d}"


def get_status_style(status: str | None) -> tuple[str, str]:
    """Get status display text and Rich style."""
    if status == "success":
        return "✓ success", "green"
    if status == "failed":
        return "✗ failed", "red"
    return "unknown", "yellow"


def build_header_text(*, hash_value: str, signer: str | None = None) -> Text:
    """Build a standard header text with hash and optional signer."""
    header = Text()
    header.append("Hash: ", style="dim")
    header.append(f"{hash_value}\n")
    if signer:
        header.append("Signer: ", style="dim")
        header.append(signer)
    return header


def build_panel_title(
    item_id: str,
    label: str,
    status: str | None = None,
) -> Text:
    """Build a styled panel title with ID, label, and status."""
    title = Text()
    title.append(f"[{item_id}] ", style="cyan")
    title.append(f"{label} ", style="bold")
    if status is not None:
        status_text, status_style = get_status_style(status)
        title.append(status_text, style=status_style)
    return title


def build_key_value_table(
    rows: Iterable[tuple[str, Any]],
    *,
    key_header: str = "Key",
    value_header: str = "Value",
    max_value_length: int = MAX_VALUE_LENGTH,
) -> Table:
    """Build a simple key-value table."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column(key_header, style="dim")
    table.add_column(value_header)
    for key, value in rows:
        table.add_row(key, truncate(str(value), max_value_length))
    return table


def render_panel(
    title: Text,
    *renderables: RenderableType,
) -> None:
    """Render a panel with the given title and content."""
    content = renderables[0] if len(renderables) == 1 else Group(*renderables)
    console.print(Panel(content, title=title, title_align="left", border_style="dim"))
