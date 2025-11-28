"""CLI settings and constants."""

from contextvars import ContextVar
from enum import Enum

MAX_VALUE_DISPLAY_LENGTH = 120


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"


# Global context for CLI settings
output_format: ContextVar[OutputFormat] = ContextVar("output_format", default=OutputFormat.TABLE)
