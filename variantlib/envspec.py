"""Support for processing "variants" environment specifier"""

from __future__ import annotations

import re
from itertools import chain

from packaging.requirements import Requirement
from variantlib.errors import InvalidVariantEnvSpecError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature

TRUE_STR = "python_version != '0'"
FALSE_STR = "python_version == '0'"

VARIANT_EXPR_RE = re.compile(
    # 'value' in variants
    r"(?P<quote>[\"'])(?P<value>.*)(?P=quote) \s* (?P<neg>not \s+)? in \s+ variants\b",
    re.VERBOSE,
)

VARIANT_ERROR_RES = [
    # variants OP ...
    re.compile(r"\bvariants \s* [=!<>]", re.VERBOSE),
    # variants [not] in ...
    re.compile(r"\bvariants \s+ (not \s+)? in", re.VERBOSE),
    # ... OP variants ; where OP != "in"
    re.compile(r"[=!<>] \s* variants", re.VERBOSE),
]


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

        def repl(match: re.Match) -> str:
            if (match.group("neg") is None) == (match.group("value") in all_values):
                return TRUE_STR
            return FALSE_STR

        if parsed_req.marker is not None:
            for error_re in VARIANT_ERROR_RES:
                if error_re.search(str(parsed_req.marker)) is not None:
                    raise InvalidVariantEnvSpecError(
                        "'variants' marker can only be used in \"'foo' in variants\" "
                        "expressions"
                    )

            new_marker = VARIANT_EXPR_RE.sub(repl, str(parsed_req.marker))
            # alter the requirement only if we actually changed anything
            if new_marker != str(parsed_req.marker):
                parsed_req.marker = new_marker
                new_requirements.append(str(parsed_req))
                continue
        new_requirements.append(req)

    return new_requirements
