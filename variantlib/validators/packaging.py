from __future__ import annotations

from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement

from variantlib.errors import ValidationError


def validate_requirement_str(dependency_str: str) -> None:
    try:
        _ = Requirement(dependency_str)
    except (InvalidRequirement, ValueError) as e:
        raise ValidationError from e
