from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

from variantlib import __package_name__
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from variantlib.plugins.loader import BasePluginLoader


logger = logging.getLogger(__name__)

res_map = {
    False: "invalid",
    True: "valid",
    None: "no-plugin",
}


def validate_property(args: list[str], plugin_loader: BasePluginLoader) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} plugins validate-property",
        description="CLI interface to validate properties",
    )
    parser.add_argument(
        "property",
        nargs="+",
        type=VariantProperty.from_str,
        help="One or more properties to validate",
    )

    parsed_args = parser.parse_args(args)
    validation_result = plugin_loader.validate_properties(parsed_args.property)
    for vprop in parsed_args.property:
        sys.stdout.write(
            f"{vprop.to_str()} : {res_map[validation_result.results[vprop]]}\n"
        )
