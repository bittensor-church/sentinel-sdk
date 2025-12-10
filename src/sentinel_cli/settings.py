"""CLI settings and constants."""

from contextvars import ContextVar
from enum import Enum


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    RAW = "raw"


# Global context for CLI settings
output_format: ContextVar[OutputFormat] = ContextVar("output_format", default=OutputFormat.TABLE)
