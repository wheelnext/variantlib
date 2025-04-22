from __future__ import annotations

import logging
from typing import Any

from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.validators import validate_variants_json

logger = logging.getLogger(__name__)


def unpack_variants_json(
    variants_json: dict[str, Any],
) -> list[VariantDescription]:
    # Input Validation
    validate_variants_json(variants_json)

    result = []
    for vhash, data in variants_json[VARIANTS_JSON_VARIANT_DATA_KEY].items():
        vdesc = VariantDescription.from_dict(data)
        if vhash != vdesc.hexdigest:
            raise ValidationError(
                f"Variant hash mismatch: `{vhash=}` != `{vdesc.hexdigest=}`"
            )
        result.append(vdesc)

    return result
