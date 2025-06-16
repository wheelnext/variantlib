from __future__ import annotations

import contextlib

from packaging.specifiers import InvalidSpecifier
from packaging.specifiers import SpecifierSet
from variantlib.constants import VALIDATION_VALUE_STR_REGEX
from variantlib.constants import VALIDATION_VALUE_VSPEC_REGEX
from variantlib.validators.base import validate_matches_re


def validate_variant_property_value(value: str) -> None:
    regex = VALIDATION_VALUE_STR_REGEX
    with contextlib.suppress(InvalidSpecifier):
        SpecifierSet(value)
        regex = VALIDATION_VALUE_VSPEC_REGEX

    validate_matches_re(value, regex)
