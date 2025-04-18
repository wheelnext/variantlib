"""Support for processing "variants" environment specifier"""

from __future__ import annotations

import re
from itertools import chain
from typing import TYPE_CHECKING

from variantlib.errors import InvalidVariantEnvSpecError

if TYPE_CHECKING:
    from variantlib.models.variant import VariantProperty


TRUE_STR = "python_version != '0'"
FALSE_STR = "python_version == '0'"

VARIANT_EXPR_RE = re.compile(
    # 'value' in variants
    r"(?P<quote>[\"'])(?P<value>.*)(?P=quote) \s* (?P<neg>not \s+)? in \s+ variants\b",
    re.VERBOSE,
)

VARIANT_ERROR_RE = re.compile(
    r"("
    # variants OP ...
    r"\b variants \s* ([~=!<>] | \s (not \s+)? in) |"
    # ... OP variants ; where OP != "in"
    r"[=!<>] \s* variants\b"
    r")",
    re.VERBOSE,
)


def evaluate_variant_requirements(
    requirements: list[str], variant_properties: list[VariantProperty]
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
                x.feature_object.to_str(),
                x.namespace,
            )
            for x in variant_properties
        )
    )

    new_requirements = []
    for req in requirements:

        def repl(match: re.Match) -> str:
            if (match.group("neg") is None) == (match.group("value") in all_values):
                return TRUE_STR
            return FALSE_STR

        base_req, sep, marker = req.partition(";")
        if marker:
            if VARIANT_ERROR_RE.search(marker) is not None:
                raise InvalidVariantEnvSpecError(
                    "'variants' marker can only be used in \"'foo' in variants\" "
                    "expressions"
                )
            marker = VARIANT_EXPR_RE.sub(repl, marker)
        new_requirements.append(base_req + sep + marker)

    return new_requirements
