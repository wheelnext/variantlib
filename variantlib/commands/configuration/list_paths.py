from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from variantlib.configuration import get_configuration_files

try:
    from tzlocal import get_localzone
except ImportError:

    def get_localzone() -> None:
        return None


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def list_paths(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="list-paths",
        description="CLI interface to list configuration paths",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print additional information about files found",
    )

    parsed_args = parser.parse_args(args)

    for file_id, file_path in get_configuration_files().items():
        details = ""
        if parsed_args.verbose:
            try:
                file_stat = file_path.stat()
                file_mtime = datetime.fromtimestamp(
                    file_stat.st_mtime, tz=get_localzone()
                )
                details = f" ({file_stat.st_size} bytes, last modified: {file_mtime})"
            except FileNotFoundError:
                details = " (not found)"
        sys.stdout.write(f"{file_id.name}: {file_path}{details}\n")
