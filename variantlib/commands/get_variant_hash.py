from __future__ import annotations

import argparse
import sys

from variantlib import __package_name__
from variantlib.api import VariantDescription
from variantlib.api import VariantProperty


def get_variant_hash(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} get-variant-hash",
        description="Compute the variant hash of a set of variant properties.",
    )

    parser.add_argument(
        "-p",
        "--property",
        dest="properties",
        type=VariantProperty.from_str,
        action="extend",
        nargs="+",
        help=(
            "Variant Properties to add to the Wheel Variant, can be repeated as many "
            "times as needed"
        ),
        default=[],
    )

    parsed_args = parser.parse_args(args)

    _print_variant_hash(properties=parsed_args.properties)


def _print_variant_hash(properties: list[VariantProperty]) -> None:
    # Transform properties into a VariantDescription
    vdesc = VariantDescription(properties=properties)

    sys.stdout.write(f"{vdesc.hexdigest}\n")
