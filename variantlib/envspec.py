"""Support for processing "variants" environment specifier"""

from __future__ import annotations

from itertools import chain

from packaging.markers import Op
from packaging.markers import Value
from packaging.markers import Variable
from packaging.requirements import Requirement
from variantlib.errors import InvalidVariantEnvSpecError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature


def evaluate_variant_requirements(
    requirements: list[str], variant_desc: VariantDescription
) -> list[str]:
    """
    Evaluate variant requirements in specified requirement strings

    Evaluate the variant requirements found in the specified requirement
    strings against the described variant,  Returns the requirements
    modified according to the evaluated variants, with other environment
    specifiers unchanged.
    """

    all_values = frozenset(
        chain.from_iterable(
            (
                x.to_str(),
                VariantFeature(x.namespace, x.feature).to_str(),
                x.namespace,
            )
            for x in variant_desc.properties
        )
    )

    new_requirements = []
    for req in requirements:
        parsed_req = Requirement(req)
        marker = parsed_req.marker
        # TODO: support more complex markers
        if marker is None or len(marker._markers) != 1:  # noqa: SLF001
            new_requirements.append(req)
            continue

        parsed_marker = marker._markers[0]  # noqa: SLF001
        assert isinstance(parsed_marker[1], Op)
        # "variants OP ..." is invalid
        if (
            isinstance(parsed_marker[0], Variable)
            and str(parsed_marker[0]) == "variants"
        ):
            raise InvalidVariantEnvSpecError(
                "'variants' marker can only be used in \"'foo' in variants\" "
                "expressions"
            )
        # we are only interested in "... OP variants"
        if not (
            isinstance(parsed_marker[2], Variable)
            and str(parsed_marker[2]) == "variants"
        ):
            new_requirements.append(req)
            continue
        # only "in" operator is allowed
        if str(parsed_marker[1]) != "in" or not isinstance(parsed_marker[0], Value):
            raise InvalidVariantEnvSpecError(
                "'variants' marker can only be used in \"'foo' in variants\" "
                "expressions"
            )

        if str(parsed_marker[0]) in all_values:
            parsed_req.marker = None
            new_requirements.append(str(parsed_req))

    return new_requirements
