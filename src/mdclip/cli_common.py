"""Common CLI infrastructure for mdclip."""

import json
import logging
import sys
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Any, Optional


class ExitCode(IntEnum):
    """Standard exit codes."""

    SUCCESS = 0
    ERROR = 1
    USAGE_ERROR = 2


@dataclass
class OperationResult:
    """Structured result for JSON output."""

    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
    errors: Optional[list[str]] = None

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def setup_logging(
    verbose: bool = False,
    quiet: bool = False,
    name: str = "mdclip",
) -> logging.Logger:
    """Configure logging based on verbosity flags."""
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    return logging.getLogger(name)


def output_result(
    result: OperationResult,
    json_mode: bool = False,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Output result in appropriate format."""
    if json_mode:
        print(result.to_json())
    else:
        if logger:
            if result.success:
                logger.info(result.message)
            else:
                logger.error(result.message)
        else:
            if result.success:
                print(result.message, file=sys.stderr)
            else:
                print(f"Error: {result.message}", file=sys.stderr)
